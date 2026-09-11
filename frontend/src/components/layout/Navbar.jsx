import React from 'react';
import { NavLink, Link } from 'react-router-dom';
import { Database, Menu, X } from 'lucide-react';

export default function Navbar({ onToggleSidebar, sidebarOpen }) {
  return (
    <nav className="navbar" role="navigation" aria-label="Main navigation">
      <div className="flex items-center gap-sm">
        <button
          className="navbar-hamburger"
          onClick={onToggleSidebar}
          aria-label={sidebarOpen ? 'Close sidebar' : 'Open sidebar'}
        >
          {sidebarOpen ? <X size={22} /> : <Menu size={22} />}
        </button>

        <Link to="/chat" className="navbar-brand">
          <span className="navbar-brand-icon">
            <Database size={18} />
          </span>
          <span className="navbar-brand-text">QueryPilot</span>
        </Link>
      </div>

      <div className="navbar-nav">
        <NavLink
          to="/chat"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          CHAT
        </NavLink>
        <NavLink
          to="/explain"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          EXPLAIN
        </NavLink>
        <NavLink
          to="/connections"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          CONNECTIONS
        </NavLink>
        <NavLink
          to="/audit"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          AUDIT
        </NavLink>
        <NavLink
          to="/settings"
          className={({ isActive }) => `navbar-link ${isActive ? 'active' : ''}`}
        >
          SETTINGS
        </NavLink>
      </div>

      <div className="navbar-actions">
        {/* Placeholder for user avatar / auth controls */}
      </div>
    </nav>
  );
}
