import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check, Database } from 'lucide-react';
import { formatSQL } from '../../utils/sqlFormatter';

export default function SQLBlock({ sql, optimizedSql, databaseQueries = null, showByDefault = true }) {
  const [copied, setCopied] = useState(false);
  const [showOptimized, setShowOptimized] = useState(false);
  const [activeTab, setActiveTab] = useState('all');

  const dbKeys = databaseQueries ? Object.keys(databaseQueries) : [];
  const hasMultiDbs = dbKeys.length > 1;

  let currentSql = sql;
  if (hasMultiDbs && activeTab !== 'all' && databaseQueries[activeTab]) {
    currentSql = databaseQueries[activeTab];
  } else if (showOptimized && optimizedSql) {
    currentSql = optimizedSql;
  }

  const formattedSql = formatSQL(currentSql || '');

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(currentSql || '');
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback copy
    }
  };

  if (!sql && (!databaseQueries || dbKeys.length === 0)) return null;

  return (
    <div className="agent-section">
      <div className="agent-section-header" style={{ flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span className="agent-section-title">
            {hasMultiDbs ? 'Federated SQL Queries' : 'SQL Query'}
          </span>

          {/* Database Tabs if Multi-DB */}
          {hasMultiDbs && (
            <div className="sql-toggle" style={{ marginLeft: '6px' }}>
              <button
                type="button"
                className={`sql-toggle-btn ${activeTab === 'all' ? 'active' : ''}`}
                onClick={() => setActiveTab('all')}
              >
                All DBs ({dbKeys.length})
              </button>
              {dbKeys.map((db) => (
                <button
                  key={db}
                  type="button"
                  className={`sql-toggle-btn ${activeTab === db ? 'active' : ''}`}
                  onClick={() => setActiveTab(db)}
                >
                  {db}
                </button>
              ))}
            </div>
          )}
        </div>

        <div className="flex items-center gap-xs" style={{ marginLeft: 'auto' }}>
          {optimizedSql && optimizedSql !== sql && !hasMultiDbs && (
            <div className="sql-toggle">
              <button
                className={`sql-toggle-btn ${!showOptimized ? 'active' : ''}`}
                onClick={() => setShowOptimized(false)}
              >
                Original
              </button>
              <button
                className={`sql-toggle-btn ${showOptimized ? 'active' : ''}`}
                onClick={() => setShowOptimized(true)}
              >
                Optimized
              </button>
            </div>
          )}
          <button
            className="sql-copy-btn"
            onClick={handleCopy}
            aria-label={copied ? 'Copied' : 'Copy SQL'}
          >
            {copied ? <Check size={12} /> : <Copy size={12} />}
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      </div>
      <div className="agent-section-body sql-block">
        <SyntaxHighlighter
          language="sql"
          style={oneLight}
          customStyle={{
            background: 'transparent',
            padding: 0,
            margin: 0,
            fontSize: '14px',
            lineHeight: '22px',
          }}
          wrapLongLines
        >
          {formattedSql}
        </SyntaxHighlighter>
      </div>
    </div>
  );
}
