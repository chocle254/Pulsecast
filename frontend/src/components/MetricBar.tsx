'use client';

import React from 'react';
import { motion } from 'framer-motion';

interface MetricBarProps {
  /** 0-1 */
  value: number;
  color: string;
  trackColor?: string;
  height?: number;
  delay?: number;
}

/**
 * A single horizontal fill bar that animates its width in from 0 on mount.
 * Used anywhere a percentage needs to read as a measured, verifiable
 * quantity rather than just a number — the backtest page especially, since
 * its entire job is showing the model's track record is real.
 */
export default function MetricBar({ value, color, trackColor = '#EDEEE8', height = 6, delay = 0 }: MetricBarProps) {
  const pct = Math.max(0, Math.min(1, value)) * 100;

  return (
    <div
      className="w-full rounded-full overflow-hidden"
      style={{ height, background: trackColor }}
    >
      <motion.div
        className="h-full rounded-full"
        style={{ background: color }}
        initial={{ width: '0%' }}
        animate={{ width: `${pct}%` }}
        transition={{ duration: 0.9, delay, ease: [0.16, 1, 0.3, 1] }}
      />
    </div>
  );
}
