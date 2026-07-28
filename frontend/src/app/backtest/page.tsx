'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { History, CheckCircle, AlertOctagon, Info, ArrowRight } from 'lucide-react';
import PhaseBadge from '@/components/PhaseBadge';
import { fetchBacktestSummary, BacktestSummary } from '@/lib/api';

export default function BacktestPage() {
  const [data, setData] = useState<BacktestSummary | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const res = await fetchBacktestSummary();
        setData(res);
      } catch (err: any) {
        setError(err.message || 'Failed to load backtest summary');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, []);

  return (
    <div className="container pt-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-[#F6F6F2] border border-[#C8CCC0] rounded-lg p-5 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] uppercase tracking-wider mb-1">
            <History className="w-3.5 h-3.5 text-[#232A2E]" />
            <span>Validation & Model Evaluation</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#232A2E]">
            Backtest & Model Track Record
          </h1>
          <p className="text-sm text-[#5B6560] mt-0.5">
            Evaluating historical AR(2) model forecasts against later official NDMA bulletin classifications.
          </p>
        </div>
      </div>

      {/* Proof-of-concept disclaimer alert as per Demo Notes & README */}
      <div className="bg-[#EAF2E8] border border-[#A2C49E] p-4 rounded-md text-xs text-[#3B5A37] flex items-start gap-3">
        <Info className="w-4 h-4 shrink-0 mt-0.5" />
        <div>
          <span className="font-bold uppercase font-mono">Methodological Disclosure:</span> This backtest panel evaluates the operational feasibility of the AR(2) forecasting approach proposed by Barrett et al. (2020) on published monthly bulletin VCI3M data. It demonstrates transparency inside the tool rather than making unchecked accuracy claims.
        </div>
      </div>

      {/* Aggregate Performance Cards */}
      {loading ? (
        <div className="card p-12 text-center font-mono text-xs text-[#5B6560]">
          Calculating backtest accuracy across counties...
        </div>
      ) : error ? (
        <div className="card p-6 bg-red-50 text-red-800 font-mono text-xs">{error}</div>
      ) : data ? (
        <>
          <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
            <div className="card p-4 bg-white text-center font-mono">
              <div className="text-xs text-[#5B6560]">Total Month Predictions</div>
              <div className="text-2xl font-bold text-[#232A2E] mt-1">{data.total_predictions}</div>
            </div>

            <div className="card p-4 bg-white text-center font-mono">
              <div className="text-xs text-[#5B6560]">Exact Phase Matches</div>
              <div className="text-2xl font-bold text-[#3B5A37] mt-1">{data.correct_predictions}</div>
            </div>

            <div className="card p-4 bg-white text-center font-mono">
              <div className="text-xs text-[#5B6560]">Overall Hit Rate</div>
              <div className="text-2xl font-bold text-[#7A9B76] mt-1">
                {(data.hit_rate * 100).toFixed(1)}%
              </div>
            </div>

            <div className="card p-4 bg-white text-center font-mono">
              <div className="text-xs text-[#5B6560]">False Alarm Rate</div>
              <div className="text-2xl font-bold text-[#C9A24B] mt-1">
                {(data.false_alarm_rate * 100).toFixed(1)}%
              </div>
            </div>
          </div>

          {/* Per-County Breakdown Table */}
          <div className="card p-5 bg-white space-y-3">
            <h2 className="text-base font-bold text-[#232A2E]">Per-County Track Record Summary</h2>
            <div className="overflow-x-auto">
              <table className="w-full text-left text-xs font-mono border-collapse">
                <thead>
                  <tr className="bg-[#F8F9F5] border-b border-[#C8CCC0] text-[#5B6560] uppercase text-[11px]">
                    <th className="py-2.5 px-3">County Name</th>
                    <th className="py-2.5 px-3">Evaluated Months</th>
                    <th className="py-2.5 px-3">Correct Forecasts</th>
                    <th className="py-2.5 px-3">Hit Rate</th>
                    <th className="py-2.5 px-3">False Alarms</th>
                    <th className="py-2.5 px-3">Action</th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-[#EDEEE8]">
                  {data.counties.map((c) => (
                    <tr key={c.county_id} className="hover:bg-[#F8F9F5]">
                      <td className="py-2.5 px-3 font-bold text-[#232A2E]">{c.county_name}</td>
                      <td className="py-2.5 px-3 text-[#232A2E]">{c.total}</td>
                      <td className="py-2.5 px-3 text-[#3B5A37] font-semibold">{c.correct}</td>
                      <td className="py-2.5 px-3 font-bold text-[#232A2E]">
                        {(c.hit_rate * 100).toFixed(0)}%
                      </td>
                      <td className="py-2.5 px-3 text-[#B9713A]">{c.false_alarms}</td>
                      <td className="py-2.5 px-3">
                        <Link
                          href={`/county/${c.county_id}`}
                          className="text-[11px] text-[#B9713A] hover:underline inline-flex items-center gap-1 font-semibold"
                        >
                          View County →
                        </Link>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </div>
        </>
      ) : null}
    </div>
  );
}
