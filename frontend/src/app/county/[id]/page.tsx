'use client';

import React, { useEffect, useState } from 'react';
import { useParams } from 'next/navigation';
import Link from 'next/link';
import { ArrowLeft, Clock, ShieldAlert, FileText, Info, CheckCircle2, AlertTriangle, RefreshCw } from 'lucide-react';
import PhaseBadge from '@/components/PhaseBadge';
import ThresholdChart from '@/components/ThresholdChart';
import { fetchCountyDetail, fetchCountyExplanation, CountyDetail } from '@/lib/api';

export default function CountyDetailPage() {
  const params = useParams();
  const countyId = Number(params?.id);

  const [data, setData] = useState<CountyDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [generatingAi, setGeneratingAi] = useState(false);
  const [aiResult, setAiResult] = useState<{ explanation: string; citations: any[] } | null>(null);

  useEffect(() => {
    async function load() {
      if (!countyId) return;
      setLoading(true);
      setError(null);
      try {
        const detail = await fetchCountyDetail(countyId);
        setData(detail);

        // Fetch or use existing AI explanation
        if (detail.ai_explanation) {
          setAiResult({ explanation: detail.ai_explanation, citations: [] });
        } else {
          const ai = await fetchCountyExplanation(countyId, 'full');
          setAiResult(ai);
        }
      } catch (err: any) {
        setError(err.message || 'Failed to load county detail');
      } finally {
        setLoading(false);
      }
    }
    load();
  }, [countyId]);

  const handleRegenerateAi = async () => {
    if (!countyId) return;
    setGeneratingAi(true);
    try {
      const ai = await fetchCountyExplanation(countyId, 'full');
      setAiResult(ai);
    } catch (err) {
      console.error('Failed to regenerate AI explanation', err);
    } finally {
      setGeneratingAi(false);
    }
  };

  if (loading) {
    return (
      <div className="container pt-12 text-center font-mono text-[#5B6560]">
        Loading county forecast detail...
      </div>
    );
  }

  if (error || !data) {
    return (
      <div className="container pt-12">
        <div className="card bg-red-50 border-red-200 text-red-800 font-mono text-sm p-6">
          {error || 'County not found'}
        </div>
        <Link href="/" className="inline-flex items-center gap-2 mt-4 text-xs font-mono font-bold text-[#232A2E]">
          <ArrowLeft className="w-4 h-4" /> Back to Priority Queue
        </Link>
      </div>
    );
  }

  const { forecast } = data;

  // Format AI text to render cited numbers as interactive badges
  const renderFormattedExplanation = (text: string) => {
    if (!text) return null;
    const parts = text.split(/(\[ref:[^\]]+\])/g);

    return parts.map((part, idx) => {
      if (part.startsWith('[ref:')) {
        const match = part.slice(5, -1).split('=');
        const field = match[0];
        const val = match[1] || '';
        return (
          <span
            key={idx}
            className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded font-mono text-xs font-semibold bg-[#EAF2E8] text-[#3B5A37] border border-[#A2C49E] cursor-help"
            title={`Cited source indicator: ${field}`}
          >
            {val}
          </span>
        );
      }
      return <span key={idx}>{part}</span>;
    });
  };

  return (
    <div className="container pt-6 space-y-6">
      {/* Top Navigation & Header */}
      <div>
        <Link href="/" className="inline-flex items-center gap-1.5 text-xs font-mono font-semibold text-[#5B6560] hover:text-[#232A2E] mb-3">
          <ArrowLeft className="w-3.5 h-3.5" /> Back to Priority Queue
        </Link>

        <div className="card p-6 bg-white flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
          <div>
            <div className="flex items-center gap-3">
              <h1 className="text-3xl font-bold text-[#232A2E]">{data.name} County</h1>
              <PhaseBadge phase={data.current_phase} size="lg" />
            </div>

            <div className="flex items-center gap-3 text-xs font-mono text-[#5B6560] mt-1.5">
              <span>Region: {data.region}</span>
              <span>•</span>
              <span className="capitalize">Livelihood: {data.livelihood_zone}</span>
            </div>
          </div>

          {/* Quick Metrics */}
          <div className="flex items-center gap-6 bg-[#F8F9F5] border border-[#DDE0D8] p-3 rounded-md font-mono">
            <div className="text-center px-2">
              <div className="text-xs text-[#5B6560]">Current VCI3M</div>
              <div className="text-xl font-bold text-[#232A2E]">{data.current_vci3m ?? 'N/A'}</div>
            </div>
            <div className="h-8 w-px bg-[#DDE0D8]" />
            <div className="text-center px-2">
              <div className="text-xs text-[#5B6560]">Current SPI</div>
              <div className="text-xl font-bold text-[#232A2E]">{data.current_spi ?? 'N/A'}</div>
            </div>
            <div className="h-8 w-px bg-[#DDE0D8]" />
            <div className="text-center px-2">
              <div className="text-xs text-[#5B6560]">Priority Score</div>
              <div className="text-xl font-bold text-[#B9713A]">
                {forecast?.priority_score?.toFixed(1) ?? 'N/A'}
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* Threshold Crossing Warning Banner (if projected) */}
      {forecast?.crossing_date && forecast.days_to_crossing && (
        <div className="bg-[#FAECEB] border border-[#C46760] text-[#6D221D] p-4 rounded-md flex items-center justify-between font-mono text-xs">
          <div className="flex items-center gap-3">
            <AlertTriangle className="w-5 h-5 text-[#9B3B34] shrink-0" />
            <div>
              <span className="font-bold uppercase tracking-wider">Threshold Crossing Alert:</span> Projected to enter{' '}
              <span className="font-extrabold">{forecast.crossing_phase}</span> phase on{' '}
              <span className="font-bold">{forecast.crossing_date}</span> ({forecast.days_to_crossing} days away).
            </div>
          </div>
          <div className="bg-white/80 px-2.5 py-1 rounded border border-[#C46760] font-bold">
            Confidence: {forecast.confidence ? `${Math.round(forecast.confidence * 100)}%` : 'N/A'}
          </div>
        </div>
      )}

      {/* Two-Pane Main Layout: Left Chart / Right AI Translation */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6">
        {/* Left Pane: Full D3 Threshold Signature Chart */}
        <div className="lg:col-span-7 card p-5 bg-white space-y-3">
          <div className="flex items-center justify-between pb-2 border-b border-[#EDEEE8]">
            <div>
              <h2 className="text-base font-bold text-[#232A2E]">VCI3M Forecast & Threshold Line</h2>
              <p className="text-xs text-[#5B6560] font-mono">
                Solid = historical bulletin values · Dashed = 6-week projection with 90% confidence band
              </p>
            </div>
          </div>

          <ThresholdChart
            historical={data.historical}
            forecast={forecast?.forecast_values || []}
            crossingDate={forecast?.crossing_date}
            crossingPhase={forecast?.crossing_phase}
            daysToCrossing={forecast?.days_to_crossing}
            height={360}
          />
        </div>

        {/* Right Pane: AI Translation & Grounded Explanation */}
        <div className="lg:col-span-5 card p-5 bg-white space-y-4 flex flex-col justify-between">
          <div>
            <div className="flex items-center justify-between pb-2 border-b border-[#EDEEE8] mb-3">
              <div className="flex items-center gap-2">
                <ShieldAlert className="w-4 h-4 text-[#B9713A]" />
                <h2 className="text-base font-bold text-[#232A2E]">Grounded AI Translation</h2>
              </div>
              <button
                onClick={handleRegenerateAi}
                disabled={generatingAi}
                className="text-xs font-mono text-[#5B6560] hover:text-[#232A2E] flex items-center gap-1 border border-[#C8CCC0] px-2 py-1 rounded hover:bg-[#EDEEE8]"
              >
                <RefreshCw className={`w-3 h-3 ${generatingAi ? 'animate-spin' : ''}`} />
                <span>Regenerate</span>
              </button>
            </div>

            {/* Explanation Content */}
            <div className="space-y-3 text-sm text-[#232A2E] leading-relaxed font-sans">
              {aiResult?.explanation ? (
                renderFormattedExplanation(aiResult.explanation)
              ) : (
                <p className="text-xs font-mono text-[#5B6560]">Generating plain-language explanation...</p>
              )}
            </div>

            {/* Livelihood Guidance Note */}
            <div className="mt-4 p-3 bg-[#F8F9F5] border border-[#DDE0D8] rounded text-xs space-y-1 font-sans">
              <div className="font-mono font-bold text-[#5B6560] uppercase text-[11px]">
                Livelihood Implication ({data.livelihood_zone}):
              </div>
              <p className="text-[#232A2E]">
                {data.livelihood_zone === 'pastoralist'
                  ? 'Pastoralist zone: Prioritize early livestock vaccination, grazing management, and strategic water trucking before phase shift.'
                  : 'Agro-pastoralist zone: Focus on crop residue preservation, soil moisture conservation, and local market food stock monitoring.'}
              </p>
            </div>
          </div>

          <div className="pt-3 border-t border-[#EDEEE8] text-[11px] font-mono text-[#5B6560] flex items-center justify-between">
            <span>Model: GPT-4o-mini + AR(2)</span>
            <span>Citations linked to NDMA source data below</span>
          </div>
        </div>
      </div>

      {/* Bottom Pane: Evidence Trail Table for this County */}
      <div className="card p-5 bg-white space-y-3">
        <div className="flex items-center justify-between pb-2 border-b border-[#EDEEE8]">
          <div>
            <h2 className="text-base font-bold text-[#232A2E]">County Evidence Trail</h2>
            <p className="text-xs text-[#5B6560] font-mono">
              Historical monthly bulletin records extracted for {data.name}
            </p>
          </div>
          <Link
            href={`/evidence?county_id=${data.id}`}
            className="text-xs font-mono text-[#B9713A] font-semibold hover:underline"
          >
            View Full Evidence Trail →
          </Link>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="bg-[#F8F9F5] border-b border-[#C8CCC0] text-[#5B6560]">
                <th className="py-2.5 px-3">Month</th>
                <th className="py-2.5 px-3">Phase Classification</th>
                <th className="py-2.5 px-3">VCI3M Index</th>
                <th className="py-2.5 px-3">SPI Index</th>
                <th className="py-2.5 px-3">Source Bulletin</th>
              </tr>
            </thead>
            <tbody>
              {data.historical.map((h, i) => (
                <tr key={i} className="border-b border-[#EDEEE8] hover:bg-[#F8F9F5]">
                  <td className="py-2.5 px-3 font-bold text-[#232A2E]">{h.month}</td>
                  <td className="py-2.5 px-3">
                    <PhaseBadge phase={h.phase} size="sm" />
                  </td>
                  <td className="py-2.5 px-3 font-semibold text-[#232A2E]">{h.vci3m ?? '—'}</td>
                  <td className="py-2.5 px-3 text-[#5B6560]">{h.spi ?? '—'}</td>
                  <td className="py-2.5 px-3 text-[#5B6560]">
                    <span className="inline-flex items-center gap-1 text-[11px] underline cursor-pointer hover:text-[#232A2E]">
                      <FileText className="w-3 h-3" /> NDMA Bulletin p.{h.source_page || 1}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
