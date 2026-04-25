import { ScanFace } from "lucide-react";

import { EmotionBar } from "@/components/EmotionBar";
import type { FaceAnalysisState } from "@/lib/types";
import { cn, formatTime } from "@/lib/utils";

interface Props {
  face: FaceAnalysisState;
}

const EMOTION_MAP: Record<
  "joy" | "surprise" | "concern" | "neutral",
  { label: string; color: string }
> = {
  joy: { label: "喜", color: "var(--color-joy)" },
  surprise: { label: "驚", color: "var(--color-surprise)" },
  concern: { label: "困", color: "var(--color-concern)" },
  neutral: { label: "平", color: "var(--color-neutral)" },
};

export function FaceAnalysisPanel({ face }: Props) {
  const recent = face.expression_changes.slice(-4).reverse();

  return (
    <section className="flex h-full min-h-0 flex-col rounded-md border border-[color:var(--color-border)] bg-[color:var(--color-surface)]">
      <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-3 py-2">
        <h2 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
          表情分析
        </h2>
        <span className="font-mono text-[10px] text-[color:var(--color-fg-subtle)]">
          {face.fps > 0 ? `${face.fps.toFixed(1)} fps` : "—"}
        </span>
      </header>

      <div className="flex-1 min-h-0 overflow-y-auto overscroll-contain px-3 py-3">
        <div className="flex items-start gap-3">
          <FaceThumbnail face={face} />
          <div className="flex-1 space-y-1.5">
            <EmotionBar
              {...EMOTION_MAP.joy}
              value={face.joy}
              active={face.dominant_emotion === "joy"}
            />
            <EmotionBar
              {...EMOTION_MAP.surprise}
              value={face.surprise}
              active={face.dominant_emotion === "surprise"}
            />
            <EmotionBar
              {...EMOTION_MAP.concern}
              value={face.concern}
              active={face.dominant_emotion === "concern"}
            />
            <EmotionBar
              {...EMOTION_MAP.neutral}
              value={face.neutral}
              active={face.dominant_emotion === "neutral"}
            />
          </div>
        </div>

        <div className="mt-3 flex items-center gap-4 text-[11px]">
          <span className="text-[color:var(--color-fg-muted)]">
            うなずき{" "}
            <span className="font-mono text-[color:var(--color-fg)] tabular-nums">
              {face.nod_count}
            </span>
          </span>
          <span
            className={cn(
              "font-mono",
              face.nodding
                ? "text-[color:var(--color-accent)]"
                : "text-[color:var(--color-fg-subtle)]",
            )}
          >
            {face.nodding ? "● nodding" : "○"}
          </span>
        </div>

        {recent.length > 0 && (
          <div className="mt-3 border-t border-[color:var(--color-border)]/60 pt-2.5">
            <div className="mb-1 text-[10px] uppercase tracking-wider text-[color:var(--color-fg-muted)]">
              変化
            </div>
            <ul className="space-y-1">
              {recent.map((e, i) => (
                <li
                  key={`${e.timestamp}-${i}`}
                  className="flex gap-2 text-[11px] leading-tight"
                >
                  <span className="shrink-0 font-mono tabular-nums text-[color:var(--color-fg-subtle)]">
                    {formatTime(e.timestamp)}
                  </span>
                  <span className="text-[color:var(--color-fg-muted)]">
                    {e.detail}
                  </span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
    </section>
  );
}

function FaceThumbnail({ face }: { face: FaceAnalysisState }) {
  if (face.face_image_base64) {
    return (
      <img
        src={`data:image/jpeg;base64,${face.face_image_base64}`}
        alt="検出された顔"
        className="size-14 shrink-0 rounded-md border border-[color:var(--color-border)] object-cover"
      />
    );
  }
  return (
    <div
      aria-label={face.detected ? "顔検出中" : "顔未検出"}
      className={cn(
        "flex size-14 shrink-0 items-center justify-center rounded-md border",
        face.detected
          ? "border-[color:var(--color-accent)]/50 text-[color:var(--color-accent)]"
          : "border-[color:var(--color-border)] text-[color:var(--color-fg-subtle)]",
      )}
    >
      <ScanFace className="size-5" />
    </div>
  );
}
