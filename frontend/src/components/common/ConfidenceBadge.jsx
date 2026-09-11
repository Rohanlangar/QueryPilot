import React from 'react';
import { CheckCircle, AlertTriangle, AlertCircle } from 'lucide-react';
import Tooltip from './Tooltip';

const icons = {
  high: CheckCircle,
  medium: AlertTriangle,
  low: AlertCircle,
};

const labels = {
  high: 'High Confidence',
  medium: 'Medium Confidence',
  low: 'Low Confidence',
};

export default function ConfidenceBadge({ level = 'high', message, details }) {
  const Icon = icons[level];
  const badgeClass = `confidence-badge confidence-${level}`;

  const badge = (
    <span className={badgeClass} aria-label={`${labels[level]}: ${message}`}>
      <Icon size={14} />
      <span>{message || labels[level]}</span>
    </span>
  );

  if (details) {
    return (
      <Tooltip content={details}>
        {badge}
      </Tooltip>
    );
  }

  return badge;
}
