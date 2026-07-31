'use client';

import React, { useEffect, useState, useCallback } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { ShieldAlert, Map, Database, History, Radio, Activity, RefreshCw } from 'lucide-react';
import { fetchEvidenceStats, refreshBulletins } from '@/lib/api';

const navItems = [
  { href: '/', label: 'Priority Queue', icon: ShieldAlert },
  { href: '/map', label: 'Regional Map', icon: Map },
  { href: '/evidence', label: 'Evidence Trail', icon: Database },
  { href: '/backtest', label: 'Backtest', icon: History },
  { href: '/aid-alerts', label: 'Send Aid', icon: Radio },
];

function formatRelativeTime(iso: string | null): string {
  if (!iso) return 'never';
  const then = new Date(iso).getTime();
  if (Number.isNaN(then)) return 'never';
  const diffMs = Date.now() - then;
  const mins = Math.floor(diffMs / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours}h ago`;
  const days = Math.floor(hours / 24);
  return `${days}d ago`;
}

export default function Sidebar() {
  const pathname = usePathname();
  const [lastUpdated, setLastUpdated] = useState<string | null>(null);
  const [countiesCovered, setCountiesCovered] = useState<number | null>(null);
  const [refreshing, setRefreshing] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const loadStats = useCallback(async () => {
    try {
      const stats = await fetchEvidenceStats();
      setLastUpdated(stats.last_updated);
      setCountiesCovered(stats.counties_covered);
    } catch {
      // Non-fatal — the sidebar just shows "never" rather than blocking nav
    }
  }, []);

  useEffect(() => {
    loadStats();
  }, [loadStats]);

  async function handleRefresh() {
    setRefreshing(true);
    setError(null);
    try {
      const result = await refreshBulletins();
      setLastUpdated(result.last_updated);
      setCountiesCovered(result.counties_covered);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Refresh failed');
    } finally {
      setRefreshing(false);
    }
  }

  const isStale = !lastUpdated;

  return (
    <aside className="sidebar">
      <Link href="/" className="sidebar-brand">
        <div className="brand-icon">
          <Activity className="w-5 h-5" />
        </div>
        <div>
          <div className="brand-title" style={{ fontSize: '1.05rem' }}>PULSECAST</div>
          <div className="brand-subtitle" style={{ display: 'inline-block', marginTop: 2 }}>NDMA early-alert</div>
        </div>
      </Link>

      <nav className="sidebar-nav">
        {navItems.map((item) => {
          const Icon = item.icon;
          const isActive = pathname === item.href || (item.href !== '/' && pathname.startsWith(item.href));
          return (
            <Link key={item.href} href={item.href} className={`sidebar-link ${isActive ? 'active' : ''}`}>
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </Link>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        <div className={`data-update-card ${isStale ? 'is-stale' : ''}`}>
          <div className="flex items-center gap-2 font-mono font-semibold" style={{ color: isStale ? 'var(--ink-muted)' : '#265E36' }}>
            <span className="live-pulse" style={{ background: isStale ? 'var(--ink-light)' : 'var(--phase-normal)' }} />
            Data Update
          </div>
          <div className="mt-1.5 text-[var(--ink-muted)]">
            Last updated: <span className="mono-val">{formatRelativeTime(lastUpdated)}</span>
          </div>
          {countiesCovered !== null && (
            <div className="text-[var(--ink-muted)]">
              <span className="mono-val">{countiesCovered}</span> counties with NDMA data
            </div>
          )}
          {error && <div className="mt-1 text-[var(--phase-emergency)]">{error}</div>}
          <button className="refresh-btn" onClick={handleRefresh} disabled={refreshing}>
            <RefreshCw className={`w-3.5 h-3.5 ${refreshing ? 'refresh-spin' : ''}`} />
            {refreshing ? 'Pulling from NDMA…' : 'Refresh data'}
          </button>
        </div>
      </div>
    </aside>
  );
}
