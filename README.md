# ささやき女将 (Sasayaki Okami) — AI Meeting Assistant

リアルタイム音声認識・ターンテイキング予測・音声合成を活用した 1on1 会議支援ツール。会話の文字起こし、キーワード解説、相手プロファイル自動構築を行い、**相手の話が終わるタイミングを自動検出して、次に言うべきことをおばあちゃん声で耳元にささやいてくれます**(あなたにだけ聞こえる、いわば音声カンニングペーパー)。

**完全ローカル動作** — 音声認識 (mlx-whisper)、LLM (llama.cpp / Ollama)、ターンテイキング予測 (MaAI)、音声合成 (OmniVoice)、表情分析 (MediaPipe) のすべてがローカルマシン上で動作します。クラウド API やサブスクリプションは不要です。キーワード解説で Wikipedia API を利用しますが、オフライン時は自動的にローカル LLM にフォールバックするため、**ネットワーク接続なしでも全機能が動作します**(初回のみモデルダウンロードにネットワークが必要)。

## 主な機能

- **リアルタイム文字起こし** — システム音声(相手)とマイク(自分)を同時認識
- **ターンテイキング予測** — MaAI (VAP) で発話終了タイミングを予測 + **投機的先読み生成** で囁き開始までのレイテンシを最小化
- **沈黙レスキュー** — 数秒間沈黙すると別スタイルで自動発火
- **12 種スタイルの応答候補生成** — 深堀り / 褒める / 共感 / 話題転換 ほか
- **耳元ささやき (TTS)** — OmniVoice + 同じデバイスから出力するチャイム(開始・終了)
- **表情連動** — 相手が困表情になると自動で「共感」スタイルへ + 警告チャイム
- **会議事前コンテキスト** — 相手・目的・トーンを文章で入れて応答品質を底上げ
- **キーワード自動抽出 + Wiki/LLM 解説 + 手動検索**
- **相手プロフィール自動構築** — 会話から名前・属性・事実を抽出
- **完全ローカル & オフライン対応** — プライバシーセンシティブな会議でも安心

## アーキテクチャ

```text
┌──────────────────────────────────────────────┐
│  Tauri Desktop App (.app / .dmg)             │
│  ┌────────────────────────────────────────┐  │
│  │ React + Vite + TS + Tailwind +         │  │
│  │ shadcn/ui — Dark first                 │  │
│  └────────────────────────────────────────┘  │
│                  ▲                            │
│                  │ WebSocket /ws/state (10Hz) │
│                  │ HTTP /api/*                │
│                  ▼                            │
│  ┌────────────────────────────────────────┐  │
│  │ Python sidecar (FastAPI + Uvicorn)     │  │
│  │   sasayaki.api.server                  │  │
│  │   sasayaki.pipeline.orchestrator       │  │
│  └────────────────────────────────────────┘  │
└──────────────────────────────────────────────┘
              │
              ▼ pipeline 内部
  ┌──────────────────────────────────────────────────────┐
  │ Audio Capture (sounddevice, 16kHz)                    │
  │   System Audio (BlackHole 2ch) / Mic                  │
  ├──────────────────────────────────────────────────────┤
  │ Silero VAD → mlx-whisper ASR → Transcripts           │
  │ MaAI (VAP)   → p_now / p_future                      │
  │   ├─ pre-fire (≥ threshold-0.2) → speculative LLM    │
  │   └─ fire    (≥ threshold)      → consume + TTS      │
  │ OmniVoice TTS  → resample → headphones (TTS device)  │
  │ MediaPipe FaceLandmarker → emotion / nod             │
  │ LLM (llama.cpp / Ollama) → keyword / profile / sugg. │
  └──────────────────────────────────────────────────────┘
```

### ディレクトリ構成

```text
.
├── src/sasayaki/                # Python パッケージ
│   ├── main.py                  # エントリ (uvicorn を起動)
│   ├── config.py                # Config dataclass(全設定値)
│   ├── types.py                 # 共有データ型
│   ├── audio/                   # capture / vad / turn_taking
│   ├── asr/                     # mlx-whisper
│   ├── llm/                     # client (Ollama / llama.cpp) / suggester / profiler
│   ├── nlp/                     # keyword_extractor / wiki
│   ├── tts/                     # OmniVoice + chime 合成
│   ├── vision/                  # face_analyzer / screen_capture
│   ├── pipeline/                # 全体オーケストレーション
│   └── api/                     # FastAPI + Pydantic schema
└── tauri-app/                   # Tauri デスクトップシェル
    ├── src/                     # React + TS フロント
    │   ├── components/          # Header / Transcript / Suggestions / 各パネル
    │   ├── lib/                 # api / store / types / hooks
    │   └── styles/              # Tailwind v4 グローバル
    └── src-tauri/               # Rust 側 (window 設定・bundle)
```

## 前提条件

- **macOS** (Apple Silicon 推奨 — mlx-whisper は Apple Silicon 最適化)
- **Python 3.12 以上**
- **Node.js 18+ / pnpm 8+** (Tauri フロントのビルド用)
- **Rust toolchain** (rustup 経由)
- **llama.cpp** (デフォルト LLM バックエンド) もしくは **Ollama**
- **BlackHole 2ch** (システム音声キャプチャ用仮想オーディオドライバ)

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/shuheilocale/kuroko-ai.git
cd kuroko-ai
```

### 2. Python 環境

```bash
# uv 未導入なら
curl -LsSf https://astral.sh/uv/install.sh | sh

# 依存をインストール
uv sync
```

### 3. Tauri / Node 環境

```bash
# Rust toolchain
curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y

# Node + pnpm が無ければ Homebrew で
brew install node pnpm

# フロント側の依存
cd tauri-app
pnpm install
cd ..
```

### 4. LLM サーバ (デフォルトは llama.cpp)

```bash
brew install llama.cpp

# Gemma 3n E2B GGUF を取得 (Ollama の "gemma4:e2b" 実体は Gemma 3n E2B)
mkdir -p ~/models/gemma-3n-e2b
uv run python -c "
from huggingface_hub import hf_hub_download
hf_hub_download(
    repo_id='unsloth/gemma-3n-E2B-it-GGUF',
    filename='gemma-3n-E2B-it-Q4_K_M.gguf',
    local_dir='/Users/$USER/models/gemma-3n-e2b',
)"

# llama-server 起動 (デフォルトポート 8080)
llama-server -m ~/models/gemma-3n-e2b/gemma-3n-E2B-it-Q4_K_M.gguf \
  --port 8080 --ctx-size 4096 -ngl 99
```

> **Ollama を使う場合:** `brew install ollama && ollama serve` の後 `ollama pull gemma4:e2b` し、設定で「バックエンド」を Ollama に切り替えてください。

### 5. BlackHole

```bash
brew install blackhole-2ch
```

その後 **Audio MIDI 設定** で「複数出力デバイス」を作成し、スピーカー/ヘッドホン + BlackHole 2ch にチェック。システム出力を作成したデバイスに変更してください。

### 6. MediaPipe FaceLandmarker

```bash
mkdir -p models
curl -L -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
```

## 起動 (開発時)

ターミナル 3 枚:

```bash
# Terminal 1: LLM サーバ
llama-server -m ~/models/gemma-3n-e2b/gemma-3n-E2B-it-Q4_K_M.gguf \
  --port 8080 --ctx-size 4096 -ngl 99

# Terminal 2: Python API
uv run sasayaki

# Terminal 3: Tauri ウィンドウ
cd tauri-app
pnpm tauri dev
```

初回起動時、MaAI / OmniVoice / Whisper のモデルが HuggingFace から自動ダウンロードされます(数分〜十数分)。

## 使い方

### 画面構成

```text
┌──────────────────────────────────────────────────────────┐
│ ● ささやき女将  mic ▮▮  sys ▮▮  turn ▮▮ 0.42  llama.cpp:ok │ Header
├────────────────────────────────────┬─────────────────────┤
│                                     │  応答候補           │
│   文字起こし                        │  [深堀り][褒める]…   │
│   (mic = 右 / 青 / 自分)            │  1. ...             │
│   (sys = 左 / 紫 / 相手)            │  2. ...             │
│                                     │  3. ...             │
│                                     ├─────────────────────┤
│                                     │  キーワード(⌘K)     │
│                                     │  ...                │
├────────────────────────────────────┴─────────────────────┤
│ 相手のプロフィール    │   表情分析                         │
│ 名前 / 事実カテゴリ   │   joy/surprise/concern/neutral     │
└──────────────────────────────────────────────────────────┘
```

### キーボードショートカット

| キー | 動作 |
| ---- | ---- |
| `Space` | 直前の囁きを再再生(入力中はスキップ) |
| `⌘ ,` | 設定シートを開く |
| `⌘ K` | キーワード検索入力にフォーカス |
| `Esc` | 設定シートを閉じる |

### 設定シート(⌘,)

| セクション | 内容 |
| --- | --- |
| 会議コンテキスト | 相手・目的・トーンを文章で。LLM プロンプトに常駐 |
| オーディオ | システム音声 / マイク / TTS 出力デバイス |
| LLM | バックエンド (Ollama / llama.cpp) / モデル / コンテキストモード(固定 N or 前回発火以降) |
| ターンテイキング | MaAI ON/OFF / 閾値 / クールダウン / 最低件数 / 自動スタイル / 先読み生成 / 表情連動 / 困アラート |
| 沈黙レスキュー | 自動発火 ON/OFF / 沈黙時間閾値 / 沈黙時のスタイル |
| TTS | ウィスパー再生 / 開始 + 終了キュー音 |
| 画面 (表情分析) | モニター選択 / 範囲選択(macOS ネイティブドラッグ) |

設定変更は **Hot reload** が効くもの(スタイル / 閾値 / コンテキスト等)は即反映、デバイスやモデルなど Cold な変更のみパイプライン再起動を伴います。

### TTS 出力デバイスは必ずヘッドフォンへ

ささやきが BlackHole(システム音声側)に流れると相手の声として誤認識されます。**「TTS 出力デバイス」をヘッドフォンや専用デバイスに必ず指定してください**。

## ビルド (将来的な配布用)

```bash
cd tauri-app
pnpm tauri build
```

> **Note:** 本リポジトリは現時点ではローカル開発前提で、Python sidecar の自動バンドル(PyInstaller)は未実装です。配布パッケージを作る場合は別途設定が必要です。

## トラブルシューティング

### llama-server が「expected 2012, got 601」で死ぬ

Ollama 配布の GGUF(`~/.ollama/models/blobs/...`) は新しめのモデルで Ollama 独自のテンソル分割になっており、mainline の llama.cpp で読めません。**HuggingFace の公式 GGUF**(unsloth / bartowski 等)を使ってください。

### BlackHole が見えない

```bash
uv run python scripts/check_audio_devices.py
```

`BlackHole 2ch` が入力一覧に出なければ、`brew install blackhole-2ch` の再実行と Audio MIDI の複数出力デバイスを再作成してください。

### マイクを後から繋いでも UI に出ない

`/api/devices` は子プロセスで都度問い合わせるので、設定シートを **開き直す** だけで反映されます。再起動不要。

### TTS がプチプチ音

OmniVoice (24kHz) と出力デバイスのサンプルレートが合わない場合に発生。`resampy` で自動リサンプルしていますが、改善しなければ TTS 出力先を別デバイスに変更してください。

### TTS が文字起こしされる

ささやきが BlackHole に漏れています。**設定シートの「TTS 出力デバイス」をヘッドフォンに**。再生中〜2 秒間のシステム音声抑制も組み込み済みです。

### Tauri ウィンドウがドラッグできない

ネイティブタイトルバー(現在の標準設定)で全域ドラッグ可能です。一度 `pnpm tauri dev` を再起動して config を再読込してください。

## 開発

```bash
# Python テスト
uv run pytest

# 型チェック (TS)
cd tauri-app && pnpm build

# Tauri 単体ビルドチェック
cd tauri-app/src-tauri && cargo check
```

## 技術スタック

| レイヤ | ライブラリ |
| --- | --- |
| 音声キャプチャ | sounddevice (PortAudio) |
| VAD | Silero VAD |
| ASR | mlx-whisper (Apple Silicon 最適化) |
| ターンテイキング | MaAI (Voice Activity Projection) |
| LLM | llama.cpp (デフォルト) / Ollama (任意) |
| TTS | OmniVoice (k2-fsa) |
| 表情分析 | MediaPipe FaceLandmarker |
| API サーバ | FastAPI + Uvicorn + Pydantic v2 |
| デスクトップ | Tauri 2 + Rust |
| フロント | React 19 + Vite 7 + TS 5.8 + Tailwind v4 + shadcn/ui + Zustand + Framer Motion |
| パッケージ | uv (Python) + pnpm (Node) + cargo (Rust) |
