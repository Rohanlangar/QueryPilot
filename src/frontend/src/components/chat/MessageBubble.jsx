import React from 'react';
import { formatTimestamp } from '../../utils/dateUtils';
import AgentPipeline from './AgentPipeline';
import SQLBlock from './SQLBlock';
import QueryExplainer from './QueryExplainer';
import SuggestedQuestions from './SuggestedQuestions';
import ConfidenceBadge from '../common/ConfidenceBadge';
import ChartRenderer from '../visualization/ChartRenderer';

export default function MessageBubble({ message, onSuggestedSelect }) {
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

        {/* SQL Block */}
        {message.sql && (
          <SQLBlock
            sql={message.sql}
            optimizedSql={message.optimizedSql}
          />
        )}

        {/* Confidence Badge */}
        {message.confidence && (
          <div style={{ padding: '4px 0' }}>
            <ConfidenceBadge
              level={message.confidence.level}
              message={message.confidence.message}
              details={message.confidence.details}
            />
          </div>
        )}

        {/* Results Visualization */}
        {message.results && message.results.data && message.results.data.length > 0 && (
          <div className="agent-section">
            <div className="agent-section-header">
              <span className="agent-section-title">
                Results ({message.results.data.length} rows)
              </span>
            </div>
            <div className="agent-section-body">
              <ChartRenderer
                data={message.results.data}
                columns={message.results.columns}
              />
            </div>
          </div>
        )}

        {/* Explanation */}
        {message.explanation && (
          <QueryExplainer
            explanation={message.explanation}
            anomalies={message.anomalies}
          />
        )}

        {/* Suggested Questions */}
        {message.suggestedQuestions && (
          <SuggestedQuestions
            questions={message.suggestedQuestions}
            onSelect={onSuggestedSelect}
          />
        )}
      </div>

      <div className="message-meta">
        <span className="message-time">{formatTimestamp(message.timestamp)}</span>
      </div>
    </div>
  );
}
