import { useState } from "react";
import { Loader2, Search } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { api } from "@/lib/api";
import type { EntityEvent } from "@/lib/types";

interface Props {
  entities: EntityEvent[];
}

export function KeywordsPanel({ entities }: Props) {
  const [term, setTerm] = useState("");
  const [submitting, setSubmitting] = useState(false);

  const submit = async () => {
    const t = term.trim();
    if (!t) return;
    setSubmitting(true);
    try {
      await api.keyword(t);
      setTerm("");
    } catch {
      // Toast in P5.
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <section className="flex h-full min-h-0 flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3 py-2">
        <h2 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
          キーワード
        </h2>
        <span className="font-mono text-[10px] text-[color:var(--color-fg-subtle)]">
          {entities.length}
        </span>
      </header>

      <form
        onSubmit={(e) => {
          e.preventDefault();
          submit();
        }}
        className="flex items-center gap-1.5 border-b border-[color:var(--color-border)] px-3 py-2"
      >
        <Input
          value={term}
          onChange={(e) => setTerm(e.target.value)}
          placeholder="調べたい用語"
          disabled={submitting}
          className="flex-1"
        />
        <Button
          type="submit"
          variant="secondary"
          size="icon"
          disabled={submitting || term.trim().length === 0}
          aria-label="検索"
        >
          {submitting ? (
            <Loader2 className="size-3.5 animate-spin" />
          ) : (
            <Search className="size-3.5" />
          )}
        </Button>
      </form>

      <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-3 py-2.5">
        {entities.length === 0 ? (
          <div className="pt-6 text-center text-[12px] text-[color:var(--color-fg-subtle)]">
            会話から抽出 / 手動で入力
          </div>
        ) : (
          <ul className="space-y-2.5">
            {entities.map((e, i) => (
              <li
                key={`${e.term}-${e.timestamp}-${i}`}
                className="border-b border-[color:var(--color-border)]/60 pb-2 last:border-none"
              >
                <div className="mb-0.5 flex items-center gap-1.5">
                  <span className="text-[12px] font-semibold text-[color:var(--color-fg)]">
                    {e.term}
                  </span>
                  {e.loading && (
                    <Loader2 className="size-3 animate-spin text-[color:var(--color-accent)]" />
                  )}
                </div>
                <div className="text-[11.5px] leading-relaxed text-[color:var(--color-fg-muted)]">
                  {e.definition || (e.loading ? "…" : "")}
                </div>
              </li>
            ))}
          </ul>
        )}
      </div>
    </section>
  );
}
