import { Loader2 } from "lucide-react";

import { StyleButton } from "@/components/StyleButton";
import { api } from "@/lib/api";
import type { PipelineState, StyleKey } from "@/lib/types";
import { STYLE_KEYS } from "@/lib/types";
import { cn } from "@/lib/utils";

interface Props {
  state: PipelineState;
}

export function SuggestionsPanel({ state }: Props) {
  const onClick = (s: StyleKey) => {
    api.suggest(s).catch(() => {
      // Toast in P5.
    });
  };

  const hasStyleRow =
    state.suggesting || state.suggestion_style.length > 0;

  return (
    <section className="flex h-full min-h-0 flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3 py-2">
        <h2 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
          応答候補
        </h2>
        {hasStyleRow && (
          <span
            className={cn(
              "flex items-center gap-1.5 font-mono text-[10px]",
              state.suggesting
                ? "text-[color:var(--color-accent)]"
                : "text-[color:var(--color-fg-muted)]",
            )}
          >
            {state.suggesting && (
              <Loader2 className="size-3 animate-spin" />
            )}
            {state.suggestion_style || "生成中"}
          </span>
        )}
      </header>

      <div className="grid grid-cols-4 gap-1.5 border-b border-[color:var(--color-border)] p-3">
        {STYLE_KEYS.map((s) => (
          <StyleButton
            key={s}
            style={s}
            active={state.suggestion_style === s}
            disabled={state.suggesting}
            onClick={onClick}
          />
        ))}
      </div>

      <div className="flex-1 min-h-0 overflow-y-auto p-4">
        {state.suggestions.length === 0 ? (
          <div className="pt-12 text-center text-[13px] text-[color:var(--color-fg-subtle)]">
            {state.suggesting
              ? "生成中…"
              : "スタイルを選ぶか、ターンテイキング検出を待つ"}
          </div>
        ) : (
          <ol className="space-y-3">
            {state.suggestions.map((s, i) => (
              <li
                key={i}
                className="grid grid-cols-[1.25rem_1fr] gap-2 text-[13px] leading-relaxed"
              >
                <span className="font-mono text-[color:var(--color-accent)]">
                  {i + 1}.
                </span>
                <span>{s}</span>
              </li>
            ))}
          </ol>
        )}
      </div>
    </section>
  );
}
