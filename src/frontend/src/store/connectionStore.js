import { create } from 'zustand';
import * as connectionsApi from '../api/connectionsApi';

const useConnectionStore = create((set, get) => ({
  connections: [],
  activeConnectionId: null,
  isLoading: false,
  error: null,

  /**
   * Fetch all connections from the backend.
   */
  fetchConnections: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await connectionsApi.listConnections();
      // Map backend shape to frontend shape
      const connections = data.map(mapConnectionFromBackend);
      set({ connections, isLoading: false });
      // Auto-set active connection if none is set
      if (!get().activeConnectionId && connections.length > 0) {
        set({ activeConnectionId: connections[0].id });
      }
    } catch (err) {
      set({ isLoading: false, error: err.response?.data?.detail || 'Failed to load connections' });
    }
  },

  /**
   * Create a new connection via the API.
   */
  addConnection: async (config) => {
    set({ error: null });
    try {
      const data = await connectionsApi.createConnection(config);
      const conn = mapConnectionFromBackend(data);
      set((state) => ({
        connections: [...state.connections, conn],
      }));
      if (!get().activeConnectionId) {
        set({ activeConnectionId: conn.id });
      }
      return conn.id;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to create connection';
      set({ error: msg });
      throw err;
    }
  },

  /**
   * Update an existing connection via the API.
   */
  updateConnection: async (id, updates) => {
    set({ error: null });
    try {
      const data = await connectionsApi.updateConnection(id, updates);
      const updated = mapConnectionFromBackend(data);
      set((state) => ({
        connections: state.connections.map((c) => (c.id === id ? updated : c)),
      }));
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to update connection';
      set({ error: msg });
      throw err;
    }
  },

  /**
   * Delete a connection via the API.
   */
  removeConnection: async (id) => {
    set({ error: null });
    try {
      await connectionsApi.deleteConnection(id);
      set((state) => ({
        connections: state.connections.filter((c) => c.id !== id),
        activeConnectionId:
          state.activeConnectionId === id ? null : state.activeConnectionId,
      }));
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to delete connection';
      set({ error: msg });
      throw err;
    }
  },

  /**
   * Test a connection via the API.
   */
  testConnection: async (id) => {
    // Optimistic: set testing status
    set((state) => ({
      connections: state.connections.map((c) =>
        c.id === id ? { ...c, status: 'testing' } : c
      ),
    }));
    try {
      const result = await connectionsApi.testConnection(id);
      set((state) => ({
        connections: state.connections.map((c) =>
          c.id === id
            ? {
                ...c,
                status: result.success ? 'connected' : 'disconnected',
                lastTested: new Date().toISOString(),
                testMessage: result.message,
                latencyMs: result.latency_ms,
              }
            : c
        ),
      }));
      return result;
    } catch (err) {
      set((state) => ({
        connections: state.connections.map((c) =>
          c.id === id ? { ...c, status: 'disconnected' } : c
        ),
      }));
      return { success: false, message: err.response?.data?.detail || 'Test failed' };
    }
  },

  /**
   * Fetch schema for a connection.
   */
  fetchSchema: async (id) => {
    try {
      const data = await connectionsApi.getConnectionSchema(id);
      set((state) => ({
        connections: state.connections.map((c) =>
          c.id === id ? { ...c, schema: data } : c
        ),
      }));
      return data;
    } catch (err) {
      console.error('Failed to fetch schema:', err);
      return null;
    }
  },

  setActiveConnection: (id) => {
    set({ activeConnectionId: id });
  },

  toggleConnectionActive: async (id) => {
    const conn = get().connections.find((c) => c.id === id);
    if (!conn) return;
    const nextState = !conn.isActive;
    // Optimistic update
    set((state) => ({
      connections: state.connections.map((c) =>
        c.id === id ? { ...c, isActive: nextState } : c
      ),
    }));
    try {
      await connectionsApi.toggleConnectionActive(id);
    } catch (err) {
      // Revert on error
      set((state) => ({
        connections: state.connections.map((c) =>
          c.id === id ? { ...c, isActive: !nextState } : c
        ),
      }));
    }
  },

  getActiveConnection: () => {
    const state = get();
    return state.connections.find((c) => c.id === state.activeConnectionId) || state.connections.find((c) => c.isActive) || null;
  },

  getActiveConnections: () => {
    const state = get();
    return state.connections.filter((c) => c.isActive !== false);
  },
}));

/**
 * Map backend ConnectionResponse to frontend connection shape.
 */
function mapConnectionFromBackend(conn) {
  return {
    id: conn.id,
    name: conn.name,
    dbType: conn.db_type,
    host: conn.host,
    port: conn.port,
    database: conn.database_name,
    username: conn.username,
    ssl: conn.ssl_enabled,
    isActive: conn.is_active !== undefined ? Boolean(conn.is_active) : true,
    status: conn.last_tested_at ? 'connected' : 'connected',
    lastTested: conn.last_tested_at || null,
    schema: null,
    createdAt: conn.created_at,
    updatedAt: conn.updated_at,
  };
}

export default useConnectionStore;
