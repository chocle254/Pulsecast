'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Map, ArrowRight, ShieldAlert, Users } from 'lucide-react';
import KenyaMap from '@/components/KenyaMap';
import PhaseBadge from '@/components/PhaseBadge';
import { formatInlineText } from '@/components/FormattedText';
import {
  fetchMapData, fetchCountyDetail, fetchRegionalSynthesis,
  MapCountyData, CountyDetail, RegionalSynthesis,
} from '@/lib/api';

export default function RegionalMapPage() {
  const [mapCounties, setMapCounties] = useState<MapCountyData[]>([]);
  const [selectedCounty, setSelectedCounty] = useState<CountyDetail | null>(null);
  const [loadingMap, setLoadingMap] = useState(true);
  const [loadingDetail, setLoadingDetail] = useState(false);
  const [synthesis, setSynthesis] = useState<RegionalSynthesis | null>(null);
  const [loadingSynthesis, setLoadingSynthesis] = useState(true);

  useEffect(() => {
    fetchRegionalSynthesis()
      .then(setSynthesis)
      .catch((err) => console.error('Failed to load regional synthesis', err))
      .finally(() => setLoadingSynthesis(false));
  }, []);

  useEffect(() => {
    async function loadMap() {
      setLoadingMap(true);
      try {
        const data = await fetchMapData();
        setMapCounties(data);
        // Default select top urgent county if available
        if (data.length > 0) {
          const sorted = [...data].sort((a, b) => (b.priority_score || 0) - (a.priority_score || 0));
          loadCountyDetail(sorted[0].county_id);
        }
      } catch (err) {
        console.error('Failed to load map data', err);
      } finally {
        setLoadingMap(false);
      }
    }
    loadMap();
  }, []);

  const loadCountyDetail = async (id: number) => {
    setLoadingDetail(true);
    try {
      const detail = await fetchCountyDetail(id);
      setSelectedCounty(detail);
    } catch (err) {
      console.error(`Failed to load detail for county ${id}`, err);
    } finally {
      setLoadingDetail(false);
    }
  };

  return (
    <div className="container pt-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-[#F6F6F2] border border-[#C8CCC0] rounded-lg p-5 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] uppercase tracking-wider mb-1">
            <Map className="w-3.5 h-3.5 text-[#232A2E]" />
            <span>Spatial Cluster Analysis</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#232A2E]">
            Regional Drought Phase Map
          </h1>
          <p className="text-sm text-[#5B6560] mt-0.5">
            Identify multi-county drought clusters drifting toward crisis simultaneously across Kenya.
          </p>
        </div>
      </div>

      {/* Main Map + Selected County Panel Split */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start">
        {/* Map View */}
        <div className="lg:col-span-8">
          {loadingMap ? (
            <div className="card p-16 text-center font-mono text-xs text-[#5B6560]">
              Loading Kenya regional GIS map...
            </div>
          ) : (
            <KenyaMap
              counties={mapCounties}
              onSelectCounty={(id) => loadCountyDetail(id)}
            />
          )}
        </div>

        {/* Right Side Detail Panel */}
        <div className="lg:col-span-4 card p-5 bg-white space-y-4 sticky top-20">
          {loadingDetail ? (
            <div className="p-8 text-center font-mono text-xs text-[#5B6560]">
              Loading county inspection...
            </div>
          ) : selectedCounty ? (
            <div className="space-y-4">
              <div className="pb-3 border-b border-[#EDEEE8] flex items-center justify-between">
                <div>
                  <h3 className="text-xl font-bold text-[#232A2E]">{selectedCounty.name}</h3>
                  <div className="text-xs font-mono text-[#5B6560]">
                    {selectedCounty.region} • {selectedCounty.livelihood_zone}
                  </div>
                </div>
                <PhaseBadge phase={selectedCounty.current_phase} size="md" />
              </div>

              {/* Stats */}
              <div className="grid grid-cols-2 gap-2 text-xs font-mono">
                <div className="bg-[#F8F9F5] p-2.5 rounded border border-[#DDE0D8]">
                  <div className="text-[#5B6560]">Current VCI3M</div>
                  <div className="text-lg font-bold text-[#232A2E]">
                    {selectedCounty.current_vci3m ?? 'N/A'}
                  </div>
                </div>
                <div className="bg-[#F8F9F5] p-2.5 rounded border border-[#DDE0D8]">
                  <div className="text-[#5B6560]">Priority Score</div>
                  <div className="text-lg font-bold text-[#B9713A]">
                    {selectedCounty.forecast?.priority_score?.toFixed(1) ?? 'N/A'}
                  </div>
                </div>
              </div>

              {/* Threshold Crossing Info */}
              {selectedCounty.forecast?.crossing_date && (
                <div className="bg-[#FAECEB] p-3 rounded border border-[#C46760] text-xs font-mono text-[#6D221D]">
                  <div className="font-bold">Crossing Alert:</div>
                  <div>
                    Projected {selectedCounty.forecast.crossing_phase} in{' '}
                    <span className="font-bold">{selectedCounty.forecast.days_to_crossing} days</span> ({selectedCounty.forecast.crossing_date}).
                  </div>
                </div>
              )}

              {/* AI Summary */}
              {selectedCounty.ai_explanation && (
                <div className="text-xs text-[#5B6560] leading-relaxed line-clamp-4 font-sans bg-[#F6F6F2] p-3 rounded border border-[#C8CCC0]">
                  <span className="font-mono font-bold text-[10px] text-[#3B5A37] uppercase block mb-1">
                    AI Forecast Note:
                  </span>
                  {formatInlineText(selectedCounty.ai_explanation)}
                </div>
              )}

              <Link
                href={`/county/${selectedCounty.id}`}
                className="w-full py-2 bg-[#232A2E] text-white hover:bg-[#3B5A37] transition-colors rounded text-xs font-mono font-semibold flex items-center justify-center gap-1.5"
              >
                Inspect Full County Forecast <ArrowRight className="w-3.5 h-3.5" />
              </Link>
            </div>
          ) : (
            <div className="p-8 text-center font-mono text-xs text-[#5B6560]">
              Click any county on the map to inspect its forecast trajectory.
            </div>
          )}
        </div>
      </div>

      {/* Regional Cluster Analysis — deterministically computed by
          app/services/patterns.py::detect_regional_clusters, narrated by
          the LLM (see llm.py::generate_regional_synthesis). The LLM writes
          up these clusters; it does not detect them. */}
      <div className="card p-5 bg-white">
        <div className="flex items-center gap-2 pb-3 border-b border-[#EDEEE8] mb-3">
          <Users className="w-4 h-4" style={{ color: 'var(--accent)' }} />
          <h2 className="text-base font-bold text-[#232A2E]">Regional Cluster Analysis</h2>
        </div>

        {loadingSynthesis ? (
          <div className="text-xs font-mono text-[#5B6560] py-4 text-center">
            Analyzing cross-county clusters...
          </div>
        ) : !synthesis || synthesis.computed_clusters.length === 0 ? (
          <div className="text-xs font-mono text-[#5B6560] py-2">
            No regional cluster currently meets the detection threshold (≥3 counties, ≥50% of a
            tracked region simultaneously at Alert phase or worse).
          </div>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {synthesis.computed_clusters.map((cluster) => (
                <div
                  key={cluster.region}
                  className="p-3 rounded border text-xs font-mono"
                  style={{ background: 'var(--accent-bg)', borderColor: 'var(--accent-border)' }}
                >
                  <div className="flex items-center justify-between mb-1">
                    <span className="font-bold text-[#232A2E]">{cluster.region}</span>
                    <span style={{ color: 'var(--accent)' }} className="font-bold">
                      {cluster.at_risk_count}/{cluster.region_size} at risk
                    </span>
                  </div>
                  <div className="text-[#5B6560]">{cluster.counties.join(', ')}</div>
                </div>
              ))}
            </div>

            <div className="text-sm text-[#232A2E] leading-relaxed font-sans pt-1">
              {formatInlineText(synthesis.synthesis)}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
