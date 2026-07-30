'use client';

import React, { useEffect, useState } from 'react';
import Link from 'next/link';
import { Database, FileText, Download, ExternalLink, Filter } from 'lucide-react';
import PhaseBadge from '@/components/PhaseBadge';
import ParsingMethodBadge from '@/components/ParsingMethodBadge';
import { fetchEvidenceTrail, EvidenceRecord } from '@/lib/api';

export default function EvidenceTrailPage() {
  const [records, setRecords] = useState<EvidenceRecord[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  // Filters
  const [selectedPhase, setSelectedPhase] = useState<string>('');
  const [selectedMonth, setSelectedMonth] = useState<string>('');

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const data = await fetchEvidenceTrail({
          phase: selectedPhase || undefined,
          month: selectedMonth || undefined,
          limit: 300,
        });
        setRecords(data);
      } catch (err: any) {
        setError(err.message || 'Failed to load evidence trail');
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [selectedPhase, selectedMonth]);

  const exportCsv = () => {
    const headers = ['County', 'Month', 'Phase', 'VCI3M', 'SPI', 'Source Page', 'Parsed At', 'Parsing Method'];
    const rows = records.map((r) => [
      r.county_name,
      r.month,
      r.phase,
      r.vci3m ?? '',
      r.spi ?? '',
      r.source_page ?? '',
      r.parsed_at,
      r.parsing_method,
    ]);

    const csvContent =
      'data:text/csv;charset=utf-8,' +
      [headers.join(','), ...rows.map((e) => e.join(','))].join('\n');

    const encodedUri = encodeURI(csvContent);
    const link = document.createElement('a');
    link.setAttribute('href', encodedUri);
    link.setAttribute('download', 'pulsecast_evidence_trail.csv');
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
  };

  return (
    <div className="container pt-6 space-y-6">
      {/* Header Banner */}
      <div className="bg-[#F6F6F2] border border-[#C8CCC0] rounded-lg p-5 shadow-sm flex flex-col md:flex-row justify-between items-start md:items-center gap-4">
        <div>
          <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] uppercase tracking-wider mb-1">
            <Database className="w-3.5 h-3.5 text-[#232A2E]" />
            <span>Traceability & Verification</span>
          </div>
          <h1 className="text-2xl font-bold tracking-tight text-[#232A2E]">
            Evidence Trail — Parsed NDMA Bulletins
          </h1>
          <p className="text-sm text-[#5B6560] mt-0.5">
            Every number traceable to its source PDF bulletin page. Deliberately precise and unvarnished.
          </p>
        </div>

        <button
          onClick={exportCsv}
          className="px-3.5 py-2 bg-[#232A2E] text-white hover:bg-[#3B5A37] transition-colors rounded text-xs font-mono font-semibold flex items-center gap-2"
        >
          <Download className="w-4 h-4" /> Export CSV Data
        </button>
      </div>

      {/* Filter Bar */}
      <div className="bg-white border border-[#C8CCC0] rounded-md p-3.5 flex items-center justify-between gap-3 text-xs font-mono">
        <div className="flex items-center gap-3">
          <div className="flex items-center gap-1.5 font-semibold text-[#5B6560]">
            <Filter className="w-3.5 h-3.5" />
            <span>Filter:</span>
          </div>

          <select
            value={selectedPhase}
            onChange={(e) => setSelectedPhase(e.target.value)}
            className="bg-[#F6F6F2] border border-[#C8CCC0] rounded px-2.5 py-1.5 text-xs text-[#232A2E] focus:outline-none"
          >
            <option value="">All Phases</option>
            <option value="Normal">Normal</option>
            <option value="Alert">Alert</option>
            <option value="Alarm">Alarm</option>
            <option value="Emergency">Emergency</option>
            <option value="Recovery">Recovery</option>
          </select>
        </div>

        <div className="text-[#5B6560] text-xs">
          Showing <span className="font-bold text-[#232A2E]">{records.length}</span> verified record(s)
        </div>
      </div>

      {/* Main Evidence Data Table */}
      <div className="card p-0 bg-white overflow-hidden border border-[#C8CCC0] shadow-sm">
        {loading ? (
          <div className="p-12 text-center font-mono text-xs text-[#5B6560]">
            Fetching evidence records...
          </div>
        ) : error ? (
          <div className="p-6 bg-red-50 text-red-800 font-mono text-xs">{error}</div>
        ) : (
          <div className="overflow-x-auto">
            <table className="w-full text-left text-xs font-mono border-collapse">
              <thead>
                <tr className="bg-[#F8F9F5] border-b border-[#C8CCC0] text-[#5B6560] uppercase text-[11px]">
                  <th className="py-3 px-4"># ID</th>
                  <th className="py-3 px-4">County Name</th>
                  <th className="py-3 px-4">Month</th>
                  <th className="py-3 px-4">Phase</th>
                  <th className="py-3 px-4">VCI3M</th>
                  <th className="py-3 px-4">SPI</th>
                  <th className="py-3 px-4">Source Page</th>
                  <th className="py-3 px-4">Parsing</th>
                  <th className="py-3 px-4">Actions</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-[#EDEEE8]">
                {records.map((r) => (
                  <tr key={r.id} className="hover:bg-[#F8F9F5] transition-colors">
                    <td className="py-2.5 px-4 text-[#5B6560]">#{r.id}</td>
                    <td className="py-2.5 px-4 font-bold text-[#232A2E]">
                      <Link href={`/county/${r.county_id}`} className="hover:underline">
                        {r.county_name}
                      </Link>
                    </td>
                    <td className="py-2.5 px-4 text-[#232A2E]">{r.month}</td>
                    <td className="py-2.5 px-4">
                      <PhaseBadge phase={r.phase} size="sm" />
                    </td>
                    <td className="py-2.5 px-4 font-bold text-[#232A2E]">{r.vci3m ?? '—'}</td>
                    <td className="py-2.5 px-4 text-[#5B6560]">{r.spi ?? '—'}</td>
                    <td className="py-2.5 px-4 text-[#5B6560]">
                      {r.source_url ? (
                        <a
                          href={r.source_url}
                          target="_blank"
                          rel="noopener noreferrer"
                          className="inline-flex items-center gap-1 bg-[#EDEEE8] px-2 py-0.5 rounded text-[11px] hover:bg-[#E2E4DC]"
                        >
                          <FileText className="w-3 h-3" />
                          {r.source_page ? `Page ${r.source_page}` : 'View source'}
                        </a>
                      ) : (
                        <span className="inline-flex items-center gap-1 bg-[#EDEEE8] px-2 py-0.5 rounded text-[11px] text-[#9AA39C]">
                          Source unavailable
                        </span>
                      )}
                    </td>
                    <td className="py-2.5 px-4">
                      <ParsingMethodBadge parsingMethod={r.parsing_method} aiEvidence={r.ai_evidence} size="sm" />
                    </td>
                    <td className="py-2.5 px-4">
                      <Link
                        href={`/county/${r.county_id}`}
                        className="text-[11px] font-semibold text-[#B9713A] hover:underline inline-flex items-center gap-1"
                      >
                        Inspect <ExternalLink className="w-3 h-3" />
                      </Link>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  );
}
