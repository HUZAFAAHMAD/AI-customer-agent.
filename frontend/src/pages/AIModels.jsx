import { useState, useEffect } from "react";
import { API_BASE_URL } from "../apiConfig";

export default function AIModels() {
  const [configId, setConfigId] = useState(null);
  const [primaryModel, setPrimaryModel] = useState("gemini-3.1-flash-lite");
  const [backupModel, setBackupModel] = useState("gemini-3.1-flash-lite");
  const [embeddingModel, setEmbeddingModel] = useState("sentence-transformers/all-MiniLM-L6-v2");
  const [temperature, setTemperature] = useState(0.2);
  const [isActive, setIsActive] = useState(true);

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [message, setMessage] = useState(null);
  const [error, setError] = useState(null);

  useEffect(() => {
    fetch(`${API_BASE_URL}/api/models/`)
      .then((res) => res.json())
      .then((data) => {
        if (data && data.length > 0) {
          const cfg = data[0];
          setConfigId(cfg.id);
          setPrimaryModel(cfg.primary_model);
          setBackupModel(cfg.backup_model);
          setEmbeddingModel(cfg.embedding_model);
          setTemperature(cfg.temperature);
          setIsActive(cfg.is_active);
        }
        setLoading(false);
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }, []);

  function handleSave(e) {
    e.preventDefault();
    setSaving(true);
    setMessage(null);
    setError(null);

    const payload = {
      name: "Production AI Config",
      primary_model: primaryModel,
      backup_model: backupModel,
      embedding_model: embeddingModel,
      temperature: parseFloat(temperature),
      is_active: isActive,
    };

    const url = configId
      ? `${API_BASE_URL}/api/models/${configId}/`
      : `${API_BASE_URL}/api/models/`;
    const method = configId ? "PATCH" : "POST";

    fetch(url, {
      method: method,
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify(payload),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Failed to save model configuration.");
        return res.json();
      })
      .then((saved) => {
        setConfigId(saved.id);
        setMessage("✅ Configuration saved successfully! Pipeline will use these settings.");
        setSaving(false);
      })
      .catch((err) => {
        setError(err.message);
        setSaving(false);
      });
  }

  if (loading) return <div className="loading-state"><p>Loading AI configurations...</p></div>;

  return (
    <div className="admin-page-container">
      <div className="admin-header">
        <div>
          <h2>AI Model Management</h2>
          <p className="admin-sub">Configure generation providers, fallback backup models, and hyper-parameters</p>
        </div>
      </div>

      {message && <div className="success-alert">{message}</div>}
      {error && <div className="error-alert">⚠️ {error}</div>}

      <div className="card model-config-card">
        <form onSubmit={handleSave} className="model-form">
          {/* Primary Model */}
          <div className="form-group">
            <label className="form-label">Primary Generation Model:</label>
            <select
              value={primaryModel}
              onChange={(e) => setPrimaryModel(e.target.value)}
              className="select-input"
            >
              <option value="gemini-3.1-flash-lite">Gemini 3.1 Flash Lite (Fastest & Cost-effective)</option>
              <option value="gemini-2.5-flash">Gemini 2.5 Flash (Balanced Reasoning)</option>
              <option value="gemini-1.5-pro">Gemini 1.5 Pro (Deep Reasoning)</option>
            </select>
            <span className="field-hint">Primary model queried for batch analysis and answer generation.</span>
          </div>

          {/* Backup Model */}
          <div className="form-group">
            <label className="form-label">Backup Fallback Model:</label>
            <select
              value={backupModel}
              onChange={(e) => setBackupModel(e.target.value)}
              className="select-input"
            >
              <option value="gemini-3.1-flash-lite">Gemini 3.1 Flash Lite (Default Fallback)</option>
              <option value="gemini-2.5-flash">Gemini 2.5 Flash (Secondary Tier)</option>
            </select>
            <span className="field-hint">If primary provider faces rate limit or API failure, system automatically falls back here.</span>
          </div>

          {/* Embedding Model */}
          <div className="form-group">
            <label className="form-label">Active Embedding Model:</label>
            <input
              type="text"
              value={embeddingModel}
              disabled
              className="chat-input disabled-input"
            />
            <span className="field-hint">Vector embeddings utilized for Chroma vectorstore indexing.</span>
          </div>

          {/* Temperature */}
          <div className="form-group">
            <label className="form-label">
              Temperature: <strong>{temperature}</strong>
            </label>
            <input
              type="range"
              min="0.0"
              max="1.0"
              step="0.05"
              value={temperature}
              onChange={(e) => setTemperature(e.target.value)}
              className="range-input"
            />
            <span className="field-hint">Lower temperature (0.0 - 0.2) ensures strict factual answers based only on context docs.</span>
          </div>

          {/* Status Checkbox */}
          <div className="form-group checkbox-group">
            <label className="checkbox-label">
              <input
                type="checkbox"
                checked={isActive}
                onChange={(e) => setIsActive(e.target.checked)}
              />
              Enable Active Model Strategy & Automatic Fallback
            </label>
          </div>

          <button type="submit" disabled={saving} className="btn-primary">
            {saving ? "Saving Changes..." : "Save AI Configuration"}
          </button>
        </form>
      </div>

      {/* Visual Fallback Architecture Box */}
      <div className="card architecture-diagram-card">
        <h3>Fallback Architecture Overview</h3>
        <div className="diagram-flow">
          <div className="diagram-box">Customer Query</div>
          <div className="diagram-arrow">➔</div>
          <div className="diagram-box highlight-primary">Primary Model ({primaryModel})</div>
          <div className="diagram-arrow">➔ [Rate Limit / Error] ➔</div>
          <div className="diagram-box highlight-backup">Backup Model ({backupModel})</div>
          <div className="diagram-arrow">➔</div>
          <div className="diagram-box highlight-success">Verified Response</div>
        </div>
      </div>
    </div>
  );
}
