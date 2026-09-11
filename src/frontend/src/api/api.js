/**
 * QueryPilot — Central API Client
 *
 * Axios instance pre-configured with:
 *  - Base URL (uses Vite proxy in dev, or env var in prod)
 *  - Automatic Authorization header injection from localStorage
 *  - 401 response interceptor → clears token & redirects to /login
 */

import axios from 'axios';

const API_BASE = import.meta.env.VITE_API_URL || '';

const api = axios.create({
  baseURL: API_BASE,
  headers: { 'Content-Type': 'application/json' },
  timeout: 120_000, // 2 min — pipeline can be slow
});

// ── Request Interceptor: inject JWT ──────────────────────────
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('qp_token');
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

// ── Response Interceptor: handle 401 ─────────────────────────
api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('qp_token');
      // Only redirect if we're not already on the login page
      if (window.location.pathname !== '/login') {
        window.location.href = '/login';
      }
    }
    return Promise.reject(error);
  },
);

export default api;
