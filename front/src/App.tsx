import { Navigate, Route, Routes } from "react-router-dom";

import { ProtectedRoute } from "./auth/ProtectedRoute";
import { Layout } from "./components/Layout";
import { DeviceDetailPage } from "./pages/DeviceDetailPage";
import { LoginPage } from "./pages/LoginPage";
import { NotificationsPage } from "./pages/NotificationsPage";
import { SiteDevicesPage } from "./pages/SiteDevicesPage";
import { SitesPage } from "./pages/SitesPage";
import { AdminDashboardPage } from "./pages/admin/AdminDashboardPage";
import { AdminDevicesPage } from "./pages/admin/AdminDevicesPage";
import { AdminSitesPage } from "./pages/admin/AdminSitesPage";
import { AdminUsersPage } from "./pages/admin/AdminUsersPage";

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

      <Route
        path="/admin"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <AdminDashboardPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/users"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <AdminUsersPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/sites"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <AdminSitesPage />
            </Layout>
          </ProtectedRoute>
        }
      />
      <Route
        path="/admin/devices"
        element={
          <ProtectedRoute adminOnly>
            <Layout>
              <AdminDevicesPage />
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
