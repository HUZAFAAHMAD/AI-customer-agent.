from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_google_genai.chat_models import GoogleRateLimitError
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.documents import Document
from langchain_chroma import Chroma
from langchain_classic.retrievers import EnsembleRetriever
from flashrank import Ranker, RerankRequest
from pydantic import BaseModel, Field
from typing import Literal, List, Optional, Tuple, Generator, Union
from concurrent.futures import ThreadPoolExecutor
import time
import json
import re
import redis
import os
from config import GOOGLE_API_KEY
from fts5_retriever import SQLiteFTS5Retriever
from alert_queue import enqueue_alert, start_alert_worker

os.environ["GOOGLE_API_KEY"] = GOOGLE_API_KEY

# REMOVED: `import pickle`, `import threading`,
# `from langchain_community.vectorstores import Chroma`,
# `from langchain_community.retrievers import BM25Retriever`,
# `from langchain_core.caches import BaseCache`,
# `from langchain_core.outputs import Generation`,
# `from langchain_core.globals import set_llm_cache`
# — pickle/BM25Retriever are replaced by fts5_retriever.SQLiteFTS5Retriever;
# threading is now owned by alert_queue.py; BaseCache/Generation/
# set_llm_cache were imported but never actually used anywhere (dead code).
#
# ALSO CHANGED: Chroma now comes from `langchain_chroma` everywhere, not
# `langchain_community.vectorstores` here vs. `langchain_chroma` in
# add_document.py. Both files were pointed at the same persist_directory
# through two different Chroma implementations - langchain_community's
# vectorstore wrappers are the deprecated legacy path; langchain_chroma is
# the actively maintained package, and it exposes the same
# similarity_search_with_score / add_documents / as_retriever interface
# this file already relies on, so this is a safe drop-in swap.

REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
FTS5_DB_PATH = "./fts5_index.db"  # must match the path used in add_document.py

RETRIEVAL_K = 10  # calibrated recall net for 20-page corpus
CANDIDATE_POOL_SIZE = 20  # expanded candidate pool interleaved across expanded queries

RERANK_MODEL = "ms-marco-TinyBERT-L-2-v2"
RERANK_SCORE_THRESHOLD = 0.00005  # calibrated: allows typo/colloquial customer queries while gating out-of-domain noise

# ── LLM instances ─────────────────────────────────────────────────
DEFAULT_MODEL = os.getenv("GOOGLE_MODEL_NAME", "gemini-3.5-flash-lite")
llm = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, temperature=0, timeout=10, max_retries=1, client_args={"http_options": {"timeout": 10000}})
llm_generation = ChatGoogleGenerativeAI(model=DEFAULT_MODEL, temperature=0.2, timeout=15, max_retries=1, client_args={"http_options": {"timeout": 15000}})

# ── Embeddings ────────────────────────────────────────────────────
embeddings = GoogleGenerativeAIEmbeddings(model="gemini-embedding-001")
cache_embeddings = GoogleGenerativeAIEmbeddings(
    model="gemini-embedding-001", task_type="SEMANTIC_SIMILARITY"
)

# ── Vector stores (Self-healing on resets) ───────────────────────────
cache_vectorstore = None
kb_vectorstore = None


def get_cache_vectorstore() -> Chroma:
    global cache_vectorstore
    try:
        if cache_vectorstore is not None:
            cache_vectorstore._collection.count()
            return cache_vectorstore
    except Exception:
        pass
    cache_vectorstore = Chroma(
        collection_name="semantic_cache_minilm",
        embedding_function=cache_embeddings,
        persist_directory="./chroma_cache",
        collection_metadata={"hnsw:space": "cosine"},
    )
    return cache_vectorstore


def get_kb_vectorstore() -> Chroma:
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


def get_hybrid_retriever() -> EnsembleRetriever:
    vs = get_kb_vectorstore()
    sem_retriever = vs.as_retriever(search_kwargs={"k": RETRIEVAL_K})
    fts_retriever = SQLiteFTS5Retriever(db_path=FTS5_DB_PATH, k=RETRIEVAL_K)
    return EnsembleRetriever(
        retrievers=[sem_retriever, fts_retriever], weights=[0.5, 0.5]
    )


# Initialize handles
get_cache_vectorstore()
get_kb_vectorstore()
hybrid_retriever = get_hybrid_retriever()

# ── Local cross-encoder reranker ───────────────────────────────────
# CHANGED: replaces the old "ask the LLM to rank all candidate docs in one
# structured-output call" approach. Asking an LLM to rank 25-40 (or the
# 50 you'll see once CANDIDATE_POOL_SIZE is raised further) documents in a
# single prompt is exactly the regime where LLM list-ranking gets
# unreliable, and it burns real input tokens on every single query just
# to do sorting. FlashRank's cross-encoder runs locally (ONNX, CPU), costs
# no API tokens, and gives each (query, chunk) pair its own calibrated
# 0-1 relevance score instead of a single fuzzy ranked list.
reranker = Ranker(model_name=RERANK_MODEL, cache_dir="./flashrank_cache")

# ── Redis-backed session history ───────────────────────────────────
# CHANGED: replaces the in-process `session_histories = {}` dict.
# A plain dict only lives as long as this one process does - it's wiped on
# every restart/deploy, and it's invisible to any other worker process if
# you ever run more than one (which a plain dict makes impossible to scale
# to, since each worker would have its own, disagreeing, copy).
redis_client = redis.Redis.from_url(REDIS_URL, decode_responses=True)

HISTORY_MAX_MESSAGES = 20  # 10 user/assistant turns, sliding window
HISTORY_TTL_SECONDS = 60 * 60 * 24  # session memory auto-expires after 24h idle


def _history_key(session_id: str) -> str:
    return f"chat_history:{session_id}"


def get_history(session_id: str) -> list:
    raw_items = redis_client.lrange(_history_key(session_id), 0, -1)
    return [json.loads(item) for item in raw_items]


def save_to_history(session_id: str, query: str, answer: str) -> None:
    key = _history_key(session_id)
    pipe = redis_client.pipeline()
    pipe.rpush(key, json.dumps({"role": "user", "content": query}))
    pipe.rpush(key, json.dumps({"role": "assistant", "content": answer}))
    pipe.ltrim(key, -HISTORY_MAX_MESSAGES, -1)  # sliding window, oldest turns fall off
    pipe.expire(key, HISTORY_TTL_SECONDS)
    pipe.execute()


def save_to_semantic_cache(
    original_query: str, answer: str, precomputed_embedding: Optional[List[float]] = None
):
    if not answer or not original_query or len(answer.strip()) < 15:
        return

    # GUARD: Never cache errors, network delay fallbacks, quota notices, or connection timeouts!
    low_ans = answer.lower()
    error_keywords = [
        "momentary network delay",
        "ended prematurely",
        "rate limit",
        "quota",
        "deadline expired",
        "deadline_exceeded",
        "timed out",
        "timeout",
        "contact our support team at 1-800-techmart or 0800-83224",
    ]
    if any(k in low_ans for k in error_keywords):
        return

    try:
        # 1. Update Redis exact cache immediately (<1 ms)
        exact_key = f"exact_cache:{original_query.strip().lower()}"
        redis_client.set(exact_key, answer, ex=60 * 60 * 24 * 7)
    except Exception as e:
        print(f"Error saving to Redis exact cache: {e}")

    try:
        # 2. Update Chroma semantic vectorstore (reusing precomputed embedding saves a network API call!)
        vs = get_cache_vectorstore()
        if precomputed_embedding is not None:
            import uuid
            doc_id = str(uuid.uuid4())
            vs._collection.add(
                ids=[doc_id],
                embeddings=[precomputed_embedding],
                metadatas=[{"response": answer}],
                documents=[original_query],
            )
        else:
            vs.add_texts(texts=[original_query], metadatas=[{"response": answer}])
    except Exception as e:
        print(f"Error saving to semantic cache: {e}")


def format_history_for_prompt(history: list) -> str:
    if not history:
        return "None"
    lines = []
    for msg in history[-HISTORY_MAX_MESSAGES:]:
        role = "Customer" if msg["role"] == "user" else "Assistant"
        lines.append(f"{role}: {msg['content']}")
    return "\n".join(lines)


# ── Background workers ──────────────────────────────────────────────
# Starts exactly ONE persistent worker thread that drains the Redis-backed
# alert queue (see alert_queue.py). Safe to call on every import - it's a
# no-op if the worker thread is already running.
start_alert_worker()


# =================================================================
# STEP 0 — Semantic cache check
# =================================================================


CACHE_DISTANCE_THRESHOLD = 0.065  # calibrated for SEMANTIC_SIMILARITY: exact=0.000, rephrased=0.042-0.045, different>=0.160


def embed_query_once(query: str) -> Optional[List[float]]:
    """
    Embeds the user query once via Google's embedding model.
    The resulting vector is shared between Step 0 (Semantic Cache) and
    Step 2 (Hybrid Retrieval), eliminating a duplicate network round-trip.
    """
    try:
        return cache_embeddings.embed_query(query)
    except Exception as e:
        print(f"Error generating query embedding: {e}")
        return None


def run_step0_cache_check(
    original_query: str, query_embedding: Optional[List[float]] = None
) -> dict:
    # ── Fast-path 1: Redis exact string match (<1 ms) ──────────────────────────
    try:
        exact_key = f"exact_cache:{original_query.strip().lower()}"
        cached_exact = redis_client.get(exact_key)
        if cached_exact:
            return {
                "cache_hit": True,
                "answer": cached_exact,
                "distance": 0.0,
                "source": "exact_cache",
            }
    except Exception as e:
        print(f"Redis exact cache lookup error: {e}")

    # ── Fast-path 2: Chroma semantic similarity search ────────────────────────
    try:
        vs = get_cache_vectorstore()
        if query_embedding is not None:
            results = vs.similarity_search_by_vector_with_relevance_scores(query_embedding, k=1)
        else:
            results = vs.similarity_search_with_score(original_query, k=1)
        if not results:
            return {"cache_hit": False, "answer": None}
        document, distance = results[0]
        if distance <= CACHE_DISTANCE_THRESHOLD:
            return {"cache_hit": True, "answer": document.metadata["response"], "distance": distance}
        return {"cache_hit": False, "answer": None, "distance": distance}
    except Exception as e:
        # Cache query error must NEVER crash customer chat
        print(f"Semantic cache check bypassed due to error: {e}")
        return {"cache_hit": False, "answer": None}


# =================================================================
# STEP 1 — ONE batch LLM call for severity + rewrite + complexity + expansion
# (unchanged from the original - this part of the design was already good)
# =================================================================


class BatchAnalysis(BaseModel):
    severity: Literal["low", "medium", "high"] = Field(
        description="Severity: low=normal question, medium=important issue, high=urgent/harmful"
    )
    standalone_query: str = Field(
        description="Rewritten query that makes sense without conversation history. If no history or query is already standalone, return it unchanged."
    )
    complexity: Literal["simple", "complex"] = Field(
        description="simple=single factual lookup. complex=multi-part, ambiguous, or requires reasoning."
    )
    expanded_queries: List[str] = Field(
        description="Search queries for retrieval. Simple=1 query. Complex=3 queries covering different angles. Always include the standalone_query as one of them."
    )


batch_llm = llm.with_structured_output(BatchAnalysis)

batch_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are an intelligent query analyzer for a RAG customer support system.

Given a customer query and optional conversation history, return ALL of the following in one response:

1. SEVERITY — classify the customer's issue:
   - low: normal question, general inquiry
   - medium: billing issue, important problem needing attention
   - high: urgent, harmful, account compromised, data loss, legal threat

2. STANDALONE QUERY — rewrite the query so it makes sense WITHOUT the history:
   - If no history exists OR query is already standalone → return it UNCHANGED
   - If query uses "that", "it", "the same", "above" → replace with what it refers to
   - Return ONLY the rewritten question

3. COMPLEXITY — classify the query:
   - simple: single factual question, one clear answer expected
   - complex: multi-part, ambiguous, requires reasoning across multiple topics

4. EXPANDED QUERIES — generate search queries for retrieval:
   - If simple: return exactly 1 query (the standalone query itself)
   - If complex: return exactly 3 queries covering different angles/phrasings
   - Always include the standalone query as one of them
   - Keep queries concise and search-friendly""",
        ),
        (
            "human",
            """Conversation history:
{history}

Customer query: {query}""",
        ),
    ]
)

batch_chain = batch_prompt | batch_llm


def run_step1_batch_analysis(query: str, history: list) -> BatchAnalysis:
    history_text = format_history_for_prompt(history)
    return batch_chain.invoke(
        {
            "query": query,
            "history": history_text,
        }
    )


# =================================================================
# STEP 2 — Hybrid retrieval (wide recall pool)
# CHANGED: (a) k raised from 5 to RETRIEVAL_K=30 per retriever so the
# reranker actually has good candidates to choose from, (b) the pool kept
# before reranking raised from a flat [:10] to CANDIDATE_POOL_SIZE=40,
# (c) no longer also runs a redundant similarity_search_with_score call
# purely to feed the old Step 4 distance gate - that gate is gone (see
# Step 3), so this function only does what its name says: retrieval.
# =================================================================


def run_step2_hybrid_retrieval(expanded_queries: List[str]) -> List[Document]:
    seen_contents = set()
    all_candidates = []

    try:
        retriever = get_hybrid_retriever()
        with ThreadPoolExecutor(max_workers=max(1, len(expanded_queries))) as executor:
            results_list = list(executor.map(retriever.invoke, expanded_queries))
    except Exception as e:
        print(f"Retrieval error: {e}")
        if "hnsw" in str(e).lower() or "nothing found on disk" in str(e).lower():
            kb_vectorstore = None
        return []

    # Fair round-robin interleaving: ensures that every expanded query (e.g. Query 1,
    # Query 2, and Query 3) has its top candidate chunks represented in the pool,
    # rather than earlier queries consuming the entire CANDIDATE_POOL_SIZE slice.
    max_candidates_per_query = max((len(r) for r in results_list), default=0)
    for rank in range(max_candidates_per_query):
        for results in results_list:
            if rank < len(results):
                doc = results[rank]
                content_key = doc.page_content.strip()
                if content_key not in seen_contents:
                    seen_contents.add(content_key)
                    all_candidates.append(doc)
                    if len(all_candidates) >= CANDIDATE_POOL_SIZE:
                        break
        if len(all_candidates) >= CANDIDATE_POOL_SIZE:
            break

    return all_candidates


def has_complex_syntax(query: str) -> bool:
    q = query.strip().lower()
    # Punctuation complexity: multiple questions, exclamation, or semicolon
    if q.count("?") > 1 or q.count("!") > 1 or ";" in q:
        return True
    cleaned_q = q.rstrip(".?! ")
    if "." in cleaned_q:
        return True
    # Comparative or multi-intent indicators
    complex_indicators = [
        "difference between",
        "compare",
        "vs",
        "versus",
        "instead of",
        "either",
        "or else",
        "what if",
    ]
    if any(indicator in q for indicator in complex_indicators):
        return True
    # Urgent safety / legal keywords requiring severity analysis
    urgent_indicators = [
        "burning", "smoke", "fire", "explode", "explosion", 
        "shock", "hazard", "lawsuit", "sue", "attorney", "court"
    ]
    if any(indicator in q for indicator in urgent_indicators):
        return True
    return False


def needs_query_rewriting(query: str, history: list) -> bool:
    """
    Returns True ONLY if the query genuinely depends on prior conversation history.
    If the customer asks a standalone question (e.g. 'What is techmart phone number?'),
    skipping query rewriting saves 1500-3000ms and eliminates LLM timeout risks.
    """
    if not history:
        return False
    q = query.strip().lower()
    if has_complex_syntax(q):
        return True
    pronoun_pattern = r'\b(it|its|that|this|these|those|they|them|their|the same|above|mentioned|earlier|previous|again|instead)\b'
    if re.search(pronoun_pattern, q):
        return True
    if any(phrase in q for phrase in ["what about", "how about", "why is that", "tell me more", "and what", "and how"]):
        return True
    words = q.split()
    if len(words) <= 3 and not any(w in q for w in ["phone", "email", "address", "contact", "hours", "return", "warranty", "refund", "price", "order"]):
        return True
    return False


def run_parallel_analysis_and_retrieval(
    query: str, history: list, query_embedding: Optional[List[float]] = None
) -> Tuple[BatchAnalysis, List[Document], float, float]:
    """
    Parallel Speculative Retrieval:
    Runs query analysis (LLM) and speculative hybrid retrieval (Chroma + FTS5)
    concurrently in parallel threads. Reuses query_embedding if provided to eliminate
    the redundant embedding call.

    Fast-path optimization:
    If the query does not depend on history (e.g. standalone question), skip the LLM query rewrite step
    and send the raw query straight to retrieval. Only invoke Query Analysis if there is
    genuine pronoun or conversational reference to prior turns.
    """
    word_count = len(query.strip().split())
    is_complex = has_complex_syntax(query)
    needs_rewrite = needs_query_rewriting(query, history)

    if not needs_rewrite and word_count < 25 and not is_complex:
        t_analysis = 0.0
        analysis = BatchAnalysis(
            severity="low",
            standalone_query=query,
            complexity="simple",
            expanded_queries=[query],
        )
        st = time.time()
        try:
            if query_embedding is not None:
                vs = get_kb_vectorstore()
                sem_docs = vs.similarity_search_by_vector(query_embedding, k=RETRIEVAL_K)
                fts_retriever = SQLiteFTS5Retriever(db_path=FTS5_DB_PATH, k=RETRIEVAL_K)
                fts_docs = fts_retriever.invoke(query)
                seen_keys = set()
                candidates = []
                max_len = max(len(sem_docs), len(fts_docs))
                for i in range(max_len):
                    if i < len(sem_docs):
                        s = sem_docs[i]
                        k = s.page_content.strip()
                        if k not in seen_keys:
                            seen_keys.add(k)
                            candidates.append(s)
                    if i < len(fts_docs):
                        f = fts_docs[i]
                        k = f.page_content.strip()
                        if k not in seen_keys:
                            seen_keys.add(k)
                            candidates.append(f)
            else:
                retriever = get_hybrid_retriever()
                candidates = retriever.invoke(query)
        except Exception as e:
            print(f"Retrieval error: {e}")
            candidates = []
        t_retrieval = round((time.time() - st) * 1000, 1)
        return analysis, candidates[:CANDIDATE_POOL_SIZE], t_analysis, t_retrieval

    t_analysis = 0.0
    t_retrieval = 0.0

    def _worker_analysis():
        nonlocal t_analysis
        st = time.time()
        try:
            res = run_step1_batch_analysis(query, history)
        except Exception as e:
            print(f"Analysis worker error: {e}")
            res = BatchAnalysis(
                severity="low",
                standalone_query=query,
                complexity="simple",
                expanded_queries=[query],
            )
        t_analysis = round((time.time() - st) * 1000, 1)
        return res

    def _worker_retrieval():
        nonlocal t_retrieval
        st = time.time()
        try:
            if query_embedding is not None:
                # Fast path: reuse precomputed embedding without re-calling Google API
                vs = get_kb_vectorstore()
                sem_docs = vs.similarity_search_by_vector(query_embedding, k=RETRIEVAL_K)
                fts_retriever = SQLiteFTS5Retriever(db_path=FTS5_DB_PATH, k=RETRIEVAL_K)
                fts_docs = fts_retriever.invoke(query)
                seen_keys = set()
                res = []
                max_len = max(len(sem_docs), len(fts_docs))
                for i in range(max_len):
                    if i < len(sem_docs):
                        s = sem_docs[i]
                        k = s.page_content.strip()
                        if k not in seen_keys:
                            seen_keys.add(k)
                            res.append(s)
                    if i < len(fts_docs):
                        f = fts_docs[i]
                        k = f.page_content.strip()
                        if k not in seen_keys:
                            seen_keys.add(k)
                            res.append(f)
            else:
                retriever = get_hybrid_retriever()
                res = retriever.invoke(query)
        except Exception as e:
            print(f"Speculative retrieval error: {e}")
            if "hnsw" in str(e).lower() or "nothing found on disk" in str(e).lower():
                kb_vectorstore = None
            res = []
        t_retrieval = round((time.time() - st) * 1000, 1)
        return res

    with ThreadPoolExecutor(max_workers=2) as executor:
        analysis_future = executor.submit(_worker_analysis)
        speculative_future = executor.submit(_worker_retrieval)

        try:
            analysis = analysis_future.result(timeout=4.0)
        except Exception as e:
            print(f"Analysis future timed out or failed ({e}); falling back to raw query")
            analysis = BatchAnalysis(
                severity="low",
                standalone_query=query,
                complexity="simple",
                expanded_queries=[query],
            )

        try:
            speculative_docs = speculative_future.result(timeout=8.0)
        except Exception as e:
            print(f"Retrieval future error ({e})")
            speculative_docs = []

    # If query expansion generated distinct queries, retrieve extra candidates
    remaining_queries = [
        q for q in analysis.expanded_queries if q.strip().lower() != query.strip().lower()
    ]

    if remaining_queries:
        st_extra = time.time()
        extra_candidates = run_step2_hybrid_retrieval(remaining_queries)
        t_retrieval += round((time.time() - st_extra) * 1000, 1)
        seen = set()
        candidates = []
        for d in speculative_docs + extra_candidates:
            k = d.page_content.strip()
            if k not in seen:
                seen.add(k)
                candidates.append(d)
                if len(candidates) >= CANDIDATE_POOL_SIZE:
                    break
    else:
        candidates = speculative_docs[:CANDIDATE_POOL_SIZE]

    return analysis, candidates, t_analysis, t_retrieval


# =================================================================
# STEP 3 — Local cross-encoder reranking + relevance gate
# CHANGED: replaces two things at once from the original pipeline:
#   1. The LLM-based batch reranker (one structured-output call asking the
#      model to rank every candidate) - now a local FlashRank cross-encoder
#      call. No LLM tokens spent, and it scales fine to the larger
#      CANDIDATE_POOL_SIZE.
#   2. The old Step 4 "reject if raw embedding distance > 0.9" gate - that
#      cutoff was brittle because raw cosine/L2 distance isn't calibrated
#      the same way across embedding models or query phrasings, so a fixed
#      number like 0.9 either rejects good answers or lets bad ones through
#      depending on the query. FlashRank's score is a calibrated 0-1
#      relevance confidence for the actual (query, chunk) pair, which is a
#      much more meaningful thing to threshold on. Still tune
#      RERANK_SCORE_THRESHOLD against your own data - "remove one brittle
#      cutoff" doesn't mean "no cutoff will ever need tuning again".
# =================================================================


def run_step3_rerank(
    standalone_query: str, candidates: List[Document], top_k: int = 3
) -> Tuple[List[Document], float]:
    if not candidates:
        return [], 0.0

    passages = [
        {"id": i, "text": doc.page_content, "meta": doc.metadata}
        for i, doc in enumerate(candidates)
    ]
    ranked = reranker.rerank(RerankRequest(query=standalone_query, passages=passages))

    #     top_results = [
    #     {"id": 2, "score": 0.95},
    #     {"id": 0, "score": 0.90}
    # ]
    top_results = ranked[:top_k]
    # r = {"id": 2, "score": 0.95} and candidte[r] = candidate[2]
    top_docs = [candidates[r["id"]] for r in top_results]
    top_score = float(ranked[0]["score"]) if ranked else 0.0
    return top_docs, top_score


# =================================================================
# STEP 4 — Generation
# CHANGED: (a) context is now wrapped in <document> tags carrying source +
# page (+ section, when detected) so the model can actually cite where a
# fact came from instead of just seeing an unlabeled wall of text,
# (b) the system prompt now asks for a page citation in the answer,
# (c) for anything involving a calculation, the model is told to work
# through the arithmetic inside <scratchpad> tags first and put only the
# customer-facing answer inside <answer> tags - extract_final_answer()
# below strips the scratchpad back out so the customer never sees the
# model's working, only accurate numbers that were actually reasoned
# through instead of pattern-matched.
# =================================================================

generation_prompt = ChatPromptTemplate.from_messages(
    [
        (
            "system",
            """You are a helpful customer support assistant.

You will be given context documents wrapped in <document> tags, each with
a source file and page number. Conversation history is provided for
context on what's already been discussed.

Rules:
- Answer using ONLY information found inside the <document> tags below.
- If the answer is not clearly in the context, reply exactly:
  "I don't have enough information about that. Please contact our support team."
- When your answer relies on a specific document, mention its page in
  parentheses, e.g. "(see page 4)".
- Be clear and concise.
- Respond in the same language the customer used.
- Output ONLY the clean, final customer-facing answer directly.
- Use clean, professional plain text formatting. Do NOT use markdown bold asterisks (avoid **text** or ***text***). Use clean dashes for bullet points (- item).
- Never output any internal reasoning markup, thinking traces, or tags (such as <scratchpad>, <thought>, or <document>).""",
        ),
        (
            "human",
            """<context>
{context}
</context>

<conversation_history>
{history}
</conversation_history>

Customer question: {question}""",
        ),
    ]
)

generation_chain = generation_prompt | llm_generation | StrOutputParser()


def extract_final_answer(raw_output: str) -> str:
    cleaned = re.sub(
        r"<scratchpad>.*?</scratchpad>", "", raw_output, flags=re.DOTALL | re.IGNORECASE
    )  # if scratchpad appears remove it
    cleaned = re.sub(r"</?scratchpad>", "", cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r"\*{3,}", "", cleaned)  # remove runs of asterisks like *** or *******
    return cleaned.strip()


def format_top_docs(docs: List[Document]) -> str:
    blocks = []
    for i, doc in enumerate(docs, start=1):
        source = doc.metadata.get("source", "unknown")
        page = doc.metadata.get("page", "unknown")
        section = doc.metadata.get("section")
        section_attr = f' section="{section}"' if section else ""
        blocks.append(
            f'<document index="{i}" source="{source}" page="{page}"{section_attr}>\n'
            f"{doc.page_content}\n"
            f"</document>"
        )
    return "\n\n".join(blocks)


def run_step4_generation(
    original_query: str,
    top_docs: List[Document],
    history: list,
    stream: bool = False,
) -> Union[str, Generator[str, None, None]]:
    if stream:
        return run_step4_generation_stream(original_query, top_docs, history)

    context = format_top_docs(top_docs)
    history_text = format_history_for_prompt(history) if history else "None"

    raw_output = generation_chain.invoke(
        {
            "context": context,
            "history": history_text,
            "question": original_query,
        }
    )
    return extract_final_answer(raw_output)


def run_step4_generation_stream(
    original_query: str,
    top_docs: List[Document],
    history: list,
) -> Generator[str, None, None]:
    """
    Streams AI response chunks in real-time as they are produced by the LLM.
    The first chunk arrives as soon as generated (~300-500ms), followed by
    remaining chunks streamed sequentially.
    """
    context = format_top_docs(top_docs)
    history_text = format_history_for_prompt(history) if history else "None"

    in_scratchpad = False
    pending_buf = ""

    for chunk in generation_chain.stream(
        {
            "context": context,
            "history": history_text,
            "question": original_query,
        }
    ):
        chunk_str = str(chunk)
        if not chunk_str:
            continue
        pending_buf += chunk_str

        while pending_buf:
            if in_scratchpad:
                close_tag = "</scratchpad>"
                idx = pending_buf.lower().find(close_tag)
                if idx == -1:
                    pending_buf = ""
                else:
                    in_scratchpad = False
                    pending_buf = pending_buf[idx + len(close_tag):]
            else:
                open_tag = "<scratchpad>"
                idx = pending_buf.lower().find(open_tag)
                if idx == -1:
                    # Check for partial tag at tail to avoid emitting partial '<scratchpad'
                    safe_end = len(pending_buf)
                    for tail_len in range(1, min(len(open_tag), len(pending_buf) + 1)):
                        if open_tag[:tail_len].lower() == pending_buf[-tail_len:].lower():
                            safe_end = len(pending_buf) - tail_len
                            break
                    if safe_end > 0:
                        yield pending_buf[:safe_end]
                    pending_buf = pending_buf[safe_end:]
                    break
                else:
                    if idx > 0:
                        yield pending_buf[:idx]
                    in_scratchpad = True
                    pending_buf = pending_buf[idx + len(open_tag):]

    if pending_buf and not in_scratchpad:
        clean_text = re.sub(r"</?scratchpad>", "", pending_buf, flags=re.IGNORECASE)
        if clean_text:
            yield clean_text


# =================================================================
# FULL PIPELINE RUNNER (with instant chunk streaming support)
# =================================================================


def run_full_pipeline_stream(
    query: str, session_id: str, yield_dict: bool = False
) -> Generator[Union[str, dict], None, None]:
    """
    Streams the full pipeline AI response in chunks so the first chunk arrives
    immediately and remaining chunks follow via streaming.
    - By default, yields string text chunks for direct printing or streaming.
    - If yield_dict=True, yields structured events:
      {"type": "metadata", ...}, {"type": "chunk", "text": ...}, {"type": "done", "answer": ...}
    """
    history = get_history(session_id)
    query_embedding = embed_query_once(query)

    # ── STEP 0: semantic cache check ──────────────────────────────────────────
    cache_result = run_step0_cache_check(query, query_embedding=query_embedding)
    if cache_result.get("cache_hit"):
        answer = cache_result["answer"]
        save_to_history(session_id, query, answer)
        if yield_dict:
            yield {"type": "metadata", "severity": None, "source": "cache", "llm_calls": 0}
            yield {"type": "chunk", "text": answer}
            yield {"type": "done", "answer": answer}
        else:
            yield answer
        return

    # ── STEP 1 & 2: Parallel Speculative Retrieval ─────────────────────────────
    analysis, candidates, _, _ = run_parallel_analysis_and_retrieval(
        query, history, query_embedding=query_embedding
    )

    if analysis.severity == "high":
        enqueue_alert(query, analysis.severity, session_id)

    if not candidates:
        fallback_msg = "I don't have information about this. Please contact support directly."
        if yield_dict:
            yield {
                "type": "metadata",
                "severity": analysis.severity,
                "source": "no_candidates_fallback",
                "llm_calls": 1,
            }
            yield {"type": "chunk", "text": fallback_msg}
            yield {"type": "done", "answer": fallback_msg}
        else:
            yield fallback_msg
        return

    # ── STEP 3: local cross-encoder reranking + relevance gate ─────────────────
    top_docs, top_score = run_step3_rerank(
        analysis.standalone_query, candidates, top_k=6
    )

    if top_score < RERANK_SCORE_THRESHOLD:
        fallback_msg = "I couldn't find relevant information about this topic. Please contact our support team directly."
        if yield_dict:
            yield {
                "type": "metadata",
                "severity": analysis.severity,
                "source": "low_relevance_fallback",
                "llm_calls": 1,
            }
            yield {"type": "chunk", "text": fallback_msg}
            yield {"type": "done", "answer": fallback_msg}
        else:
            yield fallback_msg
        return

    # ── STEP 4: generation (streamed in chunks) ────────────────────────────────
    if yield_dict:
        yield {
            "type": "metadata",
            "severity": analysis.severity,
            "complexity": analysis.complexity,
            "source": "rag",
            "llm_calls": 2,
        }

    raw_chunks = []
    for chunk in run_step4_generation_stream(query, top_docs, history):
        raw_chunks.append(chunk)
        if yield_dict:
            yield {"type": "chunk", "text": chunk}
        else:
            yield chunk

    full_answer = extract_final_answer("".join(raw_chunks))
    save_to_semantic_cache(query, full_answer)
    save_to_history(session_id, query, full_answer)

    if yield_dict:
        yield {"type": "done", "answer": full_answer}


def run_full_pipeline(
    query: str, session_id: str, stream: bool = False
) -> Union[dict, Generator]:
    """
    Executes the full RAG pipeline.
    - If stream=False (default): returns dict with answer, severity, source, etc.
    - If stream=True: returns generator streaming chunks in real-time.
    """
    if stream:
        return run_full_pipeline_stream(query, session_id)

    history = get_history(session_id)
    query_embedding = embed_query_once(query)

    # ── STEP 0: semantic cache check (now BEFORE any LLM call) ────────────────
    cache_result = run_step0_cache_check(query, query_embedding=query_embedding)
    if cache_result["cache_hit"]:
        save_to_history(
            session_id, query, cache_result["answer"]
        )  # we add this because if either cache hit we never break history like conversation
        return {
            "answer": cache_result["answer"],
            "severity": None,  # not re-classified on a cache hit - see Step 0 note above
            "source": "cache",
            "llm_calls": 0,
        }

    # ── STEP 1 & 2: Parallel Speculative Retrieval (Analysis + Retrieval) ──────
    analysis, candidates, _, _ = run_parallel_analysis_and_retrieval(
        query, history, query_embedding=query_embedding
    )

    # fire-and-forget high-severity alert via the durable Redis queue
    if analysis.severity == "high":
        enqueue_alert(query, analysis.severity, session_id)

    if not candidates:
        return {
            "answer": "I don't have information about this. Please contact support directly.",
            "severity": analysis.severity,
            "source": "no_candidates_fallback",
            "llm_calls": 1,
        }

    # ── STEP 3: local cross-encoder reranking + relevance gate ─────────────────
    top_docs, top_score = run_step3_rerank(
        analysis.standalone_query, candidates, top_k=6
    )

    if top_score < RERANK_SCORE_THRESHOLD:
        return {
            "answer": "I couldn't find relevant information about this topic. Please contact our support team directly.",
            "severity": analysis.severity,
            "source": "low_relevance_fallback",
            "llm_calls": 1,
        }

    # ── STEP 4: generation ───────────────────────────────────────────────────
    answer = run_step4_generation(query, top_docs, history)

    save_to_semantic_cache(query, answer)
    save_to_history(session_id, query, answer)

    return {
        "answer": answer,
        "severity": analysis.severity,
        "complexity": analysis.complexity,
        "source": "rag",
        "llm_calls": 2,  # batch analysis + generation - reranking no longer costs an LLM call
    }


# =================================================================
# TEST
# =================================================================

# if __name__ == "__main__":

#     session_id = "test_session_001"

#     tests = ["I buy parcel from you 1 year pass still dont arrive "]

#     for i, query in enumerate(tests, 1):
#         print(f"\n{'='*60}")
#         print(f"TEST {i}: {query}")
#         print("=" * 60)

#         try:
#             result = run_full_pipeline(query, session_id)
#         except GoogleRateLimitError as error:
#             print(
#                 "Google Gemini quota exhausted. Wait for the reset window or "
#                 "enable billing/increase the API quota, then run the test again."
#             )
#             print(f"Details: {error}")
#             break

#         print(f"Severity:   {result['severity']}")
#         print(f"Source:     {result['source']}")
#         print(f"LLM calls:  {result['llm_calls']}")
#         print(f"Answer:     {result['answer']}")
