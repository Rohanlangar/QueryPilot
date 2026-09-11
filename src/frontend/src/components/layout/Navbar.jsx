import React from 'react';
import { NavLink, Link, useNavigate } from 'react-router-dom';
import { Database, Menu, X, User as UserIcon, LogOut, LogIn } from 'lucide-react';
import useAuthStore from '../../store/authStore';

export default function Navbar({ onToggleSidebar, sidebarOpen }) {
  const { user, isAuthenticated, logout } = useAuthStore();
  const navigate = useNavigate();

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

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

      <div className="navbar-actions" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        {isAuthenticated ? (
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <span
              style={{
                fontSize: '12px',
                color: 'var(--color-muted)',
                display: 'flex',
                alignItems: 'center',
                gap: '5px',
              }}
            >
              <UserIcon size={14} />
              {user?.username || 'user'}
            </span>
            <button
              onClick={handleLogout}
              title="Sign Out"
              style={{
                background: 'none',
                border: 'none',
                color: 'var(--color-muted)',
                cursor: 'pointer',
                padding: '4px',
                display: 'flex',
                alignItems: 'center',
              }}
            >
              <LogOut size={16} />
            </button>
          </div>
        ) : (
          <Link
            to="/login"
            style={{
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              fontSize: '12px',
              color: 'var(--color-primary)',
              textDecoration: 'none',
              padding: '6px 12px',
              borderRadius: 'var(--radius-sm)',
              border: '1px solid var(--color-border)',
            }}
          >
            <LogIn size={14} />
            <span>Sign In</span>
          </Link>
        )}
      </div>
    </nav>
  );
}
