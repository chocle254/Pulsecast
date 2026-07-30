'use client';

import React from 'react';
import { Sparkles, FileCode } from 'lucide-react';

interface ParsingMethodBadgeProps {
  parsingMethod: string;
  aiEvidence?: string | null;
  size?: 'sm' | 'md';
}

/**
 * Flags which bulletin records came from the deterministic regex/table
 * parser versus the AI parsing fallback (see backend/app/services/parser.py
 * and llm.py's extract_bulletin_fields_ai). This is deliberately visible on
 * the credibility screen — the AI fallback is a recovery path for bulletins
 * whose layout the parser couldn't match, not a silent substitute, and
 * every AI-recovered record carries the verbatim source quote it was
 * grounded in as a tooltip.
 */
export default function ParsingMethodBadge({
  parsingMethod,
  aiEvidence,
  size = 'sm',
}: ParsingMethodBadgeProps) {
  const sizeClasses = size === 'sm' ? 'text-[10px] px-1.5 py-0.5 gap-1' : 'text-xs px-2 py-1 gap-1.5';

  if (parsingMethod === 'ai_fallback') {
    return (
      <span
        className={`inline-flex items-center rounded font-mono font-semibold uppercase border shrink-0 ${sizeClasses}`}
        style={{ color: '#B9713A', background: '#FBF0E6', borderColor: '#E8C9AA' }}
        title={aiEvidence ? `AI-recovered — source quote: "${aiEvidence}"` : 'AI-recovered parse'}
      >
        <Sparkles className="w-3 h-3" /> AI-Recovered
      </span>
    );
  }

  return (
    <span
      className={`inline-flex items-center rounded font-mono font-semibold uppercase border shrink-0 ${sizeClasses}`}
      style={{ color: '#5B6560', background: '#F6F6F2', borderColor: '#C8CCC0' }}
      title="Parsed directly from the bulletin's tables/text"
    >
      <FileCode className="w-3 h-3" /> Regex
    </span>
  );
}
