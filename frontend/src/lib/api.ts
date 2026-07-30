const API_BASE = process.env.NEXT_PUBLIC_API_URL || '';

export interface PatternSignal {
  type: 'recurrence' | 'regional_cluster';
  note: string;
  // recurrence-only fields
  same_month_years?: string[];
  same_month_occurrences?: { month: string; phase: string }[];
  persistent_streak?: number | null;
  streak_occurrences?: { month: string; phase: string }[];
  // regional_cluster-only fields
  region?: string;
  at_risk_count?: number;
  region_size?: number;
  peer_counties?: string[];
}

export interface PatternSignals {
  signals: PatternSignal[];
}

export interface PriorityItem {
  rank: number;
  county_id: number;
  county_name: string;
  region: string;
  livelihood_zone: string;
  current_phase: string;
  current_vci3m: number | null;
  forecast_vci3m: number | null;
  crossing_date: string | null;
  crossing_phase: string | null;
  days_to_crossing: number | null;
  confidence: number | null;
  priority_score: number;
  sparkline_data: number[];
  ai_summary: string | null;
  pattern_signals: PatternSignals | null;
}

export interface CountyDetail {
  id: number;
  name: string;
  region: string;
  livelihood_zone: string;
  latitude: number | null;
  longitude: number | null;
  current_phase: string;
  current_vci3m: number | null;
  current_spi: number | null;
  historical: {
    month: string;
    vci3m: number | null;
    spi: number | null;
    phase: string;
    source_url?: string;
    source_page?: number;
  }[];
  forecast: {
    generated_at: string;
    forecast_weeks: number;
    forecast_values: { week: number; vci3m: number; lower: number; upper: number }[];
    crossing_date: string | null;
    crossing_phase: string | null;
    days_to_crossing: number | null;
    confidence: number | null;
    priority_score: number;
  } | null;
  ai_explanation: string | null;
  pattern_signals: PatternSignals | null;
}

export interface SeasonalOutlook {
  period: string;
  rainfall_outlook: string;
  temperature_outlook: string | null;
  source_url: string;
}

export interface AiExplanation {
  county_id: number;
  county_name: string;
  livelihood_zone: string | null;
  seasonal_outlook: SeasonalOutlook | null;
  pattern_signals: PatternSignals | null;
  explanation: string;
  citations: { field: string; value: string; position?: number }[];
  generated_at: string;
  model: string;
}

export interface EvidenceRecord {
  id: number;
  county_id: number;
  county_name: string;
  month: string;
  vci3m: number | null;
  spi: number | null;
  phase: string;
  source_url: string | null;
  source_page: number | null;
  parsed_at: string;
}

export interface MapCountyData {
  county_id: number;
  county_name: string;
  current_phase: string | null;
  forecast_phase: string | null;
  days_to_crossing: number | null;
  priority_score: number | null;
  vci3m: number | null;
  pattern_signals: PatternSignals | null;
}

export interface BacktestSummary {
  total_predictions: number;
  correct_predictions: number;
  hit_rate: number;
  false_alarm_rate: number;
  counties: {
    county_id: number;
    county_name: string;
    total: number;
    correct: number;
    hit_rate: number;
    false_alarms: number;
  }[];
}

export interface EvidenceStats {
  total_records: number;
  months_covered: number;
  counties_covered: number;
  phase_distribution: { phase: string; count: number }[];
  last_updated: string | null;
}

export interface RefreshResult {
  status: string;
  total_records: number;
  counties_covered: number;
  last_updated: string | null;
}

export async function fetchPriorityQueue(filters?: {
  phase?: string;
  region?: string;
  livelihood_zone?: string;
  sort_by?: string;
  sort_order?: string;
}): Promise<PriorityItem[]> {
  const params = new URLSearchParams();
  if (filters?.phase) params.append('phase', filters.phase);
  if (filters?.region) params.append('region', filters.region);
  if (filters?.livelihood_zone) params.append('livelihood_zone', filters.livelihood_zone);
  if (filters?.sort_by) params.append('sort_by', filters.sort_by);
  if (filters?.sort_order) params.append('sort_order', filters.sort_order);

  const res = await fetch(`${API_BASE}/api/counties/priority-queue?${params.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch priority queue');
  return res.json();
}

export async function fetchCountyDetail(id: number): Promise<CountyDetail> {
  const res = await fetch(`${API_BASE}/api/counties/${id}`);
  if (!res.ok) throw new Error(`Failed to fetch county ${id}`);
  return res.json();
}

export async function fetchCountyExplanation(
  id: number,
  detailLevel: 'summary' | 'full' = 'full'
): Promise<AiExplanation> {
  const res = await fetch(`${API_BASE}/api/forecast/${id}/explain?detail_level=${detailLevel}`);
  if (!res.ok) throw new Error('Failed to fetch AI explanation');
  return res.json();
}

export async function fetchMapData(): Promise<MapCountyData[]> {
  const res = await fetch(`${API_BASE}/api/counties/map-data`);
  if (!res.ok) throw new Error('Failed to fetch map data');
  return res.json();
}

export interface ComputedCluster {
  region: string;
  at_risk_count: number;
  region_size: number;
  counties: string[];
}

export interface RegionalSynthesis {
  synthesis: string;
  citations: { field: string; value: string; position?: number }[];
  computed_clusters: ComputedCluster[];
  generated_at: string;
  model: string;
}

export async function fetchRegionalSynthesis(): Promise<RegionalSynthesis> {
  const res = await fetch(`${API_BASE}/api/counties/regional-synthesis`);
  if (!res.ok) throw new Error('Failed to fetch regional synthesis');
  return res.json();
}

export async function fetchEvidenceTrail(params?: {
  county_id?: number;
  month?: string;
  phase?: string;
  limit?: number;
}): Promise<EvidenceRecord[]> {
  const searchParams = new URLSearchParams();
  if (params?.county_id) searchParams.append('county_id', params.county_id.toString());
  if (params?.month) searchParams.append('month', params.month);
  if (params?.phase) searchParams.append('phase', params.phase);
  if (params?.limit) searchParams.append('limit', params.limit.toString());

  const res = await fetch(`${API_BASE}/api/evidence/?${searchParams.toString()}`);
  if (!res.ok) throw new Error('Failed to fetch evidence trail');
  return res.json();
}

export async function fetchBacktestSummary(): Promise<BacktestSummary> {
  const res = await fetch(`${API_BASE}/api/forecast/backtest/summary`);
  if (!res.ok) throw new Error('Failed to fetch backtest summary');
  return res.json();
}

export async function fetchRegions(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/counties/regions/list`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchLivelihoodZones(): Promise<string[]> {
  const res = await fetch(`${API_BASE}/api/counties/livelihood-zones/list`);
  if (!res.ok) return [];
  return res.json();
}

export async function fetchEvidenceStats(): Promise<EvidenceStats> {
  const res = await fetch(`${API_BASE}/api/evidence/stats`);
  if (!res.ok) throw new Error('Failed to fetch evidence stats');
  return res.json();
}

/**
 * Triggers a real, on-demand pull of NDMA's published bulletins on the
 * backend (crawl -> parse -> upsert -> regenerate forecasts). This can take
 * a while — it's a live network operation against NDMA's site, not a cache
 * refresh — so callers should show a busy state for the duration.
 */
export async function refreshBulletins(): Promise<RefreshResult> {
  const res = await fetch(`${API_BASE}/api/admin/refresh-bulletins`, { method: 'POST' });
  if (!res.ok) {
    const body = await res.json().catch(() => null);
    throw new Error(body?.detail || 'Failed to refresh NDMA data');
  }
  return res.json();
}
