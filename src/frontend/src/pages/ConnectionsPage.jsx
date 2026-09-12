import React, { useState, useEffect } from 'react';
import {
  Database, Plus, Wifi, WifiOff, Loader2, Pencil, Trash2, Zap,
  CheckCircle, XCircle, AlertCircle, Network,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';
import Toggle from '../components/common/Toggle';
import SchemaVisualizerModal from '../components/schema/SchemaVisualizerModal';
import useConnectionStore from '../store/connectionStore';
import { testConnectionParams } from '../api/connectionsApi';

const DB_TYPES = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'mssql', label: 'MSSQL' },
  { value: 'oracle', label: 'Oracle' },
];

const DEFAULT_PORTS = {
  postgresql: 5432,
  mysql: 3306,
  mssql: 1433,
  oracle: 1521,
};

const INITIAL_FORM = {
  name: '',
  dbType: 'postgresql',
  host: '',
  port: '5432',
  database: '',
  username: '',
  password: '',
  ssl: false,
};

export default function ConnectionsPage() {
  const {
    connections,
    activeConnectionId,
    fetchConnections,
    addConnection,
    updateConnection,
    removeConnection,
    setActiveConnection,
    testConnection,
  } = useConnectionStore();

  const [showModal, setShowModal] = useState(false);
  const [editingId, setEditingId] = useState(null);
  const [form, setForm] = useState(INITIAL_FORM);
  const [testResult, setTestResult] = useState(null);
  const [isTesting, setIsTesting] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveError, setSaveError] = useState(null);
  const [visualizingConn, setVisualizingConn] = useState(null);

  useEffect(() => {
    fetchConnections();
  }, [fetchConnections]);

  const handleOpenNew = () => {
    setForm(INITIAL_FORM);
    setEditingId(null);
    setTestResult(null);
    setSaveError(null);
    setShowModal(true);
  };

  const handleOpenEdit = (conn) => {
    setForm({
      name: conn.name,
      dbType: conn.dbType,
      host: conn.host,
      port: String(conn.port),
      database: conn.database,
      username: conn.username,
      password: '',
      ssl: conn.ssl,
    });
    setEditingId(conn.id);
    setTestResult(null);
    setSaveError(null);
    setShowModal(true);
  };

  const handleDbTypeChange = (e) => {
    const dbType = e.target.value;
    setForm((f) => ({
      ...f,
      dbType,
      port: String(DEFAULT_PORTS[dbType] || ''),
    }));
  };

  const handleFormChange = (field) => (e) => {
    setForm((f) => ({ ...f, [field]: e.target.value }));
  };

  const handleTestConnection = async () => {
    setIsTesting(true);
    setTestResult(null);
    try {
      const res = await testConnectionParams(form);
      setTestResult(res);
    } catch (err) {
      setTestResult({
        success: false,
        message: err.response?.data?.detail || err.message || 'Connection test failed',
      });
    } finally {
      setIsTesting(false);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    setSaveError(null);

    const config = {
      name: form.name,
      dbType: form.dbType,
      host: form.host,
      port: Number(form.port) || DEFAULT_PORTS[form.dbType] || 5432,
      database: form.database,
      username: form.username,
      ssl: form.ssl,
    };

    if (form.password) {
      config.password = form.password;
    }

    try {
      if (editingId) {
        await updateConnection(editingId, config);
      } else {
        if (!form.password) {
          throw new Error('Password is required for new database connections.');
        }
        const id = await addConnection(config);
        if (!activeConnectionId && id) {
          setActiveConnection(id);
        }
      }
      setShowModal(false);
    } catch (err) {
      const errorMsg =
        typeof err.response?.data?.detail === 'string'
          ? err.response.data.detail
          : Array.isArray(err.response?.data?.detail)
          ? err.response.data.detail.map((d) => d.msg).join(', ')
          : err.message || 'Failed to save connection';
      setSaveError(errorMsg);
    } finally {
      setIsSaving(false);
    }
  };

  const handleDelete = (id) => {
    if (window.confirm('Remove this connection?')) {
      removeConnection(id);
    }
  };

  const getStatusIcon = (status) => {
    switch (status) {
      case 'connected': return <Wifi size={14} style={{ color: 'var(--color-secondary)' }} />;
      case 'testing': return <Loader2 size={14} style={{ color: 'var(--color-muted)', animation: 'spin 1s linear infinite' }} />;
      default: return <WifiOff size={14} style={{ color: 'var(--color-error)' }} />;
    }
  };

  return (
    <PageLayout>
      <div className="page-content">
        <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-md)' }}>
          <div>
            <h1 className="page-title" style={{ marginBottom: '4px' }}>Database Connections</h1>
            <p className="text-body-md text-muted">Manage your database connections and schemas.</p>
          </div>
          <Button variant="secondary" icon={Plus} onClick={handleOpenNew}>
            Add Connection
          </Button>
        </div>

        {connections.length === 0 ? (
          <Card bordered surface style={{ textAlign: 'center', padding: 'var(--space-xl) var(--space-lg)' }}>
            <Database size={48} style={{ color: 'var(--color-muted)', margin: '0 auto 16px' }} />
            <h3 className="text-body-lg" style={{ fontWeight: 600, marginBottom: '8px' }}>
              No connections yet
            </h3>
            <p className="text-body-sm text-muted" style={{ maxWidth: '400px', margin: '0 auto 24px' }}>
              Add your first database connection to start querying with natural language.
            </p>
            <Button variant="secondary" icon={Plus} onClick={handleOpenNew}>
              Add Your First Connection
            </Button>
          </Card>
        ) : (
          <div className="connections-grid">
            {connections.map((conn) => (
              <Card
                key={conn.id}
                bordered
                className={`connection-card ${conn.id === activeConnectionId ? 'card-surface' : ''}`}
                style={conn.id === activeConnectionId ? { borderColor: 'var(--color-secondary)' } : {}}
              >
                <div className="connection-card-header">
                  <div className="connection-card-icon">
                    <Database size={20} />
                  </div>
                  <div className="connection-card-info">
                    <div className="connection-card-name">{conn.name}</div>
                    <div className="connection-card-type">{conn.dbType}</div>
                  </div>
                </div>

                <div className="connection-card-details">
                  <span>{conn.host}:{conn.port}</span>
                  <span>Database: {conn.database}</span>
                  <span>User: {conn.username}</span>
                </div>

                <div className="connection-card-status">
                  <span className={`connection-status-dot ${conn.status}`} />
                  {getStatusIcon(conn.status)}
                  <span className="text-label-sm">
                    {conn.status === 'connected' ? 'Connected' : conn.status === 'testing' ? 'Testing...' : 'Disconnected'}
                  </span>
                  {conn.lastTested && (
                    <span className="text-label-sm text-muted" style={{ marginLeft: 'auto' }}>
                      Tested {new Date(conn.lastTested).toLocaleTimeString()}
                    </span>
                  )}
                </div>

                <div className="connection-card-actions">
                  <Button variant="ghost" size="sm" icon={Zap} onClick={() => testConnection(conn.id)}>
                    Test
                  </Button>
                  <Button
                    variant="ghost"
                    size="sm"
                    icon={Network}
                    onClick={() => setVisualizingConn(conn)}
                    title="Visualize Database Schema & ERD"
                    style={{ color: '#020707ff' }}
                  >
                    Visualize
                  </Button>
                  <Button variant="ghost" size="sm" icon={Pencil} onClick={() => handleOpenEdit(conn)}>
                    Edit
                  </Button>
                  <Button variant="ghost" size="sm" icon={Trash2} onClick={() => handleDelete(conn.id)} style={{ color: 'var(--color-error)' }}>
                    Delete
                  </Button>
                  {conn.id !== activeConnectionId && (
                    <Button
                      variant="secondary"
                      size="sm"
                      onClick={() => setActiveConnection(conn.id)}
                      style={{ marginLeft: 'auto' }}
                    >
                      Set Active
                    </Button>
                  )}
                </div>
              </Card>
            ))}
          </div>
        )}

        {/* Add/Edit Modal */}
        <Modal
          isOpen={showModal}
          onClose={() => setShowModal(false)}
          title={editingId ? 'Edit Connection' : 'Add Connection'}
          maxWidth="600px"
          footer={
            <>
              <Button variant="ghost" onClick={() => setShowModal(false)} disabled={isSaving}>
                Cancel
              </Button>
              <Button
                variant="primary"
                onClick={handleSave}
                disabled={!form.name || !form.host || !form.database || (!editingId && !form.password) || isSaving}
              >
                {isSaving ? (
                  <>
                    <Loader2 size={16} style={{ animation: 'spin 1s linear infinite', marginRight: '8px' }} />
                    Saving...
                  </>
                ) : editingId ? (
                  'Update'
                ) : (
                  'Save Connection'
                )}
              </Button>
            </>
          }
        >
          <div className="connection-form">
            {saveError && (
              <div
                className="connection-test-result error"
                style={{ marginBottom: '16px', display: 'flex', alignItems: 'center', gap: '8px' }}
              >
                <AlertCircle size={16} />
                <span>{saveError}</span>
              </div>
            )}

            <Input
              label="Connection Name"
              value={form.name}
              onChange={handleFormChange('name')}
              placeholder="e.g. Production DB"
              required
            />
            <Select
              label="Database Type"
              value={form.dbType}
              onChange={handleDbTypeChange}
              options={DB_TYPES}
              required
            />
            <div className="connection-form-row">
              <Input
                label="Host"
                value={form.host}
                onChange={handleFormChange('host')}
                placeholder="localhost or IP address"
                required
              />
              <Input
                label="Port"
                type="number"
                value={form.port}
                onChange={handleFormChange('port')}
                placeholder="5432"
              />
            </div>
            <Input
              label="Database Name"
              value={form.database}
              onChange={handleFormChange('database')}
              placeholder="my_database"
              required
            />
            <div className="connection-form-row">
              <Input
                label="Username"
                value={form.username}
                onChange={handleFormChange('username')}
                placeholder="db_user"
                required
              />
              <Input
                label={editingId ? "Password (leave blank to keep current)" : "Password"}
                type="password"
                value={form.password}
                onChange={handleFormChange('password')}
                placeholder="••••••••"
                required={!editingId}
              />
            </div>
            <Toggle
              label="Use SSL"
              checked={form.ssl}
              onChange={(val) => setForm((f) => ({ ...f, ssl: val }))}
            />

            <Button
              variant="ghost"
              icon={isTesting ? Loader2 : Zap}
              onClick={handleTestConnection}
              disabled={!form.host || !form.database || !form.username || isTesting}
            >
              {isTesting ? 'Testing Connectivity...' : 'Test Connection'}
            </Button>

            {isTesting && (
              <div className="connection-test-result" style={{ backgroundColor: 'var(--color-border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                Connecting to {form.host}:{form.port || DEFAULT_PORTS[form.dbType] || 5432}...
              </div>
            )}
            {!isTesting && testResult && testResult.success && (
              <div className="connection-test-result success" style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <CheckCircle size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 600 }}>Connection successful!</div>
                  <div style={{ fontSize: '12px', opacity: 0.85 }}>
                    {testResult.message} {testResult.latency_ms != null && `(${testResult.latency_ms}ms)`}
                  </div>
                </div>
              </div>
            )}
            {!isTesting && testResult && !testResult.success && (
              <div className="connection-test-result error" style={{ display: 'flex', alignItems: 'flex-start', gap: '8px' }}>
                <XCircle size={16} style={{ marginTop: '2px', flexShrink: 0 }} />
                <div>
                  <div style={{ fontWeight: 600 }}>Connection failed</div>
                  <div style={{ fontSize: '12px', opacity: 0.85, wordBreak: 'break-word' }}>
                    {testResult.message}
                  </div>
                </div>
              </div>
            )}
          </div>
        </Modal>

        {/* Database Schema Visualizer (ERD) Modal */}
        <SchemaVisualizerModal
          isOpen={Boolean(visualizingConn)}
          onClose={() => setVisualizingConn(null)}
          connection={visualizingConn}
        />
      </div>
    </PageLayout>
  );
}
