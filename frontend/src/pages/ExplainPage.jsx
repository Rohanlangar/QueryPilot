import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Code, ArrowRight, Copy, Check } from 'lucide-react';
import PageLayout from '../components/layout/PageLayout';
import Button from '../components/common/Button';
import Card from '../components/common/Card';
import Select from '../components/common/Select';
import Loader from '../components/common/Loader';

const DIALECTS = [
  { value: 'postgresql', label: 'PostgreSQL' },
  { value: 'mysql', label: 'MySQL' },
  { value: 'mssql', label: 'MSSQL' },
  { value: 'oracle', label: 'Oracle' },
];

const SAMPLE_SQL = `SELECT 
  d.department_name,
  COUNT(e.employee_id) AS total_employees,
  AVG(e.salary) AS avg_salary,
  SUM(CASE WHEN e.hire_date >= '2024-01-01' THEN 1 ELSE 0 END) AS new_hires
FROM departments d
LEFT JOIN employees e ON d.department_id = e.department_id
WHERE d.is_active = true
GROUP BY d.department_name
HAVING COUNT(e.employee_id) > 5
ORDER BY avg_salary DESC;`;

const MOCK_EXPLANATION = [
  {
    clause: 'SELECT',
    sql: "d.department_name, COUNT(e.employee_id) AS total_employees, AVG(e.salary) AS avg_salary, SUM(CASE WHEN e.hire_date >= '2024-01-01' THEN 1 ELSE 0 END) AS new_hires",
    explanation: 'Retrieves 4 columns: the department name, a count of employees, average salary, and the number of employees hired since January 1, 2024 (using a conditional sum to count only recent hires).',
  },
  {
    clause: 'FROM / JOIN',
    sql: 'FROM departments d LEFT JOIN employees e ON d.department_id = e.department_id',
    explanation: 'Starts from the departments table and left-joins employees. The LEFT JOIN ensures departments with zero employees still appear in results (they would show NULL for employee metrics).',
  },
  {
    clause: 'WHERE',
    sql: 'WHERE d.is_active = true',
    explanation: 'Filters to only include active departments. Inactive or archived departments are excluded before any aggregation happens.',
  },
  {
    clause: 'GROUP BY',
    sql: 'GROUP BY d.department_name',
    explanation: 'Groups all rows by department name, so each row in the result represents one department with its aggregated metrics.',
  },
  {
    clause: 'HAVING',
    sql: 'HAVING COUNT(e.employee_id) > 5',
    explanation: 'Filters out departments with 5 or fewer employees after grouping. This is applied after aggregation (unlike WHERE which filters before).',
  },
  {
    clause: 'ORDER BY',
    sql: 'ORDER BY avg_salary DESC',
    explanation: 'Sorts the results by average salary in descending order — highest-paying departments appear first.',
  },
];

export default function ExplainPage() {
  const [sql, setSql] = useState('');
  const [dialect, setDialect] = useState('postgresql');
  const [loading, setLoading] = useState(false);
  const [explanation, setExplanation] = useState(null);
  const [copied, setCopied] = useState(false);

  const handleExplain = () => {
    if (!sql.trim()) return;
    setLoading(true);
    // Simulate API call
    setTimeout(() => {
      setExplanation(MOCK_EXPLANATION);
      setLoading(false);
    }, 1500);
  };

  const handleLoadSample = () => {
    setSql(SAMPLE_SQL);
    setExplanation(null);
  };

  const handleCopyExplanation = async () => {
    if (!explanation) return;
    const text = explanation
      .map((e) => `${e.clause}:\n${e.explanation}`)
      .join('\n\n');
    try {
      await navigator.clipboard.writeText(text);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {}
  };

  return (
    <PageLayout>
      <div className="page-content" style={{ maxWidth: '900px', margin: '0 auto' }}>
        <h1 className="page-title">Explain This Query</h1>
        <p className="page-subtitle">
          Paste any SQL query and get a clause-by-clause breakdown in plain English.
        </p>

        {/* SQL Input */}
        <div style={{ marginBottom: 'var(--space-md)' }}>
          <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-xs)' }}>
            <label className="input-label">SQL Query</label>
            <Button variant="link" onClick={handleLoadSample} size="sm">
              Load sample query
            </Button>
          </div>
          <textarea
            className="input-field"
            value={sql}
            onChange={(e) => { setSql(e.target.value); setExplanation(null); }}
            placeholder="Paste your SQL query here..."
            rows={12}
            style={{
              fontFamily: "'DM Mono', 'Fira Code', monospace",
              fontSize: '14px',
              lineHeight: '22px',
              resize: 'vertical',
            }}
          />
        </div>

        {/* Controls */}
        <div className="flex items-end gap-sm" style={{ marginBottom: 'var(--space-lg)' }}>
          <Select
            label="SQL Dialect"
            value={dialect}
            onChange={(e) => setDialect(e.target.value)}
            options={DIALECTS}
            className="flex-1"
          />
          <Button
            variant="primary"
            icon={ArrowRight}
            onClick={handleExplain}
            disabled={!sql.trim()}
            loading={loading}
          >
            Explain
          </Button>
        </div>

        {/* Loading */}
        {loading && (
          <div style={{ padding: '48px', textAlign: 'center' }}>
            <Loader size="md" />
            <p className="text-body-sm text-muted" style={{ marginTop: '16px' }}>
              Analyzing your query...
            </p>
          </div>
        )}

        {/* Results */}
        {explanation && !loading && (
          <div>
            <div className="flex items-center justify-between" style={{ marginBottom: 'var(--space-sm)' }}>
              <h2 className="text-body-lg" style={{ fontWeight: 600 }}>
                Clause-by-Clause Breakdown
              </h2>
              <Button
                variant="ghost"
                size="sm"
                icon={copied ? Check : Copy}
                onClick={handleCopyExplanation}
              >
                {copied ? 'Copied' : 'Copy Explanation'}
              </Button>
            </div>

            <div className="flex flex-col gap-sm">
              {explanation.map((item, idx) => (
                <Card key={idx} bordered surface>
                  <div style={{ marginBottom: '10px' }}>
                    <span
                      className="chip chip-secondary"
                      style={{ fontWeight: 600, fontSize: '13px' }}
                    >
                      {item.clause}
                    </span>
                  </div>
                  <div style={{ marginBottom: '12px', borderRadius: 'var(--rounded-sm)', overflow: 'hidden' }}>
                    <SyntaxHighlighter
                      language="sql"
                      style={oneLight}
                      customStyle={{
                        background: 'var(--color-background)',
                        padding: '12px',
                        margin: 0,
                        fontSize: '13px',
                        lineHeight: '20px',
                        borderRadius: 'var(--rounded-sm)',
                      }}
                      wrapLongLines
                    >
                      {item.sql}
                    </SyntaxHighlighter>
                  </div>
                  <p className="text-body-sm" style={{ color: 'var(--color-on-surface)' }}>
                    {item.explanation}
                  </p>
                </Card>
              ))}
            </div>
          </div>
        )}
      </div>
    </PageLayout>
  );
}
