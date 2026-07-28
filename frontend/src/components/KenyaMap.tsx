'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import PhaseBadge from './PhaseBadge';
import { MapCountyData } from '@/lib/api';

interface KenyaMapProps {
  counties: MapCountyData[];
  onSelectCounty?: (countyId: number) => void;
}

// Kenya County centroid positions & path approximations for interactive GIS map display
const KENYA_COUNTY_POSITIONS: Record<string, { x: number; y: number; code: string }> = {
  Turkana: { x: 200, y: 100, code: 'TUR' },
  Marsabit: { x: 380, y: 120, code: 'MAR' },
  Mandera: { x: 560, y: 90, code: 'MAN' },
  Wajir: { x: 520, y: 180, code: 'WAJ' },
  Garissa: { x: 490, y: 290, code: 'GAR' },
  Isiolo: { x: 380, y: 220, code: 'ISI' },
  Samburu: { x: 300, y: 200, code: 'SAM' },
  'West Pokot': { x: 190, y: 200, code: 'WPO' },
  Baringo: { x: 230, y: 260, code: 'BAR' },
  Laikipia: { x: 300, y: 280, code: 'LAI' },
  Meru: { x: 370, y: 280, code: 'MER' },
  'Tharaka Nithi': { x: 385, y: 315, code: 'THA' },
  Embu: { x: 360, y: 335, code: 'EMB' },
  Kitui: { x: 420, y: 360, code: 'KIT' },
  Machakos: { x: 350, y: 380, code: 'MAC' },
  Makueni: { x: 370, y: 420, code: 'MAK' },
  Kajiado: { x: 300, y: 440, code: 'KAJ' },
  Narok: { x: 210, y: 410, code: 'NAR' },
  Nakuru: { x: 240, y: 320, code: 'NAK' },
  'Elgeyo Marakwet': { x: 220, y: 230, code: 'EMAR' },
  Nandi: { x: 185, y: 285, code: 'NAN' },
  'Uasin Gishu': { x: 190, y: 255, code: 'UG' },
  'Trans Nzoia': { x: 170, y: 210, code: 'TNZ' },
  Bungoma: { x: 130, y: 230, code: 'BUN' },
  Busia: { x: 110, y: 260, code: 'BUS' },
  Kakamega: { x: 140, y: 270, code: 'KAK' },
  Vihiga: { x: 140, y: 295, code: 'VIH' },
  Siaya: { x: 100, y: 310, code: 'SIA' },
  Kisumu: { x: 135, y: 325, code: 'KIS' },
  'Homa Bay': { x: 110, y: 360, code: 'HB' },
  Migori: { x: 120, y: 395, code: 'MIG' },
  Kisii: { x: 155, y: 375, code: 'KSI' },
  Nyamira: { x: 165, y: 350, code: 'NYA' },
  Kericho: { x: 190, y: 335, code: 'KER' },
  Bomet: { x: 185, y: 370, code: 'BOM' },
  Nyandarua: { x: 280, y: 320, code: 'NYD' },
  Nyeri: { x: 315, y: 315, code: 'NYE' },
  Kirinyaga: { x: 335, y: 330, code: 'KIR' },
  "Murang'a": { x: 315, y: 345, code: 'MUR' },
  Kiambu: { x: 300, y: 365, code: 'KIA' },
  Nairobi: { x: 315, y: 385, code: 'NBO' },
  'Tana River': { x: 470, y: 380, code: 'TAN' },
  Lamu: { x: 550, y: 410, code: 'LAM' },
  Kilifi: { x: 490, y: 470, code: 'KIL' },
  Kwale: { x: 450, y: 530, code: 'KWA' },
  Mombasa: { x: 495, y: 515, code: 'MSA' },
  'Taita Taveta': { x: 400, y: 480, code: 'TTA' },
};

const PHASE_COLORS: Record<string, string> = {
  Normal: '#7A9B76',
  Alert: '#C9A24B',
  Alarm: '#B9713A',
  Emergency: '#9B3B34',
  Recovery: '#4A8B8C',
};

export default function KenyaMap({ counties, onSelectCounty }: KenyaMapProps) {
  const [hoveredCounty, setHoveredCounty] = useState<MapCountyData | null>(null);

  const countyDataMap = new Map<string, MapCountyData>();
  counties.forEach((c) => countyDataMap.set(c.county_name, c));

  return (
    <div className="card relative p-4 bg-white">
      <div className="flex items-center justify-between mb-3 pb-2 border-b border-gray-200">
        <div>
          <h3 className="text-base font-bold">Regional Drought Map</h3>
          <p className="text-xs text-gray-500 font-mono">
            Spatial distribution across Kenya's 47 counties
          </p>
        </div>

        {/* Legend */}
        <div className="flex items-center gap-3 text-xs">
          {Object.entries(PHASE_COLORS).map(([phase, color]) => (
            <div key={phase} className="flex items-center gap-1.5 font-mono">
              <span className="w-3 h-3 rounded-xs inline-block" style={{ backgroundColor: color }} />
              <span className="text-gray-700">{phase}</span>
            </div>
          ))}
        </div>
      </div>

      {/* SVG Map Layout */}
      <div className="relative w-full overflow-hidden flex justify-center items-center min-h-[560px] bg-[#EDEEE8]/40 rounded-md border border-gray-200">
        <svg viewBox="0 0 700 600" className="w-full max-w-[720px] h-auto">
          {/* Background grid */}
          <pattern id="grid" width="30" height="30" patternUnits="userSpaceOnUse">
            <path d="M 30 0 L 0 0 0 30" fill="none" stroke="#DDE0D8" strokeWidth="0.5" />
          </pattern>
          <rect width="700" height="600" fill="url(#grid)" opacity="0.6" />

          {/* Render County Nodes / Regions */}
          {Object.entries(KENYA_COUNTY_POSITIONS).map(([name, pos]) => {
            const data = countyDataMap.get(name);
            const phase = data?.current_phase || 'Normal';
            const color = PHASE_COLORS[phase] || '#7A9B76';
            const isHovered = hoveredCounty?.county_name === name;

            return (
              <g
                key={name}
                transform={`translate(${pos.x}, ${pos.y})`}
                className="cursor-pointer transition-transform duration-150 hover:scale-110"
                onMouseEnter={() => setHoveredCounty(data || { county_id: 0, county_name: name, current_phase: 'Normal', forecast_phase: null, days_to_crossing: null, priority_score: 0, vci3m: null })}
                onMouseLeave={() => setHoveredCounty(null)}
                onClick={() => data && onSelectCounty && onSelectCounty(data.county_id)}
              >
                {/* Node Box */}
                <rect
                  x="-22"
                  y="-16"
                  width="44"
                  height="32"
                  rx="4"
                  fill={color}
                  stroke={isHovered ? '#232A2E' : '#FFFFFF'}
                  strokeWidth={isHovered ? 2.5 : 1.5}
                  className="shadow-sm transition-all"
                  opacity={isHovered ? 1 : 0.9}
                />

                {/* County Code */}
                <text
                  x="0"
                  y="4"
                  fill="#FFFFFF"
                  fontSize="10px"
                  fontWeight="700"
                  fontFamily="var(--font-mono)"
                  textAnchor="middle"
                  className="pointer-events-none drop-shadow-xs"
                >
                  {pos.code}
                </text>
              </g>
            );
          })}
        </svg>

        {/* Hover Tooltip Overlay */}
        {hoveredCounty && (
          <div className="absolute top-4 right-4 bg-white/95 backdrop-blur-xs p-3 rounded-md shadow-lg border border-gray-300 w-56 pointer-events-none z-10 transition-opacity duration-150">
            <div className="flex items-center justify-between mb-1.5">
              <span className="font-bold text-sm text-gray-900">{hoveredCounty.county_name}</span>
              <PhaseBadge phase={hoveredCounty.current_phase} size="sm" />
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
    </div>
  );
}
