'use client';

import React from 'react';

interface SparklineProps {
  data: number[];
  forecastValue?: number | null;
  width?: number;
  height?: number;
  threshold?: number;
}

export default function Sparkline({
  data,
  forecastValue,
  width = 120,
  height = 36,
  threshold = 35, // Alert threshold
}: SparklineProps) {
  if (!data || data.length === 0) {
    return <div style={{ width, height }} className="bg-gray-100 rounded" />;
  }

  const allPoints = [...data];
  if (forecastValue !== undefined && forecastValue !== null) {
    allPoints.push(forecastValue);
  }

  const padding = 4;
  const minVal = Math.min(...allPoints, threshold - 5, 0);
  const maxVal = Math.max(...allPoints, threshold + 5, 100);

  const getY = (val: number) => {
    const range = maxVal - minVal || 1;
    return height - padding - ((val - minVal) / range) * (height - 2 * padding);
  };

  const getX = (idx: number, total: number) => {
    const step = (width - 2 * padding) / (total - 1 || 1);
    return padding + idx * step;
  };

  // Historical path
  const historicalCount = data.length;
  const totalCount = allPoints.length;

  const histPointsStr = data
    .map((val, i) => `${getX(i, totalCount)},${getY(val)}`)
    .join(' ');

  // Forecast path
  let forecastPointsStr = '';
  if (forecastValue !== undefined && forecastValue !== null) {
    const lastHistX = getX(historicalCount - 1, totalCount);
    const lastHistY = getY(data[data.length - 1]);
    const forecastX = getX(totalCount - 1, totalCount);
    const forecastY = getY(forecastValue);
    forecastPointsStr = `${lastHistX},${lastHistY} ${forecastX},${forecastY}`;
  }

  const thresholdY = getY(threshold);

  return (
    <svg width={width} height={height} className="overflow-visible">
      {/* Threshold reference line */}
      <line
        x1={padding}
        y1={thresholdY}
        x2={width - padding}
        y2={thresholdY}
        stroke="#E0BE6C"
        strokeDasharray="2,2"
        strokeWidth="1"
        opacity="0.85"
      />

      {/* Historical line */}
      <polyline
        fill="none"
        stroke="#232A2E"
        strokeWidth="1.75"
        points={histPointsStr}
        strokeLinecap="round"
        strokeLinejoin="round"
      />

      {/* Forecast extension (dashed) */}
      {forecastPointsStr && (
        <polyline
          fill="none"
          stroke="#B9713A"
          strokeWidth="1.75"
          strokeDasharray="3,3"
          points={forecastPointsStr}
          strokeLinecap="round"
          strokeLinejoin="round"
        />
      )}

      {/* Last historical point dot */}
      <circle
        cx={getX(historicalCount - 1, totalCount)}
        cy={getY(data[data.length - 1])}
        r="2.5"
        fill="#232A2E"
      />

      {/* Forecast endpoint dot */}
      {forecastValue !== undefined && forecastValue !== null && (
        <circle
          cx={getX(totalCount - 1, totalCount)}
          cy={getY(forecastValue)}
          r="2.5"
          fill="#B9713A"
        />
      )}
    </svg>
  );
}
