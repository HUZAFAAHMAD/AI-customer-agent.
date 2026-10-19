"""
SQLite FTS5-backed keyword retriever.

REPLACES: the old pickled in-memory `BM25Retriever` (rank_bm25 loaded fully
into RAM, rebuilt from a .pkl file whenever the cache was missing/stale).

Why this was a real problem:
  - Every restart either re-loads the whole corpus into memory from the
    pickle, or (on a cache miss) pulls EVERY document out of Chroma and
    rebuilds the BM25 index from scratch in-process.
  - There is no incremental "add one more document" path — ingesting a
    single new PDF meant rebuilding the entire index.
  - A pickle file with model/index objects is fragile across library
    version bumps (pickle format changes silently break it).

SQLite FTS5 fixes all three: it's a persisted, disk-backed, incrementally
updatable full-text index, and it ships in Python's standard library
(no extra native dependency to install or version-pin).

SCALING UPDATE (1,000+ Pages):
  - Stopword filtering in `sanitize_fts_query`: on a 1,000-page document,
    conversational words ("what", "is", "the", "for") appear on every page.
    Filtering them prevents stopword pollution from crowding out actual
    technical keywords (warranties, policies, SKUs).
  - Preserves exact alphanumeric codes and hyphenated tokens (e.g. SKU-12-EXP,
    ERR-808, DRONE-REP-909) so precision product/error searches succeed.
"""

import re
import sqlite3
from typing import List, Optional, Set

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.retrievers import BaseRetriever

# Common English conversational stopwords that degrade BM25 scoring at scale
FTS_STOPWORDS: Set[str] = {
    "a",
    "an",
    "and",
    "are",
    "as",
    "at",
    "be",
    "by",
    "for",
    "from",
    "has",
    "he",
    "in",
    "is",
    "it",
    "its",
    "of",
    "on",
    "or",
    "that",
    "the",
    "to",
    "was",
    "were",
    "will",
    "with",
    "what",
    "how",
    "why",
    "when",
    "where",
    "who",
    "which",
    "can",
    "could",
    "should",
    "would",
    "do",
    "does",
    "did",
    "i",
    "my",
    "me",
    "you",
    "your",
    "we",
    "our",
    "they",
    "them",
    "their",
    "this",
    "these",
    "those",
    "tell",
    "about",
}


def sanitize_fts_query(text: str) -> str:
    """
    Turn free-form customer text into a safe, high-precision FTS5 MATCH expression.

    1. Preserves hyphenated technical terms / SKUs (e.g., "SKU-CRYO-FLUSH", "ERR-808").
    2. Strips common conversational stopwords so 1,000-page documents aren't flooded
       by matches on "what", "is", "the", "for".
    3. Falls back safely to all tokens if every word happens to be a stopword.
    4. Quotes each token individually and joins with OR for candidate recall.
    """
    # Extract hyphenated alphanumeric codes or standard words
    tokens = re.findall(
        r"[A-Za-z0-9]+(?:-[A-Za-z0-9]+)*", text
    )  # it just make token from actual text just little thing it preserve "BM-3838"
    if not tokens:
        return '""'  # matches nothing, but never raises a MATCH syntax error

    # Filter out stopwords if we have meaningful domain keywords left
    filtered = [t for t in tokens if t.lower() not in FTS_STOPWORDS]
    target_tokens = filtered if filtered else tokens

    # Quote each token safely for SQLite FTS5 MATCH syntax
    clean_terms = []
    for t in target_tokens:
        clean_t = t.replace('"', '""')
        clean_terms.append(f'"{clean_t}"')

    return " OR ".join(clean_terms)


class SQLiteFTS5Retriever(BaseRetriever):
    """
    Drop-in BaseRetriever replacement for BM25Retriever, backed by a
    persisted SQLite FTS5 virtual table instead of an in-memory pickle.

    Plugs directly into EnsembleRetriever alongside the Chroma semantic
    retriever, exactly like the old BM25Retriever did — no changes needed
    anywhere else that consumes `hybrid_retriever`.
    """

    db_path: str = "./fts5_index.db"
    k: int = 50

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path)
        # idempotent — cheap no-op after the first call once the table exists
        conn.execute(  # if table already exist and we run it multiple times no new table will form
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS kb_fts USING fts5(
                content, source UNINDEXED, page UNINDEXED, section UNINDEXED,
                tokenize='porter unicode61'
            )
            """
        )
        return conn

    def add_documents(self, docs: List[Document]) -> None:
        """Index new chunks. Called from add_document.py at ingestion time,
        right alongside kb_vectorstore.add_documents, so both indexes
        (semantic + keyword) always stay in sync with each other."""
        if not docs:
            return
        conn = self._get_connection()
        with conn:
            conn.executemany(
                "INSERT INTO kb_fts (content, source, page, section) VALUES (?, ?, ?, ?)",
                [
                    (
                        d.page_content,
                        str(d.metadata.get("source", "")),
                        str(d.metadata.get("page", "")),
                        str(d.metadata.get("section", "")),
                    )
                    for d in docs
                ],
            )
        conn.close()

    def clear(self) -> None:
        """Wipe the index — use when you want to force a full rebuild."""
        conn = self._get_connection()
        with conn:
            conn.execute("DELETE FROM kb_fts")
        conn.close()

    def count(self) -> int:
        conn = self._get_connection()
        n = conn.execute("SELECT COUNT(*) FROM kb_fts").fetchone()[0]
        conn.close()
        return n

    def _get_relevant_documents(
        self,
        query: str,
        *,
        run_manager: Optional[CallbackManagerForRetrieverRun] = None,
    ) -> List[Document]:
        fts_query = sanitize_fts_query(query)
        conn = self._get_connection()
        try:
            # NOTE: SQLite's bm25() returns MORE NEGATIVE = MORE RELEVANT
            # (opposite sign convention from classic BM25 scores), so the
            # best match sorts first with ORDER BY ... ASC, not DESC.
            cursor = conn.execute(
                """
                SELECT content, source, page, section, bm25(kb_fts) AS score
                FROM kb_fts
                WHERE kb_fts MATCH ?
                ORDER BY score ASC
                LIMIT ?
                """,
                (fts_query, self.k),
            )
            rows = (
                cursor.fetchall()
            )  # it will fetch data of one document in the form of rows like "2","page.content",etc
        except sqlite3.OperationalError:
            # belt-and-braces: sanitize_fts_query should already prevent
            # this, but a keyword-search edge case should never take down
            # the whole pipeline
            rows = []
        conn.close()

        return [
            Document(
                page_content=row[0],
                metadata={
                    "source": row[1],
                    "page": row[2],
                    "section": row[3],
                    "bm25_score": row[4],
                },
            )
            for row in rows
        ]
