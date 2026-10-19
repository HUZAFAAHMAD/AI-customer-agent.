import { useState, useEffect } from "react";

export default function AdminDocuments() {
  const [documents, setDocuments] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [message, setMessage] = useState(null);

  // Upload PDF state
  const [file, setFile] = useState(null);
  const [uploadingPdf, setUploadingPdf] = useState(false);

  // Manual text state
  const [sourceName, setSourceName] = useState("");
  const [policyText, setPolicyText] = useState("");
  const [uploadingText, setUploadingText] = useState(false);

  async function extractErrorMessage(res, defaultMsg) {
    try {
      const data = await res.json();
      return data.error || data.message || data.detail || defaultMsg;
    } catch {
      return `${defaultMsg} (HTTP ${res.status}: ${res.statusText})`;
    }
  }

  // Phase 2 Topic 1 & Phase 3 Topic 3: Fetch on mount
  async function loadDocuments() {
    setLoading(true);
    setError(null);
    try {
      const res = await fetch("http://localhost:8000/api/documents/");
      if (!res.ok) {
        const exactMsg = await extractErrorMessage(res, "Failed to load documents");
        throw new Error(exactMsg);
      }
      const data = await res.json();
      if (data.error) {
        throw new Error(data.error);
      }
      setDocuments(data.documents || []);
      setStats(data.stats || { chroma_chunks: 0, fts_chunks: 0 });
      setLoading(false);
    } catch (err) {
      setError(`Error loading documents: ${err.message}`);
      setLoading(false);
    }
  }

  useEffect(() => {
    loadDocuments();
  }, []);

  // Phase 3 Topic 5: DELETE flow
  async function handleDeleteDocument(sourceName) {
    if (!window.confirm(`Are you sure you want to delete all chunks for "${sourceName}" from ChromaDB and FTS5?`)) {
      return;
    }
    setError(null);
    setMessage(null);

    try {
      const res = await fetch(`http://localhost:8000/api/documents/?source=${encodeURIComponent(sourceName)}`, {
        method: "DELETE",
      });
      if (!res.ok) {
        const exactMsg = await extractErrorMessage(res, `Failed to delete "${sourceName}"`);
        throw new Error(exactMsg);
      }
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setDocuments(documents.filter((doc) => doc.source !== sourceName));
      setMessage(`🗑️ Deleted "${sourceName}" from both ChromaDB and FTS5.`);
      loadDocuments();
    } catch (err) {
      setError(`Delete failed: ${err.message}`);
    }
  }

  // Phase 3 Topic 4: POST with FormData for PDF upload
  async function handlePdfUpload(e) {
    e.preventDefault();
    if (!file) {
      alert("Please select a PDF file first.");
      return;
    }

    setUploadingPdf(true);
    setMessage(null);
    setError(null);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const res = await fetch("http://localhost:8000/api/documents/", {
        method: "POST",
        body: formData,
      });
      if (!res.ok) {
        const exactMsg = await extractErrorMessage(res, "Failed to index PDF document");
        throw new Error(exactMsg);
      }
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessage(`✅ ${data.message}`);
      setFile(null);
      setUploadingPdf(false);
      const fileInput = document.getElementById("pdf-file-input");
      if (fileInput) fileInput.value = "";
      loadDocuments();
    } catch (err) {
      setError(`Upload failed: ${err.message}`);
      setUploadingPdf(false);
    }
  }

  // Quick 1-click Re-index TechMart Support Guide
  async function handleReindexDefault() {
    setUploadingPdf(true);
    setMessage(null);
    setError(null);

    try {
      const res = await fetch("http://localhost:8000/api/documents/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ reindex_default: true }),
      });
      if (!res.ok) {
        const exactMsg = await extractErrorMessage(res, "Failed to re-index default PDF");
        throw new Error(exactMsg);
      }
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessage(`✅ ${data.message}`);
      setUploadingPdf(false);
      loadDocuments();
    } catch (err) {
      setError(`Re-index failed: ${err.message}`);
      setUploadingPdf(false);
    }
  }

  // Phase 3 Topic 4: POST JSON for text/policy input
  async function handleTextUpload(e) {
    e.preventDefault();
    if (!sourceName.trim() || !policyText.trim()) {
      alert("Please enter both a source name and text content.");
      return;
    }

    setUploadingText(true);
    setMessage(null);
    setError(null);

    try {
      const res = await fetch("http://localhost:8000/api/documents/", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          text: policyText,
          source_name: sourceName,
        }),
      });
      if (!res.ok) {
        const exactMsg = await extractErrorMessage(res, "Failed to add text to knowledge base");
        throw new Error(exactMsg);
      }
      const data = await res.json();
      if (data.error) throw new Error(data.error);

      setMessage(`✅ ${data.message}`);
      setSourceName("");
      setPolicyText("");
      setUploadingText(false);
      loadDocuments();
    } catch (err) {
      setError(`Text addition failed: ${err.message}`);
      setUploadingText(false);
    }
  }

  return (
    <div className="admin-page-container">
      {/* Top Header */}
      <div className="admin-header">
        <div>
          <h2>Knowledge Base Documents</h2>
          <p className="admin-sub">
            Add or delete documents indexed into ChromaDB (Vectorstore) and SQLite FTS5 (Keyword Search) using your <code>add_documents.py</code> pipeline
          </p>
        </div>
        <button onClick={loadDocuments} className="btn-secondary">
          🔄 Refresh
        </button>
      </div>

      {message && <div className="success-alert">{message}</div>}
      {error && <div className="error-alert">⚠️ {error}</div>}

      {/* KPI Stats for Knowledge Base */}
      <div className="kpi-grid">
        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-blue">📚</div>
          <div className="kpi-content">
            <span className="kpi-label">Indexed Documents</span>
            <span className="kpi-value">{documents.length}</span>
            <span className="kpi-sub">Distinct Sources</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-green">🧬</div>
          <div className="kpi-content">
            <span className="kpi-label">ChromaDB Chunks</span>
            <span className="kpi-value">{stats ? stats.chroma_chunks : 0}</span>
            <span className="kpi-sub">Semantic Vectorstore</span>
          </div>
        </div>

        <div className="kpi-card">
          <div className="kpi-icon-wrap icon-purple">🔍</div>
          <div className="kpi-content">
            <span className="kpi-label">SQLite FTS5 Chunks</span>
            <span className="kpi-value">{stats ? stats.fts_chunks : 0}</span>
            <span className="kpi-sub">Keyword Full-Text Index</span>
          </div>
        </div>
      </div>

      {/* Documents Table */}
      <div className="card">
        <div className="card-header">
          <h3>Active Indexed Documents</h3>
          <button
            onClick={handleReindexDefault}
            disabled={uploadingPdf}
            className="btn-secondary"
            title="Re-index techmart_support_guide.pdf from disk"
          >
            {uploadingPdf ? "Indexing..." : "⚡ Quick Index: techmart_support_guide.pdf"}
          </button>
        </div>

        {loading ? (
          <p style={{ padding: "20px" }}>Loading knowledge base index...</p>
        ) : (
          <div className="table-responsive">
            <table className="data-table">
              <thead>
                <tr>
                  <th>Source Document</th>
                  <th>Indexed Chunks</th>
                  <th>Storage Backends</th>
                  <th>Action</th>
                </tr>
              </thead>
              <tbody>
                {documents.length === 0 ? (
                  <tr>
                    <td colSpan="4" style={{ textAlign: "center", padding: "28px" }}>
                      No documents currently indexed in ChromaDB or FTS5.
                      <br />
                      Upload a PDF below or click <strong>"Quick Index: techmart_support_guide.pdf"</strong>!
                    </td>
                  </tr>
                ) : (
                  documents.map((doc, idx) => (
                    <tr key={idx}>
                      <td>
                        <strong>📄 {doc.source}</strong>
                      </td>
                      <td>
                        <span className="badge badge-model">{doc.chunks} chunks</span>
                      </td>
                      <td>
                        <span className="badge badge-cache">ChromaDB (Cosine)</span>{" "}
                        <span className="badge badge-neutral">SQLite FTS5</span>
                      </td>
                      <td>
                        <button
                          onClick={() => handleDeleteDocument(doc.source)}
                          className="btn-danger-small"
                          title="Delete from both Chroma and FTS5"
                        >
                          🗑️ Delete
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

      {/* Add Document Section (Two Forms) */}
      <div className="dashboard-columns">
        {/* Form 1: Upload PDF */}
        <div className="card" style={{ flex: 1 }}>
          <div className="card-header">
            <h3>📤 Upload & Index PDF</h3>
          </div>
          <p className="admin-sub" style={{ marginBottom: "16px" }}>
            Uses your <code>add_documents.py</code> layout-aware PyMuPDF4LLM extraction, heading contextualization, and chunk batching.
          </p>

          <form onSubmit={handlePdfUpload} className="model-form">
            <div className="form-group">
              <label className="form-label">Select PDF Document:</label>
              <input
                id="pdf-file-input"
                type="file"
                accept=".pdf"
                onChange={(e) => setFile(e.target.files[0])}
                disabled={uploadingPdf}
                className="chat-input"
              />
            </div>

            <button
              type="submit"
              disabled={uploadingPdf || !file}
              className="btn-primary"
            >
              {uploadingPdf ? "Indexing Chunks into Chroma & FTS5..." : "Upload & Index PDF"}
            </button>
          </form>
        </div>

        {/* Form 2: Add Plain Text / FAQ */}
        <div className="card" style={{ flex: 1 }}>
          <div className="card-header">
            <h3>📝 Add Plain Text / Policy</h3>
          </div>
          <p className="admin-sub" style={{ marginBottom: "16px" }}>
            Useful for quick policy additions, return rules, or FAQs (uses <code>add_text()</code>).
          </p>

          <form onSubmit={handleTextUpload} className="model-form">
            <div className="form-group">
              <label className="form-label">Policy / Document Label:</label>
              <input
                type="text"
                value={sourceName}
                onChange={(e) => setSourceName(e.target.value)}
                placeholder="e.g. cancellation_policy or international_shipping"
                disabled={uploadingText}
                className="chat-input"
              />
            </div>

            <div className="form-group">
              <label className="form-label">Policy Content / Text:</label>
              <textarea
                value={policyText}
                onChange={(e) => setPolicyText(e.target.value)}
                placeholder="Type or paste policy text here..."
                rows="4"
                disabled={uploadingText}
                className="chat-input"
                style={{ resize: "vertical" }}
              />
            </div>

            <button
              type="submit"
              disabled={uploadingText || !sourceName.trim() || !policyText.trim()}
              className="btn-primary"
            >
              {uploadingText ? "Adding Chunks..." : "Add Text to Knowledge Base"}
            </button>
          </form>
        </div>
      </div>
    </div>
  );
}
