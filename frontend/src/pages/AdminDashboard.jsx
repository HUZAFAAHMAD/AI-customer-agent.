import { useState, useEffect } from "react";
import { Link } from "react-router-dom";
import RequestDetailModal from "../components/RequestDetailModal";

export default function AdminDashboard() {
  // Phase 1 Topic 3 & Phase 3 Topic 3: state for data, loading, error
  const [stats, setStats] = useState(null);
  const [recentRequests, setRecentRequests] = useState([]);
  const [systemStatus, setSystemStatus] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [selectedRequest, setSelectedRequest] = useState(null);

  function loadDashboardData() {
    setLoading(true);
    // Fetch stats, recent requests, and system health in parallel
    Promise.all([
      fetch("http://localhost:8000/api/stats/").then((r) => r.json()),
      fetch("http://localhost:8000/api/requests/").then((r) => r.json()),
      fetch("http://localhost:8000/api/system/").then((r) => r.json()),
    ])
      .then(([statsData, reqsData, sysData]) => {
        setStats(statsData);
        setRecentRequests(reqsData.slice(0, 7)); // top 7 recent
        setSystemStatus(sysData);
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  const handleReset = async () => {
    if (!window.confirm("WARNING: This will instantly delete ALL documents in the knowledge base, ALL request logs, chat history, and cache. Your app will be completely empty. Continue?")) return;
    try {
      const res = await fetch("http://localhost:8000/api/system/reset/", { method: "POST" });
      const data = await res.json();
      if (res.ok) {
        alert("System Reset Complete! Database, Vector Stores, and Redis are empty.");
        loadDashboardData();
      } else {
        alert("Reset failed: " + JSON.stringify(data));
      }
    } catch (err) {
      alert("Error calling reset API: " + err);
    }
  };

  // Phase 2 Topic 1: useEffect on mount with []
  useEffect(() => {
    loadDashboardData();
  }, []);

  // Phase 2 Topic 4: Conditional rendering with early returns
  if (loading && !stats) {
    return <div className="loading-state"><p>Loading monitoring telemetry...</p></div>;
  }

  if (error && !stats) {
    return (
      <div className="error-alert">
        <p>⚠️ Failed to load admin dashboard data: {error}</p>
        <button onClick={loadDashboardData} className="btn-secondary">Retry</button>
      </div>
    );
  }

  return (
    <div className="admin-page-container">
      {/* Top Header */}
      <div className="admin-header">
        <div>
          <h2>Dashboard</h2>
          <p className="admin-sub">Overview of AI pipeline system performance, usage, and cost</p>
        </div>
        <div className="header-actions">
          <button onClick={handleReset} className="btn-danger-small" style={{ marginRight: '10px' }} title="Factory reset all data">
            ⚠️ Factory Reset
          </button>
          <button onClick={loadDashboardData} className="btn-secondary" title="Refresh metrics">
            🔄 Refresh
          </button>
        </div>
      </div>

      {/* KPI Cards Grid (Matches Section 3 of Prompt) */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-blue">📊</div>
          <div className="kpi-content">
            <span className="kpi-label">Total Requests</span>
            <span className="kpi-value">{stats ? stats.total_requests : 0}</span>
            <span className="kpi-sub positive">↑ live tracking</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-green">⚡</div>
          <div className="kpi-content">
            <span className="kpi-label">Cache Hit Rate</span>
            <span className="kpi-value">{stats ? stats.cache_hit_rate : 0}%</span>
            <span className="kpi-sub positive">Semantic Chroma cache</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-purple">⏱️</div>
          <div className="kpi-content">
            <span className="kpi-label">Average Latency</span>
            <span className="kpi-value">{stats ? stats.avg_latency : 0}s</span>
            <span className="kpi-sub">End-to-end pipeline</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-orange">🪙</div>
          <div className="kpi-content">
            <span className="kpi-label">Total Tokens</span>
            <span className="kpi-value">{stats ? stats.total_tokens.toLocaleString() : 0}</span>
            <span className="kpi-sub">Input + Output</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-teal">💰</div>
          <div className="kpi-content">
            <span className="kpi-label">Estimated AI Cost</span>
            <span className="kpi-value">${stats ? stats.estimated_cost.toFixed(2) : "0.00"}</span>
            <span className="kpi-sub">Gemini Flash pricing</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-red">✉️</div>
          <div className="kpi-content">
            <span className="kpi-label">Emails Sent</span>
            <span className="kpi-value">{stats ? stats.emails_sent : 0}</span>
            <span className="kpi-sub negative">High-severity alerts</span>
          </div>
        </div>
      </div>

      {/* Middle Grid: Request Chart + Recent Requests */}
      <div className="dashboard-columns">
        {/* Request Overview Chart Card */}
        <div className="card dashboard-chart-card">
          <div className="card-header">
            <h3>Request Overview</h3>
            <div className="chart-legend">
              <span className="legend-dot dot-requests"></span> Total Requests
              <span className="legend-dot dot-cache" style={{ marginLeft: "12px" }}></span> Cache Hits
            </div>
          </div>
          <div className="chart-body">
            {stats && stats.daily_trends ? (
              <svg viewBox="0 0 500 180" className="chart-svg">
                <line x1="40" y1="140" x2="480" y2="140" stroke="#e2e8f0" strokeWidth="1" />
                <line x1="40" y1="80" x2="480" y2="80" stroke="#f1f5f9" strokeWidth="1" />
                <line x1="40" y1="20" x2="480" y2="20" stroke="#f1f5f9" strokeWidth="1" />
                {stats.daily_trends.map((item, idx) => {
                  const x = 50 + idx * 65;
                  const maxH = Math.max(10, ...stats.daily_trends.map((d) => d.requests));
                  const yReq = 140 - (item.requests / maxH) * 110;
                  const yCache = 140 - (item.cache_hits / maxH) * 110;
                  return (
                    <g key={idx}>
                      <circle cx={x} cy={yReq} r="4" fill="#2563eb" />
                      <circle cx={x} cy={yCache} r="4" fill="#10b981" />
                      <text x={x} y="160" textAnchor="middle" fontSize="11" fill="#64748b">
                        {item.date}
                      </text>
                    </g>
                  );
                })}
              </svg>
            ) : (
              <p>No trend data available.</p>
            )}
          </div>
        </div>

        {/* System Status Card */}
        <div className="card system-status-card">
          <div className="card-header">
            <h3>System Health Status</h3>
          </div>
          <div className="status-list">
            <div className="status-item">
              <span className="status-name">API Server (DRF)</span>
              <span className="status-badge status-online">● {systemStatus ? systemStatus.api : "Online"}</span>
            </div>
            <div className="status-item">
              <span className="status-name">Database (SQLite)</span>
              <span className="status-badge status-online">● {systemStatus ? systemStatus.database : "Online"}</span>
            </div>
            <div className="status-item">
              <span className="status-name">Redis (Memory & Alert Queue)</span>
              <span className="status-badge status-online">● {systemStatus ? systemStatus.redis : "Online"}</span>
            </div>
            <div className="status-item">
              <span className="status-name">Email Worker (SMTP)</span>
              <span className="status-badge status-online">● {systemStatus ? systemStatus.email : "Online"}</span>
            </div>
          </div>

          <div className="quick-actions-box">
            <h4>Quick Actions</h4>
            <div className="quick-actions-btns">
              <Link to="/admin/models" className="btn-secondary action-btn">⚙️ AI Model Config</Link>
              <Link to="/admin/requests" className="btn-secondary action-btn">📋 View All Logs</Link>
            </div>
          </div>
        </div>
      </div>

      {/* Recent Requests Table */}
      <div className="card recent-requests-card">
        <div className="card-header">
          <h3>Recent AI Requests</h3>
          <Link to="/admin/requests" className="link-view-all">View All Requests →</Link>
        </div>
        <div className="table-responsive">
          <table className="data-table">
            <thead>
              <tr>
                <th>Time</th>
                <th>User Input</th>
                <th>Response Snippet</th>
                <th>Model</th>
                <th>Tokens</th>
                <th>Latency</th>
                <th>Cache</th>
                <th>Action</th>
              </tr>
            </thead>
            <tbody>
              {recentRequests.length === 0 ? (
                <tr>
                  <td colSpan="8" style={{ textAlign: "center", padding: "20px" }}>
                    No AI requests logged yet. Try asking questions on the Customer page!
                  </td>
                </tr>
              ) : (
                recentRequests.map((req) => (
                  <tr key={req.id}>
                    <td>{req.formatted_time || new Date(req.created_at).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}</td>
                    <td className="cell-truncate" title={req.input_text}>
                      {req.input_text.length > 35 ? req.input_text.slice(0, 35) + "..." : req.input_text}
                    </td>
                    <td className="cell-truncate" title={req.output_text}>
                      {req.output_text.length > 40 ? req.output_text.slice(0, 40) + "..." : req.output_text}
                    </td>
                    <td><span className="badge badge-model">{req.model_name}</span></td>
                    <td>{req.total_tokens}</td>
                    <td>{(req.latency_ms / 1000).toFixed(2)}s</td>
                    <td>
                      <span className={`badge ${req.cache_hit ? "badge-cache" : "badge-neutral"}`}>
                        {req.cache_hit ? "Yes" : "No"}
                      </span>
                    </td>
                    <td>
                      <button
                        onClick={() => setSelectedRequest(req)}
                        className="btn-link"
                      >
                        Inspect Trace
                      </button>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </div>

      {/* Request Detail Trace Modal (Phase 2 Topic 4) */}
      {selectedRequest && (
        <RequestDetailModal
          requestItem={selectedRequest}
          onClose={() => setSelectedRequest(null)}
        />
      )}
    </div>
  );
}
