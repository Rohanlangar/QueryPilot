import React from 'react';
import { Save } from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import Card from '../components/common/Card';
import Input from '../components/common/Input';
import Select from '../components/common/Select';
import Toggle from '../components/common/Toggle';
import Button from '../components/common/Button';
import useSettingsStore from '../store/settingsStore';
import useAuthStore from '../store/authStore';

export default function SettingsPage() {
  const user = useAuthStore((s) => s.user);
  const settings = useSettingsStore();
  const update = useSettingsStore((s) => s.updateSettings);

  return (
    <PageLayout>
      <div className="page-content" style={{ maxWidth: '800px', margin: '0 auto' }}>
        <h1 className="page-title">Settings</h1>

        {/* Profile */}
        <Card bordered surface style={{ marginBottom: 'var(--space-md)' }} padding="lg">
          <h3 className="text-body-lg" style={{ fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
            Profile
          </h3>
          <div className="flex flex-col gap-sm">
            <Input label="Display Name" value={user?.name || ''} disabled />
            <Input label="Email" value={user?.email || ''} disabled />
            <div className="flex items-center gap-xs">
              <span className="input-label" style={{ marginRight: '8px' }}>Role:</span>
              <span className="chip chip-secondary" style={{ textTransform: 'capitalize' }}>
                {user?.role || 'viewer'}
              </span>
            </div>
          </div>
        </Card>

        {/* Query Preferences */}
        <Card bordered surface style={{ marginBottom: 'var(--space-md)' }} padding="lg">
          <h3 className="text-body-lg" style={{ fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
            Query Preferences
          </h3>
          <div className="flex flex-col gap-sm">
            <Select
              label="Default Row Limit"
              value={String(settings.defaultRowLimit)}
              onChange={(e) => update({ defaultRowLimit: Number(e.target.value) })}
              options={[
                { value: '100', label: '100 rows' },
                { value: '500', label: '500 rows' },
                { value: '1000', label: '1,000 rows' },
                { value: '5000', label: '5,000 rows' },
              ]}
            />
            <Select
              label="Default Chart Type"
              value={settings.defaultChartType}
              onChange={(e) => update({ defaultChartType: e.target.value })}
              options={[
                { value: 'auto', label: 'Auto-detect' },
                { value: 'bar', label: 'Bar Chart' },
                { value: 'line', label: 'Line Chart' },
                { value: 'table', label: 'Table' },
              ]}
            />
            <Toggle
              label="Show SQL by default"
              checked={settings.showSqlByDefault}
              onChange={(val) => update({ showSqlByDefault: val })}
            />
          </div>
        </Card>

        {/* Notifications */}
        <Card bordered surface style={{ marginBottom: 'var(--space-md)' }} padding="lg">
          <h3 className="text-body-lg" style={{ fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
            Notifications
          </h3>
          <div className="flex flex-col gap-sm">
            <Toggle
              label="Query completion alerts"
              checked={settings.queryCompletionAlerts}
              onChange={(val) => update({ queryCompletionAlerts: val })}
            />
            <Input
              label="Cost warning threshold (seconds)"
              type="number"
              value={String(settings.costWarningThreshold)}
              onChange={(e) => update({ costWarningThreshold: Number(e.target.value) })}
              helper="Alert when estimated query time exceeds this threshold"
            />
          </div>
        </Card>

        {/* API / Mode */}
        <Card bordered surface style={{ marginBottom: 'var(--space-md)' }} padding="lg">
          <h3 className="text-body-lg" style={{ fontWeight: 600, marginBottom: 'var(--space-sm)' }}>
            AI Configuration
          </h3>
          <div className="flex flex-col gap-sm">
            <Toggle
              label="Offline mode (local model)"
              checked={settings.mode === 'offline'}
              onChange={(val) => update({ mode: val ? 'offline' : 'online' })}
            />
            {settings.mode === 'online' ? (
              <Input
                label="API Endpoint"
                value={settings.apiEndpoint}
                onChange={(e) => update({ apiEndpoint: e.target.value })}
                placeholder="https://api.example.com/v1"
              />
            ) : (
              <Select
                label="Local Model"
                value={settings.selectedModel}
                onChange={(e) => update({ selectedModel: e.target.value })}
                options={[
                  { value: '', label: 'Select a model...' },
                  { value: 'sqlcoder-7b', label: 'SQLCoder 7B' },
                  { value: 'sqlcoder-15b', label: 'SQLCoder 15B' },
                  { value: 'codellama-13b', label: 'Code Llama 13B' },
                ]}
              />
            )}
          </div>
        </Card>

        <div className="flex justify-end">
          <Button variant="primary" icon={Save}>
            Save Settings
          </Button>
        </div>
      </div>
    </PageLayout>
  );
}
