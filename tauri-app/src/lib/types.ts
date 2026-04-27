// Mirrors sasayaki.api.schemas.PipelineStateSchema.
// Hand-written for P2 — will be replaced by codegen from OpenAPI in P3+.

export type Source = "system" | "mic";

export interface TranscriptEvent {
  text: string;
  source: Source;
  is_partial: boolean;
  timestamp: number;
}

export interface EntityEvent {
  term: string;
  definition: string;
  timestamp: number;
  loading: boolean;
}

export interface ProfileFact {
  category: string;
  content: string;
  timestamp: number;
}

export interface PartnerProfile {
  name: string | null;
  facts: ProfileFact[];
  summary: string;
}

export interface ExpressionChangeEvent {
  detail: string;
  transcript_snippet: string;
  timestamp: number;
}

export interface FaceAnalysisState {
  detected: boolean;
  joy: number;
  surprise: number;
  concern: number;
  neutral: number;
  dominant_emotion: string;
  nodding: boolean;
  nod_count: number;
  expression_changes: ExpressionChangeEvent[];
  fps: number;
  face_image_base64: string;
}

export interface TurnTakingState {
  p_now: number;
  p_future: number;
  is_turn_change: boolean;
  last_trigger_time: number;
  enabled: boolean;
}

export type LLMBackend = "ollama" | "llamacpp";

export interface PipelineState {
  transcripts: TranscriptEvent[];
  entities: EntityEvent[];
  suggestions: string[];
  suggesting: boolean;
  suggestion_style: string;
  profile: PartnerProfile;
  profiling: boolean;
  is_running: boolean;
  error: string | null;
  system_device: string;
  mic_device: string;
  tts_output_device: string;
  ollama_ok: boolean;
  system_level: number;
  mic_level: number;
  face: FaceAnalysisState;
  turn_taking: TurnTakingState;
  tts_playing: boolean;
  auto_suggestion_pending: boolean;
  llm_backend: LLMBackend;
  ollama_model: string;
  llamacpp_url: string;
  auto_suggest_style: string;
  turn_taking_threshold: number;
  turn_taking_cooldown_sec: number;
  turn_taking_min_transcripts: number;
  llm_context_mode: ContextMode;
  llm_context_turns: number;
  screen_region: [number, number, number, number];
  screen_monitor: number;
  silence_seconds: number;
  silence_rescue_enabled: boolean;
  silence_rescue_seconds: number;
  silence_rescue_style: string;
  speculative_pre_fire_enabled: boolean;
  last_whisper_text: string;
  meeting_context: string;
  adapt_style_to_emotion: boolean;
  concern_alert_enabled: boolean;
}

export type ContextMode = "fixed" | "since_last_fire";

export interface MonitorInfo {
  index: number;
  width: number;
  height: number;
}

export interface MonitorsResponse {
  monitors: MonitorInfo[];
}

export interface ScreenRegionResponse {
  region: [number, number, number, number] | null;
}

export interface DevicesResponse {
  input_devices: { name: string }[];
  output_devices: { name: string }[];
}

export type StyleKey =
  | "深堀り"
  | "褒める"
  | "批判的"
  | "矛盾指摘"
  | "よいしょ"
  | "共感"
  | "まとめる"
  | "話題転換"
  | "具体例を求める"
  | "ボケる"
  | "謝罪"
  | "知識でマウント";

export const STYLE_KEYS: StyleKey[] = [
  "深堀り",
  "褒める",
  "批判的",
  "矛盾指摘",
  "よいしょ",
  "共感",
  "まとめる",
  "話題転換",
  "具体例を求める",
  "ボケる",
  "謝罪",
  "知識でマウント",
];
