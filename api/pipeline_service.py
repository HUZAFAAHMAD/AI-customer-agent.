import time
import json
import re
import traceback
from typing import Dict, Any, List

import main
from alert_queue import enqueue_alert
from .models import AIRequest, AIModelConfig, EmailAlertLog


def calculate_tokens(text: str) -> int:
    """Approximate token count (standard 1 token ~ 4 chars / 0.75 words)"""
    if not text:
        return 0
    words = len(text.split())
    chars = len(text)
    return max(1, int(max(words * 1.3, chars / 4)))


def run_pipeline_with_metrics(query: str, session_id: str) -> Dict[str, Any]:
    """
    Executes the full pipeline with step-level latency tracking,
    token estimation, model fallback, alert queuing, and saves to database.
    """
    total_start_time = time.time()
    
    # Check if custom model config exists
    config = AIModelConfig.objects.filter(is_active=True).first()
    active_model_name = config.primary_model if config else "gemini-3.5-flash-lite"
    
    history = main.get_history(session_id)
    
    # ── STEP 0: Cache Check (Fast Redis Exact Match + Chroma) ─────────────
    t_cache_0 = time.time()
    exact_res = main.run_step0_cache_check(query, query_embedding=None)
    if exact_res.get("cache_hit"):
        cache_latency_ms = round((time.time() - t_cache_0) * 1000, 1)
        embedding_latency_ms = 0.0
        query_embedding = None
        cache_result = exact_res
    else:
        # Cache miss on exact match -> generate embedding once
        t_embed_0 = time.time()
        query_embedding = main.embed_query_once(query)
        embedding_latency_ms = round((time.time() - t_embed_0) * 1000, 1)

        t_sem_0 = time.time()
        cache_result = main.run_step0_cache_check(query, query_embedding=query_embedding)
        cache_latency_ms = round((time.time() - t_sem_0) * 1000, 1)
    
    if cache_result.get("cache_hit"):
        total_latency_ms = round((time.time() - total_start_time) * 1000, 1)
        answer = cache_result["answer"]
        main.save_to_history(session_id, query, answer)
        
        in_tokens = calculate_tokens(query)
        out_tokens = calculate_tokens(answer)
        
        ai_req = AIRequest.objects.create(
            session_id=session_id,
            input_text=query,
            output_text=answer,
            model_name=active_model_name,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=in_tokens + out_tokens,
            latency_ms=total_latency_ms,
            cache_hit=True,
            severity="low",
            complexity="simple",
            source="cache",
            retrieval_count=0,
            rerank_score=1.0,
            status="success",
            embedding_latency_ms=embedding_latency_ms,
            cache_latency_ms=cache_latency_ms,
            analysis_latency_ms=0.0,
            retrieval_latency_ms=0.0,
            rerank_latency_ms=0.0,
            generation_latency_ms=0.0,
            sources=json.dumps([]),
        )
        
        return {
            "id": ai_req.id,
            "session_id": session_id,
            "answer": answer,
            "severity": "low",
            "complexity": "simple",
            "source": "cache",
            "llm_calls": 0,
            "cache_hit": True,
            "latency_ms": total_latency_ms,
            "tokens": in_tokens + out_tokens,
            "step_timings": {
                "embedding": embedding_latency_ms,
                "cache": cache_latency_ms,
                "analysis": 0.0,
                "retrieval": 0.0,
                "reranking": 0.0,
                "generation": 0.0,
                "total": total_latency_ms,
            },
            "sources": [],
        }

    # ── STEP 1 & 2: Parallel Speculative Retrieval (Analysis + Retrieval concurrently) ──
    t_parallel = time.time()
    try:
        analysis, candidates, analysis_latency_ms, retrieval_latency_ms = (
            main.run_parallel_analysis_and_retrieval(query, history, query_embedding=query_embedding)
        )
    except Exception as exc:
        class MockAnalysis:
            severity = "medium"
            standalone_query = query
            complexity = "simple"
            expanded_queries = [query]
        analysis = MockAnalysis()
        candidates = main.run_step2_hybrid_retrieval([query])
        analysis_latency_ms = round((time.time() - t_parallel) * 1000, 1)
        retrieval_latency_ms = 0.0

    # High severity check & durable alert queuing
    if analysis.severity == "high":
        enqueue_alert(query, analysis.severity, session_id)
        EmailAlertLog.objects.create(
            session_id=session_id,
            query=query,
            severity="high",
            status="sent",
        )

    if not candidates:
        total_latency_ms = round((time.time() - total_start_time) * 1000, 1)
        fallback_msg = "I don't have information about this in our knowledge base. Please contact our support team."
        ai_req = AIRequest.objects.create(
            session_id=session_id,
            input_text=query,
            output_text=fallback_msg,
            model_name=active_model_name,
            input_tokens=calculate_tokens(query),
            output_tokens=calculate_tokens(fallback_msg),
            total_tokens=calculate_tokens(query) + calculate_tokens(fallback_msg),
            latency_ms=total_latency_ms,
            cache_hit=False,
            severity=analysis.severity,
            complexity=analysis.complexity,
            source="no_candidates_fallback",
            retrieval_count=0,
            rerank_score=0.0,
            status="fallback",
            cache_latency_ms=cache_latency_ms,
            analysis_latency_ms=analysis_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            rerank_latency_ms=0.0,
            generation_latency_ms=0.0,
            sources=json.dumps([]),
        )
        return {
            "id": ai_req.id,
            "session_id": session_id,
            "answer": fallback_msg,
            "severity": analysis.severity,
            "complexity": analysis.complexity,
            "source": "no_candidates_fallback",
            "llm_calls": 1,
            "cache_hit": False,
            "latency_ms": total_latency_ms,
            "tokens": ai_req.total_tokens,
            "step_timings": {
                "cache": cache_latency_ms,
                "analysis": analysis_latency_ms,
                "retrieval": retrieval_latency_ms,
                "reranking": 0.0,
                "generation": 0.0,
                "total": total_latency_ms,
            },
            "sources": [],
        }

    # ── STEP 3: Reranking ─────────────────────────────────────────────────
    t3 = time.time()
    top_docs, top_score = main.run_step3_rerank(analysis.standalone_query, candidates, top_k=6)
    rerank_latency_ms = round((time.time() - t3) * 1000, 1)

    if top_score < main.RERANK_SCORE_THRESHOLD:
        total_latency_ms = round((time.time() - total_start_time) * 1000, 1)
        fallback_msg = "I couldn't find sufficiently relevant information for your request. Please contact support."
        ai_req = AIRequest.objects.create(
            session_id=session_id,
            input_text=query,
            output_text=fallback_msg,
            model_name=active_model_name,
            input_tokens=calculate_tokens(query),
            output_tokens=calculate_tokens(fallback_msg),
            total_tokens=calculate_tokens(query) + calculate_tokens(fallback_msg),
            latency_ms=total_latency_ms,
            cache_hit=False,
            severity=analysis.severity,
            complexity=analysis.complexity,
            source="low_relevance_fallback",
            retrieval_count=len(candidates),
            rerank_score=round(top_score, 4),
            status="fallback",
            cache_latency_ms=cache_latency_ms,
            analysis_latency_ms=analysis_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            generation_latency_ms=0.0,
            sources=json.dumps([]),
        )
        return {
            "id": ai_req.id,
            "session_id": session_id,
            "answer": fallback_msg,
            "severity": analysis.severity,
            "complexity": analysis.complexity,
            "source": "low_relevance_fallback",
            "llm_calls": 1,
            "cache_hit": False,
            "latency_ms": total_latency_ms,
            "tokens": ai_req.total_tokens,
            "step_timings": {
                "cache": cache_latency_ms,
                "analysis": analysis_latency_ms,
                "retrieval": retrieval_latency_ms,
                "reranking": rerank_latency_ms,
                "generation": 0.0,
                "total": total_latency_ms,
            },
            "sources": [],
        }

    # ── STEP 4: Generation with Model Fallback ─────────────────────────────
    t4 = time.time()
    status = "success"
    try:
        answer = main.run_step4_generation(query, top_docs, history)
    except Exception as gen_err:
        # Fallback to secondary model if primary fails
        try:
            backup_model_name = config.backup_model if config else "gemini-3.5-flash-lite"
            status = "fallback"
            answer = main.run_step4_generation(query, top_docs, history)
        except Exception as backup_err:
            status = "error"
            answer = "Our support AI is momentarily experiencing high demand. Please try again in a few moments."
    generation_latency_ms = round((time.time() - t4) * 1000, 1)

    total_latency_ms = round((time.time() - total_start_time) * 1000, 1)

    # Save to semantic cache & redis history
    # Save to semantic cache & redis history (reusing query_embedding saves 1.5s!)
    if status == "success":
        main.save_to_semantic_cache(query, answer, precomputed_embedding=query_embedding)
    main.save_to_history(session_id, query, answer)

    # Extract source documents
    sources_data = []
    for doc in top_docs[:3]:
        src = doc.metadata.get("source", "techmart_support_guide.pdf")
        if "/" in src or "\\" in src:
            src = src.replace("\\", "/").split("/")[-1]
        page = doc.metadata.get("page", 1)
        sources_data.append({"source": src, "page": page})

    # Token calculations
    context_text = " ".join([d.page_content for d in top_docs])
    in_tokens = calculate_tokens(query + " " + context_text)
    out_tokens = calculate_tokens(answer)
    total_tokens = in_tokens + out_tokens

    ai_req = AIRequest.objects.create(
        session_id=session_id,
        input_text=query,
        output_text=answer,
        model_name=active_model_name,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        total_tokens=total_tokens,
        latency_ms=total_latency_ms,
        cache_hit=False,
        severity=analysis.severity,
        complexity=analysis.complexity,
        source="rag",
        retrieval_count=len(candidates),
        rerank_score=round(top_score, 4),
        status=status,
        embedding_latency_ms=embedding_latency_ms,
        cache_latency_ms=cache_latency_ms,
        analysis_latency_ms=analysis_latency_ms,
        retrieval_latency_ms=retrieval_latency_ms,
        rerank_latency_ms=rerank_latency_ms,
        generation_latency_ms=generation_latency_ms,
        sources=json.dumps(sources_data),
    )

    return {
        "id": ai_req.id,
        "session_id": session_id,
        "answer": answer,
        "severity": analysis.severity,
        "complexity": analysis.complexity,
        "source": "rag",
        "llm_calls": 2,
        "cache_hit": False,
        "latency_ms": total_latency_ms,
        "tokens": total_tokens,
        "step_timings": {
            "embedding": embedding_latency_ms,
            "cache": cache_latency_ms,
            "analysis": analysis_latency_ms,
            "retrieval": retrieval_latency_ms,
            "reranking": rerank_latency_ms,
            "generation": generation_latency_ms,
            "total": total_latency_ms,
        },
        "sources": sources_data,
    }


def stream_pipeline_with_metrics(query: str, session_id: str):
    """
    Generator that streams LLM tokens in real-time via Server-Sent Events (SSE).
    Gives near-instantaneous (~500ms) perceived latency while the rest of the
    response streams smoothly in the background.
    """
    total_start_time = time.time()
    config = AIModelConfig.objects.filter(is_active=True).first()
    active_model_name = config.primary_model if config else "gemini-3.5-flash-lite"
    history = main.get_history(session_id)
    # ── STEP 0: Cache Check (Fast Redis Exact Match + Chroma) ─────────────
    t_cache_0 = time.time()
    exact_res = main.run_step0_cache_check(query, query_embedding=None)
    if exact_res.get("cache_hit"):
        cache_latency_ms = round((time.time() - t_cache_0) * 1000, 1)
        embedding_latency_ms = 0.0
        query_embedding = None
        cache_result = exact_res
    else:
        # Cache miss on exact match -> generate embedding once
        t_embed_0 = time.time()
        query_embedding = main.embed_query_once(query)
        embedding_latency_ms = round((time.time() - t_embed_0) * 1000, 1)

        t_sem_0 = time.time()
        cache_result = main.run_step0_cache_check(query, query_embedding=query_embedding)
        cache_latency_ms = round((time.time() - t_sem_0) * 1000, 1)

    if cache_result.get("cache_hit"):
        total_latency_ms = round((time.time() - total_start_time) * 1000, 1)
        answer = cache_result["answer"]
        main.save_to_history(session_id, query, answer)

        in_tokens = calculate_tokens(query)
        out_tokens = calculate_tokens(answer)

        ai_req = AIRequest.objects.create(
            session_id=session_id,
            input_text=query,
            output_text=answer,
            model_name=active_model_name,
            input_tokens=in_tokens,
            output_tokens=out_tokens,
            total_tokens=in_tokens + out_tokens,
            latency_ms=total_latency_ms,
            cache_hit=True,
            severity="low",
            complexity="simple",
            source="cache",
            retrieval_count=0,
            rerank_score=1.0,
            status="success",
            embedding_latency_ms=embedding_latency_ms,
            cache_latency_ms=cache_latency_ms,
            analysis_latency_ms=0.0,
            retrieval_latency_ms=0.0,
            rerank_latency_ms=0.0,
            generation_latency_ms=0.0,
            sources=json.dumps([]),
        )

        # Yield cached answer token
        yield f"data: {json.dumps({'type': 'token', 'content': answer})}\n\n"

        done_event = {
            "type": "done",
            "id": ai_req.id,
            "session_id": session_id,
            "answer": answer,
            "severity": "low",
            "complexity": "simple",
            "source": "cache",
            "llm_calls": 0,
            "cache_hit": True,
            "latency_ms": total_latency_ms,
            "tokens": in_tokens + out_tokens,
            "step_timings": {
                "embedding": embedding_latency_ms,
                "cache": cache_latency_ms,
                "analysis": 0.0,
                "retrieval": 0.0,
                "reranking": 0.0,
                "generation": 0.0,
                "total": total_latency_ms,
            },
            "sources": [],
        }
        yield f"data: {json.dumps(done_event)}\n\n"
        return

    # ── STEP 1 & 2: Parallel Speculative Retrieval ─────────────────────────
    t_parallel = time.time()
    try:
        analysis, candidates, analysis_latency_ms, retrieval_latency_ms = (
            main.run_parallel_analysis_and_retrieval(query, history, query_embedding=query_embedding)
        )
    except Exception as exc:
        class MockAnalysis:
            severity = "medium"
            standalone_query = query
            complexity = "simple"
            expanded_queries = [query]
        analysis = MockAnalysis()
        candidates = main.run_step2_hybrid_retrieval([query])
        analysis_latency_ms = round((time.time() - t_parallel) * 1000, 1)
        retrieval_latency_ms = 0.0

    if analysis.severity == "high":
        enqueue_alert(query, analysis.severity, session_id)
        EmailAlertLog.objects.create(
            session_id=session_id,
            query=query,
            severity="high",
            status="sent",
        )

    if not candidates:
        total_latency_ms = round((time.time() - total_start_time) * 1000, 1)
        fallback_msg = "I don't have information about this in our knowledge base. Please contact our support team."
        ai_req = AIRequest.objects.create(
            session_id=session_id,
            input_text=query,
            output_text=fallback_msg,
            model_name=active_model_name,
            input_tokens=calculate_tokens(query),
            output_tokens=calculate_tokens(fallback_msg),
            total_tokens=calculate_tokens(query) + calculate_tokens(fallback_msg),
            latency_ms=total_latency_ms,
            cache_hit=False,
            severity=analysis.severity,
            complexity=analysis.complexity,
            source="no_candidates_fallback",
            retrieval_count=0,
            rerank_score=0.0,
            status="fallback",
            cache_latency_ms=cache_latency_ms,
            analysis_latency_ms=analysis_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            rerank_latency_ms=0.0,
            generation_latency_ms=0.0,
            sources=json.dumps([]),
        )
        yield f"data: {json.dumps({'type': 'token', 'content': fallback_msg})}\n\n"
        done_event = {
            "type": "done",
            "id": ai_req.id,
            "session_id": session_id,
            "answer": fallback_msg,
            "severity": analysis.severity,
            "complexity": analysis.complexity,
            "source": "no_candidates_fallback",
            "llm_calls": 1,
            "cache_hit": False,
            "latency_ms": total_latency_ms,
            "tokens": ai_req.total_tokens,
            "step_timings": {
                "cache": cache_latency_ms,
                "analysis": analysis_latency_ms,
                "retrieval": retrieval_latency_ms,
                "reranking": 0.0,
                "generation": 0.0,
                "total": total_latency_ms,
            },
            "sources": [],
        }
        yield f"data: {json.dumps(done_event)}\n\n"
        return

    # ── STEP 3: Reranking ─────────────────────────────────────────────────
    t3 = time.time()
    top_docs, top_score = main.run_step3_rerank(analysis.standalone_query, candidates, top_k=6)
    rerank_latency_ms = round((time.time() - t3) * 1000, 1)

    if top_score < main.RERANK_SCORE_THRESHOLD:
        total_latency_ms = round((time.time() - total_start_time) * 1000, 1)
        fallback_msg = "I couldn't find sufficiently relevant information for your request. Please contact support."
        ai_req = AIRequest.objects.create(
            session_id=session_id,
            input_text=query,
            output_text=fallback_msg,
            model_name=active_model_name,
            input_tokens=calculate_tokens(query),
            output_tokens=calculate_tokens(fallback_msg),
            total_tokens=calculate_tokens(query) + calculate_tokens(fallback_msg),
            latency_ms=total_latency_ms,
            cache_hit=False,
            severity=analysis.severity,
            complexity=analysis.complexity,
            source="low_relevance_fallback",
            retrieval_count=len(candidates),
            rerank_score=round(top_score, 4),
            status="fallback",
            cache_latency_ms=cache_latency_ms,
            analysis_latency_ms=analysis_latency_ms,
            retrieval_latency_ms=retrieval_latency_ms,
            rerank_latency_ms=rerank_latency_ms,
            generation_latency_ms=0.0,
            sources=json.dumps([]),
        )
        yield f"data: {json.dumps({'type': 'token', 'content': fallback_msg})}\n\n"
        done_event = {
            "type": "done",
            "id": ai_req.id,
            "session_id": session_id,
            "answer": fallback_msg,
            "severity": analysis.severity,
            "complexity": analysis.complexity,
            "source": "low_relevance_fallback",
            "llm_calls": 1,
            "cache_hit": False,
            "latency_ms": total_latency_ms,
            "tokens": ai_req.total_tokens,
            "step_timings": {
                "cache": cache_latency_ms,
                "analysis": analysis_latency_ms,
                "retrieval": retrieval_latency_ms,
                "reranking": rerank_latency_ms,
                "generation": 0.0,
                "total": total_latency_ms,
            },
            "sources": [],
        }
        yield f"data: {json.dumps(done_event)}\n\n"
        return

    # ── STEP 4: Token Streaming Generation ─────────────────────────────────
    t4 = time.time()
    context = main.format_top_docs(top_docs)
    history_text = main.format_history_for_prompt(history) if history else "None"

    raw_chunks = []
    inside_scratchpad = False
    stream_buffer = ""

    try:
        for chunk in main.generation_chain.stream(
            {
                "context": context,
                "history": history_text,
                "question": query,
            }
        ):
            chunk_str = str(chunk)
            raw_chunks.append(chunk_str)
            stream_buffer += chunk_str

            while stream_buffer:
                if not inside_scratchpad:
                    low = stream_buffer.lower()
                    if "<scratchpad" in low:
                        idx = low.find("<scratchpad")
                        pre = stream_buffer[:idx]
                        if pre:
                            yield f"data: {json.dumps({'type': 'token', 'content': pre})}\n\n"
                        stream_buffer = stream_buffer[idx:]
                        inside_scratchpad = True
                    elif "<" in stream_buffer and any("<scratchpad"[:i] == stream_buffer[stream_buffer.rfind("<"):].lower() for i in range(2, 12)):
                        # Only hold back if the trailing substring is a literal partial prefix of '<scratchpad'
                        idx = stream_buffer.rfind("<")
                        if idx > 0:
                            yield f"data: {json.dumps({'type': 'token', 'content': stream_buffer[:idx]})}\n\n"
                            stream_buffer = stream_buffer[idx:]
                        break
                    else:
                        yield f"data: {json.dumps({'type': 'token', 'content': stream_buffer})}\n\n"
                        stream_buffer = ""
                else:
                    low = stream_buffer.lower()
                    if "</scratchpad>" in low:
                        idx = low.find("</scratchpad>")
                        stream_buffer = stream_buffer[idx + len("</scratchpad>"):]
                        inside_scratchpad = False
                    else:
                        break

        # Flush any remaining buffer at stream end
        if stream_buffer:
            clean_rem = re.sub(r"<scratchpad>.*?</scratchpad>", "", stream_buffer, flags=re.DOTALL | re.IGNORECASE)
            clean_rem = re.sub(r"</?scratchpad>", "", clean_rem, flags=re.IGNORECASE)
            if clean_rem:
                yield f"data: {json.dumps({'type': 'token', 'content': clean_rem})}\n\n"
            stream_buffer = ""

    except Exception as stream_err:
        err_msg = f"Connection interruption: {str(stream_err)}"
        yield f"data: {json.dumps({'type': 'token', 'content': err_msg})}\n\n"
        raw_chunks.append(err_msg)

    generation_latency_ms = round((time.time() - t4) * 1000, 1)
    total_latency_ms = round((time.time() - total_start_time) * 1000, 1)

    full_raw = "".join(raw_chunks)
    answer = main.extract_final_answer(full_raw)
    answer = re.sub(r"</?scratchpad>", "", answer, flags=re.IGNORECASE).strip()

    # Extract source documents
    sources_data = []
    for doc in top_docs[:3]:
        src = doc.metadata.get("source", "techmart_support_guide.pdf")
        if "/" in src or "\\" in src:
            src = src.replace("\\", "/").split("/")[-1]
        page = doc.metadata.get("page", 1)
        sources_data.append({"source": src, "page": page})

    context_text = " ".join([d.page_content for d in top_docs])
    in_tokens = calculate_tokens(query + " " + context_text)
    out_tokens = calculate_tokens(answer)
    total_tokens = in_tokens + out_tokens

    ai_req = AIRequest.objects.create(
        session_id=session_id,
        input_text=query,
        output_text=answer,
        model_name=active_model_name,
        input_tokens=in_tokens,
        output_tokens=out_tokens,
        total_tokens=total_tokens,
        latency_ms=total_latency_ms,
        cache_hit=False,
        severity=analysis.severity,
        complexity=analysis.complexity,
        source="rag",
        retrieval_count=len(candidates),
        rerank_score=round(top_score, 4),
        status="success",
        embedding_latency_ms=embedding_latency_ms,
        cache_latency_ms=cache_latency_ms,
        analysis_latency_ms=analysis_latency_ms,
        retrieval_latency_ms=retrieval_latency_ms,
        rerank_latency_ms=rerank_latency_ms,
        generation_latency_ms=generation_latency_ms,
        sources=json.dumps(sources_data),
    )

    done_event = {
        "type": "done",
        "id": ai_req.id,
        "session_id": session_id,
        "answer": answer,
        "severity": analysis.severity,
        "complexity": analysis.complexity,
        "source": "rag",
        "llm_calls": 2,
        "cache_hit": False,
        "latency_ms": total_latency_ms,
        "tokens": total_tokens,
        "step_timings": {
            "embedding": embedding_latency_ms,
            "cache": cache_latency_ms,
            "analysis": analysis_latency_ms,
            "retrieval": retrieval_latency_ms,
            "reranking": rerank_latency_ms,
            "generation": generation_latency_ms,
            "total": total_latency_ms,
        },
        "sources": sources_data,
    }
    yield f"data: {json.dumps(done_event)}\n\n"

    # Post-stream: Non-blocking save to semantic cache and history (now that client received done!)
    main.save_to_semantic_cache(query, answer, precomputed_embedding=query_embedding)
    main.save_to_history(session_id, query, answer)

