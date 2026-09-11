import { create } from 'zustand';

const useAuthStore = create((set) => ({
  user: {
    id: 'user-1',
    name: 'Demo User',
    email: 'demo@querypilot.dev',
    role: 'admin',
    permissions: ['*'],
  },
  isAuthenticated: true,

  login: (credentials) => {
    // Placeholder — will be replaced with API call
    set({
      user: {
        id: 'user-1',
        name: credentials.name || 'Demo User',
        email: credentials.email || 'demo@querypilot.dev',
        role: 'admin',
        permissions: ['*'],
      },
      isAuthenticated: true,
    });
  },

  logout: () => {
    set({ user: null, isAuthenticated: false });
  },
}));

export default useAuthStore;
