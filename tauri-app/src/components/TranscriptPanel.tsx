import { useEffect, useRef } from "react";

import { ChatBubble } from "@/components/ChatBubble";
import type { TranscriptEvent } from "@/lib/types";

interface Props {
  transcripts: TranscriptEvent[];
}

export function TranscriptPanel({ transcripts }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const el = scrollRef.current;
    if (!el) return;
    // Stick to bottom if the user hasn't scrolled up meaningfully.
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    if (distanceFromBottom < 120) {
      el.scrollTop = el.scrollHeight;
    }
  }, [transcripts.length, transcripts[transcripts.length - 1]?.text]);

  return (
    <section className="flex h-full flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3 py-2">
        <h2 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
          文字起こし
        </h2>
        <span className="font-mono text-[10px] text-[color:var(--color-fg-subtle)]">
          {transcripts.length}
        </span>
      </header>
      <div
        ref={scrollRef}
        className="flex-1 space-y-1.5 overflow-y-auto px-3 py-3"
      >
        {transcripts.length === 0 ? (
          <div className="pt-12 text-center text-[13px] text-[color:var(--color-fg-subtle)]">
            音声を待機中…
          </div>
        ) : (
          transcripts.map((t, i) => (
            <ChatBubble
              key={`${t.source}-${t.timestamp}-${i}`}
              evt={t}
            />
          ))
        )}
      </div>
    </section>
  );
}
