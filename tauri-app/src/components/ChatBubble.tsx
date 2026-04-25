import { motion } from "framer-motion";

import type { TranscriptEvent } from "@/lib/types";
import { cn, formatTime } from "@/lib/utils";

export function ChatBubble({ evt }: { evt: TranscriptEvent }) {
  const isMic = evt.source === "mic";
  const time = (
    <span
      className={cn(
        "shrink-0 pt-1 font-mono text-[10px] tabular-nums",
        "text-[color:var(--color-fg-subtle)]",
      )}
    >
      {formatTime(evt.timestamp)}
    </span>
  );
  const bubble = (
    <div
      className={cn(
        "max-w-[78%] rounded-md border px-3 py-1.5",
        "text-[13px] leading-relaxed",
        isMic
          ? "border-[color:var(--color-mic)]/35 bg-[color:var(--color-mic)]/15"
          : "border-[color:var(--color-system)]/35 bg-[color:var(--color-system)]/15",
        evt.is_partial && "italic opacity-70",
      )}
    >
      {evt.text}
    </div>
  );

  return (
    <motion.div
      initial={{ opacity: 0, y: 4 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.18, ease: "easeOut" }}
      className={cn(
        "flex gap-2",
        isMic ? "justify-end" : "justify-start",
      )}
    >
      {isMic ? (
        <>
          {bubble}
          {time}
        </>
      ) : (
        <>
          {time}
          {bubble}
        </>
      )}
    </motion.div>
  );
}
