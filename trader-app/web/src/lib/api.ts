const BASE = "/api";

async function fetchJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, { cache: "no-store" });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

async function postJson<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

async function postJsonWithBody<T>(path: string, body: Record<string, unknown> = {}): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
    cache: "no-store",
  });
  if (!res.ok) throw new Error(`API error: ${res.status} ${res.statusText}`);
  return res.json();
}

export interface Portfolio {
  cash_usd: number;
  positions: Position[];
  total_value_usd: number;
  starting_capital: number;
  last_updated: string;
  trade_count: number;
  all_time_high: number;
  all_time_low: number;
}

export interface Position {
  ticker: string;
  instrument_type: string;
  quantity: number;
  entry_price: number;
  entry_date: string;
  current_price: number;
  unrealized_pnl: number;
  notes: string;
  initial_stop?: number | null;
  trailing_stop?: number | null;
  highest_since_entry?: number | null;
  take_profit_partial_hit?: boolean;
}

export interface TradeEntry {
  raw: string;
  date?: string;
  action?: string;
  instrument?: string;
  quantity?: string;
  price?: string;
  reasoning?: string;
  realized_pnl?: string;
  portfolio_balance?: string;
}

export interface TaskInfo {
  task_id: string;
  name: string;
  cron: string;
  is_running: boolean;
  last_run: {
    task_id: string;
    task_name: string;
    status: string;
    started_at: string;
    finished_at: string | null;
    error: string | null;
  } | null;
}

export interface TaskHistoryEntry {
  task_id: string;
  task_name: string;
  status: string;
  started_at: string;
  finished_at: string | null;
  error: string | null;
}

export interface ReportSummary {
  filename: string;
  date: string;
}

export interface ReportDetail {
  filename: string;
  content: string;
}

export interface AgentConfig {
  model: string;
  ollama_url: string;
  temperature: number;
  timezone: string;
  hourly_cron: string;
  morning_report_cron: string;
  instruments: Record<string, { type: string; tracks: string }>;
  indices: Record<string, string>;
  max_position_pct: number;
}

export interface PortfolioSnapshot {
  timestamp: string;
  total_value_usd: number;
  cash_usd: number;
}

export interface ExpansionProposal {
  id: string;
  ticker: string;
  instrument_type: string;
  description: string;
  category: string;
  region: string;
  risk_level: string;
  expected_return: string;
  rationale: string;
  source: string;
  status: "pending" | "approved" | "rejected";
  created_at: string;
  decided_at: string | null;
  rejection_reason: string | null;
}

export const api = {
  getPortfolio: () => fetchJson<Portfolio>("/portfolio"),
  getPortfolioHistory: (days = 30) =>
    fetchJson<PortfolioSnapshot[]>(`/portfolio/history?days=${days}`),
  getIndices: () => fetchJson<Record<string, unknown>>("/market/indices"),
  getInstruments: () => fetchJson<Record<string, unknown>>("/market/instruments"),
  getTechnicals: () => fetchJson<Record<string, Record<string, number | string | null>>>("/market/technicals"),
  getRegime: () => fetchJson<{
    regime: string;
    timestamp: string;
    signals: Record<string, unknown>;
    parameters: Record<string, unknown>;
  }>("/market/regime"),
  getTrades: (limit = 50) => fetchJson<TradeEntry[]>(`/trades?limit=${limit}`),
  getReflections: (limit = 20) =>
    fetchJson<{ raw: string }[]>(`/reflections?limit=${limit}`),
  getResearch: (limit = 20) =>
    fetchJson<{ raw: string }[]>(`/research?limit=${limit}`),
  getReports: () => fetchJson<ReportSummary[]>("/reports"),
  getReport: (filename: string) =>
    fetchJson<ReportDetail>(`/reports/${filename}`),
  getTasks: () => fetchJson<TaskInfo[]>("/tasks"),
  getTaskHistory: (limit = 50) =>
    fetchJson<TaskHistoryEntry[]>(`/tasks/history?limit=${limit}`),
  runTask: (taskId: string) => postJson<{ status: string }>(`/tasks/${taskId}/run`),
  stopTask: (taskId: string) =>
    postJson<{ status: string }>(`/tasks/${taskId}/stop`),
  getConfig: () => fetchJson<AgentConfig>("/config"),
  getSentiment: (limit = 10) =>
    fetchJson<{ raw: string }[]>(`/sentiment?limit=${limit}`),
  getRiskAlerts: (limit = 20) =>
    fetchJson<{ raw: string }[]>(`/risk-alerts?limit=${limit}`),
  getPerformance: (limit = 5) =>
    fetchJson<{ raw: string }[]>(`/performance?limit=${limit}`),
  getEvents: () => fetchJson<{ content: string }>("/events"),
  // Expansion proposals
  getProposals: (status = "") =>
    fetchJson<ExpansionProposal[]>(`/expansion/proposals${status ? `?status=${status}` : ""}`),
  approveProposal: (id: string) =>
    postJson<ExpansionProposal>(`/expansion/proposals/${id}/approve`),
  rejectProposal: (id: string, reason = "") =>
    postJson<ExpansionProposal>(`/expansion/proposals/${id}/reject${reason ? `?reason=${encodeURIComponent(reason)}` : ""}`),
  getTradeableInstruments: () =>
    fetchJson<Record<string, { type: string; tracks: string }>>("/expansion/instruments"),
};
