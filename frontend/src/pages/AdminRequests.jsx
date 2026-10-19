import { useState, useEffect } from "react";
import RequestDetailModal from "../components/RequestDetailModal";

export default function AdminRequests() {
  const [requests, setRequests] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [search, setSearch] = useState("");
  const [filterCache, setFilterCache] = useState("all");
  const [selectedRequest, setSelectedRequest] = useState(null);

  function fetchRequests() {
    setLoading(true);
    fetch("http://localhost:8000/api/requests/")
      .then((res) => {
        if (!res.ok) throw new Error("Failed to load requests");
        return res.json();
      })
      .then((data) => {
        setRequests(data);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  useEffect(() => {
    fetchRequests();
  }, []);

  // Phase 1 Topic 5: Filtered array using .filter()
  const filteredRequests = requests.filter((req) => {
    const matchesSearch =
      req.input_text.toLowerCase().includes(search.toLowerCase()) ||
      req.output_text.toLowerCase().includes(search.toLowerCase()) ||
      req.session_id.toLowerCase().includes(search.toLowerCase());

    const matchesCache =
      filterCache === "all" ||
      (filterCache === "yes" && req.cache_hit) ||
      (filterCache === "no" && !req.cache_hit);

    return matchesSearch && matchesCache;
  });

  return (
    <div className="admin-page-container">
      <div className="admin-header">
        <div>
          <h2>Request Logs & Telemetry</h2>
          <p className="admin-sub">Audit trail of all customer interactions, latencies, tokens, and routing</p>
        </div>
        <button onClick={fetchRequests} className="btn-secondary">
          🔄 Refresh
        </button>
      </div>

      {/* Filter and Search Bar (Phase 1 Topic 5) */}
      <div className="filter-bar">
        <input
          type="text"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          placeholder="Search by query, response or session ID..."
          className="search-input"
        />

        <div className="filter-group">
          <label>Cache:</label>
          <select value={filterCache} onChange={(e) => setFilterCache(e.target.value)} className="select-input">
            <option value="all">All Requests</option>
            <option value="yes">Cache Hits Only</option>
            <option value="no">RAG Pipeline Only</option>
          </select>
        </div>
      </div>

      {/* Table Card */}
      <div className="card">
        {loading ? (
          <p style={{ padding: "20px" }}>Loading request logs...</p>
        ) : error ? (
          <p style={{ color: "red", padding: "20px" }}>Error: {error}</p>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <th>Time</th>
                  <th>Session ID</th>
                  <th>User Input</th>
                  <th>Output Snippet</th>
                  <th>Model</th>
                  <th>Tokens</th>
                  <th>Latency</th>
                  <th>Cache</th>
                  <th>Severity</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {filteredRequests.length === 0 ? (
                  <tr>
                    <td colSpan="11" style={{ textAlign: "center", padding: "24px" }}>
                      No matching requests found.
                    </td>
                  </tr>
                ) : (
                  filteredRequests.map((req) => (
                    <tr key={req.id}>
                      <td>#{req.id}</td>
                      <td>{req.formatted_time || new Date(req.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
                      <td><code>{req.session_id.slice(0, 12)}...</code></td>
                      <td className="cell-truncate" title={req.input_text}>
                        {req.input_text.length > 30 ? req.input_text.slice(0, 30) + "..." : req.input_text}
                      </td>
                      <td className="cell-truncate" title={req.output_text}>
                        {req.output_text.length > 35 ? req.output_text.slice(0, 35) + "..." : req.output_text}
                      </td>
                      <td><span className="badge badge-model">{req.model_name}</span></td>
                      <td>{req.total_tokens}</td>
                      <td>{(req.latency_ms / 1000).toFixed(2)}s</td>
                      <td>
                        <span className={`badge ${req.cache_hit ? "badge-cache" : "badge-neutral"}`}>
                          {req.cache_hit ? "Hit" : "Miss"}
                        </span>
                      </td>
                      <td>
                        {req.severity === "high" ? (
                          <span className="badge badge-high">High</span>
                        ) : (
                          <span className="badge badge-low">{req.severity || "Low"}</span>
                        )}
                      </td>
                      <td>
                        <button
                          onClick={() => setSelectedRequest(req)}
                          className="btn-link"
                        >
                          View Trace
                        </button>
                      </td>
                    </tr>
                  ))
                )}
              </tbody>
            </table>
          </div>
        )}
      </div>

      {selectedRequest && (
        <RequestDetailModal
          requestItem={selectedRequest}
          onClose={() => setSelectedRequest(null)}
        />
      )}
    </div>
  );
}
