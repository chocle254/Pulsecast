'use client';

import React from 'react';
import { History, Users } from 'lucide-react';
import { PatternSignals } from '@/lib/api';

interface PatternBadgeProps {
  signals: PatternSignals | null | undefined;
  size?: 'sm' | 'md';
}

export default function PatternBadge({ signals, size = 'sm' }: PatternBadgeProps) {
  if (!signals || !signals.signals.length) return null;

  const hasRecurrence = signals.signals.some((s) => s.type === 'recurrence');
  const hasCluster = signals.signals.some((s) => s.type === 'regional_cluster');
  const title = signals.signals.map((s) => s.note).join(' ');

  let label = 'Pattern';
  if (hasCluster && !hasRecurrence) label = 'Regional Cluster';
  else if (hasRecurrence && !hasCluster) label = 'Recurring';

  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5 gap-1' : 'text-xs px-2 py-1 gap-1.5';

  return (
    <span
      className={`inline-flex items-center rounded font-mono font-semibold uppercase border shrink-0 ${sizeClasses}`}
      style={{ color: 'var(--accent)', background: 'var(--accent-bg)', borderColor: 'var(--accent-border)' }}
      title={title}
    >
      {hasCluster ? <Users className="w-3 h-3" /> : <History className="w-3 h-3" />}
      {label}
    </span>
  );
}
