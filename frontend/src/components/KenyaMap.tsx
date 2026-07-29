'use client';

import React, { useMemo, useState } from 'react';
import PhaseBadge from './PhaseBadge';
import { MapCountyData } from '@/lib/api';
import { KENYA_COUNTY_PATHS, KENYA_MAP_VIEWBOX } from '@/lib/kenyaCountyPaths';

interface KenyaMapProps {
  counties: MapCountyData[];
  onSelectCounty?: (countyId: number) => void;
  /** Smaller embedded rendering for the homepage dashboard — shorter map,
   *  no repeated phase-count strip (the legend above already covers it). */
  compact?: boolean;
}

// Phases in legend order, mapped to the app's shared --phase-* CSS custom
// properties (see src/styles/globals.css) so the map always matches the
// colors used everywhere else (badges, cards, etc).
const PHASES = ['Normal', 'Alert', 'Alarm', 'Emergency', 'Recovery'] as const;
const NO_DATA_COLOR = '#C8CCC0';

function phaseColorVar(phase: string): string {
  return `var(--phase-${phase.toLowerCase()})`;
}

export default function KenyaMap({ counties, onSelectCounty, compact = false }: KenyaMapProps) {
  const [hoveredCounty, setHoveredCounty] = useState<MapCountyData | null>(null);

  const countyDataMap = useMemo(() => {
    const map = new Map<string, MapCountyData>();
    counties.forEach((c) => map.set(c.county_name, c));
    return map;
  }, [counties]);

  const phaseCounts = useMemo(() => {
    const counts: Record<string, number> = { Normal: 0, Alert: 0, Alarm: 0, Emergency: 0, Recovery: 0 };
    counties.forEach((c) => {
      if (c.current_phase && counts[c.current_phase] !== undefined) {
        counts[c.current_phase] += 1;
      }
    });
    return counts;
  }, [counties]);

  return (
    <div className="card relative p-4 bg-white">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200">
        <div>
          <h3 className="text-base font-bold">Regional Drought Map</h3>
          <p className="text-xs text-gray-500 font-mono">
            Spatial distribution across Kenya&apos;s 23 ASAL counties
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          {PHASES.map((phase) => (
            <div key={phase} className="flex items-center gap-1.5 font-mono">
              <span
                className="w-3 h-3 rounded-xs inline-block"
                style={{ backgroundColor: phaseColorVar(phase) }}
              />
              <span className="text-gray-700">{phase}</span>
            </div>
          ))}
          <div className="flex items-center gap-1.5 font-mono">
            <span className="w-3 h-3 rounded-xs inline-block" style={{ backgroundColor: NO_DATA_COLOR }} />
            <span className="text-gray-500">No data</span>
          </div>
        </div>
      </div>

      {/* SVG Map: accurate Kenya county boundaries */}
      <div className={`relative w-full overflow-hidden flex justify-center items-center ${compact ? 'min-h-[320px]' : 'min-h-[560px]'} bg-[#EDEEE8]/40 rounded-md border border-gray-200`}>
        <svg viewBox={KENYA_MAP_VIEWBOX} className="w-full max-w-[560px] h-auto">
          {KENYA_COUNTY_PATHS.map(({ id, name, path }) => {
            const data = countyDataMap.get(name);
            const phase = data?.current_phase;
            const color = phase ? phaseColorVar(phase) : NO_DATA_COLOR;
            const isHovered = hoveredCounty?.county_name === name;

            return (
              <path
                key={id}
                d={path}
                fill={color}
                stroke={isHovered ? '#232A2E' : '#FFFFFF'}
                strokeWidth={isHovered ? 1.6 : 0.6}
                strokeLinejoin="round"
                className={data ? 'cursor-pointer transition-[filter] duration-150' : 'cursor-default'}
                style={isHovered ? { filter: 'brightness(0.92)' } : undefined}
                onMouseEnter={() => setHoveredCounty(data ?? null)}
                onMouseLeave={() => setHoveredCounty(null)}
                onClick={() => data && onSelectCounty && onSelectCounty(data.county_id)}
              >
                <title>{name}</title>
              </path>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredCounty && (
          <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-xs p-3 rounded-md shadow-lg border border-gray-300 w-56 pointer-events-none z-10 transition-opacity duration-150">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-sm text-gray-900">{hoveredCounty.county_name}</span>
              {hoveredCounty.current_phase && <PhaseBadge phase={hoveredCounty.current_phase} size="sm" />}
            </div>

            <div className="space-y-1 text-xs font-mono text-gray-600">
              <div className="flex justify-between">
                <span>Current VCI3M:</span>
                <span className="font-bold text-gray-900">{hoveredCounty.vci3m ?? 'N/A'}</span>
              </div>
              <div className="flex justify-between">
                <span>Priority Score:</span>
                <span className="font-bold text-gray-900">{hoveredCounty.priority_score ?? 'N/A'}</span>
              </div>
              {hoveredCounty.days_to_crossing && (
                <div className="flex justify-between text-red-700 font-semibold pt-1 border-t border-gray-100">
                  <span>Crossing in:</span>
                  <span>{hoveredCounty.days_to_crossing} days</span>
                </div>
              )}
            </div>

            <div className="mt-2 text-[10px] text-gray-400 font-mono text-right">
              Click to view full detail →
            </div>
          </div>
        )}
      </div>

      {/* Phase Summary strip */}
      {!compact && (
        <div className="mt-3 pt-3 border-t border-gray-200 flex flex-wrap items-center gap-x-5 gap-y-1.5 text-xs font-mono">
          <span className="text-gray-500">{counties.length} counties reporting</span>
          {PHASES.map((phase) => (
            <div key={phase} className="flex items-center gap-1.5">
              <span
                className="w-2.5 h-2.5 rounded-full inline-block"
                style={{ backgroundColor: phaseColorVar(phase) }}
              />
              <span className="text-gray-700">
                {phase} <span className="font-bold text-gray-900">{phaseCounts[phase]}</span>
              </span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
}

