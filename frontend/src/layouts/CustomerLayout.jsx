import { NavLink, Outlet } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Phase 4 Topic 3: Shared layout with <Outlet />
export default function CustomerLayout() {
  const { isLoggedIn, logout } = useAuth();

  return (
    <div className="app-shell customer-shell">
      {/* Top Navigation Bar */}
      <header className="customer-topbar">
        <div className="brand-logo">
          <span className="logo-icon">🤖</span>
          <span className="logo-text">SupportAI</span>
          <span className="brand-tag">Customer Portal</span>
        </div>

        <nav className="topbar-nav">
          <NavLink
            to="/"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            💬 Support Chat
          </NavLink>
          <NavLink
            to="/admin"
            className={({ isActive }) => (isActive ? "nav-link active" : "nav-link")}
          >
            🛡️ Admin Panel
          </NavLink>

          {isLoggedIn ? (
            <button onClick={logout} className="btn-logout-small">
              Logout
            </button>
          ) : (
            <NavLink to="/login" className="nav-link login-pill">
              Admin Login
            </NavLink>
          )}
        </nav>
      </header>

      {/* Main Content (Phase 4 Topic 3: <Outlet /> mirrors {% block content %}) */}
      <main className="customer-main">
        <Outlet />
      </main>
    </div>
  );
}
