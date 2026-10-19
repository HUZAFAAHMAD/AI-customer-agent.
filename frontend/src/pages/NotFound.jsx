import { useNavigate } from "react-router-dom";

// Phase 4 Topic 5: 404 — catch-all route
export default function NotFound() {
  const navigate = useNavigate();

  return (
    <div className="notfound-container">
      <div className="notfound-card">
        <h1>404</h1>
        <h2>Page Not Found</h2>
        <p>The page you are looking for does not exist or has moved.</p>
        <button onClick={() => navigate("/")} className="btn-primary">
          Return to Customer Support
        </button>
      </div>
    </div>
  );
}
