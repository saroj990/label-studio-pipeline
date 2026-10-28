import { Navigate, Route, Routes } from "react-router-dom";
import { getToken } from "./api";
import LoginPage from "./pages/LoginPage";
import ProjectsPage from "./pages/ProjectsPage";
import ProjectWorkspacePage from "./pages/ProjectWorkspacePage";
import TestPage from "./pages/TestPage";

function RequireAuth({ children }: { children: React.ReactNode }) {
  if (!getToken()) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />
      <Route
        path="/"
        element={
          <RequireAuth>
            <ProjectsPage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:projectId"
        element={
          <RequireAuth>
            <ProjectWorkspacePage />
          </RequireAuth>
        }
      />
      <Route
        path="/projects/:projectId/test"
        element={
          <RequireAuth>
            <TestPage />
          </RequireAuth>
        }
      />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  );
}
