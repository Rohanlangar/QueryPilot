import React, { useState } from 'react';
import { BrowserRouter, Routes, Route, useLocation } from 'react-router-dom';
import Navbar from './components/layout/Navbar';
import LandingPage from './pages/LandingPage';
import ChatPage from './pages/ChatPage';
import ExplainPage from './pages/ExplainPage';
import ConnectionsPage from './pages/ConnectionsPage';
import AuditPage from './pages/AuditPage';
import SettingsPage from './pages/SettingsPage';

function AppLayout() {
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(true);
  const isLanding = location.pathname === '/';

  return (
    <>
      {!isLanding && (
        <Navbar
          onToggleSidebar={() => setSidebarOpen((s) => !s)}
          sidebarOpen={sidebarOpen}
        />
      )}
      <Routes>
        <Route path="/" element={<LandingPage />} />
        <Route path="/chat" element={<ChatPage />} />
        <Route path="/chat/:id" element={<ChatPage />} />
        <Route path="/explain" element={<ExplainPage />} />
        <Route path="/connections" element={<ConnectionsPage />} />
        <Route path="/audit" element={<AuditPage />} />
        <Route path="/settings" element={<SettingsPage />} />
      </Routes>
    </>
  );
}

export default function App() {
  return (
    <BrowserRouter>
      <AppLayout />
    </BrowserRouter>
  );
}
