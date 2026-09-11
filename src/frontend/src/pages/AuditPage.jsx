import React, { useState } from 'react';
import {
  Download, ChevronDown, ChevronUp, Search,
  CheckCircle, XCircle, ShieldOff,
} from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import Card from '../components/common/Card';
import Button from '../components/common/Button';
import Input from '../components/common/Input';
import Chip from '../components/common/Chip';
import ConfidenceBadge from '../components/common/ConfidenceBadge';

// Mock audit data
const MOCK_STATS = {
  totalQueries: 284,
  uniqueUsers: 12,
  avgConfidence: 87,
  blockedQueries: 3,
};

const MOCK_LOGS = [
  {
    id: 'log-1',
    timestamp: '2024-03-15T14:23:00Z',
    user: 'Sarah Chen',
    question: "What were last month's top 10 products by revenue?",
    sql: 'SELECT p.product_name, SUM(oi.quantity * oi.unit_price) AS total_revenue FROM products p JOIN order_items oi ON p.product_id = oi.product_id GROUP BY p.product_name ORDER BY total_revenue DESC LIMIT 10;',
    database: 'prod_analytics',
    confidence: { level: 'high', message: 'All columns verified' },
    executionTime: '234ms',
    rowCount: 10,
    status: 'success',
  },
  {
    id: 'log-2',
    timestamp: '2024-03-15T13:45:00Z',
    user: 'James Wilson',
    question: 'Show all customer emails from the last quarter',
    sql: null,
    database: 'prod_analytics',
    confidence: { level: 'low', message: 'PII column blocked' },
    executionTime: '—',
    rowCount: 0,
    status: 'blocked',
  },
  {
    id: 'log-3',
    timestamp: '2024-03-15T12:10:00Z',
    user: 'Maria Garcia',
    question: 'Monthly revenue trend for 2024',
    sql: "SELECT DATE_TRUNC('month', order_date) AS month, SUM(total_amount) AS revenue FROM orders WHERE order_date >= '2024-01-01' GROUP BY month ORDER BY month;",
    database: 'prod_analytics',
    confidence: { level: 'high', message: 'Exact match' },
    executionTime: '187ms',
    rowCount: 3,
    status: 'success',
  },
  {
    id: 'log-4',
    timestamp: '2024-03-15T11:30:00Z',
    user: 'Alex Thompson',
    question: 'Compare Q3 vs Q4 performance by department',
    sql: "SELECT d.name, SUM(CASE WHEN o.order_date BETWEEN '2024-07-01' AND '2024-09-30' THEN o.total ELSE 0 END) AS q3, SUM(CASE WHEN o.order_date BETWEEN '2024-10-01' AND '2024-12-31' THEN o.total ELSE 0 END) AS q4 FROM departments d JOIN orders o ON d.id = o.dept_id GROUP BY d.name;",
    database: 'prod_analytics',
    confidence: { level: 'medium', message: 'Assumed fiscal quarters' },
    executionTime: '412ms',
    rowCount: 8,
    status: 'success',
  },
  {
    id: 'log-5',
    timestamp: '2024-03-15T10:05:00Z',
    user: 'Sarah Chen',
    question: 'Average delivery time by product category',
    sql: "SELECT c.name, AVG(EXTRACT(DAY FROM d.delivered_at - o.created_at)) AS avg_days FROM categories c JOIN products p ON c.id = p.category_id JOIN orders o ON p.id = o.product_id JOIN deliveries d ON o.id = d.order_id WHERE d.delivered_at IS NOT NULL GROUP BY c.name ORDER BY avg_days;",
    database: 'prod_analytics',
    confidence: { level: 'high', message: 'All columns verified' },
    executionTime: '567ms',
    rowCount: 12,
    status: 'success',
  },
];

export default function AuditPage() {
  const [expandedRow, setExpandedRow] = useState(null);
  const [searchTerm, setSearchTerm] = useState('');

  const filteredLogs = MOCK_LOGS.filter((log) =>
    log.question.toLowerCase().includes(searchTerm.toLowerCase()) ||
    log.user.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const getStatusChip = (status) => {
    switch (status) {
      case 'success':
        return <Chip variant="secondary" icon={CheckCircle}>Success</Chip>;
      case 'blocked':
        return <Chip variant="error" icon={ShieldOff}>Blocked</Chip>;
      case 'failed':
        return <Chip variant="error" icon={XCircle}>Failed</Chip>;
      default:
        return <Chip variant="muted">{status}</Chip>;
    }
  };

  const handleExport = () => {
    const csv = [
      'Timestamp,User,Question,Database,Confidence,Status,Execution Time,Row Count',
      ...MOCK_LOGS.map((log) =>
        `"${log.timestamp}","${log.user}","${log.question}","${log.database}","${log.confidence.level}","${log.status}","${log.executionTime}","${log.rowCount}"`
      ),
    ].join('\n');
    const blob = new Blob([csv], { type: 'text/csv' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'audit-log.csv';
    a.click();
    URL.revokeObjectURL(url);
  };

  return (
    <PageLayout>
      <div className="page-content">
        <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-md)' }}>
          <div>
            <h1 className="page-title" style={{ marginBottom: '4px' }}>Audit Trail</h1>
            <p className="text-body-md text-muted">Complete query provenance log for compliance and governance.</p>
          </div>
          <Button variant="ghost" icon={Download} onClick={handleExport}>
            Export CSV
          </Button>
        </div>

        {/* Stats */}
        <div className="audit-stats">
          <Card bordered surface className="audit-stat-card">
            <div className="audit-stat-value">{MOCK_STATS.totalQueries}</div>
            <div className="audit-stat-label">Total Queries</div>
          </Card>
          <Card bordered surface className="audit-stat-card">
            <div className="audit-stat-value">{MOCK_STATS.uniqueUsers}</div>
            <div className="audit-stat-label">Unique Users</div>
          </Card>
          <Card bordered surface className="audit-stat-card">
            <div className="audit-stat-value">{MOCK_STATS.avgConfidence}%</div>
            <div className="audit-stat-label">Avg Confidence</div>
          </Card>
          <Card bordered surface className="audit-stat-card">
            <div className="audit-stat-value" style={{ color: MOCK_STATS.blockedQueries > 0 ? 'var(--color-error)' : undefined }}>
              {MOCK_STATS.blockedQueries}
            </div>
            <div className="audit-stat-label">Blocked Queries</div>
          </Card>
        </div>

        {/* Filter */}
        <div className="audit-filters">
          <div className="flex items-center gap-xs" style={{ flex: 1, maxWidth: '400px' }}>
            <Search size={16} style={{ color: 'var(--color-muted)' }} />
            <input
              className="input-field"
              placeholder="Search by question or user..."
              value={searchTerm}
              onChange={(e) => setSearchTerm(e.target.value)}
              style={{ fontSize: '14px', padding: '10px 14px' }}
            />
          </div>
        </div>

        {/* Log Table */}
        <div className="audit-table-wrapper">
          <table className="data-table">
            <thead>
              <tr>
                <th style={{ width: '40px' }}></th>
                <th>Time</th>
                <th>User</th>
                <th>Question</th>
                <th>Database</th>
                <th>Confidence</th>
                <th>Time</th>
                <th>Rows</th>
                <th>Status</th>
              </tr>
            </thead>
            <tbody>
              {filteredLogs.map((log) => (
                <React.Fragment key={log.id}>
                  <tr
                    className={expandedRow === log.id ? 'audit-row-expanded' : ''}
                    style={{ cursor: 'pointer' }}
                    onClick={() => setExpandedRow(expandedRow === log.id ? null : log.id)}
                  >
                    <td>
                      {expandedRow === log.id ? (
                        <ChevronUp size={16} style={{ color: 'var(--color-muted)' }} />
                      ) : (
                        <ChevronDown size={16} style={{ color: 'var(--color-muted)' }} />
                      )}
                    </td>
                    <td className="text-label-sm">{new Date(log.timestamp).toLocaleTimeString()}</td>
                    <td>{log.user}</td>
                    <td style={{ maxWidth: '280px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                      {log.question}
                    </td>
                    <td><Chip variant="muted">{log.database}</Chip></td>
                    <td>
                      <ConfidenceBadge
                        level={log.confidence.level}
                        message={log.confidence.message}
                      />
                    </td>
                    <td className="text-label-sm">{log.executionTime}</td>
                    <td className="text-label-sm">{log.rowCount}</td>
                    <td>{getStatusChip(log.status)}</td>
                  </tr>
                  {expandedRow === log.id && (
                    <tr>
                      <td colSpan={9}>
                        <div className="audit-row-detail">
                          <div className="audit-row-detail-section">
                            <span className="audit-row-detail-label">Full Question</span>
                            <p className="text-body-sm">{log.question}</p>
                          </div>
                          {log.sql && (
                            <div className="audit-row-detail-section">
                              <span className="audit-row-detail-label">Generated SQL</span>
                              <pre
                                style={{
                                  background: 'var(--color-surface)',
                                  padding: '12px',
                                  borderRadius: 'var(--rounded-sm)',
                                  fontSize: '13px',
                                  fontFamily: "'DM Mono', monospace",
                                  overflow: 'auto',
                                  whiteSpace: 'pre-wrap',
                                }}
                              >
                                {log.sql}
                              </pre>
                            </div>
                          )}
                          {!log.sql && log.status === 'blocked' && (
                            <div className="audit-row-detail-section">
                              <span className="audit-row-detail-label">Block Reason</span>
                              <p className="text-body-sm" style={{ color: 'var(--color-error)' }}>
                                Query attempted to access PII-tagged columns. Access denied per organization policy.
                              </p>
                            </div>
                          )}
                        </div>
                      </td>
                    </tr>
                  )}
                </React.Fragment>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </PageLayout>
  );
}
