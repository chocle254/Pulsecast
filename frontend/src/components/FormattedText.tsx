'use client';

import React from 'react';

/**
 * Renders AI-generated explanation/analysis text. The LLM (and its
 * template fallback) produces two things beyond plain prose:
 *   - **bold** section labels ("**Forecast:**", "**Recommended Action:**")
 *   - [ref:field=val] citation markers, rendered as small badges
 * Paragraphs are separated by blank lines in the source text.
 *
 * This is intentionally a small hand-rolled tokenizer, not a full markdown
 * parser — the LLM prompts only ever produce **bold** and paragraph breaks,
 * so a real markdown library would be more dependency than this needs.
 */
export default function FormattedText({ text, className = '' }: { text: string; className?: string }) {
  if (!text) return null;

  const paragraphs = text.split(/\n\n+/);

  return (
    <div className={className}>
      {paragraphs.map((para, pIdx) => (
        <p key={pIdx} className={pIdx > 0 ? 'mt-3' : ''}>
          {renderInline(para)}
        </p>
      ))}
    </div>
  );
}

export function formatInlineText(text: string): React.ReactNode[] {
  return renderInline(text);
}

function renderInline(text: string): React.ReactNode[] {
  // Split on **bold** and [ref:field=val] together, keeping the
  // delimiters, so both can be handled in one left-to-right pass.
  const tokens = text.split(/(\*\*[^*]+\*\*|\[ref:[^\]]+\])/g);

  return tokens.map((token, idx) => {
    if (token.startsWith('**') && token.endsWith('**')) {
      return (
        <strong key={idx} className="font-semibold">
          {token.slice(2, -2)}
        </strong>
      );
    }

    if (token.startsWith('[ref:')) {
      const [field, val] = token.slice(5, -1).split('=');
      return (
        <span
          key={idx}
          className="inline-flex items-center px-1.5 py-0.5 mx-0.5 rounded font-mono text-xs font-semibold bg-[#EAF2E8] text-[#3B5A37] border border-[#A2C49E] cursor-help"
          title={`Cited source indicator: ${field}`}
        >
          {val || token}
        </span>
      );
    }

    return <React.Fragment key={idx}>{token}</React.Fragment>;
  });
}
