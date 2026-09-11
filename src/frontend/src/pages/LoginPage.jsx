import React, { useState } from 'react';
import { useNavigate, useLocation, Link } from 'react-router-dom';
import { Database, Lock, User, Mail, ArrowRight } from 'lucide-react';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Card from '../components/common/Card';
import useAuthStore from '../store/authStore';

export default function LoginPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const from = location.state?.from?.pathname || '/chat';

  const [mode, setMode] = useState('login'); // 'login' | 'register'
  const [username, setUsername] = useState('admin');
  const [password, setPassword] = useState('admin123');
  const [email, setEmail] = useState('');
  const [fullName, setFullName] = useState('');

  const { login, register, isLoading, error, clearError } = useAuthStore();

  const handleSubmit = async (e) => {
    e.preventDefault();
    clearError();
    try {
      if (mode === 'login') {
        await login({ username, password });
      } else {
        await register({ username, password, email, fullName });
      }
      navigate(from, { replace: true });
    } catch (err) {
      // error is handled in store
    }
  };

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--color-background)',
        padding: '24px',
      }}
    >
      <div style={{ width: '100%', maxWidth: '420px' }}>
        <div style={{ textAlign: 'center', marginBottom: '28px' }}>
          <div
            style={{
              display: 'inline-flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '48px',
              height: '48px',
              borderRadius: '12px',
              background: 'var(--color-primary-dim)',
              color: 'var(--color-primary)',
              marginBottom: '12px',
            }}
          >
            <Database size={24} />
          </div>
          <h1 className="text-display-sm" style={{ fontWeight: 600 }}>QueryPilot</h1>
          <p className="text-body-sm text-muted" style={{ marginTop: '6px' }}>
            Autonomous Multi-Agent SQL Intelligence
          </p>
        </div>

        <Card variant="default">
          <div
            style={{
              display: 'flex',
              borderBottom: '1px solid var(--color-border)',
              marginBottom: '20px',
            }}
          >
            <button
              type="button"
              onClick={() => { setMode('login'); clearError(); }}
              style={{
                flex: 1,
                padding: '10px',
                textAlign: 'center',
                background: 'none',
                border: 'none',
                borderBottom: mode === 'login' ? '2px solid var(--color-primary)' : '2px solid transparent',
                color: mode === 'login' ? 'var(--color-text)' : 'var(--color-muted)',
                fontWeight: mode === 'login' ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              Sign In
            </button>
            <button
              type="button"
              onClick={() => { setMode('register'); clearError(); }}
              style={{
                flex: 1,
                padding: '10px',
                textAlign: 'center',
                background: 'none',
                border: 'none',
                borderBottom: mode === 'register' ? '2px solid var(--color-primary)' : '2px solid transparent',
                color: mode === 'register' ? 'var(--color-text)' : 'var(--color-muted)',
                fontWeight: mode === 'register' ? 600 : 400,
                cursor: 'pointer',
              }}
            >
              Create Account
            </button>
          </div>

          {error && (
            <div
              style={{
                padding: '10px 14px',
                marginBottom: '16px',
                borderRadius: 'var(--radius-md)',
                background: 'rgba(239, 68, 68, 0.1)',
                border: '1px solid rgba(239, 68, 68, 0.3)',
                color: 'var(--color-error)',
                fontSize: '13px',
              }}
            >
              {error}
            </div>
          )}

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: '14px' }}>
            {mode === 'register' && (
              <>
                <Input
                  label="Full Name"
                  placeholder="Alex Mercer"
                  value={fullName}
                  onChange={(e) => setFullName(e.target.value)}
                />
                <Input
                  label="Email"
                  type="email"
                  placeholder="alex@example.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  required
                />
              </>
            )}

            <Input
              label="Username"
              placeholder="Username"
              value={username}
              onChange={(e) => setUsername(e.target.value)}
              required
            />

            <Input
              label="Password"
              type="password"
              placeholder="••••••••"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
            />

            <div style={{ marginTop: '10px' }}>
              <Button
                type="submit"
                variant="primary"
                fullWidth
                loading={isLoading}
                icon={ArrowRight}
              >
                {mode === 'login' ? 'Sign In' : 'Create Account'}
              </Button>
            </div>
          </form>

          {mode === 'login' && (
            <div
              style={{
                marginTop: '16px',
                padding: '10px',
                borderRadius: 'var(--radius-sm)',
                background: 'var(--color-surface)',
                border: '1px solid var(--color-border)',
                fontSize: '12px',
                color: 'var(--color-muted)',
                textAlign: 'center',
              }}
            >
              Default Credentials: <code style={{ color: 'var(--color-primary)' }}>admin</code> / <code style={{ color: 'var(--color-primary)' }}>admin123</code>
            </div>
          )}
        </Card>

        <div style={{ textAlign: 'center', marginTop: '18px' }}>
          <Link to="/" style={{ fontSize: '13px', color: 'var(--color-muted)', textDecoration: 'none' }}>
            &larr; Back to QueryPilot Overview
          </Link>
        </div>
      </div>
    </div>
  );
}
