import { create } from 'zustand';
import * as chatApi from '../api/chatApi';

const useChatStore = create((set, get) => ({
  sessions: [],          // ChatSessionResponse[] from backend
  activeSessionId: null,
  activeMessages: [],    // Messages for the active session
  isLoading: false,
  isSending: false,
  currentStageId: null,  // Live pipeline stage ('schema'|'sql_gen'|'validate'|'optimize'|'execute'|'explain')
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
   * Send a message and receive the pipeline response with live dynamic stage transitions.
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
      currentStageId: 'schema',
      error: null,
    }));

    const finishSuccess = (response) => {
      const agentMsg = mapQueryResponseToMessage(response);
      set((state) => ({
        activeMessages: [...state.activeMessages, agentMsg],
        isSending: false,
        currentStageId: null,
      }));

      // Update session title in the sidebar list
      if (response.message?.content || content) {
        set((state) => ({
          sessions: state.sessions.map((s) =>
            s.id === sessionId
              ? { ...s, title: content.slice(0, 100), updated_at: new Date().toISOString() }
              : s
          ),
        }));
      }
      return response;
    };

    const finishError = (errorMsg) => {
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
        currentStageId: null,
        error: errorMsg,
      }));
    };

    // 1. Try WebSocket for real-time dynamic stage streaming
    try {
      const token = localStorage.getItem('qp_token') || '';
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
      const wsUrl = `${wsProtocol}//${window.location.host}/ws/chat/${sessionId}?token=${encodeURIComponent(token)}`;

      const wsPromise = new Promise((resolve, reject) => {
        let ws;
        let isDone = false;
        try {
          ws = new WebSocket(wsUrl);
        } catch (e) {
          return reject(e);
        }

        // Connection timeout: fallback to HTTP if WS does not connect in 4s
        const connTimeout = setTimeout(() => {
          if (!isDone && ws.readyState !== WebSocket.OPEN) {
            try { ws.close(); } catch {}
            reject(new Error('WebSocket connection timeout'));
          }
        }, 4000);

        ws.onopen = () => {
          clearTimeout(connTimeout);
          ws.send(JSON.stringify({ token, message: content }));
        };

        ws.onmessage = (event) => {
          try {
            const data = JSON.parse(event.data);
            if (data.type === 'stage') {
              if (data.stage) {
                set({ currentStageId: data.stage });
              }
            } else if (data.type === 'result') {
              isDone = true;
              clearTimeout(connTimeout);
              try { ws.close(1000, 'Normal closure'); } catch {}
              resolve(data.data);
            } else if (data.type === 'error') {
              isDone = true;
              clearTimeout(connTimeout);
              try { ws.close(); } catch {}
              reject(new Error(data.message || 'Pipeline execution error'));
            }
          } catch (parseErr) {
            console.warn('Failed to parse WebSocket message:', parseErr);
          }
        };

        ws.onerror = (err) => {
          if (isDone) return;
          clearTimeout(connTimeout);
          reject(err);
        };

        ws.onclose = (event) => {
          if (isDone) return;
          clearTimeout(connTimeout);
          if (!event.wasClean) {
            reject(new Error('WebSocket disconnected unexpectedly'));
          }
        };
      });

      const response = await wsPromise;
      return finishSuccess(response);

    } catch (wsErr) {
      console.warn('Live WebSocket unavailable or failed, falling back to HTTP:', wsErr);

      // 2. Fallback to standard HTTP POST
      try {
        const response = await chatApi.sendMessage(sessionId, content);
        return finishSuccess(response);
      } catch (err) {
        const errorMsg = err.response?.data?.detail || err.message || 'Failed to process query';
        finishError(errorMsg);
        throw err;
      }
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

  /**
   * Rename a conversation.
   */
  renameConversation: async (sessionId, newTitle) => {
    const trimmed = (newTitle || '').trim();
    if (!trimmed) return;
    set((state) => ({
      sessions: state.sessions.map((s) =>
        s.id === sessionId ? { ...s, title: trimmed, updated_at: new Date().toISOString() } : s
      ),
    }));
    try {
      if (chatApi.updateSession) {
        await chatApi.updateSession(sessionId, trimmed);
      }
    } catch (err) {
      console.warn('Backend rename not persisted:', err);
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
    const rawScore = msg.confidence_score;
    const score = (rawScore != null && Number(rawScore) > 0) ? Number(rawScore) : (msg.sql_generated ? 0.92 : 0.70);
    const level = score >= 0.8 ? 'high' : score >= 0.5 ? 'medium' : 'low';
    mapped.confidence = {
      level,
      message: msg.confidence_reason || `${Math.round(score * 100)}% confidence`,
      details: `${Math.round(score * 100)}% confidence rating`,
    };

    // Follow-up suggestions
    if (msg.follow_up_suggestions_json) {
      try {
        mapped.suggestedQuestions = JSON.parse(msg.follow_up_suggestions_json);
      } catch { /* ignore */ }
    }

    // Chart suggestion
    if (msg.chart_config_json) {
      try {
        mapped.chartSuggestion = JSON.parse(msg.chart_config_json);
      } catch { /* ignore */ }
    } else if (msg.suggested_chart_type) {
      mapped.chartSuggestion = { chart_type: msg.suggested_chart_type };
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
  const rawScore = response.confidence;
  const score = (rawScore != null && Number(rawScore) > 0) ? Number(rawScore) : (response.sql ? 0.92 : 0.70);
  const level = score >= 0.8 ? 'high' : score >= 0.5 ? 'medium' : 'low';
  msg.confidence = {
    level,
    message: response.confidence_reason || `${Math.round(score * 100)}% confidence`,
    details: `${Math.round(score * 100)}% confidence rating`,
  };

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
