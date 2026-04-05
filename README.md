# ささやき女将 (Sasayaki Okami) — AI Meeting Assistant

リアルタイム音声認識と LLM を活用した会議支援ツール。会話の文字起こし、キーワード解説、会話相手のプロファイル自動構築を行います。

## 機能

- **リアルタイム文字起こし** — システム音声（相手の声）とマイク（自分の声）を同時に認識
- **キーワード自動抽出・解説** — 会話中の専門用語や固有名詞を検出し、Wikipedia / LLM で解説
- **相手プロフィール構築** — 会話から相手の名前・仕事・趣味・スキルなどを自動的に抽出・��積
- **応答候補生成** — 相手の発言に対する返答の選択肢を LLM が提案（折りたたみ表示）
- **Web UI** — ブラウザベースの3カラムUI（NiceGUI）

## アーキテクチャ

```
Audio Capture (sounddevice)
├── System Audio (BlackHole 2ch) ─┐
└── Mic ──────────────────────────┤
                                  ↓
                        VAD (Silero VAD)
                                  ↓
                     ASR (mlx-whisper, Japanese)
                                  ↓
                    ┌─────────────┼─────────────┐
                    ↓             ↓             ↓
             Keyword         Profile       Response
             Extraction      Extraction    Suggestion
             (Ollama)        (Ollama)      (Ollama)
                    ↓             ↓             ↓
                    └─────────────┼──���──────────┘
                                  ↓
                         NiceGUI Web UI
                        (localhost:7860)
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

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

### 3. Python 環境の構築

```bash
uv venv --python 3.12
source .venv/bin/activate
uv pip install -e .
```

### 4. Ollama のセットアップ

Ollama をインストールして、使用する LLM モデルをダウンロードします。

```bash
# Ollama のインストール (https://ollama.com)
brew install ollama

# Ollama サーバーの起動
ollama serve

# モデルのダウンロード (別ターミナルで実行)
ollama pull qwen3.5:9b
```

動作確認:

```bash
uv run python scripts/test_ollama.py
```

### 5. BlackHole（仮想オーディオドライバ）のセットアップ

BlackHole は相手の音声（システム音声）をキャプチャするために必要です。

```bash
brew install blackhole-2ch
```

インストール後、macOS の **Audio MIDI 設定** で複数出力デバイスを作成します:

1. **Audio MIDI 設定**アプリを開く（Spotlight で「Audio MIDI」と検索）
2. 左下の「+」をクリック →「**複数出力デバイスを作成**」
3. 以下の2つにチェックを入れる:
   - 使用中のスピーカー/ヘッドフォン
   - **BlackHole 2ch**
4. **システム環境設定 → サウンド → 出力** で、作成した複数出力デバイスをシステムの音声出力に設定

これにより、システム音声がスピーカーと BlackHole の両方に送られ、アプリがシステム音声をキャプチャできるようになります。

動作確���:

```bash
uv run python scripts/check_audio_devices.py
```

`BlackHole 2ch` が入力デバイスとして表示されれば OK です。

### 6. 起動

```bash
uv run sasayaki
```

ブラウザで http://127.0.0.1:7860 を開きます。

## 使い方

### デバイス選択

画面上部のドロップダウンから **System Audio** と **Mic** を選択し、「適用」ボタンを押すとパイプラインが再起動します。

- **System Audio**: 相手の音声を取り込むデバイス（通常は `BlackHole 2ch`��
- **Mic**: 自分のマイクデバイス

### 画面構成

| カラム | 内容 |
|--------|------|
| 左（文字起こし） | リアルタイムの会話テキスト。紫 = 相手、青 = 自分 |
| 中央（キーワード） | 自動抽出された用語とその解説。手動検索も可能 |
| 右（プロフィール） | 会話から自動構築された相手の情報（カテゴリ別） |
| 下部（応答候補） | 折りたたみ式。相手の発言に対する返答案3つ |

### 手動キーワード検索

中央カラムの入力欄に用語を入力して Enter または「検索」ボタンで、Wikipedia / LLM による解説を取得できます。

## 設定

主��設定は `src/sasayaki/config.py` の `Config` クラスで管理されています。

| 設定 | デフォルト値 | 説明 |
|------|-------------|------|
| `system_audio_device` | `"BlackHole 2ch"` | システム音声デバイス名 |
| `mic_device` | `"MacBook Proのマイク"` | マイクデバイス名 |
| `ollama_model` | `"qwen3.5:9b"` | Ollama で使用する LLM モデル |
| `whisper_model` | `"mlx-community/whisper-large-v3-turbo"` | Whisper モデル |
| `whisper_language` | `"ja"` | 音声認識の言語 |
| `vad_threshold` | `0.5` | 音声検出の閾値 |
| `llm_debounce_sec` | `1.5` | LLM 呼び出しのデバウンス時間（秒） |
| `profile_max_facts` | `50` | プロフィールに保持する最大事実数 |

## トラブルシューティング

### BlackHole が見つからない

```bash
uv run python scripts/check_audio_devices.py
```

を実行して、BlackHole 2ch が入力デバイスとして表示されるか確認してください。表示されない場合は、BlackHole のインストールと Audio MIDI 設定を再確認してください。

### Ollama に接続できない

```bash
# Ollama が起動しているか確認
ollama list

# 起動していない場合
ollama serve
```

### モデルが見つからない

```bash
# 必要なモデルをダウンロード
ollama pull qwen3.5:9b
```

### ポートが使用中

既に別のプロセスがポート 7860 を使用している場合:

```bash
lsof -ti:7860 | xargs kill -9
uv run sasayaki
```

## 開発

```bash
# 開発用依存関係のインストール
uv pip install -e ".[dev]"

# テスト
uv run pytest
```

## 技術スタック

| コンポーネント | ライブラリ |
|---------------|-----------|
| 音声キャプチャ | sounddevice |
| 音声区間検出 (VAD) | Silero VAD |
| 音声認識 (ASR) | mlx-whisper |
| 形態素解析 / NER | spaCy + GiNZA |
| 知識検索 | Wikipedia API |
| LLM | Ollama (qwen3.5:9b) |
| Web UI | NiceGUI |
| パッケージ管理 | uv + hatchling |
