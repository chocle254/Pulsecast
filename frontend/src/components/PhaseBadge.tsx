import React from 'react';

interface PhaseBadgeProps {
  phase: string;
  size?: 'sm' | 'md' | 'lg';
  showDot?: boolean;
}

export default function PhaseBadge({ phase, size = 'md', showDot = true }: PhaseBadgeProps) {
  const normalized = (phase || 'Normal').toLowerCase();
  const phaseClass = `phase-${normalized}`;

  const sizeClasses = {
    sm: 'text-[11px] px-1.5 py-0.5',
    md: 'text-xs px-2 py-1',
    lg: 'text-sm px-3 py-1.5',
  };

  return (
    <span className={`phase-badge ${phaseClass} ${sizeClasses[size]}`}>
      {showDot && <span className="phase-dot" />}
      <span>{phase}</span>
    </span>
  );
}
