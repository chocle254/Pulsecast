'use client';

import React, { useEffect, useState, useMemo } from 'react';
import Link from 'next/link';
import { Filter, ArrowUpDown, Clock, ArrowRight, Search, ShieldAlert, Flame, TriangleAlert, TimerReset } from 'lucide-react';
import PhaseBadge from '@/components/PhaseBadge';
import PatternBadge from '@/components/PatternBadge';
import Sparkline from '@/components/Sparkline';
import KenyaMap from '@/components/KenyaMap';
import CountUp from '@/components/CountUp';
import { formatInlineText } from '@/components/FormattedText';
import { fetchPriorityQueue, fetchRegions, fetchLivelihoodZones, fetchMapData, PriorityItem, MapCountyData } from '@/lib/api';

const PHASE_BORDER_COLORS: Record<string, string> = {
  Normal: 'var(--phase-normal)',
  'Pre-Alert': 'var(--phase-pre-alert)',
  Alert: 'var(--phase-alert)',
  Alarm: 'var(--phase-alarm)',
  Emergency: 'var(--phase-emergency)',
  Recovery: 'var(--phase-recovery)',
};

function glowClassFor(phase: string): string {
  return `glow-${(phase || 'normal').toLowerCase().replace(' ', '-')}`;
}

export default function PriorityQueuePage() {
  const [items, setItems] = useState<PriorityItem[]>([]);
  const [mapData, setMapData] = useState<MapCountyData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters & Sorting
  const [searchQuery, setSearchQuery] = useState('');
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
        const [rList, lList, mData] = await Promise.all([fetchRegions(), fetchLivelihoodZones(), fetchMapData()]);
        setRegions(rList);
        setLivelihoods(lList);
        setMapData(mData);
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

  const visibleItems = useMemo(() => {
    if (!searchQuery.trim()) return items;
    const q = searchQuery.trim().toLowerCase();
    return items.filter((i) => i.county_name.toLowerCase().includes(q));
  }, [items, searchQuery]);

  const alertCount = items.filter((i) => i.current_phase === 'Alert' || i.current_phase === 'Pre-Alert').length;
  const alarmCount = items.filter((i) => i.current_phase === 'Alarm' || i.current_phase === 'Emergency').length;
  const imminentCrossingCount = items.filter((i) => i.days_to_crossing && i.days_to_crossing <= 21).length;

  const kpis = [
    { label: 'Counties Tracked', value: items.length, icon: ShieldAlert, color: 'var(--ink)', bg: 'var(--bg-elevated)' },
    { label: 'Alert / Pre-Alert', value: alertCount, icon: TriangleAlert, color: 'var(--phase-alert)', bg: 'var(--phase-alert-bg)' },
    { label: 'Alarm / Emergency', value: alarmCount, icon: Flame, color: 'var(--phase-emergency)', bg: 'var(--phase-emergency-bg)' },
    { label: '< 3wk to Crossing', value: imminentCrossingCount, icon: TimerReset, color: 'var(--phase-alarm)', bg: 'var(--phase-alarm-bg)' },
  ];

  return (
    <div className="container pt-6 space-y-6">
      {/* Header */}
      <div>
        <div className="text-xs font-mono text-[var(--ink-muted)] uppercase tracking-wider mb-1">
          National Early Alert Queue
        </div>
        <h1 className="text-2xl font-bold tracking-tight text-[var(--ink)]">
          Priority Queue & Drought Phase Forecasts
        </h1>
        <p className="text-sm text-[var(--ink-muted)] mt-0.5">
          Counties ranked by priority score (severity × time-to-crossing × model confidence).
        </p>
      </div>

      {/* KPI Strip */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-3">
        {kpis.map((kpi) => {
          const Icon = kpi.icon;
          return (
            <div key={kpi.label} className="card p-4 flex items-center gap-3.5">
              <div
                className="w-11 h-11 rounded-lg flex items-center justify-center shrink-0"
                style={{ background: kpi.bg, color: kpi.color }}
              >
                <Icon className="w-5 h-5" />
              </div>
              <div>
                <div className="text-2xl font-bold font-mono text-[var(--ink)] leading-none">
                  <CountUp value={kpi.value} />
                </div>
                <div className="text-xs text-[var(--ink-muted)] mt-1">{kpi.label}</div>
              </div>
            </div>
          );
        })}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-[1fr_320px] gap-6 items-start">
        {/* Main column: search, filters, list */}
        <div className="space-y-4 min-w-0">
          {/* Search */}
          <div className="relative">
            <Search className="w-4 h-4 absolute left-3.5 top-1/2 -translate-y-1/2 text-[var(--ink-light)]" />
            <input
              type="text"
              value={searchQuery}
              onChange={(e) => setSearchQuery(e.target.value)}
              placeholder="Search for a county…"
              className="w-full bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-md pl-10 pr-3.5 py-2.5 text-sm text-[var(--ink)] focus:outline-none focus:border-[var(--ink)] transition-colors"
            />
          </div>

          {/* Filter Bar */}
          <div className="bg-[var(--bg-card)] border border-[var(--border-medium)] rounded-md p-3.5 shadow-sm flex flex-wrap items-center justify-between gap-3 text-xs">
            <div className="flex flex-wrap items-center gap-3">
              <div className="flex items-center gap-1.5 font-semibold text-[var(--ink-muted)]">
                <Filter className="w-3.5 h-3.5" />
                <span>Filters:</span>
              </div>

              <select
                value={selectedPhase}
                onChange={(e) => setSelectedPhase(e.target.value)}
                className="bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded px-2.5 py-1.5 font-mono text-xs text-[var(--ink)] focus:outline-none focus:border-[var(--ink)]"
              >
                <option value="">All Phases</option>
                <option value="Normal">Normal</option>
                <option value="Pre-Alert">Pre-Alert</option>
                <option value="Alert">Alert</option>
                <option value="Alarm">Alarm</option>
                <option value="Emergency">Emergency</option>
                <option value="Recovery">Recovery</option>
              </select>

              <select
                value={selectedRegion}
                onChange={(e) => setSelectedRegion(e.target.value)}
                className="bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded px-2.5 py-1.5 font-mono text-xs text-[var(--ink)] focus:outline-none focus:border-[var(--ink)]"
              >
                <option value="">All Regions</option>
                {regions.map((r) => (
                  <option key={r} value={r}>{r}</option>
                ))}
              </select>

              <select
                value={selectedLivelihood}
                onChange={(e) => setSelectedLivelihood(e.target.value)}
                className="bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded px-2.5 py-1.5 font-mono text-xs text-[var(--ink)] focus:outline-none focus:border-[var(--ink)]"
              >
                <option value="">All Livelihoods</option>
                {livelihoods.map((l) => (
                  <option key={l} value={l}>{l}</option>
                ))}
              </select>
            </div>

            <div className="flex items-center gap-2 font-mono">
              <div className="flex items-center gap-1 text-[var(--ink-muted)]">
                <ArrowUpDown className="w-3.5 h-3.5" />
                <span>Sort:</span>
              </div>
              <select
                value={sortBy}
                onChange={(e) => setSortBy(e.target.value)}
                className="bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded px-2.5 py-1.5 text-xs text-[var(--ink)] focus:outline-none"
              >
                <option value="priority_score">Priority Score</option>
                <option value="days_to_crossing">Days to Crossing</option>
                <option value="current_vci3m">Current VCI3M</option>
                <option value="county_name">County Name</option>
              </select>
              <button
                onClick={() => setSortOrder(sortOrder === 'desc' ? 'asc' : 'desc')}
                className="px-2 py-1.5 bg-[var(--bg-surface)] border border-[var(--border-medium)] rounded hover:bg-[var(--bg-elevated)] font-bold"
              >
                {sortOrder.toUpperCase()}
              </button>
            </div>
          </div>

          {/* List */}
          {loading ? (
            <div className="space-y-3">
              {[...Array(6)].map((_, i) => (
                <div key={i} className="card p-4 flex items-center gap-4">
                  <div className="skeleton w-9 h-9 rounded shrink-0" />
                  <div className="flex-1 space-y-2">
                    <div className="skeleton h-4 w-40 rounded" />
                    <div className="skeleton h-3 w-56 rounded" />
                  </div>
                  <div className="skeleton h-8 w-28 rounded shrink-0" />
                  <div className="skeleton h-8 w-20 rounded shrink-0" />
                </div>
              ))}
            </div>
          ) : error ? (
            <div className="card p-8 bg-red-50 border-red-200 text-red-800 font-mono text-sm">
              Error: {error}
            </div>
          ) : visibleItems.length === 0 ? (
            <div className="card p-12 text-center text-[var(--ink-muted)] font-mono">
              {searchQuery ? `No county matching "${searchQuery}".` : 'No counties match the selected filters.'}
            </div>
          ) : (
            <div className="space-y-3">
              {visibleItems.map((item, index) => {
                const isTopUrgent = index < 3 && item.priority_score > 30;
                const ambientClass =
                  item.current_phase === 'Emergency' ? 'ambient-glow-emergency' :
                  item.current_phase === 'Alarm' ? 'ambient-glow-alarm' : '';

                return (
                  <Link
                    href={`/county/${item.county_id}`}
                    key={item.county_id}
                    className={`county-card group ${glowClassFor(item.current_phase)} ${ambientClass} animate-row-enter block p-4 no-underline`}
                    style={{
                      animationDelay: `${index * 40}ms`,
                      borderLeft: `4px solid ${PHASE_BORDER_COLORS[item.current_phase] || 'var(--phase-normal)'}`,
                    }}
                  >
                    <div className="flex flex-col lg:flex-row items-start lg:items-center justify-between gap-4">
                      {/* Left: Rank, County Name, Metadata, Phase */}
                      <div className="flex items-start gap-4 min-w-[280px]">
                        <div className="flex items-center justify-center w-9 h-9 rounded bg-[var(--bg-elevated)] border border-[var(--border-medium)] font-mono font-bold text-sm text-[var(--ink)] shrink-0">
                          #{item.rank}
                        </div>

                        <div>
                          <div className="flex items-center gap-2.5 flex-wrap">
                            <span className="text-lg font-bold text-[var(--ink)] flex items-center gap-1.5">
                              {item.county_name}
                              <ArrowRight className="w-4 h-4 opacity-0 group-hover:opacity-100 transition-opacity" />
                            </span>
                            <PhaseBadge phase={item.current_phase} size="sm" />
                            <PatternBadge signals={item.pattern_signals} size="sm" />
                            {isTopUrgent && (
                              <span className="live-pulse" title="Top urgency" />
                            )}
                          </div>

                          <div className="flex items-center gap-2 text-xs font-mono text-[var(--ink-muted)] mt-1">
                            <span>{item.region}</span>
                            <span>•</span>
                            <span className="capitalize">{item.livelihood_zone}</span>
                          </div>
                        </div>
                      </div>

                      {/* Middle: Threshold Sparkline */}
                      <div className="flex items-center gap-3 px-3 py-1 bg-[var(--bg-surface)] border border-[var(--border-subtle)] rounded">
                        <div className="text-[11px] font-mono text-[var(--ink-muted)]">
                          <div>VCI3M: <span className="font-bold text-[var(--ink)]">{item.current_vci3m ?? 'N/A'}</span></div>
                          {item.forecast_vci3m && (
                            <div>Proj: <span className="font-bold" style={{ color: 'var(--phase-alarm)' }}>{item.forecast_vci3m}</span></div>
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
                        <div className="text-right">
                          {item.days_to_crossing && item.crossing_date ? (
                            <div className="space-y-0.5">
                              <div
                                className="inline-flex items-center gap-1 text-xs font-mono font-bold px-2 py-0.5 rounded border"
                                style={{ color: 'var(--phase-emergency)', background: 'var(--phase-emergency-bg)', borderColor: 'var(--phase-emergency-border)' }}
                              >
                                <Clock className="w-3 h-3" />
                                <span>{item.days_to_crossing}d to {item.crossing_phase}</span>
                              </div>
                              <div className="text-[11px] font-mono text-[var(--ink-muted)]">
                                Est. {item.crossing_date} ({item.confidence ? `${Math.round(item.confidence * 100)}% conf` : ''})
                              </div>
                            </div>
                          ) : (
                            <div
                              className="inline-flex items-center gap-1 text-xs font-mono font-semibold px-2 py-0.5 rounded border"
                              style={{ color: '#166534', background: 'var(--phase-normal-bg)', borderColor: 'var(--phase-normal-border)' }}
                            >
                              No crossing projected
                            </div>
                          )}
                        </div>

                        <div className="text-right min-w-[75px]">
                          <div className="text-xs font-mono text-[var(--ink-muted)] uppercase">Score</div>
                          <div className="text-xl font-bold font-mono text-[var(--ink)]">
                            {item.priority_score.toFixed(1)}
                          </div>
                        </div>

                        <span className="px-3 py-1.5 bg-[var(--bg-elevated)] transition-all text-xs font-mono font-semibold rounded border border-[var(--border-medium)] flex items-center gap-1 shrink-0">
                          Detail →
                        </span>
                      </div>
                    </div>

                    {item.pattern_signals && item.pattern_signals.signals.length > 0 && (
                      <div className="mt-3 pt-2.5 border-t border-[var(--border-subtle)] text-xs text-[var(--ink-muted)] font-sans flex items-start gap-2">
                        <span
                          className="font-mono text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase shrink-0 mt-0.5"
                          style={{ color: 'var(--accent)', background: 'var(--accent-bg)' }}
                        >
                          Pattern
                        </span>
                        <p className="line-clamp-2 leading-relaxed">
                          {item.pattern_signals.signals.map((s) => s.note).join(' ')}
                        </p>
                      </div>
                    )}

                    {item.ai_summary && (
                      <div className="mt-3 pt-2.5 border-t border-[var(--border-subtle)] text-xs text-[var(--ink-muted)] font-sans flex items-start gap-2">
                        <span
                          className="font-mono text-[10px] px-1.5 py-0.5 rounded font-semibold uppercase shrink-0 mt-0.5"
                          style={{ color: '#166534', background: 'var(--phase-normal-bg)' }}
                        >
                          AI Note
                        </span>
                        <p className="line-clamp-2 leading-relaxed">
                          {formatInlineText(item.ai_summary)}
                        </p>
                      </div>
                    )}
                  </Link>
                );
              })}
            </div>
          )}
        </div>

        {/* Right rail: mini regional map preview */}
        <Link href="/map" className="block sticky top-6">
          <div className="card p-4 hover:shadow-[var(--shadow-float)] transition-shadow">
            <div className="flex items-center justify-between mb-3">
              <h3 className="text-sm font-bold text-[var(--ink)]">Regional Map</h3>
              <span className="text-xs font-mono text-[var(--ink-muted)] flex items-center gap-1">
                View full <ArrowRight className="w-3 h-3" />
              </span>
            </div>
            <KenyaMap counties={mapData} compact />
            <p className="text-[11px] text-[var(--ink-light)] font-mono mt-3">
              Click to explore county-by-county phase distribution
            </p>
          </div>
        </Link>
      </div>
    </div>
  );
}
