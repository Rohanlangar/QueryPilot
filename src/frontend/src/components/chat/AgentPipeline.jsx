import React from 'react';
import { Check, Circle, Loader2 } from 'lucide-react';
import Tooltip from '../common/Tooltip';

const STAGE_ICONS = {
  complete: Check,
  active: Loader2,
  pending: Circle,
};

export default function AgentPipeline({ stages = [] }) {
  const defaultStages = [
    { name: 'Schema', status: 'pending', detail: '' },
    { name: 'Generate', status: 'pending', detail: '' },
    { name: 'Validate', status: 'pending', detail: '' },
    { name: 'Optimize', status: 'pending', detail: '' },
    { name: 'Explain', status: 'pending', detail: '' },
  ];

  const displayStages = stages.length > 0 ? stages : defaultStages;

  return (
    <div className="pipeline" role="status" aria-label="Agent pipeline progress">
      {displayStages.map((stage, idx) => {
        const Icon = STAGE_ICONS[stage.status] || Circle;
        const stageEl = (
          <div
            key={stage.name}
            className={`pipeline-stage pipeline-stage-${stage.status}`}
            aria-label={`${stage.name}: ${stage.status}`}
          >
            <Icon size={12} className={stage.status === 'active' ? 'spin-slow' : ''} />
            <span>{stage.name}</span>
          </div>
        );

        return (
          <React.Fragment key={stage.name}>
            {idx > 0 && <div className="pipeline-connector" />}
            {stage.detail ? (
              <Tooltip content={stage.detail}>{stageEl}</Tooltip>
            ) : (
              stageEl
            )}
          </React.Fragment>
        );
      })}
    </div>
  );
}
