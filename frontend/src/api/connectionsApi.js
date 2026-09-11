/**
 * QueryPilot — Connections API
 *
 * CRUD for database connections + test + schema introspection.
 */

import api from './api';

export async function createConnection(body) {
  const { data } = await api.post('/api/connections', {
    name: body.name,
    db_type: body.dbType,
    host: body.host,
    port: Number(body.port),
    database_name: body.database,
    username: body.username,
    password: body.password,
    ssl_enabled: body.ssl || false,
    extra_params: body.extraParams || null,
  });
  return data;
}

export async function listConnections() {
  const { data } = await api.get('/api/connections');
  return data; // ConnectionResponse[]
}

export async function getConnection(connectionId) {
  const { data } = await api.get(`/api/connections/${connectionId}`);
  return data;
}

export async function updateConnection(connectionId, body) {
  const payload = {};
  if (body.name !== undefined) payload.name = body.name;
  if (body.host !== undefined) payload.host = body.host;
  if (body.port !== undefined) payload.port = Number(body.port);
  if (body.database !== undefined) payload.database_name = body.database;
  if (body.username !== undefined) payload.username = body.username;
  if (body.password) payload.password = body.password;
  if (body.ssl !== undefined) payload.ssl_enabled = body.ssl;

  const { data } = await api.patch(`/api/connections/${connectionId}`, payload);
  return data;
}

export async function deleteConnection(connectionId) {
  await api.delete(`/api/connections/${connectionId}`);
}

export async function testConnection(connectionId) {
  const { data } = await api.post(`/api/connections/${connectionId}/test`);
  return data; // { success, message, latency_ms }
}

export async function testConnectionParams(body) {
  const { data } = await api.post('/api/connections/test-params', {
    db_type: body.dbType,
    host: body.host,
    port: Number(body.port),
    database_name: body.database,
    username: body.username,
    password: body.password,
    ssl_enabled: body.ssl || false,
    extra_params: body.extraParams || null,
  });
  return data; // { success, message, latency_ms }
}

export async function getConnectionSchema(connectionId) {
  const { data } = await api.get(`/api/connections/${connectionId}/schema`);
  return data; // { connection_id, database_name, tables, total_tables }
}
