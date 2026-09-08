import { BrowserRouter, Routes, Route, useLocation, Navigate } from "react-router-dom";
import { useEffect, useState } from "react";
import Navbar from "./components/Navbar";
import BottomNav from "./components/common/BottomNav";
import MobileMoreDrawer from "./components/common/MobileMoreDrawer";
import CameraScannerModal from "./components/common/CameraScannerModal";
import Home from "./pages/Home";
import Dashboard from "./pages/Dashboard";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Recommendations from "./pages/Recommendations";
import Weather from "./pages/Weather";
import Market from "./pages/Market";
import Forum from "./pages/Forum";
import AITools from "./pages/AITools";
import Marketplace from "./pages/Marketplace";
import KisanChat from "./pages/KisanChat";
import PredictiveYield from "./pages/PredictiveYield";
import History from "./pages/History";
import ProtectedRoute from "./components/ProtectedRoute";
import Admin from "./pages/Admin";
import { ThemeProvider } from "./context/ThemeContext";
import { LanguageProvider } from "./context/LanguageContext";
import { HistoryProvider } from "./context/HistoryContext";
import { useAuth } from "./context/AuthContext";

// Offline notification banner rendered inside router context
const OfflineBar = () => {
  const [isOnline, setIsOnline] = useState(navigator.onLine);
  useEffect(() => {
    const on = () => setIsOnline(true);
    const off = () => setIsOnline(false);
    window.addEventListener("online", on);
    window.addEventListener("offline", off);
    return () => {
      window.removeEventListener("online", on);
      window.removeEventListener("offline", off);
    };
  }, []);
  if (isOnline) return null;
  return (
    <div className="offline-bar" role="alert">
      📡 Offline Field Mode: Showing cached data. Reconnect for real-time AI scan.
    </div>
  );
};

const MainLayout = ({ children }) => {
  const [isCameraOpen, setIsCameraOpen] = useState(false);
  const [isMoreOpen, setIsMoreOpen] = useState(false);

  return (
    <>
      <Navbar />
      <OfflineBar />
      {children}
      <BottomNav
        onOpenScan={() => setIsCameraOpen(true)}
        onOpenMore={() => setIsMoreOpen(true)}
      />
      <MobileMoreDrawer
        isOpen={isMoreOpen}
        onClose={() => setIsMoreOpen(false)}
      />
      <CameraScannerModal
        isOpen={isCameraOpen}
        onClose={() => setIsCameraOpen(false)}
      />
    </>
  );
};

const App = () => {
  return (
    <ThemeProvider>
      <LanguageProvider>
        <HistoryProvider>
          <BrowserRouter>
            <MainLayout>
              <Routes>
                <Route path="/" element={<Home />} />
                <Route path="/home" element={<Home />} />
                <Route path="/dashboard" element={<ProtectedRoute><Dashboard /></ProtectedRoute>} />
                <Route path="/recommendations" element={<ProtectedRoute><Recommendations /></ProtectedRoute>} />
                <Route path="/weather" element={<ProtectedRoute><Weather /></ProtectedRoute>} />
                <Route path="/market" element={<ProtectedRoute><Market /></ProtectedRoute>} />
                <Route path="/forum" element={<ProtectedRoute><Forum /></ProtectedRoute>} />
                <Route path="/ai-tools" element={<ProtectedRoute><AITools /></ProtectedRoute>} />
                <Route path="/marketplace" element={<ProtectedRoute><Marketplace /></ProtectedRoute>} />
                <Route path="/predictive-yield" element={<ProtectedRoute><PredictiveYield /></ProtectedRoute>} />
                <Route path="/history" element={<ProtectedRoute><History /></ProtectedRoute>} />
                <Route path="/chat" element={<ProtectedRoute><KisanChat /></ProtectedRoute>} />
                <Route path="/admin" element={<ProtectedRoute><Admin /></ProtectedRoute>} />
                <Route path="/login" element={<Login />} />
                <Route path="/register" element={<Register />} />
              </Routes>
            </MainLayout>
          </BrowserRouter>
        </HistoryProvider>
      </LanguageProvider>
    </ThemeProvider>
  );
};

export default App;
