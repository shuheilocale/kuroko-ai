from dataclasses import dataclass, field


@dataclass
class Config:
    # Audio devices
    system_audio_device: str = "BlackHole 2ch"
    mic_device: str = "MacBook Proのマイク"
    sample_rate: int = 16000

    # VAD
    vad_threshold: float = 0.5
    vad_min_silence_ms: int = 700
    vad_speech_pad_ms: int = 300
    vad_partial_flush_sec: float = 1.5

    # ASR
    whisper_model: str = "mlx-community/whisper-large-v3-turbo"
    whisper_language: str = "ja"

    # NER - GiNZA uses fine-grained labels (e.g., "Company", "Product_Other")
    # Exclude labels that are not useful for keyword explanation
    ner_exclude_labels: list[str] = field(
        default_factory=lambda: [
            "Date", "Time", "Money", "Percent", "Ordinal_Number",
            "N_Event", "N_Person", "N_Country", "N_Product", "N_Organization",
            "N_Facility", "N_Flora", "N_Location_Other", "N_Natural_Object_Other",
            "Age", "Period_Day", "Period_Month", "Period_Time", "Period_Week",
            "Period_Year", "Periodx_Other", "Time_Top_Other", "Timex_Other",
            "Phone_Number", "Email", "URL", "ID_Number", "Postal_Address",
            "Frequency", "Speed", "Temperature", "Weight", "Volume",
            "Calorie", "Intensity", "Physical_Extent", "Measurement_Other",
            "Multiplication", "Point", "Rank", "Numex_Other",
            "Unit_Other", "Money_Form", "Latitude_Longtitude",
            "Day_Of_Week", "Era",
        ]
    )

    # Wikipedia
    wiki_cache_size: int = 256
    wiki_max_sentences: int = 2

    # LLM
    llm_backend: str = "llamacpp"  # "ollama" or "llamacpp"
    ollama_model: str = "gemma4:e2b"
    llamacpp_url: str = "http://127.0.0.1:8080"
    # Free-form note about the partner / goal of this meeting that gets
    # injected into the suggester's system prompt. Set once at the
    # start of a session to anchor whispers.
    meeting_context: str = ""
    llm_context_turns: int = 5
    # "fixed": last N turns. "since_last_fire": only transcripts that
    # arrived after the last turn-taking trigger (so each suggestion
    # uses just the new exchange).
    llm_context_mode: str = "fixed"
    llm_debounce_sec: float = 1.5

    # Vision
    screen_monitor: int = 1

    # Profile
    profile_max_facts: int = 50
    profile_summary_interval: int = 5

    # Turn-Taking (MaAI)
    maai_enabled: bool = True
    maai_frame_rate: int = 10
    maai_device: str = "cpu"
    turn_taking_threshold: float = 0.6
    turn_taking_cooldown_sec: float = 8.0
    turn_taking_min_transcripts: int = 3
    auto_suggest_style: str = "深堀り"

    # Silence rescue: fire a topic-shifter when nobody speaks for a while.
    silence_rescue_enabled: bool = True
    silence_rescue_seconds: float = 6.0
    silence_rescue_style: str = "話題転換"

    # Speculative pre-fire LLM generation: start the suggestion call as
    # soon as p_now climbs to (threshold - offset) so candidates are
    # ready by the time the real fire crosses the threshold.
    speculative_pre_fire_enabled: bool = True
    speculative_pre_fire_offset: float = 0.2
    speculative_max_age_sec: float = 5.0

    # Soften the auto-fire style when the partner's dominant emotion
    # has gone "concern" — pivot to 共感 to avoid pouring oil on fire.
    adapt_style_to_emotion: bool = True
    # Play a short alert chime when the partner's dominant emotion
    # transitions to "concern". Heads-up cue so the user can adjust
    # without waiting for the next whisper cycle.
    concern_alert_enabled: bool = True
    concern_alert_cooldown_sec: float = 12.0

    # TTS (ささやき)
    tts_enabled: bool = True
    tts_backend: str = "omnivoice"
    tts_omnivoice_model: str = "k2-fsa/OmniVoice"
    tts_omnivoice_instruct: str = (
        "female, elderly, whisper, very low pitch"
    )
    tts_omnivoice_speed: float = 1.1
    # OmniVoice 推論デバイス。"auto" で MPS が使えれば MPS、なければ CPU。
    # CPU + fp32 比で MPS は約 3 倍速いので Apple Silicon では既定で MPS。
    tts_omnivoice_device: str = "auto"
    # Voice clone 用の参照音声と書き起こし。両方が指定されたとき
    # `instruct` ではなく cloning モードで合成される。
    # 推奨: 3-10 秒のクリーンな朗読(WAV/FLAC など)。
    tts_omnivoice_ref_audio: str = ""
    tts_omnivoice_ref_text: str = ""
    # クローン時のみ使う iterative decoding ステップ数。OmniVoice の既定
    # (32 前後) は重いので、品質を大きく落とさない 16 にする。
    # 上げると品質微増・遅くなる。下げると逆。
    tts_omnivoice_clone_num_step: int = 16
    # TTS 再生中(+ 直後 2 秒)の system 文字起こしを破棄するか。
    # TTS が BlackHole 等システム音声側のデバイスに漏れていると、自分の
    # ささやきが「相手の発言」として再認識される。それを避けるための
    # 抑制。TTS 出力を独立デバイス(ヘッドフォン専用)にしている場合は
    # 抑制が逆効果(本物の相手発言を捨てる)になるので False に。
    tts_loopback_suppress: bool = True
    tts_output_device: str = ""
    tts_volume: float = 0.6
    # Short attention-grabbing chime mixed in just before each whisper
    # so the user's ear catches the "incoming" cue while in conversation.
    tts_chime_enabled: bool = True

    # UI
    ui_max_transcript_messages: int = 100
    ui_max_entity_rows: int = 50
