'use client';

import React, { useEffect, useRef, useState } from 'react';
import { useMotionValue, animate } from 'framer-motion';

interface CountUpProps {
  value: number;
  decimals?: number;
  duration?: number;
  suffix?: string;
  prefix?: string;
  className?: string;
}

/**
 * Ticks a number up from its previous value to the new one whenever `value`
 * changes. Used for every headline statistic in the app — the point is that
 * re-filtering or re-loading data should feel like a live instrument
 * updating, not text popping in.
 */
export default function CountUp({
  value,
  decimals = 0,
  duration = 0.7,
  suffix = '',
  prefix = '',
  className = '',
}: CountUpProps) {
  const motionValue = useMotionValue(0);
  const [display, setDisplay] = useState('0');
  const hasMounted = useRef(false);

  useEffect(() => {
    const from = hasMounted.current ? motionValue.get() : 0;
    hasMounted.current = true;

    const controls = animate(from, value, {
      duration,
      ease: [0.16, 1, 0.3, 1],
      onUpdate: (v) => {
        setDisplay(v.toFixed(decimals));
      },
    });

    return () => controls.stop();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  return (
    <span className={`tabular-nums ${className}`}>
      {prefix}
      {display}
      {suffix}
    </span>
  );
}
