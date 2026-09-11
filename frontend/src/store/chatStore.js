import { create } from 'zustand';
import * as chatApi from '../api/chatApi';

const useChatStore = create((set, get) => ({
  sessions: [],          // ChatSessionResponse[] from backend
  activeSessionId: null,
  activeMessages: [],    // Messages for the active session
  isLoading: false,
  isSending: false,
  error: null,

  /**
   * Fetch all chat sessions for the current user.
   */
  fetchSessions: async () => {
    set({ isLoading: true, error: null });
    try {
      const data = await chatApi.listSessions();
      set({ sessions: data, isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: err.response?.data?.detail || 'Failed to load sessions' });
    }
  },

  /**
   * Load a specific session with all its messages.
   */
  loadSession: async (sessionId) => {
    set({ isLoading: true, activeSessionId: sessionId, error: null });
    try {
      const data = await chatApi.getSession(sessionId);
      const messages = (data.messages || []).map(mapMessageFromBackend);
      set({ activeMessages: messages, isLoading: false });
    } catch (err) {
      set({ isLoading: false, error: err.response?.data?.detail || 'Failed to load session' });
    }
  },

  /**
   * Create a new conversation/session.
   */
  createConversation: async (connectionId) => {
    set({ error: null });
    try {
      const session = await chatApi.createSession(connectionId);
      set((state) => ({
        sessions: [session, ...state.sessions],
        activeSessionId: session.id,
        activeMessages: [],
      }));
      return session.id;
    } catch (err) {
      const msg = err.response?.data?.detail || 'Failed to create session';
      set({ error: msg });
      throw err;
    }
  },

  /**
   * Send a message and receive the pipeline response.
   */
  sendMessage: async (sessionId, content) => {
    // Add optimistic user message
    const userMsg = {
      id: `temp-${Date.now()}`,
      role: 'user',
      content,
      timestamp: new Date().toISOString(),
    };
    set((state) => ({
      activeMessages: [...state.activeMessages, userMsg],
      isSending: true,
      error: null,
    }));

    try {
      const response = await chatApi.sendMessage(sessionId, content);
      const agentMsg = mapQueryResponseToMessage(response);

      set((state) => ({
        activeMessages: [...state.activeMessages, agentMsg],
        isSending: false,
      }));

      // Update session title in the sidebar list
      if (response.message?.content) {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, title: content.slice(0, 100), updated_at: new Date().toISOString() }
              : s
          ),
        }));
      }

      return response;
    } catch (err) {
      const errorMsg = err.response?.data?.detail || 'Failed to process query';
      // Add error message to chat
      const errorBubble = {
        id: `err-${Date.now()}`,
        role: 'agent',
        content: '',
        explanation: errorMsg,
        error: true,
        timestamp: new Date().toISOString(),
      };
      set((state) => ({
        activeMessages: [...state.activeMessages, errorBubble],
        isSending: false,
        error: errorMsg,
      }));
      throw err;
    }
  },

  /**
   * Delete a conversation.
   */
  deleteConversation: async (sessionId) => {
    try {
      await chatApi.deleteSession(sessionId);
      set((state) => {
        const sessions = state.sessions.filter((s) => s.id !== sessionId);
        const isActive = state.activeSessionId === sessionId;
        return {
          sessions,
          activeSessionId: isActive ? (sessions[0]?.id || null) : state.activeSessionId,
          activeMessages: isActive ? [] : state.activeMessages,
        };
      });
    } catch (err) {
      set({ error: err.response?.data?.detail || 'Failed to delete session' });
    }
  },

  setActiveSession: (id) => {
    set({ activeSessionId: id });
  },

  clearError: () => set({ error: null }),
}));

/**
 * Map a backend ChatMessageResponse to the shape expected by MessageBubble.
 */
function mapMessageFromBackend(msg) {
  const mapped = {
    id: msg.id,
    role: msg.role === 'assistant' ? 'agent' : msg.role,
    content: msg.content || '',
    timestamp: msg.created_at,
  };

  if (msg.role === 'assistant') {
    mapped.sql = msg.sql_generated || null;
    mapped.optimizedSql = msg.sql_executed || null;

    // Parse results JSON
    if (msg.results_json) {
      try {
        const parsed = JSON.parse(msg.results_json);
        if (parsed.rows && parsed.columns) {
          mapped.results = {
            columns: parsed.columns.map((name) => ({ name, type: 'string' })),
            data: parsed.rows,
          };
        }
      } catch { /* ignore parse errors */ }
    }

    mapped.rowCount = msg.result_row_count;
    mapped.executionTimeMs = msg.execution_time_ms;

    // Confidence
    if (msg.confidence_score != null) {
      const level = msg.confidence_score >= 0.8 ? 'high'
        : msg.confidence_score >= 0.5 ? 'medium' : 'low';
      mapped.confidence = {
        level,
        message: msg.confidence_reason || `${Math.round(msg.confidence_score * 100)}% confidence`,
      };
    }

    // Follow-up suggestions
    if (msg.follow_up_suggestions_json) {
      try {
        mapped.suggestedQuestions = JSON.parse(msg.follow_up_suggestions_json);
      } catch { /* ignore */ }
    }

    // Explanation
    mapped.explanation = msg.content || '';
  }

  return mapped;
}

/**
 * Map the full QueryResponse from POST /messages to a MessageBubble message.
 */
function mapQueryResponseToMessage(response) {
  const msg = {
    id: response.message?.id || `msg-${Date.now()}`,
    role: 'agent',
    content: '',
    sql: response.sql || null,
    optimizedSql: response.sql || null,
    timestamp: response.message?.created_at || new Date().toISOString(),
    explanation: response.explanation || '',
  };

  // Results
  if (response.results && response.columns) {
    msg.results = {
      columns: response.columns.map((name) => ({ name, type: 'string' })),
      data: response.results,
    };
  }

  msg.rowCount = response.row_count;
  msg.executionTimeMs = response.execution_time_ms;

  // Confidence
  if (response.confidence != null) {
    const level = response.confidence >= 0.8 ? 'high'
      : response.confidence >= 0.5 ? 'medium' : 'low';
    msg.confidence = {
      level,
      message: response.confidence_reason || `${Math.round(response.confidence * 100)}% confidence`,
    };
  }

  // Follow-up suggestions
  if (response.follow_up_suggestions) {
    msg.suggestedQuestions = response.follow_up_suggestions;
  }

  // Chart suggestion
  if (response.chart_suggestion) {
    msg.chartSuggestion = response.chart_suggestion;
  }

  // Pipeline status (always show completed for HTTP responses)
  msg.pipelineStatus = [
    { name: 'Schema', status: 'complete', detail: 'Schema analysis complete' },
    { name: 'Generate', status: 'complete', detail: 'SQL generated' },
    { name: 'Validate', status: 'complete', detail: response.was_cached ? 'Served from cache' : 'Validation passed' },
    { name: 'Optimize', status: 'complete', detail: 'Query optimized' },
    { name: 'Explain', status: 'complete', detail: 'Explanation generated' },
  ];

  return msg;
}

export default useChatStore;
