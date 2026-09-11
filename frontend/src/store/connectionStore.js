import { create } from 'zustand';

const useConnectionStore = create((set, get) => ({
  connections: [],
  activeConnectionId: null,

  addConnection: (config) => {
    const id = `conn-${Date.now()}`;
    const newConn = {
      id,
      ...config,
      status: 'disconnected',
      lastTested: null,
      schema: null,
    };
    set((state) => ({
      connections: [...state.connections, newConn],
    }));
    return id;
  },

  updateConnection: (id, updates) => {
    set((state) => ({
      connections: state.connections.map((c) =>
        c.id === id ? { ...c, ...updates } : c
      ),
    }));
  },

  removeConnection: (id) => {
    set((state) => ({
      connections: state.connections.filter((c) => c.id !== id),
      activeConnectionId:
        state.activeConnectionId === id ? null : state.activeConnectionId,
    }));
  },

  setActiveConnection: (id) => {
    set({ activeConnectionId: id });
  },

  testConnection: async (id) => {
    const { updateConnection } = get();
    updateConnection(id, { status: 'testing' });
    // Simulate test — will be replaced with API call
    setTimeout(() => {
      updateConnection(id, {
        status: 'connected',
        lastTested: new Date().toISOString(),
      });
    }, 1500);
  },

  setSchema: (id, schema) => {
    const { updateConnection } = get();
    updateConnection(id, { schema });
  },

  getActiveConnection: () => {
    const state = get();
    return state.connections.find((c) => c.id === state.activeConnectionId) || null;
  },
}));

export default useConnectionStore;
