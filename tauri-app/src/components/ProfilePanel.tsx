import { Loader2 } from "lucide-react";

import type { PartnerProfile, ProfileFact } from "@/lib/types";

interface Props {
  profile: PartnerProfile;
  profiling: boolean;
}

function groupByCategory(facts: ProfileFact[]): Map<string, ProfileFact[]> {
  const grouped = new Map<string, ProfileFact[]>();
  for (const f of facts) {
    const key = f.category || "その他";
    const bucket = grouped.get(key);
    if (bucket) bucket.push(f);
    else grouped.set(key, [f]);
  }
  return grouped;
}

export function ProfilePanel({ profile, profiling }: Props) {
  const hasContent =
    profile.name || profile.summary || profile.facts.length > 0;
  const grouped = groupByCategory(profile.facts);

  return (
    <section className="flex h-full min-h-0 flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3 py-2">
        <h2 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
          相手のプロフィール
        </h2>
        {profiling && (
          <span className="flex items-center gap-1 font-mono text-[10px] text-[color:var(--color-accent)]">
            <Loader2 className="size-3 animate-spin" />
            分析中
          </span>
        )}
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-3 py-3">
        {!hasContent ? (
          <div className="pt-6 text-center text-[12px] text-[color:var(--color-fg-subtle)]">
            {profiling ? "…" : "会話から抽出中"}
          </div>
        ) : (
          <div className="space-y-3">
            {profile.name && (
              <div className="text-[14px] font-semibold text-[color:var(--color-fg)]">
                {profile.name}
              </div>
            )}
            {profile.summary && (
              <div className="text-[12px] italic leading-relaxed text-[color:var(--color-fg-muted)]">
                {profile.summary}
              </div>
            )}
            {grouped.size > 0 && (
              <ul className="space-y-2.5">
                {[...grouped.entries()].map(([category, facts]) => (
                  <li key={category}>
                    <div className="mb-0.5 text-[10px] font-semibold uppercase tracking-wider text-[color:var(--color-accent)]">
                      {category}
                    </div>
                    <ul className="space-y-1 border-l-2 border-[color:var(--color-border)] pl-2.5">
                      {facts.map((f, i) => (
                        <li
                          key={`${category}-${f.timestamp}-${i}`}
                          className="text-[12px] leading-relaxed text-[color:var(--color-fg)]"
                        >
                          {f.content}
                        </li>
                      ))}
                    </ul>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </div>
    </section>
  );
}
