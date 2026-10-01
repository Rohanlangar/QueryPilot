/**
 * QueryPilot — Admin API Client
 *
 * Endpoints for user management, role assignments, and RBAC table access policies.
 */

import api from './api';

export const listUsers = async () => {
  const res = await api.get('/api/admin/users');
  return res.data;
};

export const updateUserRole = async (userId, role) => {
  const res = await api.patch(`/api/admin/users/${userId}/role`, { role });
  return res.data;
};

export const deactivateUser = async (userId) => {
  const res = await api.patch(`/api/admin/users/${userId}/deactivate`);
  return res.data;
};

export const listRoles = async () => {
  const res = await api.get('/api/admin/roles');
  return res.data;
};

export const createRole = async (roleData) => {
  const res = await api.post('/api/admin/roles', roleData);
  return res.data;
};

export const deleteRole = async (roleId) => {
  const res = await api.delete(`/api/admin/roles/${roleId}`);
  return res.data;
};

export const listPolicies = async (connectionId, roleId) => {
  const params = {};
  if (connectionId) params.connection_id = connectionId;
  if (roleId) params.role_id = roleId;
  const res = await api.get('/api/admin/policies', { params });
  return res.data;
};

export const createPolicy = async (policyData) => {
  const res = await api.post('/api/admin/policies', policyData);
  return res.data;
};

export const deletePolicy = async (policyId) => {
  const res = await api.delete(`/api/admin/policies/${policyId}`);
  return res.data;
};
