# sasayaki-tauri

Tauri desktop shell for ささやき女将. Hosts the React frontend and (in
packaged builds) the Python API server as a sidecar.

## Dev workflow

Two processes, two terminals:

```bash
# Terminal 1 — Python API backend (port 7861)
cd /Users/shuhei/99_private/kuroko-ai
uv run sasayaki --mode=api --port 7861

# Terminal 2 — Tauri dev window (port 1420 → WebKit)
cd /Users/shuhei/99_private/kuroko-ai/tauri-app
pnpm tauri dev
```

The frontend defaults to `http://127.0.0.1:7861` for HTTP and
`ws://127.0.0.1:7861/ws/state` for the WebSocket stream. Override via
`.env`:

```dotenv
VITE_SASAYAKI_API=http://127.0.0.1:7862
VITE_SASAYAKI_WS=ws://127.0.0.1:7862
```

## Build

```bash
pnpm build            # frontend only (dist/)
pnpm tauri build      # full desktop bundle (macOS .app + .dmg)
```

Packaged builds in P6 will bundle the Python API via PyInstaller as a
Tauri sidecar so end users do not need to run a separate process.

## Stack

- React 19 + Vite 7 + TypeScript 5.8
- Tailwind CSS v4 (tokens in `src/styles/globals.css`)
- shadcn/ui (added per-component as needed)
- Zustand (state) + Framer Motion (motion) + Lucide (icons)
- Tauri 2.10 (Rust shell)
