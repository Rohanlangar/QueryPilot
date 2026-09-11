import React, { useState } from 'react';
import {
  Database, Plus, Wifi, WifiOff, Loader2, Pencil, Trash2, Zap,
  CheckCircle, XCircle,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Modal from '../components/common/Modal';
import Toggle from '../components/common/Toggle';
import useConnectionStore from '../store/connectionStore';

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

  const handleOpenNew = () => {
    setForm(INITIAL_FORM);
    setEditingId(null);
    setTestResult(null);
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

  const handleTestConnection = () => {
    setTestResult('testing');
    setTimeout(() => {
      setTestResult('success');
    }, 1500);
  };

  const handleSave = () => {
    const config = {
      name: form.name,
      dbType: form.dbType,
      host: form.host,
      port: Number(form.port),
      database: form.database,
      username: form.username,
      ssl: form.ssl,
    };

    if (editingId) {
      updateConnection(editingId, config);
    } else {
      const id = addConnection(config);
      if (!activeConnectionId) setActiveConnection(id);
    }
    setShowModal(false);
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
              <Button variant="ghost" onClick={() => setShowModal(false)}>
                Cancel
              </Button>
              <Button variant="primary" onClick={handleSave} disabled={!form.name || !form.host || !form.database}>
                {editingId ? 'Update' : 'Save Connection'}
              </Button>
            </>
          }
        >
          <div className="connection-form">
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
              />
              <Input
                label="Password"
                type="password"
                value={form.password}
                onChange={handleFormChange('password')}
                placeholder="••••••••"
              />
            </div>
            <Toggle
              label="Use SSL"
              checked={form.ssl}
              onChange={(val) => setForm((f) => ({ ...f, ssl: val }))}
            />

            <Button
              variant="ghost"
              icon={Zap}
              onClick={handleTestConnection}
              disabled={!form.host || !form.database}
            >
              Test Connection
            </Button>

            {testResult === 'testing' && (
              <div className="connection-test-result" style={{ backgroundColor: 'var(--color-border)' }}>
                <Loader2 size={16} style={{ animation: 'spin 1s linear infinite' }} />
                Testing connection...
              </div>
            )}
            {testResult === 'success' && (
              <div className="connection-test-result success">
                <CheckCircle size={16} />
                Connection successful!
              </div>
            )}
            {testResult === 'error' && (
              <div className="connection-test-result error">
                <XCircle size={16} />
                Connection failed. Check your credentials.
              </div>
            )}
          </div>
        </Modal>
      </div>
    </PageLayout>
  );
}
