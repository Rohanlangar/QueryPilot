import React from 'react';

export default function QueryExplainer({ explanation, anomalies = [] }) {
  if (!explanation) return null;

  return (
    <div className="agent-section">
      <div className="agent-section-header">
        <span className="agent-section-title">Explanation</span>
      </div>
      <div className="agent-section-body">
        <div className="explanation-text" dangerouslySetInnerHTML={{ __html: explanation }} />
        {anomalies.length > 0 && (
          <div style={{ marginTop: 'var(--space-sm)' }}>
            {anomalies.map((anomaly, idx) => (
              <div key={idx} className="explanation-anomaly">
                ⚠️ {anomaly}
              </div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
