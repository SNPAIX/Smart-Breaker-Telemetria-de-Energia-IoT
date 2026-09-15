import { Toaster } from "react-hot-toast";
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
    <>
      <Toaster
        position="top-center"
        containerStyle={{ top: "calc(env(safe-area-inset-top, 0px) + 70px)" }}
        toastOptions={{
          style: {
            background: "rgba(23, 16, 41, 0.92)",
            color: "white",
            backdropFilter: "blur(10px)",
            borderRadius: "14px",
            fontSize: "0.85rem",
          },
          success: { iconTheme: { primary: "#14b881", secondary: "white" } },
          error: { iconTheme: { primary: "#e0304a", secondary: "white" }, duration: 5000 },
        }}
      />
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
    </>
  );
}

export default App;
