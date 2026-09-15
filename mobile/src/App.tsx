import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { SiteDevicesPage } from "./pages/SiteDevicesPage";
import { SitesPage } from "./pages/SitesPage";

function App() {
  return (
    <Routes>
      <Route path="/login" element={<LoginPage />} />

      <Route
        path="/sites"
        element={
          <ProtectedRoute>
            <Layout>
              <SitesPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/sites/:siteId"
        element={
          <ProtectedRoute>
            <Layout>
              <SiteDevicesPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/devices/:deviceId"
        element={
          <ProtectedRoute>
            <Layout>
              <DeviceDetailPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/notifications"
        element={
          <ProtectedRoute>
            <Layout>
              <NotificationsPage />
            </Layout>
          </ProtectedRoute>
        }
      />

      <Route path="/" element={<Navigate to="/sites" replace />} />
      <Route path="*" element={<Navigate to="/sites" replace />} />
    </Routes>
  );
}

export default App;
