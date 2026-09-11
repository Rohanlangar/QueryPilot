/**
 * QueryPilot — Auth API
 *
 * Endpoints: register, login, getMe, updateMe
 */

import api from './api';

export async function register({ email, username, password, fullName }) {
  const { data } = await api.post('/api/auth/register', {
    email,
    username,
    password,
    full_name: fullName,
  });
  return data;
}

export async function login({ username, password }) {
  const { data } = await api.post('/api/auth/login', { username, password });
  return data; // { access_token, token_type, expires_in }
}

export async function refreshToken() {
  const { data } = await api.post('/api/auth/refresh');
  return data;
}

export async function getMe() {
  const { data } = await api.get('/api/auth/me');
  return data; // { id, email, username, full_name, role, is_active, created_at }
}

export async function updateMe(updates) {
  const { data } = await api.patch('/api/auth/me', updates);
  return data;
}
