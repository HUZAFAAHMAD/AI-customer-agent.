// Phase 2 Topic 4: Conditional rendering & props
export default function RequestDetailModal({ requestItem, onClose }) {
  if (!requestItem) return null;

  const timings = requestItem.step_timings || {
    embedding: requestItem.embedding_latency_ms || 0,
    cache: requestItem.cache_latency_ms || 0,
    analysis: requestItem.analysis_latency_ms || 0,
    retrieval: requestItem.retrieval_latency_ms || 0,
    reranking: requestItem.rerank_latency_ms || 0,
    generation: requestItem.generation_latency_ms || 0,
    total: requestItem.latency_ms || 0,
  };

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        {/* Modal Header */}
        <div className="modal-header">
          <div>
            <h3>🔍 Request Trace Details</h3>
            <p className="modal-sub">
              Request #{requestItem.id} • Session: {requestItem.session_id} • {requestItem.formatted_time || new Date(requestItem.created_at).toLocaleTimeString()}
            </p>
          </div>
          <button className="modal-close-btn" onClick={onClose}>✕</button>
        </div>

        {/* Modal Body */}
        <div className="modal-body">
          {/* Metadata Grid */}
          <div className="detail-meta-grid">
            <div className="detail-meta-card">
              <span className="meta-label">Model</span>
              <span className="meta-val">{requestItem.model_name}</span>
            </div>
            <div className="detail-meta-card">
              <span className="meta-label">Cache Hit</span>
              <span className={`meta-val ${requestItem.cache_hit ? "text-success" : "text-neutral"}`}>
                {requestItem.cache_hit ? "YES" : "NO"}
              </span>
            </div>
            <div className="detail-meta-card">
              <span className="meta-label">Total Latency</span>
              <span className="meta-val">{requestItem.latency_ms} ms</span>
            </div>
            <div className="detail-meta-card">
              <span className="meta-label">Total Tokens</span>
              <span className="meta-val">{requestItem.total_tokens}</span>
            </div>
            <div className="detail-meta-card">
              <span className="meta-label">Severity</span>
              <span className={`meta-val ${requestItem.severity === "high" ? "text-danger" : ""}`}>
                {requestItem.severity || "None"}
              </span>
            </div>
            <div className="detail-meta-card">
              <span className="meta-label">Status</span>
              <span className="meta-val text-success">{requestItem.status || "success"}</span>
            </div>
          </div>

          {/* User Input & AI Response */}
          <div className="io-box-container">
            <div className="io-box">
              <h4>Customer Query:</h4>
              <p>{requestItem.input_text}</p>
            </div>
            <div className="io-box">
              <h4>AI Response:</h4>
              <p>{requestItem.output_text}</p>
            </div>
          </div>

          {/* Pipeline Step Execution Trace */}
          <div className="trace-section">
            <h4>Pipeline Step-by-Step Execution Trace</h4>
            <div className="step-pipeline-flow">
              <div className="step-node active">
                <span className="step-num">1</span>
                <span className="step-title">User Input</span>
              </div>
              <div className="step-arrow">↓</div>
              <div className={`step-node ${requestItem.cache_hit ? "highlight-cache" : "active"}`}>
                <span className="step-num">2</span>
                <span className="step-title">Cache Check ({timings.cache}ms)</span>
              </div>
              <div className="step-arrow">↓</div>
              <div className={`step-node ${requestItem.cache_hit ? "skipped" : "active"}`}>
                <span className="step-num">3</span>
                <span className="step-title">Query Analysis ({timings.analysis}ms)</span>
              </div>
              <div className="step-arrow">↓</div>
              <div className={`step-node ${requestItem.cache_hit ? "skipped" : "active"}`}>
                <span className="step-num">4</span>
                <span className="step-title">Retrieval ({timings.retrieval}ms)</span>
              </div>
              <div className="step-arrow">↓</div>
              <div className={`step-node ${requestItem.cache_hit ? "skipped" : "active"}`}>
                <span className="step-num">5</span>
                <span className="step-title">Reranking ({timings.reranking}ms)</span>
              </div>
              <div className="step-arrow">↓</div>
              <div className={`step-node ${requestItem.cache_hit ? "skipped" : "active"}`}>
                <span className="step-num">6</span>
                <span className="step-title">Generation ({timings.generation}ms)</span>
              </div>
              <div className="step-arrow">↓</div>
              <div className="step-node active">
                <span className="step-num">7</span>
                <span className="step-title">Final Response</span>
              </div>
            </div>
          </div>

          {/* Latency Breakdown Table */}
          <div className="latency-table-section">
            <h4>Latency Breakdown</h4>
            <table className="latency-table">
              <thead>
                <tr>
                  <th>Pipeline Step</th>
                  <th>Execution Time</th>
                  <th>% of Total</th>
                </tr>
              </thead>
              <tbody>
                {timings.embedding > 0 && (
                  <tr>
                    <td>Query Embedding (Google API)</td>
                    <td>{timings.embedding} ms</td>
                    <td>{timings.total > 0 ? Math.round((timings.embedding / timings.total) * 100) : 0}%</td>
                  </tr>
                )}
                <tr>
                  <td>Semantic Cache Check</td>
                  <td>{timings.cache} ms</td>
                  <td>{timings.total > 0 ? Math.round((timings.cache / timings.total) * 100) : 0}%</td>
                </tr>
                <tr>
                  <td>Query Analysis (Severity + Rewrite + Expansion)</td>
                  <td>{timings.analysis} ms</td>
                  <td>{timings.total > 0 ? Math.round((timings.analysis / timings.total) * 100) : 0}%</td>
                </tr>
                <tr>
                  <td>Hybrid Retrieval (Semantic + FTS5)</td>
                  <td>{timings.retrieval} ms</td>
                  <td>{timings.total > 0 ? Math.round((timings.retrieval / timings.total) * 100) : 0}%</td>
                </tr>
                <tr>
                  <td>Reranking (FlashRank Cross-Encoder)</td>
                  <td>{timings.reranking} ms</td>
                  <td>{timings.total > 0 ? Math.round((timings.reranking / timings.total) * 100) : 0}%</td>
                </tr>
                <tr>
                  <td>Generation (Gemini LLM)</td>
                  <td>{timings.generation} ms</td>
                  <td>{timings.total > 0 ? Math.round((timings.generation / timings.total) * 100) : 0}%</td>
                </tr>
                <tr className="latency-total-row">
                  <td><strong>Total End-to-End Latency</strong></td>
                  <td><strong>{timings.total} ms ({(timings.total / 1000).toFixed(2)}s)</strong></td>
                  <td><strong>100%</strong></td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        {/* Modal Footer */}
        <div className="modal-footer">
          <button className="btn-secondary" onClick={onClose}>Close</button>
        </div>
      </div>
    </div>
  );
}
