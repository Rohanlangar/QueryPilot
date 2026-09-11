/**
 * QueryPilot — Audit API
 *
 * Paginated audit logs and aggregate statistics.
 */

import api from './api';

export async function getAuditLogs({
  userId,
  sessionId,
  connectionId,
  action,
  status,
  page = 1,
  pageSize = 50,
} = {}) {
  const params = { page, page_size: pageSize };
  if (userId) params.user_id = userId;
  if (sessionId) params.session_id = sessionId;
  if (connectionId) params.connection_id = connectionId;
  if (action) params.action = action;
  if (status) params.status = status;

  const { data } = await api.get('/api/audit/logs', { params });
  return data; // { logs, total, page, page_size, total_pages }
}

export async function getAuditStats() {
  const { data } = await api.get('/api/audit/stats');
  return data; // AuditStats
}
