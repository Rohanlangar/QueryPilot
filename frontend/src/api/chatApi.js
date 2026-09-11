/**
 * QueryPilot — Chat API
 *
 * Sessions, messages (main pipeline query), and SQL explanation.
 */

import api from './api';

// ── Sessions ─────────────────────────────────────────────────

export async function createSession(connectionId, title) {
  const { data } = await api.post('/api/chat/sessions', {
    connection_id: connectionId,
    title: title || 'New Conversation',
  });
  return data; // ChatSessionResponse
}

export async function listSessions() {
  const { data } = await api.get('/api/chat/sessions');
  return data; // ChatSessionResponse[]
}

export async function getSession(sessionId) {
  const { data } = await api.get(`/api/chat/sessions/${sessionId}`);
  return data; // ChatSessionDetailResponse (includes messages[])
}

export async function deleteSession(sessionId) {
  await api.delete(`/api/chat/sessions/${sessionId}`);
}

// ── Messages (Main Query Pipeline) ──────────────────────────

export async function sendMessage(sessionId, content) {
  const { data } = await api.post(`/api/chat/sessions/${sessionId}/messages`, {
    content,
  });
  return data; // QueryResponse
}

// ── SQL Explanation ──────────────────────────────────────────

export async function explainSQL(sql, connectionId = null) {
  const { data } = await api.post('/api/chat/explain-sql', {
    sql,
    connection_id: connectionId,
  });
  return data; // ExplainSQLResponse
}
