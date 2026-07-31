'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Radio, PawPrint, Loader2 } from 'lucide-react';
import PhaseBadge from '@/components/PhaseBadge';
import { fetchPriorityQueue, PriorityItem } from '@/lib/api';
import { AID_ALERT_ELIGIBLE_PHASES } from '@/components/AidAlertPanel';

function isPastoralistZone(zone: string | null | undefined): boolean {
  if (!zone) return false;
  const z = zone.toLowerCase();
  return z.includes('pastoral') || z.includes('agro-pastoral');
}

export default function AidAlertsPage() {
  const [counties, setCounties] = useState<PriorityItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    (async () => {
      try {
        const all = await fetchPriorityQueue();
        setCounties(all.filter((c) => AID_ALERT_ELIGIBLE_PHASES.includes(c.current_phase)));
      } catch (e) {
        setError(e instanceof Error ? e.message : 'Failed to load counties');
      } finally {
        setLoading(false);
      }
    })();
  }, []);

  return (
    <div className="space-y-5">
      <div>
        <div className="flex items-center gap-2">
          <Radio className="w-5 h-5" style={{ color: 'var(--phase-alarm)' }} />
          <h1 className="text-xl font-bold text-[#232A2E]">Send Aid</h1>
        </div>
        <p className="text-sm text-[#5B6560] mt-1">
          Counties currently in Alert, Alarm, or Emergency phase. Select a county to open its Aid Alert broadcast tool.
        </p>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-[#5B6560] font-mono">
          <Loader2 className="w-4 h-4 animate-spin" /> Loading counties…
        </div>
      )}

      {error && (
        <div className="text-sm font-mono text-[#9B3B34] bg-[#FAECEB] border border-[#C46760] rounded px-3 py-2">{error}</div>
      )}

      {!loading && !error && counties.length === 0 && (
        <div className="text-sm text-[#5B6560]">No counties are currently in an aid-eligible phase.</div>
      )}

      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-3">
        {counties.map((c) => {
          const pastoralist = isPastoralistZone(c.livelihood_zone);
          return (
            <Link
              key={c.county_id}
              href={`/county/${c.county_id}`}
              className="card p-4 bg-white hover:shadow-md transition-shadow block"
            >
              <div className="flex items-start justify-between gap-2">
                <div>
                  <div className="font-bold text-[#232A2E]">{c.county_name}</div>
                  <div className="text-xs text-[#9AA39C] mt-0.5">{c.region}</div>
                </div>
                <PhaseBadge phase={c.current_phase} />
              </div>
              <div className="mt-3 flex items-center gap-1.5 text-xs font-mono text-[#5B6560]">
                {pastoralist && <PawPrint className="w-3.5 h-3.5" style={{ color: '#B08A2E' }} />}
                <span>{c.livelihood_zone}</span>
              </div>
              {pastoralist && (
                <div className="mt-1.5 text-[11px] font-mono text-[#6B5313] bg-[#FBF3E4] border border-[#D8B978] rounded px-2 py-1">
                  Pastoralist zone — factor in livestock feed &amp; water
                </div>
              )}
            </Link>
          );
        })}
      </div>
    </div>
  );
}
