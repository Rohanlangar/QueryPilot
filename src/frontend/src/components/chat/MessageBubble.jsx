import React, { useState } from 'react';
import { formatTimestamp } from '../../utils/dateUtils';
import AgentPipeline from './AgentPipeline';
import SQLBlock from './SQLBlock';
import QueryExplainer from './QueryExplainer';
import SuggestedQuestions from './SuggestedQuestions';
import ConfidenceBadge from '../common/ConfidenceBadge';
import ResultsInsights from './ResultsInsights';
import { BookOpen, Play, AlertCircle } from 'lucide-react';

export default function MessageBubble({ message, onSuggestedSelect }) {
  const [showExplanation, setShowExplanation] = useState(false);
  const [showResults, setShowResults] = useState(false);

  if (message.role === 'user') {
    return (
      <div className="message message-user">
        <div className="message-bubble">
          {message.content}
        </div>
        <div className="message-meta">
          <span className="message-time">{formatTimestamp(message.timestamp)}</span>
        </div>
      </div>
    );
  }

  // Agent error message
  if (message.error) {
    return (
      <div className="message message-agent message-error-state">
        <div className="agent-response">
          <div className="agent-error-box">
            <AlertCircle size={18} className="error-icon" />
            <div className="error-text">
              <strong>Query Execution Error</strong>
              <p>{message.explanation || message.content || 'An unexpected error occurred during execution.'}</p>
            </div>
          </div>
        </div>
        <div className="message-meta">
          <span className="message-time">{formatTimestamp(message.timestamp)}</span>
        </div>
      </div>
    );
  }

  // Agent message — structured response
  return (
    <div className="message message-agent">
      <div className="agent-response">
        {/* Pipeline Status */}
        {message.pipelineStatus && (
          <div className="agent-section" style={{ padding: 0 }}>
            <AgentPipeline stages={message.pipelineStatus} />
          </div>
        )}

        {/* Sources Used Badge List */}
        {message.sourcesUsed && message.sourcesUsed.length > 0 && (
          <div
            style={{
              display: 'flex',
              flexWrap: 'wrap',
              alignItems: 'center',
              gap: '8px',
              padding: '8px 12px',
              marginBottom: '10px',
              borderRadius: '6px',
              background: 'rgba(52, 211, 153, 0.08)',
              border: '1px solid rgba(52, 211, 153, 0.25)',
              fontSize: '12px',
            }}
          >
            <span style={{ fontWeight: 600, color: 'var(--color-secondary)' }}>Sources used:</span>
            {message.sourcesUsed.map((s, idx) => (
              <span
                key={idx}
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '5px',
                  padding: '3px 8px',
                  borderRadius: '4px',
                  background: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid var(--color-border)',
                  color: 'var(--color-text)',
                }}
              >
                <span style={{ color: 'var(--color-secondary)', fontWeight: 'bold' }}>✓</span>
                <strong style={{ color: 'var(--color-secondary)' }}>{s.database}</strong>
                {s.tables && s.tables.length > 0 && (
                  <span style={{ color: 'var(--color-muted)' }}>→ {s.tables.join(', ')}</span>
                )}
              </span>
            ))}
          </div>
        )}

        {/* Federated Execution Plan Visual */}
        {message.executionPlan && message.isFederated && (
          <div
            style={{
              padding: '10px 14px',
              marginBottom: '12px',
              borderRadius: '6px',
              background: '#0d1117',
              border: '1px solid #30363d',
              fontFamily: 'monospace',
              fontSize: '12px',
              lineHeight: '18px',
              color: '#7ee787',
              whiteSpace: 'pre-wrap',
            }}
          >
            <div style={{ color: '#8b949e', fontWeight: 600, marginBottom: '6px', fontSize: '11px', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Federated Execution Plan:
            </div>
            {message.executionPlan}
          </div>
        )}

        {/* SQL Block - Always Visible */}
        {message.sql && (
          <SQLBlock
            sql={message.sql}
            optimizedSql={message.optimizedSql}
            databaseQueries={message.databaseQueries}
          />
        )}

        {/* Confidence Badge - Always Visible */}
        {message.confidence && (
          <div className="message-confidence-row">
            <ConfidenceBadge
              level={message.confidence.level}
              message={message.confidence.message}
              details={message.confidence.details}
            />
          </div>
        )}

        {/* Action Controls: Explain and Execute */}
        <div className="message-action-bar">
          <button
            type="button"
            className={`action-btn action-btn-explain ${showExplanation ? 'action-btn-active' : ''}`}
            onClick={() => setShowExplanation((prev) => !prev)}
            title="Explain this query in plain business English"
          >
            <BookOpen size={15} />
            <span>{showExplanation ? 'Hide Explanation' : 'Explain'}</span>
          </button>

          <button
            type="button"
            className={`action-btn action-btn-execute ${showResults ? 'action-btn-active' : ''}`}
            onClick={() => setShowResults((prev) => !prev)}
            title="Execute query and inspect results table"
          >
            <Play size={15} />
            <span>{showResults ? 'Hide Results' : 'Execute'}</span>
          </button>
        </div>

        {/* Results Section - Revealed on Execute click */}
        {showResults && (
          <div className="agent-section results-animated-section">
            <div className="agent-section-header">
              <span className="agent-section-title">
                Query Results & Analytics
              </span>
            </div>
            <div className="agent-section-body" style={{ padding: '12px' }}>
              {message.results && message.results.data && message.results.data.length > 0 ? (
                <ResultsInsights
                  results={message.results}
                  rowCount={message.rowCount}
                  executionTimeMs={message.executionTimeMs}
                  chartSuggestion={message.chartSuggestion}
                />
              ) : (
                <div className="empty-results-notice">
                  Query executed successfully with 0 rows returned.
                </div>
              )}
            </div>
          </div>
        )}

        {/* Explanation Section - Revealed on Explain click */}
        {showExplanation && (
          <div className="explanation-animated-section">
            {message.explanation ? (
              <QueryExplainer
                explanation={message.explanation}
                anomalies={message.anomalies}
              />
            ) : (
              <div className="empty-explanation-notice">
                No explanation available for this query.
              </div>
            )}

            {/* Suggested Follow-up Questions */}
            {message.suggestedQuestions && message.suggestedQuestions.length > 0 && (
              <div style={{ marginTop: '12px' }}>
                <SuggestedQuestions
                  questions={message.suggestedQuestions}
                  onSelect={onSuggestedSelect}
                />
              </div>
            )}
          </div>
        )}
      </div>

      <div className="message-meta">
        <span className="message-time">{formatTimestamp(message.timestamp)}</span>
      </div>
    </div>
  );
}
