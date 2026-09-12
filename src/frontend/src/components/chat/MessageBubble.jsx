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
  const [showResults, setShowResults] = useState(
    message.results ? true : false
  );

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

        {/* SQL Block - Always Visible */}
        {message.sql && (
          <SQLBlock
            sql={message.sql}
            optimizedSql={message.optimizedSql}
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
