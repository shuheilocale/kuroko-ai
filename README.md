# ささやき女将 (Sasayaki Okami) — AI Meeting Assistant

リアルタイム音声認識・ターンテイキング予測・音声合成を活用した会議支援ツール。会話の文字起こし、キーワード解説、相手プロファイル自動構築を行い、**相手の話が終わるタイミングを自動検出して、次に言うべきことをおばあちゃん声でささやいてくれます。**

**完全ローカル動作** — 音声認識 (mlx-whisper)、LLM (Ollama)、ターンテイキング予測 (MaAI)、音声合成 (OmniVoice)、表情分析 (MediaPipe) のすべてがローカルマシン上で動作します。クラウド API やサブスクリプションは不要です。キーワード解説で Wikipedia API を利用しますが、オフライン時は自動的にローカル LLM にフォールバックするため、**ネットワーク接続なしでも全機能が動作します。**（初回のみモデルダウンロードにネットワークが必要です）

## 機能

- **リアルタイム文字起こし** — システム音声（相手の声）とマイク（自分の声）を同時に認識
- **ターンテイキング予測** — MaAI (Voice Activity Projection) で相手の発話終了タイミングをリアルタイム予測
- **自動応答候補生成 & TTS ささやき** — ターン交代を検出すると LLM で応答候補を生成し、OmniVoice で耳元にささやく
- **手動応答候補生成** — 12種類のスタイルボタン（深堀り、褒める、知識でマウント等）で任意タイミングでも生成可能
- **キーワード自動抽出・解説** — 会話中の専門用語を検出し、Wikipedia / LLM で解説
- **相手プロフィール構築** — 会話から名前・仕事・趣味・スキルなどを自動的に抽出・蓄積
- **表情分析** — MediaPipe で相手の表情（喜び・驚き・困惑）、うなずき、表情変化を検出
- **完全ローカル & オフライン対応** — すべての AI 処理がローカルで完結。プライバシーセンシティブな会議でも安心
- **Web UI** — NiceGUI によるブラウザベース UI（localhost:7860）

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                  Audio Capture (sounddevice, 16kHz)              │
│       System Audio (BlackHole 2ch)    Mic (MacBook Pro Mic)     │
└──────────────┬─────────────────────────────┬────────────────────┘
               │                             │
               ▼                             ▼
         ┌──────────┐                  ┌──────────┐
         │ Tee Queue │                  │ Tee Queue │
         └──┬────┬──┘                  └──┬────┬──┘
            │    │                        │    │
            ▼    ▼                        ▼    ▼
     ┌──────┐  ┌──────────────────────────────────┐
     │ VAD  │  │      MaAI Turn-Taking (VAP)      │
     │Silero│  │ 512→160 sample resampling → Maai  │
     └──┬───┘  │ p_now / p_future prediction      │
        │      └──────────────┬───────────────────┘
        ▼                     │
  ┌───────────┐               │ p_now > threshold?
  │    ASR    │               ▼
  │mlx-whisper│        ┌─────────────┐
  │ (Japanese)│        │ Auto-Suggest │
  └─────┬─────┘        │ + TTS Whisper│
        │              └──────┬──────┘
        ▼                     │
  ┌─────────────┐             │
  │ Transcripts │             │
  └──┬──┬──┬────┘             ▼
     │  │  │          ┌──────────────┐
     │  │  │          │  OmniVoice   │
     │  │  │          │ TTS (24kHz)  │
     │  │  │          │  → resample  │
     │  │  │          │  → headphone │
     │  │  │          └──────────────┘
     ▼  ▼  ▼
  ┌──────────────────────────────────┐
  │         LLM (Ollama)             │
  │  ┌──────────┐ ┌───────────────┐  │
  │  │ Keyword  │ │   Profile     │  │
  │  │Extraction│ │  Extraction   │  │
  │  └──────────┘ └───────────────┘  │
  └──────────────────────────────────┘
     │  │  │
     ▼  ▼  ▼
  ┌──────────────────────────────────┐
  │    Screen Capture (mss)          │
  │    → MediaPipe FaceLandmarker    │
  │    → Emotion / Nod Detection     │
  └──────────────────────────────────┘
     │
     ▼
  ┌──────────────────────────────────┐
  │      NiceGUI Web UI              │
  │      http://127.0.0.1:7860       │
  │                                  │
  │  ┌──────────────┬─────────────┐  │
  │  │  文字起こし  │  応答候補   │  │
  │  │  (transcript)│ (suggestions│  │
  │  │              │  + auto TTS)│  │
  │  ├──────┬───────┴──┬──────────┤  │
  │  │ KW   │ Profile  │ 表情分析 │  │
  │  └──────┴──────────┴──────────┘  │
  └──────────────────────────────────┘
```

### ディレクトリ構成

```
src/sasayaki/
├── main.py                    # エントリーポイント
├── config.py                  # Config dataclass（全設定値）
├── types.py                   # 共有データ型（イベント・状態）
├── audio/
│   ├── capture.py             # sounddevice による音声キャプチャ
│   ├── vad.py                 # Silero VAD による音声区間検出
│   └── turn_taking.py         # MaAI ラッパー（ターンテイキング予測）
├── asr/
│   └── transcriber.py         # mlx-whisper によるリアルタイム文字起こし
├── llm/
│   ├── client.py              # LLM クライアント（Ollama / llama.cpp）
│   ├── profiler.py            # 会話相手のプロフィール抽出
│   └── suggester.py           # 応答候補生成（12スタイル）
├── nlp/
│   ├── keyword_extractor.py   # LLM によるキーワード抽出
│   └── wiki.py                # Wikipedia 検索（LRU キャッシュ付き）
├── tts/
│   └── whisper_playback.py    # OmniVoice TTS + sounddevice 再生
├── vision/
│   ├── face_analyzer.py       # MediaPipe 表情分析・うなずき検出
│   └── screen_capture.py      # mss による画面キャプチャ
├── pipeline/
│   └── orchestrator.py        # 全パイプラインのオーケストレーション
└── ui/
    └── app.py                 # NiceGUI Web UI
```

## 前提条件

- **macOS** (Apple Silicon 推奨 — mlx-whisper は Apple Silicon に最適化)
- **Python 3.12 以上**
- **Ollama** (ローカル LLM サーバー)
- **BlackHole 2ch** (システム音声キャプチャ用仮想オーディオドライバ)

## セットアップ

### 1. リポジトリのクローン

```bash
git clone https://github.com/shuheilocale/kuroko-ai.git
cd kuroko-ai
```

### 2. uv のインストール（未導入の場合）

[uv](https://docs.astral.sh/uv/) は高速な Python パッケージマネージャです。

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

インストール後、シェルを再起動するか `source ~/.zshrc` を実行してください。

### 3. Python 環境の構築

```bash
# Python 3.12 の仮想環境を作成
uv venv --python 3.12

# 仮想環境を有効化
source .venv/bin/activate

# 全依存パッケージをインストール（maai, omnivoice 含む）
uv sync
```

> **Note:** 初回の `uv sync` では PyTorch, Transformers, MediaPipe 等の大きなパッケージがダウンロードされるため、数分かかる場合があります。

### 4. Ollama のセットアップ

[Ollama](https://ollama.com) はローカルで LLM を動かすためのツールです。キーワード抽出・プロフィール構築・応答候補生成に使用します。

#### 4-1. Ollama のインストール

```bash
brew install ollama
```

#### 4-2. Ollama サーバーの起動

```bash
ollama serve
```

> **Tip:** バックグラウンドで起動したい場合は `brew services start ollama` を使ってください。

#### 4-3. LLM モデルのダウンロード

別のターミナルを開いて、使用するモデルをダウンロードします。

```bash
# デフォルトモデル
ollama pull gemma4:e2b
```

他のモデルも使用可能です（UI のドロップダウンから切り替えられます）。

#### 4-4. 動作確認

```bash
ollama list
```

`gemma4:e2b` が表示されれば OK です。

### 5. BlackHole（仮想オーディオドライバ）のセットアップ

BlackHole は相手の音声（Zoom、Teams 等のシステム音声）をアプリでキャプチャするために必要な仮想オーディオドライバです。

#### 5-1. インストール

```bash
brew install blackhole-2ch
```

#### 5-2. macOS Audio MIDI 設定

**重要:** BlackHole をインストールしただけでは、システム音声をキャプチャできません。以下の設定が必要です。

1. **Audio MIDI 設定** アプリを開く
   - Spotlight（`Cmd + Space`）で「Audio MIDI 設定」と検索
   - または `/Applications/Utilities/Audio MIDI Setup.app` を直接開く

2. **複数出力デバイスを作成**
   - 左下の **「+」** ボタンをクリック
   - **「複数出力デバイスを作成」** を選択

3. **デバイスを選択**（以下の2つにチェック）
   - 使用中のスピーカーまたはヘッドフォン
   - **BlackHole 2ch**

4. **システム出力を変更**
   - **システム環境設定 → サウンド → 出力** を開く
   - 作成した**複数出力デバイス**を選択

これにより、システム音声がスピーカーと BlackHole の両方に送られ、アプリがシステム音声をキャプチャできるようになります。

#### 5-3. 動作確認

```bash
uv run python scripts/check_audio_devices.py
```

出力に `BlackHole 2ch` が入力デバイスとして表示されれば OK です。

### 6. MediaPipe モデルのダウンロード（表情分析用）

表情分析機能を使用する場合、MediaPipe の FaceLandmarker モデルが必要です。

```bash
mkdir -p models
curl -L -o models/face_landmarker.task \
  https://storage.googleapis.com/mediapipe-models/face_landmarker/face_landmarker/float16/latest/face_landmarker.task
```

### 7. 起動

```bash
uv run sasayaki
```

ブラウザで **http://127.0.0.1:7860** を開きます。

> **Note:** 初回起動時、MaAI と OmniVoice のモデルが HuggingFace から自動ダウンロードされます。数分かかる場合があります。

## 使い方

### 画面構成

起動すると以下のレイアウトの Web UI が表示されます。

```
┌─────────────────────────────────────────────────────────┐
│ ささやき女将  [Sys: ██] [Mic: ██] [TT: ██ 0.45 ██ 0.32]│ ← ヘッダー
├─────────────────────────────────────────────────────────┤
│ ▶ 設定 (クリックで展開)                                 │ ← 折りたたみ設定
├──────────────────────────┬──────────────────────────────┤
│                          │                              │
│   文字起こし             │   応答候補                   │
│                          │   [自動ささやきモード: 深堀り]│
│   18:30:45 こんにちは    │   [深堀り][褒める][批判的]... │
│        はい、こんにちは  │                              │
│   18:30:52 今日は...     │   1. ○○についてもう少し...   │
│                          │   2. それは△△ということ...   │
│                          │   3. 具体的には...           │
│                          │                              │
├────────┬─────────┬───────┴──────────────────────────────┤
│ KW     │ Profile │ 表情分析                             │
│ ─────  │ ─────── │ [喜 ██][驚 ██][困 ██][平 ██]        │
│ 用語1  │ 名前    │ [顔画像] 検出中 — 喜び              │
│  説明  │  山田   │ うなずき: 3                          │
│ 用語2  │ 仕事    │ 表情変化                             │
│  説明  │  エンジ │ 18:30:50 平常→喜び                  │
└────────┴─────────┴──────────────────────────────────────┘
```

**上段（メイン）:**

| エリア | 説明 |
|--------|------|
| 文字起こし | リアルタイムの会話テキスト。紫 = 相手、青 = 自分。自動スクロール |
| 応答候補 | 自動 or 手動で生成された返答案。自動ささやきモードの選択も可能 |

**下段（サブ情報）:**

| エリア | 説明 |
|--------|------|
| キーワード | 自動抽出された用語とその解説。手動検索も可能 |
| プロフィール | 会話から自動構築された相手の情報（カテゴリ別） |
| 表情分析 | 感情バー、顔サムネイル、うなずきカウント、表情変化ログ |

### 設定パネル

ヘッダー下の **「設定」** をクリックすると展開されます。

| 設定項目 | 説明 |
|----------|------|
| System Audio | 相手の音声を取り込むデバイス（通常は `BlackHole 2ch`） |
| Mic | 自分のマイクデバイス |
| Screen | 表情分析用のスクリーンキャプチャ対象モニター |
| LLM / Model | LLM バックエンド（Ollama or llama.cpp）とモデル選択 |
| Turn-Taking | MaAI ターンテイキング予測の ON/OFF |
| TTS | OmniVoice 音声ささやきの ON/OFF |
| TTS出力先 | ささやき音声の出力デバイス（ヘッドフォン推奨） |

設定を変更したら **「適用」** ボタンで反映されます。

### 応答候補

**手動モード:** 12種類のスタイルボタンから好みを選んでクリック。

| ボタン | 用途 |
|--------|------|
| 深堀り | 相手の発言の核心に迫る質問 |
| 褒める | ポジティブなフィードバック |
| 批判的 | 論理的な弱点の指摘 |
| 矛盾指摘 | 発言内の矛盾の指摘 |
| よいしょ | 相手を持ち上げる |
| 共感 | 感情に寄り添う |
| まとめる | 議論の整理 |
| 話題転換 | 新しいトピックへ |
| 具体例を求める | 事例・データを求める |
| ボケる | ユーモアで場を和ませる |
| 謝罪 | 誠意ある謝罪 |
| 知識でマウント | 専門知識を披露 |

**自動モード:** ターンテイキング予測（MaAI）が「相手が話し終わりそう」と判断すると、選択中のスタイルで自動生成し、OmniVoice でささやきます。モード表示:
- **オレンジ「自動」バッジ** — 自動トリガーによる生成
- **青「手動」バッジ** — ボタン押下による生成

### TTS ささやき出力先の設定

ささやき音声が BlackHole に流れてしまうと、相手の声として文字起こしされてしまいます。**TTS出力先を「外部ヘッドフォン」などの専用デバイスに設定してください。**

> **Note:** TTS 再生中〜再生後2秒間はシステム音声の文字起こしを自動抑制する機能が組み込まれていますが、出力先を分離するのが最も確実です。

## 設定リファレンス

主な設定は `src/sasayaki/config.py` の `Config` クラスで管理されています。

### 音声・認識

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `system_audio_device` | `"BlackHole 2ch"` | システム音声デバイス名 |
| `mic_device` | `"MacBook Proのマイク"` | マイクデバイス名 |
| `sample_rate` | `16000` | サンプルレート (Hz) |
| `vad_threshold` | `0.5` | 音声検出の閾値 |
| `vad_min_silence_ms` | `700` | 無音判定までの最短時間 (ms) |
| `whisper_model` | `"mlx-community/whisper-large-v3-turbo"` | Whisper モデル |
| `whisper_language` | `"ja"` | 音声認識の言語 |

### LLM

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `llm_backend` | `"ollama"` | `"ollama"` or `"llamacpp"` |
| `ollama_model` | `"gemma4:e2b"` | Ollama モデル名 |
| `llamacpp_url` | `"http://127.0.0.1:8080"` | llama.cpp サーバー URL |
| `llm_context_turns` | `5` | 応答候補生成時の文脈ターン数 |
| `llm_debounce_sec` | `1.5` | プロフィール抽出のデバウンス (秒) |

### ターンテイキング (MaAI)

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `maai_enabled` | `True` | ターンテイキング予測の有効/無効 |
| `maai_frame_rate` | `10` | 予測の Hz (5/10/20) |
| `maai_device` | `"cpu"` | 推論デバイス |
| `turn_taking_threshold` | `0.6` | p_now がこの値を超えたらトリガー |
| `turn_taking_cooldown_sec` | `8.0` | 自動トリガーの最小間隔 (秒) |
| `turn_taking_min_transcripts` | `3` | 最低発話数（少なすぎると誤トリガー） |
| `auto_suggest_style` | `"深堀り"` | 自動ささやき時のスタイル |

### TTS (OmniVoice)

| 設定 | デフォルト | 説明 |
|------|-----------|------|
| `tts_enabled` | `True` | TTS ささやきの有効/無効 |
| `tts_backend` | `"omnivoice"` | TTS エンジン |
| `tts_omnivoice_model` | `"k2-fsa/OmniVoice"` | OmniVoice モデル |
| `tts_omnivoice_instruct` | `"female, elderly, whisper, very low pitch"` | 声質の指定 |
| `tts_omnivoice_speed` | `1.1` | 発話速度 |
| `tts_output_device` | `""` | 出力デバイス名（空=デフォルト） |
| `tts_volume` | `0.6` | 音量 (0.0〜1.0) |

**`tts_omnivoice_instruct` で使用可能なキーワード:**

- 性別: `male`, `female`
- 年齢: `child`, `teenager`, `young adult`, `middle-aged`, `elderly`
- ピッチ: `very low pitch`, `low pitch`, `moderate pitch`, `high pitch`, `very high pitch`
- スタイル: `whisper`
- アクセント: `american accent`, `british accent`, `japanese accent` 等

## トラブルシューティング

### BlackHole が見つからない

```bash
uv run python scripts/check_audio_devices.py
```

`BlackHole 2ch` が入力デバイスとして表示されない場合:
- `brew install blackhole-2ch` を再実行
- Audio MIDI 設定で複数出力デバイスを再作成
- macOS を再起動

### Ollama に接続できない

```bash
# Ollama が起動しているか確認
ollama list

# 起動していない場合
ollama serve
```

### モデルが見つからない

```bash
ollama pull gemma4:e2b
```

### TTS がプチプチ音になる

TTS 出力先のデバイスのサンプルレートと OmniVoice の出力 (24kHz) が不一致の場合に発生します。`resampy` による自動リサンプリングが組み込まれていますが、改善しない場合は `tts_output_device` を別のデバイスに変更してみてください。

### ささやき音声が文字起こしされる

TTS 音声が BlackHole 経由でシステム音声として拾われています。対策:
1. **TTS出力先をヘッドフォンに直接指定**（設定パネルの「TTS出力先」で変更）
2. TTS 再生中の transcript 自動抑制が組み込み済み（2秒間のクールダウン）

### ポートが使用中

```bash
lsof -ti:7860 | xargs kill -9
uv run sasayaki
```

### MaAI / OmniVoice モデルのダウンロードが止まる

初回起動時に HuggingFace からモデルがダウンロードされます。ネットワーク環境を確認してください。キャッシュは `~/.cache/huggingface/` に保存されるため、2回目以降は高速に起動します。

## 開発

```bash
# 開発用依存関係のインストール
uv pip install -e ".[dev]"

# テスト
uv run pytest
```

## 技術スタック

| コンポーネント | ライブラリ | 用途 |
|---------------|-----------|------|
| 音声キャプチャ | sounddevice | マイク・システム音声の取り込み |
| 音声区間検出 (VAD) | Silero VAD | 発話区間の検出 |
| 音声認識 (ASR) | mlx-whisper | リアルタイム文字起こし (Apple Silicon 最適化) |
| ターンテイキング | MaAI (VAP) | 発話終了タイミングの予測 |
| LLM | Ollama (gemma4:e2b) | キーワード抽出・プロフィール構築・応答候補生成 |
| 音声合成 (TTS) | OmniVoice | ささやき音声の生成 (600+ 言語対応) |
| オーディオリサンプリング | resampy | TTS 出力のサンプルレート変換 |
| 表情分析 | MediaPipe | 感情検出・うなずき検出 |
| 画面キャプチャ | mss | 表情分析用のスクリーンキャプチャ |
| 知識検索 | Wikipedia API | キーワードの解説取得 |
| Web UI | NiceGUI | ブラウザベースのリアルタイム UI |
| パッケージ管理 | uv + hatchling | 依存管理・ビルド |
