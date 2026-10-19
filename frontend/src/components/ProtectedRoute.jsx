import { Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";

// Phase 5, Topic 5: Protected routes — redirecting unauthenticated users to /login
export default function ProtectedRoute({ children }) {
  const { isLoggedIn } = useAuth();

  if (!isLoggedIn) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
