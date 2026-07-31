'use client';

import React, { useEffect, useMemo, useState } from 'react';
import {
  Radio,
  Plus,
  X,
  Send,
  Lock,
  ShieldCheck,
  Users,
  MessageSquare,
  ChevronDown,
  Trash2,
} from 'lucide-react';

/**
 * ---------------------------------------------------------------------------
 * NGO Aid Alert Broadcast
 * ---------------------------------------------------------------------------
 * Only surfaces on counties currently in a phase severe enough to warrant an
 * aid distribution notice. Lets an NGO coordinator draft a distribution
 * (aid type, date/time, drop-off locations within the county) and broadcasts
 * it as an SMS to every resident registered in that county.
 *
 * HACKATHON SCOPE: there is no real SMS gateway wired up. Sending is
 * *simulated* — the exact text that would go out over SMS is rendered on
 * screen (per language) instead of actually being dispatched. Swapping in a
 * real provider (e.g. Africa's Talking / Twilio) later only means replacing
 * `simulateBroadcast()` below with a real API call; nothing else about this
 * component needs to change.
 *
 * ACCESS CONTROL: per the product plan, this is meant to be open to any user
 * for the hackathon demo, and locked to *verified NGO officials only* once
 * the product ships for real. Rather than hardcoding "anyone can use this",
 * the gating already lives here as `REQUIRE_NGO_VERIFICATION` — a single
 * flag to flip post-hackathon. The role selector below lets you preview both
 * states today. Wiring `isVerifiedNgoOfficial` to a real value later is a
 * one-line change: pull it from the authenticated session (e.g. a
 * `role: "ngo_official"` claim on the user's account) instead of local state.
 */

// Flip this to true once real NGO-official auth exists. While false, every
// visitor is treated as verified so the feature stays demoable pre-launch.
const REQUIRE_NGO_VERIFICATION = false;

// Which forecast phases are severe enough to show the aid-alert tool at all.
// Alert/Alarm per the product spec; Emergency is included too since it's
// strictly more urgent than Alarm — remove it here if you want it stricter.
export const AID_ALERT_ELIGIBLE_PHASES = ['Alert', 'Alarm', 'Emergency'];

interface AidType {
  value: string;
  label_en: string;
  label_sw: string;
}

const AID_TYPES: AidType[] = [
  { value: 'food', label_en: 'Food Assistance', label_sw: 'Msaada wa Chakula' },
  { value: 'water', label_en: 'Water & Sanitation', label_sw: 'Maji na Usafi wa Mazingira' },
  { value: 'cash', label_en: 'Cash Transfer', label_sw: 'Uhamisho wa Fedha' },
  { value: 'medical', label_en: 'Medical & Health Support', label_sw: 'Huduma za Afya' },
  { value: 'livestock', label_en: 'Livestock Feed & Vet Support', label_sw: 'Chakula cha Mifugo na Huduma za Mifugo' },
  { value: 'shelter', label_en: 'Shelter & Non-Food Items', label_sw: 'Makazi na Vifaa Muhimu' },
  { value: 'other', label_en: 'Other Aid', label_sw: 'Msaada Mwingine' },
];

type LangCode = 'en' | 'sw';

const LANGUAGES: { code: LangCode; label: string }[] = [
  { code: 'en', label: 'English' },
  { code: 'sw', label: 'Kiswahili' },
];

export interface SentAlert {
  id: string;
  sentAt: string; // ISO
  aidTypeLabel: Record<LangCode, string>;
  date: string;
  time: string;
  locations: string[];
  notes: string;
  messages: Record<LangCode, string>;
}

function formatDate(dateStr: string): string {
  if (!dateStr) return '';
  const d = new Date(`${dateStr}T00:00:00`);
  if (isNaN(d.getTime())) return dateStr;
  return d.toLocaleDateString('en-KE', { weekday: 'short', day: 'numeric', month: 'short', year: 'numeric' });
}

function formatTime(timeStr: string): string {
  if (!timeStr) return '';
  const [h, m] = timeStr.split(':').map(Number);
  if (isNaN(h)) return timeStr;
  const period = h >= 12 ? 'PM' : 'AM';
  const h12 = h % 12 === 0 ? 12 : h % 12;
  return `${h12}:${String(m).padStart(2, '0')} ${period}`;
}

/** Builds the exact SMS text for a given language. Template-based (not an
 *  LLM call) so the broadcast is instant and works offline in a demo. */
function buildMessage(
  lang: LangCode,
  countyName: string,
  aidType: AidType,
  dateStr: string,
  timeStr: string,
  locations: string[],
  notes: string
): string {
  const dateFmt = formatDate(dateStr);
  const timeFmt = formatTime(timeStr);
  const locList = locations.join(', ');

  if (lang === 'sw') {
    const notePart = notes.trim() ? ` ${notes.trim()}` : '';
    return (
      `TAHADHARI YA MSAADA (PULSECAST): ${aidType.label_sw} itagawiwa katika Kaunti ya ${countyName} ` +
      `tarehe ${dateFmt} saa ${timeFmt}. Mahali pa ugawaji: ${locList}.${notePart} ` +
      `Tafadhali fika na kitambulisho. Imetolewa kupitia mwitikio ulioratibiwa na NDMA.`
    );
  }

  const notePart = notes.trim() ? ` ${notes.trim()}` : '';
  return (
    `PULSECAST AID ALERT: ${aidType.label_en} will be distributed in ${countyName} County on ${dateFmt} at ${timeFmt}. ` +
    `Distribution point(s): ${locList}.${notePart} ` +
    `Please bring valid ID. Issued via NDMA-coordinated emergency response.`
  );
}

function smsSegmentCount(text: string): number {
  // Standard GSM-7 SMS: 160 chars for a single segment, 153 per segment
  // once it has to concatenate across multiple messages.
  if (text.length <= 160) return 1;
  return Math.ceil(text.length / 153);
}

export default function AidAlertPanel({ countyId, countyName, phase }: { countyId: number; countyName: string; phase: string }) {
  const eligible = AID_ALERT_ELIGIBLE_PHASES.includes(phase);

  const [viewAsRole, setViewAsRole] = useState<'ngo' | 'resident'>('ngo');
  const isVerifiedNgoOfficial = REQUIRE_NGO_VERIFICATION ? viewAsRole === 'ngo' : true;

  const [aidTypeValue, setAidTypeValue] = useState(AID_TYPES[0].value);
  const [date, setDate] = useState('');
  const [time, setTime] = useState('');
  const [locations, setLocations] = useState<string[]>([]);
  const [locationInput, setLocationInput] = useState('');
  const [notes, setNotes] = useState('');
  const [selectedLangs, setSelectedLangs] = useState<LangCode[]>(['en', 'sw']);
  const [error, setErrorMsg] = useState<string | null>(null);
  const [sending, setSending] = useState(false);
  const [sentAlerts, setSentAlerts] = useState<SentAlert[]>([]);

  const storageKey = `pulsecast_aid_alerts_${countyId}`;

  useEffect(() => {
    try {
      const raw = localStorage.getItem(storageKey);
      if (raw) setSentAlerts(JSON.parse(raw));
    } catch {
      // ignore malformed/local-storage-unavailable cases
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countyId]);

  const aidType = useMemo(() => AID_TYPES.find((a) => a.value === aidTypeValue) || AID_TYPES[0], [aidTypeValue]);

  if (!eligible) return null;

  const addLocation = () => {
    const trimmed = locationInput.trim();
    if (!trimmed) return;
    if (!locations.includes(trimmed)) setLocations([...locations, trimmed]);
    setLocationInput('');
  };

  const removeLocation = (loc: string) => setLocations(locations.filter((l) => l !== loc));

  const toggleLang = (code: LangCode) => {
    setSelectedLangs((prev) => (prev.includes(code) ? prev.filter((c) => c !== code) : [...prev, code]));
  };

  const preview: Record<LangCode, string> | null =
    date && time && locations.length > 0
      ? {
          en: buildMessage('en', countyName, aidType, date, time, locations, notes),
< truncated lines 191-318 >
                <input
                  type="date"
                  value={date}
                  onChange={(e) => setDate(e.target.value)}
                  className="w-full border border-[#C8CCC0] rounded-md px-3 py-2 text-sm bg-white"
                />
              </div>
              <div>
                <label className="text-xs font-mono font-bold text-[#5B6560] block mb-1">Time</label>
                <input
                  type="time"
                  value={time}
                  onChange={(e) => setTime(e.target.value)}
                  className="w-full border border-[#C8CCC0] rounded-md px-3 py-2 text-sm bg-white"
                />
              </div>
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-mono font-bold text-[#5B6560] block mb-1">
                Distribution Location(s) within {countyName}
              </label>
              <div className="flex gap-2">
                <input
                  type="text"
                  value={locationInput}
                  onChange={(e) => setLocationInput(e.target.value)}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter' || e.key === ',') {
                      e.preventDefault();
                      addLocation();
                    }
                  }}
                  placeholder="e.g. Kakuma Ward chief's camp — Enter to add"
                  className="flex-1 border border-[#C8CCC0] rounded-md px-3 py-2 text-sm bg-white"
                />
                <button
                  type="button"
                  onClick={addLocation}
                  className="px-3 py-2 rounded-md border border-[#C8CCC0] text-xs font-mono font-semibold text-[#232A2E] hover:bg-[#F8F9F5] flex items-center gap-1"
                >
                  <Plus className="w-3.5 h-3.5" /> Add
                </button>
              </div>
              {locations.length > 0 && (
                <div className="flex flex-wrap gap-1.5 mt-2">
                  {locations.map((loc) => (
                    <span
                      key={loc}
                      className="inline-flex items-center gap-1 text-xs font-mono bg-[#F8F9F5] border border-[#DDE0D8] rounded px-2 py-1 text-[#232A2E]"
                    >
                      {loc}
                      <button type="button" onClick={() => removeLocation(loc)} aria-label={`Remove ${loc}`}>
                        <X className="w-3 h-3 text-[#5B6560] hover:text-[#9B3B34]" />
                      </button>
                    </span>
                  ))}
                </div>
              )}
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-mono font-bold text-[#5B6560] block mb-1">
                Additional Notes <span className="font-normal normal-case text-[#9AA39C]">(optional — eligibility, what to bring, etc.)</span>
              </label>
              <input
                type="text"
                value={notes}
                onChange={(e) => setNotes(e.target.value)}
                placeholder="e.g. Priority for households with children under 5"
                className="w-full border border-[#C8CCC0] rounded-md px-3 py-2 text-sm bg-white"
              />
            </div>

            <div className="md:col-span-2">
              <label className="text-xs font-mono font-bold text-[#5B6560] block mb-1">Broadcast Language(s)</label>
              <div className="flex gap-2">
                {LANGUAGES.map(({ code, label }) => (
                  <button
                    type="button"
                    key={code}
                    onClick={() => toggleLang(code)}
                    className={`text-xs font-mono font-semibold px-3 py-1.5 rounded-md border ${
                      selectedLangs.includes(code)
                        ? 'bg-[#232A2E] text-white border-[#232A2E]'
                        : 'bg-white text-[#5B6560] border-[#C8CCC0] hover:bg-[#F8F9F5]'
                    }`}
                  >
                    {label}
                  </button>
                ))}
              </div>
            </div>
          </div>

          {error && (
            <div className="text-xs font-mono text-[#9B3B34] bg-[#FAECEB] border border-[#C46760] rounded px-3 py-2">{error}</div>
          )}

          {/* --- Live SMS Preview --- */}
          {preview && (
            <div className="border-t border-[#EDEEE8] pt-4">
              <div className="flex items-center gap-2 mb-2">
                <MessageSquare className="w-3.5 h-3.5 text-[#5B6560]" />
                <span className="text-xs font-mono font-bold text-[#5B6560] uppercase tracking-wide">
                  SMS Preview — exactly as residents will receive it
                </span>
              </div>
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
                {selectedLangs.map((code) => (
                  <SmsBubble key={code} lang={code} text={preview[code]} />
                ))}
              </div>
            </div>
          )}

          <div className="flex items-center justify-between pt-2">
            <div className="flex items-center gap-1.5 text-xs font-mono text-[#5B6560]">
              <Users className="w-3.5 h-3.5" />
              Recipients: all registered resident numbers in {countyName} County (simulated — no real SMS is sent)
            </div>
            <button
              type="button"
              onClick={handleSend}
              disabled={sending}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-md text-sm font-bold text-white disabled:opacity-60"
              style={{ background: 'var(--phase-alarm)' }}
            >
              <Send className="w-4 h-4" />
              {sending ? 'Broadcasting…' : 'Send Aid Alert'}
            </button>
          </div>
        </>
      )}

      {/* --- Sent history --- */}
      {isVerifiedNgoOfficial && sentAlerts.length > 0 && (
        <div className="border-t border-[#EDEEE8] pt-4 space-y-3">
          <div className="flex items-center justify-between">
            <span className="text-xs font-mono font-bold text-[#5B6560] uppercase tracking-wide">
              Broadcast History ({sentAlerts.length})
            </span>
            <button
              type="button"
              onClick={clearHistory}
              className="inline-flex items-center gap-1 text-[11px] font-mono text-[#5B6560] hover:text-[#9B3B34]"
            >
              <Trash2 className="w-3 h-3" /> Clear
            </button>
          </div>
          <div className="space-y-2 max-h-80 overflow-y-auto">
            {sentAlerts.map((alert) => (
              <details key={alert.id} className="border border-[#DDE0D8] rounded-md p-3 bg-[#F8F9F5]">
                <summary className="cursor-pointer text-xs font-mono text-[#232A2E] flex items-center justify-between flex-wrap gap-2">
                  <span>
                    <strong>{alert.aidTypeLabel.en}</strong> · {formatDate(alert.date)} at {formatTime(alert.time)} ·{' '}
                    {alert.locations.join(', ')}
                  </span>
                  <span className="text-[#9AA39C]">Sent {new Date(alert.sentAt).toLocaleString('en-KE')}</span>
                </summary>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 mt-3">
                  {(Object.keys(alert.messages) as LangCode[]).map((code) => (
                    <SmsBubble key={code} lang={code} text={alert.messages[code]} compact />
                  ))}
                </div>
              </details>
            ))}
          </div>
        </div>
      )}
    </div>
  );
}

function SmsBubble({ lang, text, compact = false }: { lang: LangCode; text: string; compact?: boolean }) {
  const segments = smsSegmentCount(text);
  const langLabel = LANGUAGES.find((l) => l.code === lang)?.label || lang;
  return (
    <div className="rounded-lg border border-[#DDE0D8] bg-[#F0F4EF] overflow-hidden">
      <div className="flex items-center justify-between px-3 py-1.5 bg-[#232A2E] text-[10px] font-mono text-white/80 uppercase tracking-wide">
        <span>{langLabel} · From: PULSECAST-AID</span>
        <span>{segments === 1 ? '1 SMS' : `${segments} SMS parts`}</span>
      </div>
      <div className={`p-3 ${compact ? 'text-[11px]' : 'text-xs'} font-sans text-[#232A2E] leading-relaxed whitespace-pre-wrap`}>
        {text}
      </div>
    </div>
  );
}
