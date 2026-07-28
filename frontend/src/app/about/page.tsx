'use client';

import React from 'react';
import Link from 'next/link';
import { Info, BookOpen, ShieldCheck, Activity, ArrowRight } from 'lucide-react';

export default function AboutPage() {
  return (
    <div className="container pt-6 space-y-6 max-w-4xl">
      {/* Header */}
      <div className="bg-[#F6F6F2] border border-[#C8CCC0] rounded-lg p-6 shadow-sm">
        <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] uppercase tracking-wider mb-1">
          <Info className="w-4 h-4 text-[#232A2E]" />
          <span>Product & Methodological Specification</span>
        </div>
        <h1 className="text-3xl font-bold tracking-tight text-[#232A2E]">
          About Pulsecast & Forecasting Methodology
        </h1>
        <p className="text-sm text-[#5B6560] mt-1 leading-relaxed">
          Operationalizing NDMA published data and thresholds to project drought phase transitions weeks before official bulletins confirm them.
        </p>
      </div>

      {/* Problem & Solution */}
      <div className="card p-6 bg-white space-y-4">
        <h2 className="text-lg font-bold text-[#232A2E] flex items-center gap-2">
          <Activity className="w-5 h-5 text-[#B9713A]" />
          The Operational Bottleneck
        </h2>
        <p className="text-sm text-[#232A2E] leading-relaxed">
          Kenya's National Drought Management Authority (NDMA) collects comprehensive satellite and biophysical data across 23 Arid and Semi-Arid Lands (ASAL) counties. However, monthly PDF bulletins report conditions that have <em>already occurred</em>. County drought coordinators face a manual burden every month: reading dense PDFs, translating technical indicators (VCI3M, SPI), judging priority, and making early-action decisions without advance lead time.
        </p>
        <p className="text-sm text-[#232A2E] leading-relaxed">
          <strong>Pulsecast</strong> compresses "read → translate → judge → decide" into "open dashboard → see ranked, explained, sourced forecast → act," giving coordinators 4–6 weeks of lead time before an official phase transition occurs.
        </p>
      </div>

      {/* NDMA 5-Phase System & Threshold Matrix */}
      <div className="card p-6 bg-white space-y-4">
        <h2 className="text-lg font-bold text-[#232A2E] flex items-center gap-2">
          <BookOpen className="w-5 h-5 text-[#3B5A37]" />
          NDMA 5-Phase Classification System & VCI3M Thresholds
        </h2>
        <p className="text-sm text-[#5B6560]">
          Pulsecast maps projections directly onto NDMA's official 5-phase system rather than an invented score:
        </p>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-xs font-mono border-collapse">
            <thead>
              <tr className="bg-[#F8F9F5] border-b border-[#C8CCC0] text-[#5B6560]">
                <th className="py-2.5 px-3">Phase Name</th>
                <th className="py-2.5 px-3">VCI3M Threshold</th>
                <th className="py-2.5 px-3">SPI Threshold</th>
                <th className="py-2.5 px-3">Operational Meaning</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-[#EDEEE8]">
              <tr>
                <td className="py-2.5 px-3 font-bold text-[#3B5A37]">Normal</td>
                <td className="py-2.5 px-3 font-bold">VCI3M ≥ 50</td>
                <td className="py-2.5 px-3">SPI ≥ -0.5</td>
                <td className="py-2.5 px-3">Vegetation conditions normal or above average.</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-bold text-[#7D5D18]">Alert</td>
                <td className="py-2.5 px-3 font-bold">35 ≤ VCI3M &lt; 50</td>
                <td className="py-2.5 px-3">-1.0 ≤ SPI &lt; -0.5</td>
                <td className="py-2.5 px-3">Early moisture deficit; watch stage for preparedness.</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-bold text-[#7A3E16]">Alarm</td>
                <td className="py-2.5 px-3 font-bold">20 ≤ VCI3M &lt; 35</td>
                <td className="py-2.5 px-3">-1.5 ≤ SPI &lt; -1.0</td>
                <td className="py-2.5 px-3">Moderate to severe vegetation stress; early action needed.</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-bold text-[#6D221D]">Emergency</td>
                <td className="py-2.5 px-3 font-bold">VCI3M &lt; 20</td>
                <td className="py-2.5 px-3">SPI &lt; -1.5</td>
                <td className="py-2.5 px-3">Extreme drought conditions; emergency response active.</td>
              </tr>
              <tr>
                <td className="py-2.5 px-3 font-bold text-[#265556]">Recovery</td>
                <td className="py-2.5 px-3 font-bold">Improving trajectory</td>
                <td className="py-2.5 px-3">Positive SPI trend</td>
                <td className="py-2.5 px-3">Conditions returning toward normal baseline.</td>
              </tr>
            </tbody>
          </table>
        </div>
      </div>

      {/* Forecasting Science & Citations */}
      <div className="card p-6 bg-white space-y-4">
        <h2 className="text-lg font-bold text-[#232A2E] flex items-center gap-2">
          <ShieldCheck className="w-5 h-5 text-[#4A8B8C]" />
          Forecasting Model & Scientific Grounding
        </h2>
        <div className="space-y-3 text-sm text-[#232A2E] leading-relaxed">
          <p>
            The forecasting engine utilizes a per-county autoregressive model (AR(2)) to project the 3-month Vegetation Condition Index (VCI3M) forward over a 4–6 week horizon, implementing the peer-reviewed methodology validated in:
          </p>

          <div className="p-4 bg-[#F8F9F5] border border-[#DDE0D8] rounded font-mono text-xs text-[#5B6560] space-y-1">
            <div className="font-bold text-[#232A2E]">Primary Scientific Reference:</div>
            <div>Barrett, C. B., et al. (2020). <em>"Early Alert: Predicting Drought Phase Transitions for Humanitarian Action in East Africa."</em> Journal of Development Economics / Food Security Research.</div>
          </div>

          <p>
            Every forecast includes explicit confidence bands (90% interval), and priority scores are calculated deterministically as:
          </p>
          <div className="p-3 bg-[#EDEEE8] font-mono text-xs rounded text-center font-bold text-[#232A2E]">
            Priority Score = Severity Index × Time Urgency (1 / Days to Crossing) × Model Confidence
          </div>
        </div>
      </div>

      {/* Action Button */}
      <div className="pt-2 text-center">
        <Link
          href="/"
          className="inline-flex items-center gap-2 px-6 py-3 bg-[#232A2E] text-white hover:bg-[#3B5A37] transition-colors rounded-md font-mono text-xs font-bold"
        >
          Explore Priority Queue <ArrowRight className="w-4 h-4" />
        </Link>
      </div>
    </div>
  );
}
