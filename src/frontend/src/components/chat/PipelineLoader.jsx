import React, { useState, useEffect } from 'react';
import { Database, Code2, ShieldCheck, Zap, PlayCircle, Sparkles, Check, Loader2 } from 'lucide-react';

const PIPELINE_STAGES = [
  {
    id: 'schema',
    label: 'Schema Understanding',
    description: 'Analyzing tables, relationships & column types...',
    icon: Database,
  },
  {
    id: 'sql_gen',
    label: 'SQL Synthesis',
    description: 'Generating optimized dialect-specific SQL...',
    icon: Code2,
  },
  {
    id: 'validate',
    label: 'Security & Validation',
    description: 'Checking AST rules, permissions & syntax...',
    icon: ShieldCheck,
  },
  {
    id: 'optimize',
    label: 'Query Optimization',
    description: 'Evaluating indexing, joins & query plan...',
    icon: Zap,
  },
  {
    id: 'execute',
    label: 'Execution Engine',
    description: 'Executing query & applying PII masking...',
    icon: PlayCircle,
  },
  {
    id: 'explain',
    label: 'Business Explanation',
    description: 'Synthesizing plain English insights...',
    icon: Sparkles,
  },
];

export default function PipelineLoader({ activeStageId, stageProgress }) {
  const [currentIdx, setCurrentIdx] = useState(0);
  const [elapsedSeconds, setElapsedSeconds] = useState(0);

  // If activeStageId is passed from WebSocket or store, use it
  useEffect(() => {
    if (activeStageId) {
      const idx = PIPELINE_STAGES.findIndex((s) => s.id === activeStageId);
      if (idx !== -1) {
        setCurrentIdx(idx);
      }
    }
  }, [activeStageId]);

  // If no external activeStageId provided, simulate smooth progression through stages
  useEffect(() => {
    if (activeStageId) return;

    // Progression schedule (ms per stage)
    const timers = [
      setTimeout(() => setCurrentIdx(1), 1200), // to sql_gen
      setTimeout(() => setCurrentIdx(2), 2600), // to validate
      setTimeout(() => setCurrentIdx(3), 3800), // to optimize
      setTimeout(() => setCurrentIdx(4), 5000), // to execute
      setTimeout(() => setCurrentIdx(5), 6500), // to explain
    ];

    return () => timers.forEach(clearTimeout);
  }, [activeStageId]);

  // Elapsed timer ticker
  useEffect(() => {
    const interval = setInterval(() => {
      setElapsedSeconds((prev) => prev + 0.5);
    }, 500);
    return () => clearInterval(interval);
  }, []);

  return (
    <div className="pipeline-loader-card">
      <div className="pipeline-loader-header">
        <div className="pipeline-loader-badge">
          <span className="pipeline-pulse-dot" />
          <span className="pipeline-loader-title">AI Multi-Agent Pipeline Active</span>
        </div>
        <span className="pipeline-loader-timer">{elapsedSeconds.toFixed(1)}s elapsed</span>
      </div>

      <div className="pipeline-stepper-list">
        {PIPELINE_STAGES.map((stage, idx) => {
          const isDone = idx < currentIdx;
          const isActive = idx === currentIdx;
          const isPending = idx > currentIdx;
          const Icon = stage.icon;

          return (
            <div
              key={stage.id}
              className={`pipeline-step-item ${
                isDone ? 'step-done' : isActive ? 'step-active' : 'step-pending'
              }`}
            >
              <div className="pipeline-step-indicator">
                <div className="pipeline-step-icon-wrap">
                  {isDone ? (
                    <Check size={14} className="step-check-icon" />
                  ) : isActive ? (
                    <Loader2 size={14} className="step-spinner-icon" />
                  ) : (
                    <Icon size={13} className="step-pending-icon" />
                  )}
                </div>
                {idx < PIPELINE_STAGES.length - 1 && (
                  <div className={`pipeline-step-line ${isDone ? 'line-done' : ''}`} />
                )}
              </div>

              <div className="pipeline-step-details">
                <div className="pipeline-step-title-row">
                  <span className="pipeline-step-name">{stage.label}</span>
                  {isActive && <span className="pipeline-step-tag">In progress</span>}
                  {isDone && <span className="pipeline-step-tag tag-done">Completed</span>}
                </div>
                <span className="pipeline-step-desc">
                  {isActive ? stage.description : isDone ? 'Step verified' : 'Queued'}
                </span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
}
