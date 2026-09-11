import React, { useState } from 'react';
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { oneLight } from 'react-syntax-highlighter/dist/esm/styles/prism';
import { Copy, Check } from 'lucide-react';
import { formatSQL } from '../../utils/sqlFormatter';

export default function SQLBlock({ sql, optimizedSql, showByDefault = true }) {
  const [copied, setCopied] = useState(false);
  const [showOptimized, setShowOptimized] = useState(false);
  const [expanded, setExpanded] = useState(showByDefault);

  const displaySql = showOptimized && optimizedSql ? optimizedSql : sql;
  const formattedSql = formatSQL(displaySql);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(displaySql);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch {
      // Fallback copy
    }
  };

  if (!sql) return null;

  return (
    <div className="agent-section">
      <div className="agent-section-header">
        <span className="agent-section-title">SQL Query</span>
        <div className="flex items-center gap-xs">
          {optimizedSql && optimizedSql !== sql && (
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
