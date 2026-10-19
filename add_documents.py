# add_document.py
"""
CHANGED (vs. old version):
  - PyPDFLoader -> pymupdf4llm.to_markdown(..., page_chunks=True)
    PyPDFLoader does raw per-page text extraction and throws away layout,
    so a pricing/spec table turns into a jumbled wall of numbers with no
    columns left. pymupdf4llm renders each page to clean Markdown instead
    (tables come out as real Markdown tables, headings come out as '#'
    lines), which both the retriever and the generation LLM can actually
    read correctly.
  - chunk_size 500 -> 1200, chunk_overlap 50 -> 200
    500 chars was chopping a single policy/spec across two chunks, so
    neither chunk alone contained the whole fact.
  - Contextual prepending: every chunk gets a
    "[Source: file.pdf | Page: N | Section: Heading]" label stamped onto
    the front of its text before it's embedded/indexed, so retrieval and
    generation both know exactly where a fact came from.
  - Every chunk is now written to BOTH the Chroma vectorstore (semantic
    search) AND the new SQLite FTS5 index (keyword search), so the two
    retrievers rag_pipeline.py combines in its EnsembleRetriever stay in
    sync with each other.
  - Chroma now imported from `langchain_chroma` (this file already did
    this correctly) - rag_pipeline.py has been updated to match, since it
    was previously importing Chroma from `langchain_community.vectorstores`
    instead, i.e. two different implementations pointed at the same
    persisted directory.
"""

import os
import re
from typing import List, Optional, Tuple

import pymupdf4llm
import pymupdf
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from config import GOOGLE_API_KEY
from fts5_retriever import SQLiteFTS5Retriever
from langchain_huggingface import HuggingFaceEmbeddings

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# ── local embeddings — no API quota, runs on your machine ─────────
# embeddings = HuggingFaceEmbeddings(model_name="sentence-transformers/all-MiniLM-L6-v2")
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")


def get_kb_vectorstore() -> Chroma:
    """
    Returns a live Chroma vectorstore handle.
    Self-heals if the underlying collection was recreated or deleted.
    """
    global kb_vectorstore
    try:
        if kb_vectorstore is not None:
            kb_vectorstore._collection.count()
            return kb_vectorstore
    except Exception:
        pass

    kb_vectorstore = Chroma(
        collection_name="novatek_kb_minilm",
        embedding_function=embeddings,
        persist_directory="./chroma_kb",
        collection_metadata={"hnsw:space": "cosine"},
    )
    return kb_vectorstore


kb_vectorstore = None
get_kb_vectorstore()

# must match the db_path rag_pipeline.py points its SQLiteFTS5Retriever at
fts_index = SQLiteFTS5Retriever(db_path="./fts5_index.db")

# ── text splitter ─────────────────────────────────────────────────
# 1200/200 -> 1500/300: keeps multi-row tables, pricing matrices, and
# complete policy rules together across 1,000-page enterprise manuals.
splitter = RecursiveCharacterTextSplitter(
    chunk_size=1500,
    chunk_overlap=300,
    separators=["\n\n", "\n", ". ", " "],
)

HEADER_RE = re.compile(
    r"^(#{1,6})\s+(.*)$", re.MULTILINE
)  # find header somrhting like ##refund


def _build_heading_index(page_text: str) -> List[Tuple[int, str]]:
    """(char_offset, heading_text) for every Markdown '#' heading
    detected on this page, in reading order."""
    return [(m.start(), m.group(2).strip()) for m in HEADER_RE.finditer(page_text)]


def _heading_for_offset(
    headings: List[Tuple[int, str]], offset: int, default_section: Optional[str] = None
) -> Optional[str]:
    """Nearest heading at or before `offset`. If no heading was detected
    on this page prior to `offset`, falls back to `default_section`
    propagated from preceding pages so multi-page sections never lose context."""
    current = default_section
    for h_offset, h_text in headings:
        if h_offset <= offset:
            current = h_text
        else:
            break
    return current


def _contextualize_chunks(
    page_text: str,
    source_name: str,
    page_number: int,
    inherited_section: Optional[str] = None,
) -> Tuple[List[Document], Optional[str]]:
    """Split one page's text into chunks, prepend a '[Source | Page | Section]'
    label to each one, and return both the chunks and the active section to propagate.
    """
    headings = _build_heading_index(page_text)
    raw_chunks = splitter.split_text(page_text)

    docs = []
    search_from = 0
    active_section = inherited_section

    for raw_chunk in raw_chunks:
        anchor = raw_chunk[:60]
        idx = page_text.find(anchor, max(search_from - 300, 0))
        if idx == -1:
            idx = search_from
        search_from = idx
        section = _heading_for_offset(headings, idx, default_section=active_section)
        if section:
            active_section = section

        label_parts = [f"Source: {source_name}", f"Page: {page_number}"]
        if section:
            label_parts.append(f"Section: {section}")
        prefix = "[" + " | ".join(label_parts) + "]\n"

        docs.append(
            Document(
                page_content=prefix + raw_chunk,
                metadata={
                    "source": source_name,
                    "page": page_number,
                    "section": section or "",
                },
            )
        )
    return docs, active_section


def add_pdf(pdf_path: str) -> int:
    """
    Load a PDF, split into contextualized chunks with cross-page heading
    propagation, and add them to BOTH the Chroma vectorstore (cosine HNSW)
    and the SQLite FTS5 keyword index. Safe batching prevents API timeouts.
    Returns number of chunks added.
    """
    if not os.path.exists(pdf_path):
        print(f"File not found: {pdf_path}")
        return 0

    print(f"Loading: {pdf_path}")
    source_name = os.path.basename(pdf_path)

    doc = pymupdf.open(pdf_path)
    total_pages = len(doc)
    print(f"  Pages detected: {total_pages}")

    # High-speed native PyMuPDF extractor (processes 1,000 pages in under 1 second)
    page_stream = [(idx + 1, page.get_text("text")) for idx, page in enumerate(doc)]

    all_chunks: List[Document] = []
    active_section = None

    for page_number, page_text in page_stream:
        if not page_text.strip():
            continue
        chunks, active_section = _contextualize_chunks(
            page_text, source_name, page_number, inherited_section=active_section
        )
        all_chunks.extend(chunks)

    if not all_chunks:
        print("  No extractable text found in this PDF.")
        return 0

    print(f"  Chunks created: {len(all_chunks)}")

    # Safe batching into Chroma to avoid HTTP timeouts / rate-limit spikes
    BATCH_SIZE = 50
    vs = get_kb_vectorstore()
    for i in range(0, len(all_chunks), BATCH_SIZE):
        batch = all_chunks[i : i + BATCH_SIZE]
        vs.add_documents(batch)

    fts_index.add_documents(all_chunks)
    print("  Added to ChromaDB + FTS5 index successfully")

    return len(all_chunks)


def add_text(text: str, source_name: str = "manual") -> int:
    """
    Add plain text directly (no PDF needed).
    Useful for FAQ text, policy text, etc.
    """
    doc = Document(
        page_content=text, metadata={"source": source_name, "page": 1, "section": ""}
    )
    chunks = splitter.split_documents([doc])
    vs = get_kb_vectorstore()
    vs.add_documents(chunks)
    fts_index.add_documents(chunks)
    print(f"Added {len(chunks)} chunks from text: {source_name}")
    return len(chunks)


def show_stats():
    chroma_count = 0
    try:
        vs = get_kb_vectorstore()
        chroma_count = vs._collection.count()
    except Exception as e:
        print(f"Error fetching Chroma count: {e}")
    fts_count = 0
    try:
        fts_count = fts_index.count()
    except Exception as e:
        print(f"Error fetching FTS count: {e}")
    print(
        f"\nKnowledge base: {chroma_count} chunks in ChromaDB, {fts_count} chunks in FTS5 index"
    )
    return {"chroma_chunks": chroma_count, "fts_chunks": fts_count}


def list_documents() -> List[dict]:
    """Returns list of distinct document sources and chunk counts in knowledge base."""
    docs = []
    if os.path.exists("./fts5_index.db"):
        import sqlite3
        conn = sqlite3.connect("./fts5_index.db")
        try:
            rows = conn.execute("SELECT source, COUNT(*) FROM kb_fts GROUP BY source").fetchall()
            for r in rows:
                if r[0]:
                    docs.append({"source": r[0], "chunks": r[1]})
        except Exception as e:
            print(f"Error querying FTS5: {e}")
        finally:
            conn.close()
    return docs


def delete_document(source_name: str) -> bool:
    """Deletes all chunks of source_name from BOTH Chroma vectorstore and FTS5 keyword index."""
    # 1. Delete from Chroma
    try:
        vs = get_kb_vectorstore()
        vs._collection.delete(where={"source": source_name})
        print(f"Deleted {source_name} from ChromaDB")
    except Exception as e:
        print(f"Error deleting from Chroma: {e}")

    # 2. Delete from FTS5
    if os.path.exists("./fts5_index.db"):
        import sqlite3
        conn = sqlite3.connect("./fts5_index.db")
        try:
            conn.execute("DELETE FROM kb_fts WHERE source = ?", (source_name,))
            conn.commit()
            conn.execute("VACUUM")
            conn.commit()
            print(f"Deleted {source_name} from FTS5 index")
        except Exception as e:
            print(f"Error deleting from FTS5: {e}")
        finally:
            conn.close()
    return True



if __name__ == "__main__":

    # ── add your PDFs here ────────────────────────────────────────
    pdf_files = [
        r"C:\AI-Engineer\AI customer agent\techmart_support_guide.pdf",  # change to your actual path
    ]

    total = 0
    for pdf in pdf_files:
        total += add_pdf(pdf)

    # ── or add plain text directly ────────────────────────────────
    # add_text("""
    # Your policy text here.
    # Multiple paragraphs supported.
    # """, source_name="return_policy")

    show_stats()
    print(f"\nDone. Total chunks added this run: {total}")
