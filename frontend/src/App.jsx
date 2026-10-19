import { BrowserRouter, Routes, Route } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import ProtectedRoute from "./components/ProtectedRoute";

import CustomerLayout from "./layouts/CustomerLayout";
import AdminLayout from "./layouts/AdminLayout";

import CustomerChat from "./pages/CustomerChat";
import AdminDashboard from "./pages/AdminDashboard";
import AdminRequests from "./pages/AdminRequests";
import AIModels from "./pages/AIModels";
import AdminDocuments from "./pages/AdminDocuments";
import LoginPage from "./pages/LoginPage";
import NotFound from "./pages/NotFound";

import "./App.css";

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          {/* Customer Side */}
          <Route path="/" element={<CustomerLayout />}>
            <Route index element={<CustomerChat />} />
          </Route>

          {/* Admin Login */}
          <Route path="/login" element={<LoginPage />} />

          {/* Protected Admin Side */}
          <Route
            path="/admin"
            element={
              <ProtectedRoute>
                <AdminLayout />
              </ProtectedRoute>
            }
          >
            <Route index element={<AdminDashboard />} />
            <Route path="requests" element={<AdminRequests />} />
            <Route path="models" element={<AIModels />} />
            <Route path="documents" element={<AdminDocuments />} />
          </Route>

          {/* 404 Catch-All Route */}
          <Route path="*" element={<NotFound />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  );
}
