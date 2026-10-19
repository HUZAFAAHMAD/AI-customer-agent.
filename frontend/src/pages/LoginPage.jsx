import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { API_BASE_URL } from "../apiConfig";

// Phase 5 Topic 2: Login form in React — receiving and storing the token
export default function LoginPage() {
  const [username, setUsername] = useState("admin");
  const [password, setPassword] = useState("admin123");
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(false);

  const { login } = useAuth(); // from AuthContext
  const navigate = useNavigate(); // Phase 4 programmatic navigation

  function handleSubmit(e) {
    e.preventDefault();
    setLoading(true);
    setError(null);

    fetch(`${API_BASE_URL}/api/token/`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ username, password }),
    })
      .then((res) => {
        if (!res.ok) throw new Error("Invalid username or password");
        return res.json();
      })
      .then((data) => {
        login(data.access, data.refresh); // update context and localStorage
        navigate("/admin"); // redirect to Admin Dashboard
      })
      .catch((err) => {
        setError(err.message);
        setLoading(false);
      });
  }

  return (
    <div className="login-page-container">
      <div className="login-card">
        <div className="login-header">
          <div className="login-badge-icon">🛡️</div>
          <h2>Admin Portal Login</h2>
          <p>Sign in to access AI monitoring, pipeline traces, and model management</p>
        </div>

        {error && <div className="error-alert">⚠️ {error}</div>}

        <form onSubmit={handleSubmit} className="login-form">
          <div className="form-group">
            <label className="form-label">Username:</label>
            <input
              type="text"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              placeholder="Username"
              required
              className="chat-input"
            />
          </div>

          <div className="form-group">
            <label className="form-label">Password:</label>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="Password"
              required
              className="chat-input"
            />
          </div>

          <button type="submit" disabled={loading} className="btn-primary w-full">
            {loading ? "Verifying..." : "Sign In to Admin Panel"}
          </button>
        </form>

        <div className="demo-credentials-note">
          <p><strong>Demo Superuser Credentials:</strong></p>
          <p>Username: <code>admin</code> | Password: <code>admin123</code></p>
        </div>
      </div>
    </div>
  );
}
