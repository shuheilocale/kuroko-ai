import { useEffect, useState } from "react";

import { Header } from "@/components/Header";
import { SettingsSheet } from "@/components/SettingsSheet";
import { SuggestionsPanel } from "@/components/SuggestionsPanel";
import { TranscriptPanel } from "@/components/TranscriptPanel";
import { connectStateSocket } from "@/lib/api";
import { useAppStore } from "@/lib/store";

export default function App() {
  const state = useAppStore((s) => s.state);
  const status = useAppStore((s) => s.status);
  const setState = useAppStore((s) => s.setState);
  const setStatus = useAppStore((s) => s.setStatus);
  const [settingsOpen, setSettingsOpen] = useState(false);

  useEffect(() => {
    return connectStateSocket({ onState: setState, onStatus: setStatus });
  }, [setState, setStatus]);

  return (
    <main className="flex h-full flex-col bg-[color:var(--color-bg)]">
      <Header
        state={state}
        status={status}
        onOpenSettings={() => setSettingsOpen(true)}
      />

      <div className="grid flex-1 gap-3 overflow-hidden p-3 lg:grid-cols-[minmax(0,1.4fr)_minmax(0,1fr)]">
        <TranscriptPanel transcripts={state?.transcripts ?? []} />
        {state ? (
          <SuggestionsPanel state={state} />
        ) : (
          <PanelPlaceholder label="応答候補" />
        )}
      </div>

      <div className="grid h-[180px] shrink-0 grid-cols-3 gap-3 px-3 pb-3">
        <PanelPlaceholder label="キーワード" hint="P4 で実装" />
        <PanelPlaceholder label="相手のプロフィール" hint="P4 で実装" />
        <PanelPlaceholder label="表情分析" hint="P4 で実装" />
      </div>

      {state?.error && <ErrorBanner message={state.error} />}

      <SettingsSheet
        open={settingsOpen}
        onClose={() => setSettingsOpen(false)}
        state={state}
      />
    </main>
  );
}

function PanelPlaceholder({
  label,
  hint,
}: {
  label: string;
  hint?: string;
}) {
  return (
    <section className="flex h-full flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3 py-2">
        <h2 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
          {label}
        </h2>
      </header>
      <div className="flex flex-1 items-center justify-center text-[11px] text-[color:var(--color-fg-subtle)]">
        {hint ?? "接続中…"}
      </div>
    </section>
  );
}

function ErrorBanner({ message }: { message: string }) {
  return (
    <div
      role="alert"
      className="fixed bottom-4 left-1/2 z-30 max-w-[720px] -translate-x-1/2 rounded-md border border-[color:var(--color-danger)]/40 bg-[color:var(--color-danger)]/15 px-4 py-2 text-[12px] text-[color:var(--color-fg)]"
    >
      {message}
    </div>
  );
}
