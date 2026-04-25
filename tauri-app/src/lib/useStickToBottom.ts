import { useCallback, useEffect, useRef, useState } from "react";

const DEFAULT_THRESHOLD_PX = 80;

/**
 * Auto-scrolls a container to the bottom while the user is near it, and
 * yields control back once the user scrolls up.
 *
 * Pass `deps` that change when new content arrives (e.g. list length or
 * last-item content). Returns a ref to attach to the scroll container,
 * a boolean indicating "following", an onScroll handler, and a jump
 * function for an explicit "jump to latest" button.
 */
export function useStickToBottom<T extends HTMLElement = HTMLDivElement>(
  deps: readonly unknown[],
  thresholdPx: number = DEFAULT_THRESHOLD_PX,
) {
  const ref = useRef<T>(null);
  const [stuck, setStuck] = useState(true);

  const onScroll = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    const distance = el.scrollHeight - el.scrollTop - el.clientHeight;
    setStuck(distance < thresholdPx);
  }, [thresholdPx]);

  useEffect(() => {
    if (!stuck) return;
    const el = ref.current;
    if (!el) return;
    el.scrollTop = el.scrollHeight;
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [stuck, ...deps]);

  const jumpToBottom = useCallback(() => {
    const el = ref.current;
    if (!el) return;
    el.scrollTo({ top: el.scrollHeight, behavior: "smooth" });
    setStuck(true);
  }, []);

  return { ref, stuck, onScroll, jumpToBottom };
}
