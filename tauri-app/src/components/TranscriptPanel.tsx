import { ChatBubble } from "@/components/ChatBubble";
import { JumpToLatest } from "@/components/JumpToLatest";
import type { TranscriptEvent } from "@/lib/types";
import { useStickToBottom } from "@/lib/useStickToBottom";

interface Props {
  transcripts: TranscriptEvent[];
}

export function TranscriptPanel({ transcripts }: Props) {
  const last = transcripts[transcripts.length - 1];
  const { ref, stuck, onScroll, jumpToBottom } = useStickToBottom([
    transcripts.length,
    last?.text,
    last?.is_partial,
  ]);

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
        ref={ref}
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

      {!stuck && transcripts.length > 0 && (
        <JumpToLatest onClick={jumpToBottom} />
      )}
    </section>
  );
}
