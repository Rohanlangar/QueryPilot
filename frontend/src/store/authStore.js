import { create } from 'zustand';
import * as authApi from '../api/authApi';

const useAuthStore = create((set, get) => ({
  user: null,
  token: localStorage.getItem('qp_token') || null,
  isAuthenticated: false,
  isLoading: true, // true until initial check completes
  error: null,

  /**
   * Initialize auth state from persisted token.
   * Called once on app mount.
   */
  initialize: async () => {
    const token = localStorage.getItem('qp_token');
    if (!token) {
      set({ isLoading: false, isAuthenticated: false });
      return;
    }
    try {
      const user = await authApi.getMe();
      set({ user, token, isAuthenticated: true, isLoading: false, error: null });
    } catch {
      // Token expired or invalid
      localStorage.removeItem('qp_token');
      set({ user: null, token: null, isAuthenticated: false, isLoading: false });
    }
  },

  /**
   * Register a new user, then auto-login.
   */
  register: async ({ email, username, password, fullName }) => {
    set({ isLoading: true, error: null });
    try {
      await authApi.register({ email, username, password, fullName });
      // Auto-login after successful registration
      await get().login({ username, password });
    } catch (err) {
      const msg = err.response?.data?.detail || 'Registration failed';
      set({ isLoading: false, error: msg });
      throw err;
    }
  },

  /**
   * Login with username/password, store JWT, fetch user profile.
   */
  login: async ({ username, password }) => {
    set({ isLoading: true, error: null });
    try {
      const tokenData = await authApi.login({ username, password });
      const token = tokenData.access_token;
      localStorage.setItem('qp_token', token);
      set({ token });

      const user = await authApi.getMe();
      set({ user, isAuthenticated: true, isLoading: false, error: null });
    } catch (err) {
      localStorage.removeItem('qp_token');
      const msg = err.response?.data?.detail || 'Login failed';
      set({ user: null, token: null, isAuthenticated: false, isLoading: false, error: msg });
      throw err;
    }
  },

  /**
   * Clear all auth state and redirect.
   */
  logout: () => {
    localStorage.removeItem('qp_token');
    set({ user: null, token: null, isAuthenticated: false, error: null });
  },

  clearError: () => set({ error: null }),
}));

export default useAuthStore;
