import { useEffect, useRef, useState } from "react";
import { ArrowDown } from "lucide-react";

import { ChatBubble } from "@/components/ChatBubble";
import type { TranscriptEvent } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  transcripts: TranscriptEvent[];
}

const STICKY_THRESHOLD_PX = 80;

export function TranscriptPanel({ transcripts }: Props) {
  const scrollRef = useRef<HTMLDivElement>(null);
  // User "owns" the scroll position once they scroll up meaningfully.
  const [stickToBottom, setStickToBottom] = useState(true);

  const onScroll = () => {
    const el = scrollRef.current;
    if (!el) return;
    const distanceFromBottom =
      el.scrollHeight - el.scrollTop - el.clientHeight;
    setStickToBottom(distanceFromBottom < STICKY_THRESHOLD_PX);
  };

  useEffect(() => {
    if (!stickToBottom) return;
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
  }, [
    stickToBottom,
    transcripts.length,
    transcripts[transcripts.length - 1]?.text,
  ]);

  const scrollToBottom = () => {
    const el = scrollRef.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setStickToBottom(true);
  };

  return (
    <section className="relative flex h-full min-h-0 flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
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
        onScroll={onScroll}
        className="flex-1 min-h-0 space-y-1.5 overflow-y-auto overscroll-contain px-3 py-3"
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

      {!stickToBottom && transcripts.length > 0 && (
        <button
          type="button"
          onClick={scrollToBottom}
          className={cn(
            "absolute bottom-3 left-1/2 flex -translate-x-1/2 items-center gap-1.5",
            "rounded-full border px-2.5 py-1 text-[11px] font-medium",
            "border-[color:var(--color-accent)]",
            "bg-[color:var(--color-accent)] text-white",
            "shadow-lg hover:bg-[color:var(--color-accent-hover)]",
            "transition-colors",
          )}
        >
          <ArrowDown className="size-3" />
          最新へ
        </button>
      )}
    </section>
  );
}
