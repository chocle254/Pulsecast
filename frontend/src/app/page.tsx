'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Filter, ArrowUpDown, AlertTriangle, Clock, ArrowRight, Activity, ShieldAlert } from 'lucide-react';
import PhaseBadge from '@/components/PhaseBadge';
import Sparkline from '@/components/Sparkline';
import { fetchPriorityQueue, fetchRegions, fetchLivelihoodZones, PriorityItem } from '@/lib/api';

export default function PriorityQueuePage() {
  const [items, setItems] = useState<PriorityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Sorting
  const [selectedPhase, setSelectedPhase] = useState<string>('');
  const [selectedRegion, setSelectedRegion] = useState<string>('');
  const [selectedLivelihood, setSelectedLivelihood] = useState<string>('');
  const [sortBy, setSortBy] = useState<string>('priority_score');
  const [sortOrder, setSortOrder] = useState<string>('desc');

  // Filter options
  const [regions, setRegions] = useState<string[]>([]);
  const [livelihoods, setLivelihoods] = useState<string[]>([]);

  useEffect(() => {
    async function loadOptions() {
      try {
        const [rList, lList] = await Promise.all([fetchRegions(), fetchLivelihoodZones()]);
        setRegions(rList);
        setLivelihoods(lList);
      } catch (err) {
        console.error('Error loading filter options:', err);
      }
    }
    loadOptions();
  }, []);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchPriorityQueue({
          phase: selectedPhase || undefined,
          region: selectedRegion || undefined,
          livelihood_zone: selectedLivelihood || undefined,
          sort_by: sortBy,
          sort_order: sortOrder,
        });
        setItems(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load priority queue');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [selectedPhase, selectedRegion, selectedLivelihood, sortBy, sortOrder]);

  const alertCount = items.filter((i) => i.current_phase === 'Alert').length;
  const alarmCount = items.filter((i) => i.current_phase === 'Alarm' || i.current_phase === 'Emergency').length;
  const imminentCrossingCount = items.filter((i) => i.days_to_crossing && i.days_to_crossing <= 21).length;

  return (
    <div className="container pt-6 space-y-6">
      {/* Top Banner / Summary Stats */}
      <div className="bg-[#F6F6F2] border border-[#C8CCC0] rounded-lg p-5 shadow-sm flex flex-col md:flex-row gap-6 items-start md:items-center justify-between">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] uppercase tracking-wider mb-1">
            <Activity className="w-3.5 h-3.5 text-[#B9713A]" />
            <span>National Early Alert Queue</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#232A2E]">
            Priority Queue & Drought Phase Forecasts
          </h1>
          <p className="text-sm text-[#5B6560] mt-0.5">
            Counties ranked by priority score (severity × time-to-crossing × model confidence).
          </p>
        </div>

        <div className="flex items-center gap-4 bg-white px-4 py-3 rounded-md border border-[#DDE0D8] font-mono text-xs">
          <div className="text-center px-2">
            <div className="text-lg font-bold text-[#232A2E]">{items.length}</div>
            <div className="text-[11px] text-[#5B6560]">Counties</div>
          </div>
          <div className="h-8 w-px bg-[#DDE0D8]" />
          <div className="text-center px-2">
            <div className="text-lg font-bold text-[#C9A24B]">{alertCount}</div>
            <div className="text-[11px] text-[#5B6560]">Alert</div>
          </div>
          <div className="h-8 w-px bg-[#DDE0D8]" />
          <div className="text-center px-2">
            <div className="text-lg font-bold text-[#B9713A]">{alarmCount}</div>
            <div className="text-[11px] text-[#5B6560]">Alarm/Emerg</div>
          </div>
          <div className="h-8 w-px bg-[#DDE0D8]" />
          <div className="text-center px-2">
            <div className="text-lg font-bold text-[#9B3B34]">{imminentCrossingCount}</div>
            <div className="text-[11px] text-[#5B6560]">&lt; 3w Crossing</div>
          </div>
        </div>
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-[#C8CCC0] rounded-md p-3.5 shadow-xs flex flex-wrap items-center justify-between gap-3 text-xs">
        <div className="flex flex-wrap items-center gap-3">
          <div className="flex items-center gap-1.5 font-semibold text-[#5B6560]">
            <Filter className="w-3.5 h-3.5" />
            <span>Filters:</span>
          </div>

          {/* Phase Filter */}
          <select
            value={selectedPhase}
            onChange={(e) => setSelectedPhase(e.target.value)}
            className="bg-[#F6F6F2] border border-[#C8CCC0] rounded px-2.5 py-1.5 font-mono text-xs text-[#232A2E] focus:outline-none focus:border-[#232A2E]"
          >
            <option value="">All Phases</option>
            <option value="Normal">Normal</option>
            <option value="Alert">Alert</option>
            <option value="Alarm">Alarm</option>
            <option value="Emergency">Emergency</option>
            <option value="Recovery">Recovery</option>
          </select>

          {/* Region Filter */}
          <select
            value={selectedRegion}
            onChange={(e) => setSelectedRegion(e.target.value)}
            className="bg-[#F6F6F2] border border-[#C8CCC0] rounded px-2.5 py-1.5 font-mono text-xs text-[#232A2E] focus:outline-none focus:border-[#232A2E]"
          >
            <option value="">All Regions</option>
            {regions.map((r) => (
              <option key={r} value={r}>
                {r}
              </option>
            ))}
          </select>

          {/* Livelihood Filter */}
          <select
            value={selectedLivelihood}
            onChange={(e) => setSelectedLivelihood(e.target.value)}
            className="bg-[#F6F6F2] border border-[#C8CCC0] rounded px-2.5 py-1.5 font-mono text-xs text-[#232A2E] focus:outline-none focus:border-[#232A2E]"
          >
            <option value="">All Livelihoods</option>
            {livelihoods.map((l) => (
              <option key={l} value={l}>
                {l}
              </option>
            ))}
          </select>
        </div>

        {/* Sorting Controls */}
        <div className="flex items-center gap-2 font-mono">
          <div className="flex items-center gap-1 text-[#5B6560]">
            <ArrowUpDown className="w-3.5 h-3.5" />
            <span>Sort:</span>
          </div>
          <select
            value={sortBy}
            onChange={(e) => setSortBy(e.target.value)}
            className="bg-[#F6F6F2] border border-[#C8CCC0] rounded px-2.5 py-1.5 text-xs text-[#232A2E] focus:outline-none"
          >
            <option value="priority_score">Priority Score</option>
            <option value="days_to_crossing">Days to Crossing</option>
            <option value="current_vci3m">Current VCI3M</option>
            <option value="county_name">County Name</option>
          </select>
          <button
            onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
            className="px-2 py-1.5 bg-[#F6F6F2] border border-[#C8CCC0] rounded hover:bg-[#EAF2E8] font-bold"
          >
            {sortOrder.toUpperCase()}
          </button>
        </div>
      </div>

      {/* Main Ranked Priority Queue List */}
      {loading ? (
        <div className="card p-12 text-center text-[#5B6560] font-mono">
          <Activity className="w-6 h-6 animate-spin mx-auto mb-2 text-[#232A2E]" />
          Computing forecasts & priority queue rankings...
        </div>
      ) : error ? (
        <div className="card p-8 bg-red-50 border-red-200 text-red-800 font-mono text-sm">
          Error: {error}
        </div>
      ) : items.length === 0 ? (
        <div className="card p-12 text-center text-[#5B6560] font-mono">
          No counties match the selected filters.
        </div>
      ) : (
        <div className="space-y-3">
          {items.map((item, index) => {
            const isTopUrgent = index < 3 && item.priority_score > 30;

            return (
              <div
                key={item.county_id}
                className={`card hover:shadow-md transition-all duration-200 p-4 bg-white border border-[#C8CCC0] ${
                  isTopUrgent ? 'top-urgency-row' : ''
                }`}
              >
                <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                  {/* Left: Rank, County Name, Metadata, Phase */}
                  <div className="flex items-start gap-4 min-w-[280px]">
                    <div className="flex items-center justify-center w-9 h-9 rounded bg-[#EDEEE8] border border-[#C8CCC0] font-mono font-bold text-sm text-[#232A2E]">
                      #{item.rank}
                    </div>

                    <div>
                      <div className="flex items-center gap-2.5">
                        <Link
                          href={`/county/${item.county_id}`}
                          className="text-lg font-bold text-[#232A2E] hover:text-[#B9713A] transition-colors flex items-center gap-1.5"
                        >
                          {item.county_name}
                          <ArrowRight className="w-4 h-4 opacity-0 hover:opacity-100 transition-opacity" />
                        </Link>
                        <PhaseBadge phase={item.current_phase} size="sm" />
                      </div>

                      <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] mt-1">
                        <span>{item.region}</span>
                        <span>•</span>
                        <span className="capitalize">{item.livelihood_zone}</span>
                      </div>
                    </div>
                  </div>

                  {/* Middle: Threshold Sparkline */}
                  <div className="flex items-center gap-3 px-3 py-1 bg-[#F8F9F5] border border-[#DDE0D8] rounded">
                    <div className="text-[11px] font-mono text-[#5B6560]">
                      <div>VCI3M: <span className="font-bold text-[#232A2E]">{item.current_vci3m ?? 'N/A'}</span></div>
                      {item.forecast_vci3m && (
                        <div>Proj: <span className="font-bold text-[#B9713A]">{item.forecast_vci3m}</span></div>
                      )}
                    </div>
                    <Sparkline
                      data={item.sparkline_data}
                      forecastValue={item.forecast_vci3m}
                      width={110}
                      height={34}
                    />
                  </div>

                  {/* Right: Threshold Crossing Callout & Priority Score */}
                  <div className="flex items-center gap-6 justify-between w-full lg:w-auto">
                    {/* Days to Crossing Callout */}
                    <div className="text-right">
                      {item.days_to_crossing && item.crossing_date ? (
                        <div className="space-y-0.5">
                          <div className="inline-flex items-center gap-1 text-xs font-mono font-bold text-[#9B3B34] bg-[#FAECEB] px-2 py-0.5 rounded border border-[#C46760]">
                            <Clock className="w-3 h-3" />
                            <span>{item.days_to_crossing}d to {item.crossing_phase}</span>
                          </div>
                          <div className="text-[11px] font-mono text-[#5B6560]">
                            Est. {item.crossing_date} ({item.confidence ? `${Math.round(item.confidence * 100)}% conf` : ''})
                          </div>
                        </div>
                      ) : (
                        <div className="text-xs font-mono text-[#5B6560]">
                          No crossing projected
                        </div>
                      )}
                    </div>

                    {/* Priority Score */}
                    <div className="text-right min-w-[75px]">
                      <div className="text-xs font-mono text-[#5B6560] uppercase">Score</div>
                      <div className="text-xl font-bold font-mono text-[#232A2E]">
                        {item.priority_score.toFixed(1)}
                      </div>
                    </div>

                    {/* View Details Link */}
                    <Link
                      href={`/county/${item.county_id}`}
                      className="px-3 py-1.5 bg-[#EDEEE8] hover:bg-[#232A2E] hover:text-white transition-all text-xs font-mono font-semibold rounded border border-[#C8CCC0] flex items-center gap-1"
                    >
                      Detail →
                    </Link>
                  </div>
                </div>

                {/* AI Summary Banner below row */}
                {item.ai_summary && (
                  <div className="mt-3 pt-2.5 border-t border-[#EDEEE8] text-xs text-[#5B6560] font-sans flex items-start gap-2">
                    <span className="font-mono text-[10px] bg-[#EAF2E8] text-[#3B5A37] px-1.5 py-0.5 rounded font-semibold uppercase shrink-0 mt-0.5">
                      AI Note
                    </span>
                    <p className="line-clamp-2 leading-relaxed">
                      {item.ai_summary.replace(/\[ref:[^\]]+\]/g, (match) => {
                        const parts = match.slice(5, -1).split('=');
                        return parts[1] || match;
                      })}
                    </p>
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
