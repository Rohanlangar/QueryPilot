import React, { useState, useEffect, useCallback } from 'react';
import {
  Shield, Users, Lock, Plus, Trash2, CheckCircle, XCircle, AlertCircle,
  RefreshCw, Search, UserCheck, UserX, Database, Sliders,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';
import Toggle from '../components/common/Toggle';
import Chip from '../components/common/Chip';
import Loader from '../components/common/Loader';
import useAuthStore from '../store/authStore';
import useConnectionStore from '../store/connectionStore';
import * as adminApi from '../api/adminApi';

export default function AdminPage() {
  const currentUser = useAuthStore((s) => s.user);
  const connections = useConnectionStore((s) => s.connections);

  const [activeTab, setActiveTab] = useState('users'); // 'users' | 'policies' | 'roles'
  const [loading, setLoading] = useState(true);
  const [feedback, setFeedback] = useState(null); // { type: 'success' | 'error', message: string }

  // Data
  const [users, setUsers] = useState([]);
  const [roles, setRoles] = useState([]);
  const [policies, setPolicies] = useState([]);

  // Search & Filter
  const [userSearch, setUserSearch] = useState('');
  const [selectedConnectionFilter, setSelectedConnectionFilter] = useState('');
  const [selectedRoleFilter, setSelectedRoleFilter] = useState('');

  // Modals
  const [showPolicyModal, setShowPolicyModal] = useState(false);
  const [showRoleModal, setShowRoleModal] = useState(false);

  // Policy Form
  const [policyForm, setPolicyForm] = useState({
    role_id: '',
    connection_id: '',
    table_name: '',
    allowed: true,
    sensitive_columns: '',
    blocked_columns: '',
  });

  // Role Form
  const [roleForm, setRoleForm] = useState({
    name: '',
    description: '',
    can_manage_users: false,
    can_manage_connections: false,
    can_manage_policies: false,
    can_view_audit: false,
  });

  const [actionLoading, setActionLoading] = useState(false);

  const showNotification = (message, type = 'success') => {
    setFeedback({ message, type });
    setTimeout(() => setFeedback(null), 4000);
  };

  const loadData = useCallback(async () => {
    setLoading(true);
    try {
      const [usersData, rolesData, policiesData] = await Promise.all([
        adminApi.listUsers().catch(() => []),
        adminApi.listRoles().catch(() => []),
        adminApi.listPolicies().catch(() => []),
      ]);
      setUsers(usersData || []);
      setRoles(rolesData || []);
      setPolicies(policiesData || []);
    } catch (err) {
      showNotification('Failed to load admin data: ' + (err.response?.data?.detail || err.message), 'error');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    loadData();
  }, [loadData]);

  // User Actions
  const handleRoleChange = async (userId, newRole) => {
    try {
      await adminApi.updateUserRole(userId, newRole);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, role: newRole } : u))
      );
      showNotification('User role updated successfully');
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to update user role', 'error');
    }
  };

  const handleDeactivateUser = async (userId) => {
    if (!window.confirm('Are you sure you want to deactivate this user?')) return;
    try {
      await adminApi.deactivateUser(userId);
      setUsers((prev) =>
        prev.map((u) => (u.id === userId ? { ...u, is_active: false } : u))
      );
      showNotification('User deactivated successfully');
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to deactivate user', 'error');
    }
  };

  // Policy Actions
  const handleCreatePolicy = async (e) => {
    e.preventDefault();
    if (!policyForm.role_id || !policyForm.connection_id || !policyForm.table_name) {
      showNotification('Please fill in role, connection, and table name', 'error');
      return;
    }

    setActionLoading(true);
    try {
      const payload = {
        role_id: policyForm.role_id,
        connection_id: policyForm.connection_id,
        table_name: policyForm.table_name.trim(),
        allowed: policyForm.allowed,
        sensitive_columns: policyForm.sensitive_columns
          ? policyForm.sensitive_columns.split(',').map((c) => c.trim()).filter(Boolean)
          : null,
        blocked_columns: policyForm.blocked_columns
          ? policyForm.blocked_columns.split(',').map((c) => c.trim()).filter(Boolean)
          : null,
      };

      const created = await adminApi.createPolicy(payload);
      setPolicies((prev) => [created, ...prev]);
      setShowPolicyModal(false);
      setPolicyForm({
        role_id: '',
        connection_id: '',
        table_name: '',
        allowed: true,
        sensitive_columns: '',
        blocked_columns: '',
      });
      showNotification('Table access policy created successfully');
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to create policy', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeletePolicy = async (policyId) => {
    if (!window.confirm('Delete this table policy?')) return;
    try {
      await adminApi.deletePolicy(policyId);
      setPolicies((prev) => prev.filter((p) => p.id !== policyId));
      showNotification('Policy removed');
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to delete policy', 'error');
    }
  };

  // Role Actions
  const handleCreateRole = async (e) => {
    e.preventDefault();
    if (!roleForm.name.trim()) {
      showNotification('Role name is required', 'error');
      return;
    }

    setActionLoading(true);
    try {
      const created = await adminApi.createRole({
        name: roleForm.name.trim().toLowerCase(),
        description: roleForm.description,
        can_manage_users: roleForm.can_manage_users,
        can_manage_connections: roleForm.can_manage_connections,
        can_manage_policies: roleForm.can_manage_policies,
        can_view_audit: roleForm.can_view_audit,
      });
      setRoles((prev) => [...prev, created]);
      setShowRoleModal(false);
      setRoleForm({
        name: '',
        description: '',
        can_manage_users: false,
        can_manage_connections: false,
        can_manage_policies: false,
        can_view_audit: false,
      });
      showNotification('Role created successfully');
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to create role', 'error');
    } finally {
      setActionLoading(false);
    }
  };

  const handleDeleteRole = async (roleId, roleName) => {
    if (['admin', 'analyst', 'viewer'].includes(roleName)) {
      showNotification('Built-in system roles cannot be deleted', 'error');
      return;
    }
    if (!window.confirm(`Delete role "${roleName}"?`)) return;
    try {
      await adminApi.deleteRole(roleId);
      setRoles((prev) => prev.filter((r) => r.id !== roleId));
      showNotification(`Role "${roleName}" removed`);
    } catch (err) {
      showNotification(err.response?.data?.detail || 'Failed to delete role', 'error');
    }
  };

  const filteredUsers = users.filter((u) => {
    const q = userSearch.toLowerCase();
    return (
      (u.username && u.username.toLowerCase().includes(q)) ||
      (u.email && u.email.toLowerCase().includes(q)) ||
      (u.full_name && u.full_name.toLowerCase().includes(q))
    );
  });

  const filteredPolicies = policies.filter((p) => {
    if (selectedConnectionFilter && p.connection_id !== selectedConnectionFilter) return false;
    if (selectedRoleFilter && p.role_id !== selectedRoleFilter) return false;
    return true;
  });

  const getRoleName = (roleId) => {
    const found = roles.find((r) => r.id === roleId);
    return found ? found.name : 'Unknown';
  };

  const getConnectionName = (connId) => {
    const found = connections.find((c) => c.id === connId);
    return found ? (found.name || found.database_name || connId) : connId;
  };

  return (
    <PageLayout>
      <div className="page-content" style={{ maxWidth: '1200px', margin: '0 auto', padding: '24px' }}>
        {/* Header */}
        <div className="flex items-center justify-between" style={{ marginBottom: '24px' }}>
          <div>
            <h1 className="page-title" style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
              <Shield size={28} style={{ color: 'var(--color-primary)' }} />
              Security & RBAC Governance
            </h1>
            <p className="text-body-sm text-muted">
              Configure user roles, database table restrictions, and column-level PII policies.
            </p>
          </div>
          <Button variant="secondary" icon={RefreshCw} onClick={loadData} disabled={loading}>
            Refresh
          </Button>
        </div>

        {/* Feedback Alert */}
        {feedback && (
          <div
            style={{
              padding: '12px 16px',
              borderRadius: '8px',
              marginBottom: '20px',
              display: 'flex',
              alignItems: 'center',
              gap: '10px',
              backgroundColor: feedback.type === 'error' ? 'rgba(239, 68, 68, 0.15)' : 'rgba(34, 197, 94, 0.15)',
              border: `1px solid ${feedback.type === 'error' ? 'var(--color-error, #ef4444)' : 'var(--color-success, #22c55e)'}`,
              color: feedback.type === 'error' ? '#fca5a5' : '#86efac',
            }}
          >
            {feedback.type === 'error' ? <AlertCircle size={18} /> : <CheckCircle size={18} />}
            <span style={{ fontSize: '14px', fontWeight: 500 }}>{feedback.message}</span>
          </div>
        )}

        {/* Stats Row */}
        <div
          style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))',
            gap: '16px',
            marginBottom: '28px',
          }}
        >
          <Card bordered surface padding="md">
            <div className="flex items-center gap-sm">
              <div style={{ padding: '8px', background: 'rgba(99, 102, 241, 0.15)', borderRadius: '8px', color: '#818cf8' }}>
                <Users size={22} />
              </div>
              <div>
                <div className="text-body-xs text-muted">Total Users</div>
                <div style={{ fontSize: '24px', fontWeight: 700 }}>{users.length}</div>
              </div>
            </div>
          </Card>

          <Card bordered surface padding="md">
            <div className="flex items-center gap-sm">
              <div style={{ padding: '8px', background: 'rgba(34, 197, 94, 0.15)', borderRadius: '8px', color: '#4ade80' }}>
                <Shield size={22} />
              </div>
              <div>
                <div className="text-body-xs text-muted">Active Roles</div>
                <div style={{ fontSize: '24px', fontWeight: 700 }}>{roles.length}</div>
              </div>
            </div>
          </Card>

          <Card bordered surface padding="md">
            <div className="flex items-center gap-sm">
              <div style={{ padding: '8px', background: 'rgba(245, 158, 11, 0.15)', borderRadius: '8px', color: '#fbbf24' }}>
                <Lock size={22} />
              </div>
              <div>
                <div className="text-body-xs text-muted">Table Policies</div>
                <div style={{ fontSize: '24px', fontWeight: 700 }}>{policies.length}</div>
              </div>
            </div>
          </Card>

          <Card bordered surface padding="md">
            <div className="flex items-center gap-sm">
              <div style={{ padding: '8px', background: 'rgba(168, 85, 247, 0.15)', borderRadius: '8px', color: '#c084fc' }}>
                <Sliders size={22} />
              </div>
              <div>
                <div className="text-body-xs text-muted">RBAC Guardrail</div>
                <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--color-primary)' }}>Enforced (AST)</div>
              </div>
            </div>
          </Card>
        </div>

        {/* Tab Navigation */}
        <div
          style={{
            display: 'flex',
            gap: '8px',
            borderBottom: '1px solid var(--color-border)',
            marginBottom: '24px',
          }}
        >
          <button
            onClick={() => setActiveTab('users')}
            style={{
              padding: '10px 18px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'users' ? '2px solid var(--color-primary)' : '2px solid transparent',
              color: activeTab === 'users' ? 'var(--color-text)' : 'var(--color-muted)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Users size={16} />
            User Management ({users.length})
          </button>
          <button
            onClick={() => setActiveTab('policies')}
            style={{
              padding: '10px 18px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'policies' ? '2px solid var(--color-primary)' : '2px solid transparent',
              color: activeTab === 'policies' ? 'var(--color-text)' : 'var(--color-muted)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Lock size={16} />
            Table Access Policies ({policies.length})
          </button>
          <button
            onClick={() => setActiveTab('roles')}
            style={{
              padding: '10px 18px',
              background: 'none',
              border: 'none',
              borderBottom: activeTab === 'roles' ? '2px solid var(--color-primary)' : '2px solid transparent',
              color: activeTab === 'roles' ? 'var(--color-text)' : 'var(--color-muted)',
              fontWeight: 600,
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '8px',
            }}
          >
            <Shield size={16} />
            Roles & Privileges ({roles.length})
          </button>
        </div>

        {/* Loading state */}
        {loading ? (
          <div style={{ textAlign: 'center', padding: '60px' }}>
            <Loader size="lg" />
            <p className="text-muted" style={{ marginTop: '12px' }}>Loading governance data...</p>
          </div>
        ) : (
          <>
            {/* ── TAB 1: USERS ──────────────────────────────── */}
            {activeTab === 'users' && (
              <div>
                <div className="flex items-center justify-between" style={{ marginBottom: '16px' }}>
                  <div style={{ width: '320px' }}>
                    <Input
                      placeholder="Search users by name or email..."
                      icon={Search}
                      value={userSearch}
                      onChange={(e) => setUserSearch(e.target.value)}
                    />
                  </div>
                </div>

                <Card bordered surface padding="none" style={{ overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: 'var(--color-surface-hover)', borderBottom: '1px solid var(--color-border)' }}>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>User</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Email</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Status</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Current Role</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredUsers.length === 0 ? (
                        <tr>
                          <td colSpan={5} style={{ padding: '32px', textAlign: 'center', color: 'var(--color-muted)' }}>
                            No users found.
                          </td>
                        </tr>
                      ) : (
                        filteredUsers.map((u) => {
                          const isSelf = currentUser?.id === u.id;
                          return (
                            <tr key={u.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                              <td style={{ padding: '14px 18px' }}>
                                <div style={{ fontWeight: 600 }}>{u.full_name || u.username}</div>
                                <div style={{ fontSize: '12px', color: 'var(--color-muted)' }}>@{u.username}</div>
                              </td>
                              <td style={{ padding: '14px 18px', color: 'var(--color-muted)', fontSize: '14px' }}>
                                {u.email}
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                {u.is_active ? (
                                  <Chip variant="secondary" icon={UserCheck}>Active</Chip>
                                ) : (
                                  <Chip variant="error" icon={UserX}>Inactive</Chip>
                                )}
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <select
                                  value={u.role || 'viewer'}
                                  disabled={isSelf}
                                  onChange={(e) => handleRoleChange(u.id, e.target.value)}
                                  style={{
                                    padding: '6px 10px',
                                    borderRadius: '6px',
                                    background: 'var(--color-surface)',
                                    color: 'var(--color-text)',
                                    border: '1px solid var(--color-border)',
                                    fontSize: '13px',
                                    cursor: isSelf ? 'not-allowed' : 'pointer',
                                  }}
                                >
                                  {roles.map((r) => (
                                    <option key={r.id || r.name} value={r.name}>
                                      {r.name.toUpperCase()}
                                    </option>
                                  ))}
                                </select>
                                {isSelf && (
                                  <span style={{ fontSize: '11px', color: 'var(--color-muted)', display: 'block', marginTop: '4px' }}>
                                    (Your account)
                                  </span>
                                )}
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                {!isSelf && u.is_active && (
                                  <Button
                                    variant="ghost"
                                    size="sm"
                                    style={{ color: 'var(--color-error)' }}
                                    onClick={() => handleDeactivateUser(u.id)}
                                  >
                                    Deactivate
                                  </Button>
                                )}
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </Card>
              </div>
            )}

            {/* ── TAB 2: TABLE ACCESS POLICIES ────────────── */}
            {activeTab === 'policies' && (
              <div>
                <div
                  className="flex items-center justify-between"
                  style={{ marginBottom: '18px', flexWrap: 'wrap', gap: '12px' }}
                >
                  <div className="flex items-center gap-sm">
                    <select
                      value={selectedConnectionFilter}
                      onChange={(e) => setSelectedConnectionFilter(e.target.value)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '6px',
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                        fontSize: '13px',
                      }}
                    >
                      <option value="">All Database Connections</option>
                      {connections.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.name || c.database_name} ({c.db_type})
                        </option>
                      ))}
                    </select>

                    <select
                      value={selectedRoleFilter}
                      onChange={(e) => setSelectedRoleFilter(e.target.value)}
                      style={{
                        padding: '8px 12px',
                        borderRadius: '6px',
                        background: 'var(--color-surface)',
                        color: 'var(--color-text)',
                        border: '1px solid var(--color-border)',
                        fontSize: '13px',
                      }}
                    >
                      <option value="">All Roles</option>
                      {roles.map((r) => (
                        <option key={r.id} value={r.id}>
                          {r.name.toUpperCase()}
                        </option>
                      ))}
                    </select>
                  </div>

                  <Button variant="primary" icon={Plus} onClick={() => setShowPolicyModal(true)}>
                    Add Table Policy
                  </Button>
                </div>

                <Card bordered surface padding="none" style={{ overflow: 'hidden' }}>
                  <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                    <thead>
                      <tr style={{ background: 'var(--color-surface-hover)', borderBottom: '1px solid var(--color-border)' }}>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Target Table</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Role</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Connection</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Access Status</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Sensitive Columns</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Blocked Columns</th>
                        <th style={{ padding: '14px 18px', fontSize: '12px', color: 'var(--color-muted)', textTransform: 'uppercase' }}>Actions</th>
                      </tr>
                    </thead>
                    <tbody>
                      {filteredPolicies.length === 0 ? (
                        <tr>
                          <td colSpan={7} style={{ padding: '36px', textAlign: 'center', color: 'var(--color-muted)' }}>
                            No specific table policies configured yet. Built-in defaults apply.
                          </td>
                        </tr>
                      ) : (
                        filteredPolicies.map((p) => {
                          const sensitive = p.sensitive_columns ? JSON.parse(p.sensitive_columns) : [];
                          const blocked = p.blocked_columns ? JSON.parse(p.blocked_columns) : [];
                          return (
                            <tr key={p.id} style={{ borderBottom: '1px solid var(--color-border)' }}>
                              <td style={{ padding: '14px 18px', fontWeight: 600 }}>
                                <code>{p.table_name}</code>
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <span className="chip chip-secondary" style={{ textTransform: 'uppercase', fontSize: '11px' }}>
                                  {getRoleName(p.role_id)}
                                </span>
                              </td>
                              <td style={{ padding: '14px 18px', color: 'var(--color-muted)', fontSize: '13px' }}>
                                {getConnectionName(p.connection_id)}
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                {p.allowed ? (
                                  <Chip variant="secondary" icon={CheckCircle}>Allowed</Chip>
                                ) : (
                                  <Chip variant="error" icon={XCircle}>Denied</Chip>
                                )}
                              </td>
                              <td style={{ padding: '14px 18px', fontSize: '12px' }}>
                                {sensitive.length > 0 ? (
                                  <div className="flex gap-xs" style={{ flexWrap: 'wrap' }}>
                                    {sensitive.map((c) => (
                                      <span key={c} style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24', padding: '2px 6px', borderRadius: '4px' }}>
                                        {c}
                                      </span>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-muted">—</span>
                                )}
                              </td>
                              <td style={{ padding: '14px 18px', fontSize: '12px' }}>
                                {blocked.length > 0 ? (
                                  <div className="flex gap-xs" style={{ flexWrap: 'wrap' }}>
                                    {blocked.map((c) => (
                                      <span key={c} style={{ background: 'rgba(239, 68, 68, 0.15)', color: '#f87171', padding: '2px 6px', borderRadius: '4px' }}>
                                        {c}
                                      </span>
                                    ))}
                                  </div>
                                ) : (
                                  <span className="text-muted">—</span>
                                )}
                              </td>
                              <td style={{ padding: '14px 18px' }}>
                                <button
                                  onClick={() => handleDeletePolicy(p.id)}
                                  title="Delete Policy"
                                  style={{
                                    background: 'none',
                                    border: 'none',
                                    color: 'var(--color-error)',
                                    cursor: 'pointer',
                                    padding: '4px',
                                  }}
                                >
                                  <Trash2 size={16} />
                                </button>
                              </td>
                            </tr>
                          );
                        })
                      )}
                    </tbody>
                  </table>
                </Card>
              </div>
            )}

            {/* ── TAB 3: ROLES & PRIVILEGES ────────────────── */}
            {activeTab === 'roles' && (
              <div>
                <div className="flex items-center justify-between" style={{ marginBottom: '18px' }}>
                  <p className="text-muted text-body-sm">
                    Roles define user privilege levels for system management and querying.
                  </p>
                  <Button variant="primary" icon={Plus} onClick={() => setShowRoleModal(true)}>
                    Create Custom Role
                  </Button>
                </div>

                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(320px, 1fr))', gap: '20px' }}>
                  {roles.map((r) => {
                    const isBuiltin = ['admin', 'analyst', 'viewer'].includes(r.name);
                    return (
                      <Card key={r.id || r.name} bordered surface padding="lg">
                        <div className="flex items-center justify-between" style={{ marginBottom: '12px' }}>
                          <div className="flex items-center gap-xs">
                            <Shield size={18} style={{ color: 'var(--color-primary)' }} />
                            <h3 style={{ fontSize: '16px', fontWeight: 700, textTransform: 'uppercase' }}>
                              {r.name}
                            </h3>
                          </div>
                          {isBuiltin ? (
                            <span className="chip" style={{ fontSize: '11px', background: 'rgba(255,255,255,0.06)' }}>
                              Built-in
                            </span>
                          ) : (
                            <button
                              onClick={() => handleDeleteRole(r.id, r.name)}
                              style={{ background: 'none', border: 'none', color: 'var(--color-error)', cursor: 'pointer' }}
                              title="Delete Role"
                            >
                              <Trash2 size={16} />
                            </button>
                          )}
                        </div>

                        <p className="text-body-sm text-muted" style={{ marginBottom: '16px', minHeight: '38px' }}>
                          {r.description || 'No description provided.'}
                        </p>

                        <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '14px' }}>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--color-muted)', marginBottom: '8px', textTransform: 'uppercase' }}>
                            Privileges
                          </div>
                          <div className="flex flex-col gap-xs" style={{ fontSize: '13px' }}>
                            <div className="flex items-center justify-between">
                              <span>Manage Users</span>
                              {r.can_manage_users ? <CheckCircle size={15} color="#22c55e" /> : <XCircle size={15} color="#6b7280" />}
                            </div>
                            <div className="flex items-center justify-between">
                              <span>Manage Connections</span>
                              {r.can_manage_connections ? <CheckCircle size={15} color="#22c55e" /> : <XCircle size={15} color="#6b7280" />}
                            </div>
                            <div className="flex items-center justify-between">
                              <span>Manage Table Policies</span>
                              {r.can_manage_policies ? <CheckCircle size={15} color="#22c55e" /> : <XCircle size={15} color="#6b7280" />}
                            </div>
                            <div className="flex items-center justify-between">
                              <span>View Audit Logs</span>
                              {r.can_view_audit ? <CheckCircle size={15} color="#22c55e" /> : <XCircle size={15} color="#6b7280" />}
                            </div>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                </div>
              </div>
            )}
          </>
        )}

        {/* ── MODAL: CREATE TABLE POLICY ────────────────── */}
        {showPolicyModal && (
          <Modal title="Create Table Access Policy" onClose={() => setShowPolicyModal(false)}>
            <form onSubmit={handleCreatePolicy} className="flex flex-col gap-md">
              <Select
                label="Role"
                value={policyForm.role_id}
                onChange={(e) => setPolicyForm({ ...policyForm, role_id: e.target.value })}
                options={[
                  { value: '', label: 'Select a role...' },
                  ...roles.map((r) => ({ value: r.id, label: r.name.toUpperCase() })),
                ]}
              />

              <Select
                label="Target Database Connection"
                value={policyForm.connection_id}
                onChange={(e) => setPolicyForm({ ...policyForm, connection_id: e.target.value })}
                options={[
                  { value: '', label: 'Select a database connection...' },
                  ...connections.map((c) => ({
                    value: c.id,
                    label: `${c.name || c.database_name} (${c.db_type})`,
                  })),
                ]}
              />

              <Input
                label="Table Name"
                placeholder="e.g. salaries, employees, orders"
                value={policyForm.table_name}
                onChange={(e) => setPolicyForm({ ...policyForm, table_name: e.target.value })}
              />

              <Toggle
                label="Grant Table Access"
                checked={policyForm.allowed}
                onChange={(val) => setPolicyForm({ ...policyForm, allowed: val })}
              />

              <Input
                label="Sensitive Columns to Mask (comma-separated)"
                placeholder="e.g. email, phone, ssn"
                value={policyForm.sensitive_columns}
                onChange={(e) => setPolicyForm({ ...policyForm, sensitive_columns: e.target.value })}
                helper="Values in these columns will be redacted in query results."
              />

              <Input
                label="Blocked Columns to Hide (comma-separated)"
                placeholder="e.g. password_hash, salary"
                value={policyForm.blocked_columns}
                onChange={(e) => setPolicyForm({ ...policyForm, blocked_columns: e.target.value })}
                helper="Queries attempting to access these columns will be blocked by RBAC."
              />

              <div className="flex justify-end gap-sm" style={{ marginTop: '12px' }}>
                <Button variant="ghost" onClick={() => setShowPolicyModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={actionLoading}>
                  {actionLoading ? 'Saving...' : 'Save Policy'}
                </Button>
              </div>
            </form>
          </Modal>
        )}

        {/* ── MODAL: CREATE CUSTOM ROLE ─────────────────── */}
        {showRoleModal && (
          <Modal title="Create New Role" onClose={() => setShowRoleModal(false)}>
            <form onSubmit={handleCreateRole} className="flex flex-col gap-md">
              <Input
                label="Role Name"
                placeholder="e.g. auditor, compliance_officer"
                value={roleForm.name}
                onChange={(e) => setRoleForm({ ...roleForm, name: e.target.value })}
              />

              <Input
                label="Description"
                placeholder="Brief summary of duties and permissions"
                value={roleForm.description}
                onChange={(e) => setRoleForm({ ...roleForm, description: e.target.value })}
              />

              <div style={{ borderTop: '1px solid var(--color-border)', paddingTop: '12px' }}>
                <div style={{ fontWeight: 600, fontSize: '13px', marginBottom: '10px' }}>Privileges</div>
                <div className="flex flex-col gap-sm">
                  <Toggle
                    label="Can Manage Users"
                    checked={roleForm.can_manage_users}
                    onChange={(val) => setRoleForm({ ...roleForm, can_manage_users: val })}
                  />
                  <Toggle
                    label="Can Manage Connections"
                    checked={roleForm.can_manage_connections}
                    onChange={(val) => setRoleForm({ ...roleForm, can_manage_connections: val })}
                  />
                  <Toggle
                    label="Can Manage Table Policies"
                    checked={roleForm.can_manage_policies}
                    onChange={(val) => setRoleForm({ ...roleForm, can_manage_policies: val })}
                  />
                  <Toggle
                    label="Can View Audit Logs"
                    checked={roleForm.can_view_audit}
                    onChange={(val) => setRoleForm({ ...roleForm, can_view_audit: val })}
                  />
                </div>
              </div>

              <div className="flex justify-end gap-sm" style={{ marginTop: '12px' }}>
                <Button variant="ghost" onClick={() => setShowRoleModal(false)}>
                  Cancel
                </Button>
                <Button variant="primary" type="submit" disabled={actionLoading}>
                  {actionLoading ? 'Creating...' : 'Create Role'}
                </Button>
              </div>
            </form>
          </Modal>
        )}
      </div>
    </PageLayout>
  );
}
