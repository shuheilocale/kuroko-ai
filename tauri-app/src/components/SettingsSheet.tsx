import { useEffect, useState } from "react";
import { AnimatePresence, motion } from "framer-motion";
import { X } from "lucide-react";

import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Select } from "@/components/ui/select";
import { Slider } from "@/components/ui/slider";
import { Switch } from "@/components/ui/switch";
import { api } from "@/lib/api";
import type { DevicesResponse, PipelineState } from "@/lib/types";

interface Props {
  open: boolean;
  onClose: () => void;
  state: PipelineState | null;
}

type Patch = Record<string, unknown>;

export function SettingsSheet({ open, onClose, state }: Props) {
  const [devices, setDevices] = useState<DevicesResponse | null>(null);
  const [patch, setPatch] = useState<Patch>({});
  const [applying, setApplying] = useState(false);

  useEffect(() => {
    if (!open) return;
    api
      .devices()
      .then(setDevices)
      .catch(() => setDevices(null));
  }, [open]);

  useEffect(() => {
    if (!open) setPatch({});
  }, [open]);

  useEffect(() => {
    if (!open) return;
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") onClose();
    };
    window.addEventListener("keydown", onKey);
    return () => window.removeEventListener("keydown", onKey);
  }, [open, onClose]);

  const set = (k: string, v: unknown) =>
    setPatch((p) => ({ ...p, [k]: v }));

  const apply = async () => {
    if (Object.keys(patch).length === 0) {
      onClose();
      return;
    }
    setApplying(true);
    try {
      await api.settings(patch);
      onClose();
    } catch {
      // Toast in P5.
    } finally {
      setApplying(false);
    }
  };

  const inputNames = (devices?.input_devices ?? []).map((d) => d.name);
  const outputNames = (devices?.output_devices ?? []).map((d) => d.name);

  const pick = <T,>(key: string, fallback: T): T =>
    (key in patch ? patch[key] : fallback) as T;

  return (
    <AnimatePresence>
      {open && (
        <>
          <motion.div
            initial={{ opacity: 0 }}
            animate={{ opacity: 1 }}
            exit={{ opacity: 0 }}
            transition={{ duration: 0.15 }}
            className="fixed inset-0 z-40 bg-black/50"
            onClick={onClose}
          />
          <motion.aside
            role="dialog"
            aria-label="設定"
            initial={{ x: "100%" }}
            animate={{ x: 0 }}
            exit={{ x: "100%" }}
            transition={{ duration: 0.2, ease: "easeOut" }}
            className="fixed inset-y-0 right-0 z-50 flex w-[420px] flex-col border-l border-[color:var(--color-border)] bg-[color:var(--color-surface)]"
          >
            <header className="flex items-center justify-between border-b border-[color:var(--color-border)] px-4 py-3">
              <h2 className="text-sm font-medium">設定</h2>
              <Button
                variant="ghost"
                size="icon"
                onClick={onClose}
                aria-label="閉じる"
              >
                <X className="size-4" />
              </Button>
            </header>

            <div className="flex-1 space-y-6 overflow-y-auto p-4">
              <Section title="オーディオ">
                <Field label="システム音声">
                  <Select
                    value={pick(
                      "system_audio_device",
                      state?.system_device ?? "",
                    )}
                    options={inputNames}
                    onChange={(v) => set("system_audio_device", v)}
                  />
                </Field>
                <Field label="マイク">
                  <Select
                    value={pick(
                      "mic_device",
                      state?.mic_device ?? "",
                    )}
                    options={inputNames}
                    onChange={(v) => set("mic_device", v)}
                  />
                </Field>
                <Field label="TTS 出力">
                  <Select
                    value={pick("tts_output_device", "")}
                    options={["", ...outputNames]}
                    onChange={(v) => set("tts_output_device", v)}
                    placeholder="(システム既定)"
                  />
                </Field>
              </Section>

              <Section title="LLM">
                <Field label="バックエンド">
                  <Select
                    value={pick(
                      "llm_backend",
                      state?.llm_backend ?? "ollama",
                    )}
                    options={[
                      { value: "ollama", label: "Ollama" },
                      { value: "llamacpp", label: "llama.cpp" },
                    ]}
                    onChange={(v) => set("llm_backend", v)}
                  />
                </Field>
                <Field label="Ollama モデル">
                  <Input
                    value={
                      pick(
                        "ollama_model",
                        state?.ollama_model ?? "",
                      ) as string
                    }
                    placeholder="gemma4:e2b"
                    onChange={(e) =>
                      set("ollama_model", e.target.value)
                    }
                  />
                </Field>
                <Field label="llama.cpp URL">
                  <Input
                    value={
                      pick(
                        "llamacpp_url",
                        state?.llamacpp_url ?? "",
                      ) as string
                    }
                    placeholder="http://127.0.0.1:8080"
                    onChange={(e) =>
                      set("llamacpp_url", e.target.value)
                    }
                  />
                </Field>
                <Field label="コンテキストモード">
                  <Select
                    value={pick(
                      "llm_context_mode",
                      state?.llm_context_mode ?? "fixed",
                    )}
                    options={[
                      { value: "fixed", label: "固定 (直近 N 件)" },
                      {
                        value: "since_last_fire",
                        label: "動的 (前回発火以降)",
                      },
                    ]}
                    onChange={(v) => set("llm_context_mode", v)}
                  />
                </Field>
                {pick(
                  "llm_context_mode",
                  state?.llm_context_mode ?? "fixed",
                ) === "fixed" && (
                  <SliderField
                    label="コンテキスト件数"
                    hint="直近 N ターンを LLM に渡す"
                    value={pick(
                      "llm_context_turns",
                      state?.llm_context_turns ?? 5,
                    )}
                    min={2}
                    max={15}
                    step={1}
                    format={(v) => `${v.toFixed(0)}`}
                    onChange={(v) =>
                      set("llm_context_turns", Math.round(v))
                    }
                  />
                )}
              </Section>

              <Section title="ターンテイキング">
                <ToggleRow
                  label="自動検出 (MaAI)"
                  hint="話者交替を予測して自動で提案を発火"
                  checked={pick(
                    "maai_enabled",
                    state?.turn_taking.enabled ?? true,
                  )}
                  onChange={(v) => set("maai_enabled", v)}
                />
                <SliderField
                  label="発火しきい値"
                  hint="p_now がこの値を超えたら応答候補を生成"
                  value={pick(
                    "turn_taking_threshold",
                    state?.turn_taking_threshold ?? 0.6,
                  )}
                  min={0.3}
                  max={0.9}
                  step={0.05}
                  format={(v) => v.toFixed(2)}
                  onChange={(v) => set("turn_taking_threshold", v)}
                />
                <SliderField
                  label="クールダウン (秒)"
                  hint="連続発火の抑制間隔"
                  value={pick(
                    "turn_taking_cooldown_sec",
                    state?.turn_taking_cooldown_sec ?? 8.0,
                  )}
                  min={2}
                  max={20}
                  step={1}
                  format={(v) => `${v.toFixed(0)}s`}
                  onChange={(v) =>
                    set("turn_taking_cooldown_sec", v)
                  }
                />
                <SliderField
                  label="最小文字起こし件数"
                  hint="会話開始直後の誤爆を防止"
                  value={pick(
                    "turn_taking_min_transcripts",
                    state?.turn_taking_min_transcripts ?? 3,
                  )}
                  min={1}
                  max={10}
                  step={1}
                  format={(v) => `${v.toFixed(0)}`}
                  onChange={(v) =>
                    set("turn_taking_min_transcripts", Math.round(v))
                  }
                />
                <Field label="自動発火時のスタイル">
                  <Select
                    value={pick(
                      "auto_suggest_style",
                      state?.auto_suggest_style || "深堀り",
                    )}
                    options={[
                      "深堀り",
                      "褒める",
                      "批判的",
                      "矛盾指摘",
                      "よいしょ",
                      "共感",
                      "まとめる",
                      "話題転換",
                      "具体例を求める",
                      "ボケる",
                      "謝罪",
                      "知識でマウント",
                    ]}
                    onChange={(v) => set("auto_suggest_style", v)}
                  />
                </Field>
              </Section>

              <Section title="TTS">
                <ToggleRow
                  label="ウィスパー再生"
                  hint="提案を耳元に読み上げ"
                  checked={pick("tts_enabled", true)}
                  onChange={(v) => set("tts_enabled", v)}
                />
              </Section>
            </div>

            <footer className="flex items-center justify-end gap-2 border-t border-[color:var(--color-border)] p-3">
              <Button
                variant="ghost"
                onClick={onClose}
                disabled={applying}
              >
                キャンセル
              </Button>
              <Button onClick={apply} disabled={applying}>
                {applying ? "適用中…" : "適用して再起動"}
              </Button>
            </footer>
          </motion.aside>
        </>
      )}
    </AnimatePresence>
  );
}

function Section({
  title,
  children,
}: {
  title: string;
  children: React.ReactNode;
}) {
  return (
    <section className="space-y-2.5">
      <h3 className="text-[10px] font-medium uppercase tracking-wider text-[color:var(--color-fg-muted)]">
        {title}
      </h3>
      <div className="space-y-3">{children}</div>
    </section>
  );
}

function Field({
  label,
  children,
}: {
  label: string;
  children: React.ReactNode;
}) {
  return (
    <label className="flex flex-col gap-1.5">
      <span className="text-[11px] text-[color:var(--color-fg-muted)]">
        {label}
      </span>
      {children}
    </label>
  );
}

function SliderField({
  label,
  hint,
  value,
  min,
  max,
  step,
  format,
  onChange,
}: {
  label: string;
  hint?: string;
  value: number;
  min: number;
  max: number;
  step: number;
  format: (v: number) => string;
  onChange: (v: number) => void;
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-baseline justify-between gap-2">
        <span className="text-[11px] text-[color:var(--color-fg-muted)]">
          {label}
        </span>
        <span className="font-mono text-[11px] tabular-nums text-[color:var(--color-fg)]">
          {format(value)}
        </span>
      </div>
      <Slider
        value={value}
        min={min}
        max={max}
        step={step}
        onChange={onChange}
      />
      {hint && (
        <span className="text-[10.5px] text-[color:var(--color-fg-subtle)]">
          {hint}
        </span>
      )}
    </div>
  );
}

function ToggleRow({
  label,
  hint,
  checked,
  onChange,
}: {
  label: string;
  hint?: string;
  checked: boolean;
  onChange: (v: boolean) => void;
}) {
  return (
    <div className="flex items-start justify-between gap-3">
      <div>
        <div className="text-[13px]">{label}</div>
        {hint && (
          <div className="text-[11px] text-[color:var(--color-fg-muted)]">
            {hint}
          </div>
        )}
      </div>
      <Switch checked={checked} onChange={onChange} label={label} />
    </div>
  );
}
