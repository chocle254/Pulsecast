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
  PawPrint,
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
 * screen (per language) instead of actually being dispatched.
 *
 * ACCESS CONTROL: gated behind REQUIRE_NGO_VERIFICATION — a single flag to
 * flip post-hackathon. While false, every visitor is treated as verified so
 * the feature stays demoable pre-launch.
 *
 * LIVELIHOOD-AWARE AID: the county's livelihood_zone is used to flag
 * pastoralist areas, since a pastoralist household's needs include feed and
 * water for livestock in addition to human aid — this nudges the coordinator
 * toward the right aid type and a larger volume estimate.
 */

const REQUIRE_NGO_VERIFICATION = false;

export const AID_ALERT_ELIGIBLE_PHASES = ['Alert', 'Alarm', 'Emergency'];

// Livelihood zones considered pastoralist/agro-pastoralist for aid-sizing
// purposes — livestock feed & water needs apply on top of human aid.
const PASTORALIST_KEYWORDS = ['pastoral', 'agro-pastoral'];

function isPastoralistZone(zone: string | null | undefined): boolean {
  if (!zone) return false;
  const z = zone.toLowerCase();
  return PASTORALIST_KEYWORDS.some((k) => z.includes(k));
}

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
  const notePart = notes.trim() ? ` ${notes.trim()}` : '';

  if (lang === 'sw') {
    return (
      `TAHADHARI YA MSAADA (PULSECAST): ${aidType.label_sw} itagawiwa katika Kaunti ya ${countyName} ` +
      `tarehe ${dateFmt} saa ${timeFmt}. Mahali pa ugawaji: ${locList}.${notePart} ` +
      `Tafadhali fika na kitambulisho. Imetolewa kupitia mwitikio ulioratibiwa na NDMA.`
    );
  }

  return (
    `PULSECAST AID ALERT: ${aidType.label_en} will be distributed in ${countyName} County on ${dateFmt} at ${timeFmt}. ` +
    `Distribution point(s): ${locList}.${notePart} ` +
    `Please bring valid ID. Issued via NDMA-coordinated emergency response.`
  );
}

function smsSegmentCount(text: string): number {
  if (text.length <= 160) return 1;
  return Math.ceil(text.length / 153);
}

export default function AidAlertPanel({
  countyId,
  countyName,
  phase,
  livelihoodZone,
}: {
  countyId: number;
  countyName: string;
  phase: string;
  livelihoodZone?: string | null;
}) {
  const eligible = AID_ALERT_ELIGIBLE_PHASES.includes(phase);
  const pastoralist = isPastoralistZone(livelihoodZone);

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

  // Nudge the default aid type toward livestock support in pastoralist zones
  // (only before the coordinator has touched the field).
  useEffect(() => {
    if (pastoralist) setAidTypeValue('livestock');
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [countyId, pastoralist]);

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
          sw: buildMessage('sw', countyName, aidType, date, time, locations, notes),
        }
      : null;

  function handleSend() {
    setErrorMsg(null);
    if (!date || !time) {
      setErrorMsg('Please set a distribution date and time.');
      return;
    }
    if (locations.length === 0) {
      setErrorMsg('Add at least one distribution location.');
      return;
    }
    if (selectedLangs.length === 0) {
      setErrorMsg('Select at least one broadcast language.');
      return;
    }
    setSending(true);
    const messages = {
      en: buildMessage('en', countyName, aidType, date, time, locations, notes),
      sw: buildMessage('sw', countyName, aidType, date, time, locations, notes),
    };
    const alert: SentAlert = {
      id: `${Date.now()}`,
      sentAt: new Date().toISOString(),
      aidTypeLabel: { en: aidType.label_en, sw: aidType.label_sw },
      date,
      time,
      locations,
      notes,
      messages,
    };
    setTimeout(() => {
      const updated = [alert, ...sentAlerts];
      setSentAlerts(updated);
      try {
        localStorage.setItem(storageKey, JSON.stringify(updated));
      } catch {
        // non-fatal — history just won't persist
      }
      setDate('');
      setTime('');
      setLocations([]);
      setNotes('');
      setSending(false);
    }, 600);
  }

  function clearHistory() {
    setSentAlerts([]);
    try {
      localStorage.removeItem(storageKey);
    } catch {
      // ignore
    }
  }

  return (
    <div className="card p-5 bg-white space-y-4 border-2" style={{ borderColor: 'var(--phase-alarm)' }}>
      <div className="flex items-center justify-between flex-wrap gap-2">
        <div className="flex items-center gap-2">
          <Radio className="w-4 h-4" style={{ color: 'var(--phase-alarm)' }} />
          <span className="font-mono font-bold text-sm text-[#232A2E] uppercase tracking-wide">
            NGO Aid Alert — {countyName} County
          </span>
        </div>
        {!REQUIRE_NGO_VERIFICATION ? null : (
          <div className="flex items-center gap-1 text-xs font-mono">
            <button
              type="button"
              onClick={() => setViewAsRole('ngo')}
              className={`px-2 py-1 rounded border ${viewAsRole === 'ngo' ? 'bg-[#232A2E] text-white border-[#232A2E]' : 'border-[#C8CCC0] text-[#5B6560]'}`}
            >
              View as NGO official
            </button>
            <button
              type="button"
              onClick={() => setViewAsRole('resident')}
              className={`px-2 py-1 rounded border ${viewAsRole === 'resident' ? 'bg-[#232A2E] text-white border-[#232A2E]' : 'border-[#C8CCC0] text-[#5B6560]'}`}
            >
              View as resident
            </button>
          </div>
        )}
      </div>

      {pastoralist && (
        <div className="flex items-start gap-2 text-xs font-mono bg-[#FBF3E4] border border-[#D8B978] rounded px-3 py-2 text-[#6B5313]">
          <PawPrint className="w-4 h-4 mt-0.5 flex-shrink-0" />
          <span>
            <strong>{countyName}</strong> is a <strong>{livelihoodZone}</strong> livelihood zone. Pastoralist
            households typically need feed and water for livestock alongside human aid — factor this into the
            aid type and volume you plan for.
          </span>
        </div>
      )}

      {!isVerifiedNgoOfficial ? (
        <div className="flex items-center gap-2 text-xs font-mono text-[#5B6560] bg-[#F8F9F5] border border-[#DDE0D8] rounded px-3 py-3">
          <Lock className="w-4 h-4" />
          This tool is restricted to verified NGO officials.
        </div>
      ) : (
        <>
          <div className="flex items-center gap-1.5 text-[11px] font-mono text-[#5B6560]">
            <ShieldCheck className="w-3.5 h-3.5" style={{ color: 'var(--phase-normal)' }} />
            Verified NGO official
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            <div className="md:col-span-2">
              <label className="text-xs font-mono font-bold text-[#5B6560] block mb-1">
                Aid Type {pastoralist && <span className="normal-case font-normal text-[#9AA39C]">(livestock support pre-selected for this zone)</span>}
              </label>
              <div className="relative">
                <select
                  value={aidTypeValue}
                  onChange={(e) => setAidTypeValue(e.target.value)}
                  className="w-full appearance-none border border-[#C8CCC0] rounded-md px-3 py-2 text-sm bg-white pr-8"
                >
                  {AID_TYPES.map((a) => (
                    <option key={a.value} value={a.value}>
                      {a.label_en}
                    </option>
                  ))}
                </select>
                <ChevronDown className="w-4 h-4 absolute right-2.5 top-2.5 text-[#5B6560] pointer-events-none" />
              </div>
            </div>

            <div>
              <label className="text-xs font-mono font-bold text-[#5B6560] block mb-1">Date</label>
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
                placeholder={pastoralist ? 'e.g. Bring livestock headcount for feed allocation' : 'e.g. Priority for households with children under 5'}
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
