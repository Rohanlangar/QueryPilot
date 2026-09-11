import React, { useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { formatTimestamp } from '../../utils/dateUtils';
import AgentPipeline from './AgentPipeline';
import SQLBlock from './SQLBlock';
import QueryExplainer from './QueryExplainer';
import SuggestedQuestions from './SuggestedQuestions';
import ConfidenceBadge from '../common/ConfidenceBadge';
import ResultsInsights from './ResultsInsights';
import { BookOpen, Play, AlertCircle, ShieldAlert, ExternalLink } from 'lucide-react';

function SecurityIncidentCard({ incident, rawExplanation, timestamp }) {
  const navigate = useNavigate();

  const threatType = incident?.threat_type || 'CYBER_ATTACK_INTERCEPTED';
  const incidentId = incident?.incident_id || 'SEC-ALERT-BLOCKED';
  const severity = incident?.severity || 'CRITICAL';
  const policy = incident?.policy_violated || 'SEC-POL-01: Zero-Trust Database Guardrail';
  const mitigation = incident?.mitigation || 'Query execution terminated pre-flight. Malicious payload blocked from database engines.';
  const tokens = incident?.detected_tokens || [];

  return (
    <div
      style={{
        background: 'linear-gradient(135deg, rgba(239, 68, 68, 0.12) 0%, rgba(15, 23, 42, 0.95) 100%)',
        border: '1px solid rgba(239, 68, 68, 0.45)',
        boxShadow: '0 0 25px rgba(239, 68, 68, 0.18)',
        borderRadius: '12px',
        padding: '18px 20px',
        color: '#f8fafc',
        marginBottom: '10px',
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '14px', flexWrap: 'wrap', gap: '8px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              width: '36px',
              height: '36px',
              borderRadius: '8px',
              background: 'rgba(239, 68, 68, 0.2)',
              border: '1px solid rgba(239, 68, 68, 0.6)',
              color: '#ef4444',
            }}
          >
            <ShieldAlert size={22} />
          </div>
          <div>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontSize: '15px', fontWeight: 'bold', color: '#fca5a5', letterSpacing: '0.02em' }}>
                CYBER-ATTACK INTERCEPTED &amp; NEUTRALIZED
              </span>
              <span
                style={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: '4px',
                  background: 'rgba(239, 68, 68, 0.25)',
                  border: '1px solid #ef4444',
                  color: '#fee2e2',
                  fontSize: '11px',
                  fontWeight: 'bold',
                  padding: '2px 8px',
                  borderRadius: '12px',
                }}
              >
                <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: '#ef4444', display: 'inline-block', boxShadow: '0 0 8px #ef4444' }}></span>
                {severity}
              </span>
            </div>
            <div style={{ fontSize: '12px', color: '#94a3b8' }}>
              Ref: <code style={{ color: '#cbd5e1', fontWeight: 600 }}>{incidentId}</code> • Pre-Flight Deterministic Enforcement
            </div>
          </div>
        </div>
        <button
          onClick={() => navigate('/audit')}
          style={{
            display: 'inline-flex',
            alignItems: 'center',
            gap: '6px',
            background: 'rgba(239, 68, 68, 0.15)',
            border: '1px solid rgba(239, 68, 68, 0.4)',
            color: '#fecaca',
            fontSize: '12px',
            padding: '6px 12px',
            borderRadius: '6px',
            cursor: 'pointer',
            transition: 'all 0.2s ease',
          }}
          title="Inspect incident in SOC 2 Audit Trail"
        >
          <span>View Audit Trail</span>
          <ExternalLink size={13} />
        </button>
      </div>

      <div
        style={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
          gap: '10px',
          marginBottom: '14px',
        }}
      >
        <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Threat Vector</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#f87171', marginTop: '3px' }}>{threatType}</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Active Gate</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#60a5fa', marginTop: '3px' }}>Agent 3: AST Security Gate</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Target DB Integrity</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#34d399', marginTop: '3px' }}>100% UNTOUCHED</div>
        </div>
        <div style={{ background: 'rgba(0, 0, 0, 0.35)', padding: '10px 12px', borderRadius: '8px', border: '1px solid rgba(255, 255, 255, 0.08)' }}>
          <div style={{ fontSize: '11px', color: '#94a3b8', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Execution Time</div>
          <div style={{ fontSize: '13px', fontWeight: 600, color: '#fbbf24', marginTop: '3px' }}>0 ms (Aborted Pre-Flight)</div>
        </div>
      </div>

      <div style={{ fontSize: '12px', color: '#e2e8f0', lineHeight: '18px', background: 'rgba(0, 0, 0, 0.25)', padding: '10px 12px', borderRadius: '8px', borderLeft: '3px solid #ef4444' }}>
        <div><strong style={{ color: '#fca5a5' }}>Policy Violated:</strong> {policy}</div>
        <div style={{ marginTop: '4px', color: '#cbd5e1' }}><strong>Mitigation:</strong> {mitigation}</div>
      </div>

      {tokens.length > 0 && (
        <div style={{ marginTop: '10px', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '6px', flexWrap: 'wrap' }}>
          <span style={{ color: '#94a3b8' }}>Flagged Tokens:</span>
          {tokens.map((t, idx) => (
            <span key={idx} style={{ background: 'rgba(239, 68, 68, 0.2)', border: '1px solid rgba(239, 68, 68, 0.5)', color: '#fee2e2', padding: '1px 7px', borderRadius: '4px', fontFamily: 'monospace', fontSize: '11px' }}>
              {t}
            </span>
          ))}
        </div>
      )}
    </div>
  );
}

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

  // Intercepted Cyber-Attack / Security Incident
  const isSecurityIncident = Boolean(
    message.securityIncident ||
    (message.error && (
      message.explanation?.includes('CYBER-ATTACK') ||
      message.explanation?.includes('SECURITY_INCIDENT') ||
      message.explanation?.includes('Security violation') ||
      message.explanation?.includes('prohibited') ||
      message.explanation?.includes('Disallowed SQL keyword')
    )) ||
    message.explanation?.includes('CYBER-ATTACK INTERCEPTED')
  );

  if (isSecurityIncident) {
    return (
      <div className="message message-agent">
        <div className="agent-response">
          <SecurityIncidentCard
            incident={message.securityIncident}
            rawExplanation={message.explanation || message.content}
            timestamp={message.timestamp}
          />
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
