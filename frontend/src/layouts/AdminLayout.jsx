import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Phase 4 Topic 3: Shared Admin Layout with dark sidebar and <Outlet />
export default function AdminLayout() {
  const { logout } = useAuth();
  const navigate = useNavigate();

  function handleLogout() {
    logout();
    navigate("/login");
  }

  return (
    <div className="admin-shell">
      {/* Dark Sidebar (Matches uploaded mockup design) */}
      <aside className="admin-sidebar">
        <div className="sidebar-brand">
          <span className="brand-shield">🛡️</span>
          <span className="brand-title">Admin Panel</span>
        </div>

        <nav className="sidebar-nav">
          <NavLink
            to="/admin"
            end
            className={({ isActive }) =>
              isActive ? "sidebar-link active" : "sidebar-link"
            }
          >
            <span className="sidebar-icon">📊</span>
            Dashboard
          </NavLink>

          <NavLink
            to="/admin/requests"
            className={({ isActive }) =>
              isActive ? "sidebar-link active" : "sidebar-link"
            }
          >
            <span className="sidebar-icon">📋</span>
            Requests & Logs
          </NavLink>

          <NavLink
            to="/admin/models"
            className={({ isActive }) =>
              isActive ? "sidebar-link active" : "sidebar-link"
            }
          >
            <span className="sidebar-icon">⚙️</span>
            AI Models
          </NavLink>

          <NavLink
            to="/admin/documents"
            className={({ isActive }) =>
              isActive ? "sidebar-link active" : "sidebar-link"
            }
          >
            <span className="sidebar-icon">📁</span>
            Documents
          </NavLink>
        </nav>

        {/* Bottom Actions */}
        <div className="sidebar-footer">
          <NavLink to="/" className="sidebar-link return-chat-link">
            <span className="sidebar-icon">💬</span>
            Customer Chat
          </NavLink>

          <button onClick={handleLogout} className="sidebar-logout-btn">
            <span className="sidebar-icon">🚪</span>
            Logout
          </button>
        </div>
      </aside>

      {/* Main Content Area */}
      <main className="admin-main-content">
        <Outlet />
      </main>
    </div>
  );
}
