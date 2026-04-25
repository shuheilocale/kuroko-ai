import type {
  DevicesResponse,
  MonitorsResponse,
  PipelineState,
  ScreenRegionResponse,
} from "./types";

const DEFAULT_BASE = "http://127.0.0.1:7861";
const DEFAULT_WS = "ws://127.0.0.1:7861";

function getBase(): string {
  return (
    (import.meta.env.VITE_SASAYAKI_API as string | undefined) ??
    DEFAULT_BASE
  );
}

function getWs(): string {
  return (
    (import.meta.env.VITE_SASAYAKI_WS as string | undefined) ??
    DEFAULT_WS
  );
}

async function post<T>(path: string, body?: unknown): Promise<T> {
  const res = await fetch(`${getBase()}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: body === undefined ? undefined : JSON.stringify(body),
  });
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${getBase()}${path}`);
  if (!res.ok) throw new Error(`${path} -> ${res.status}`);
  return res.json() as Promise<T>;
}

export const api = {
  health: () => get<{ ok: boolean }>("/api/health"),
  state: () => get<PipelineState>("/api/state"),
  devices: () => get<DevicesResponse>("/api/devices"),
  suggest: (style: string) =>
    post<{ ok: boolean }>("/api/suggest", { style }),
  keyword: (term: string) =>
    post<{ ok: boolean }>("/api/keyword", { term }),
  replay: () => post<{ ok: boolean }>("/api/replay"),
  stop: () => post<{ ok: boolean }>("/api/stop"),
  restart: () => post<{ ok: boolean }>("/api/restart"),
  settings: (patch: Record<string, unknown>) =>
    post<{ ok: boolean }>("/api/settings", patch),
  monitors: () => get<MonitorsResponse>("/api/monitors"),
  selectScreenRegion: () =>
    post<ScreenRegionResponse>("/api/screen_region/select"),
  clearScreenRegion: () =>
    post<ScreenRegionResponse>("/api/screen_region/clear"),
};

type StateEnvelope = { type: "state"; payload: PipelineState };

export type StateSocketStatus =
  | "connecting"
  | "open"
  | "closed"
  | "error";

export interface StateSocketHandlers {
  onState: (state: PipelineState) => void;
  onStatus?: (status: StateSocketStatus) => void;
}

/**
 * Auto-reconnecting WebSocket client for /ws/state.
 * Returns a disposer that closes the socket and stops reconnecting.
 */
export function connectStateSocket(
  handlers: StateSocketHandlers,
): () => void {
  let disposed = false;
  let ws: WebSocket | null = null;
  let reconnectTimer: number | null = null;

  const notify = (s: StateSocketStatus) => handlers.onStatus?.(s);

  const open = () => {
    if (disposed) return;
    notify("connecting");
    ws = new WebSocket(`${getWs()}/ws/state`);

    ws.addEventListener("open", () => notify("open"));
    ws.addEventListener("message", (ev) => {
      try {
        const msg = JSON.parse(ev.data) as StateEnvelope;
        if (msg.type === "state") handlers.onState(msg.payload);
      } catch {
        // ignore malformed frames
      }
    });
    const scheduleReconnect = () => {
      if (disposed) return;
      reconnectTimer = window.setTimeout(open, 1000);
    };
    ws.addEventListener("close", () => {
      notify("closed");
      scheduleReconnect();
    });
    ws.addEventListener("error", () => {
      notify("error");
    });
  };

  open();

  return () => {
    disposed = true;
    if (reconnectTimer !== null) window.clearTimeout(reconnectTimer);
    ws?.close();
  };
}
