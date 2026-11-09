export type Site = { name: string; latitude: number; longitude: number };
export type Draft = {
  question: string;
  client_name: string;
  date: string;
  time: string;
  timezone: string;
  locations: Site[];
};
export type BriefingRequest = Draft & { request_id: string };
export type Measurement = Site & {
  temperature_c: number | null;
  temperature?: number | null;
  unit?: string;
  observed_at?: string;
  source?: string;
  source_id?: string;
  issue?: string;
  mock?: boolean;
};
export type Briefing = {
  request_id: string;
  status: string;
  replayed: boolean;
  request: BriefingRequest;
  comparison: {
    mock: boolean;
    incomplete: boolean;
    lowest_c: number;
    highest_c?: number;
    highest_locations?: string[];
    lowest_locations: string[];
    spread_c: number;
    ranking: { name: string; temperature_c: number }[];
  };
  measurements: Measurement[];
  limitations: string[];
  report_markdown: string;
  follow_up_draft: string;
  review?: {
    decision: "approve" | "reject";
    reviewer: string;
    reviewed_at: string;
  };
};
export type HistoryItem = {
  request_id: string;
  question: string;
  client_name: string;
  date: string;
  time: string;
  timezone: string;
  sites: number;
  status: string;
  lowest_c: number;
  highest_c?: number;
  mock: boolean;
};
export type Run = {
  id: string;
  state: "queued" | "running" | "completed" | "failed";
  request: BriefingRequest;
  created_at: string;
  events: { title: string; at: string }[];
  result: Briefing | null;
  error: { error: string; message: string } | null;
  elapsed_ms: number | null;
  execution_id: string | null;
};
export type DemoPreset = Pick<Draft, "date" | "time" | "timezone"> & {
  label: string;
};
export type DemoCoverage = {
  start: string;
  end: string;
  timezone: string;
  start_date: string;
  start_time: string;
  end_date: string;
  end_time: string;
  step_minutes: number;
  presets: DemoPreset[];
};
export type Bootstrap = {
  csrf: string;
  assistant_mode: "ai" | "guided";
  data_mode: string;
  automation_connected: boolean;
  catalog: Site[];
  history: HistoryItem[];
  latest: Briefing | null;
  latest_run: Run | null;
  fixture: { date: string; time: string; timezone: string };
  demo_coverage: DemoCoverage;
  workflow_url: string;
};
export type ChatMessage = {
  id: string;
  role: "assistant" | "user";
  content: string;
};
export type ChatReply = {
  message: string;
  draft: Draft;
  mode: "ai" | "guided";
  action: "run" | "clarify" | "answer" | "prepare";
  pending_action: "none" | "run" | "prepare";
  run?: Run;
  ready: boolean;
  missing_fields: string[];
  validation_errors: string[];
};
