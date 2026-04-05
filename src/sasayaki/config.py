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
    ollama_model: str = "qwen3.5:9b"
    llm_context_turns: int = 5
    llm_debounce_sec: float = 1.5

    # Profile
    profile_max_facts: int = 50
    profile_summary_interval: int = 5

    # UI
    ui_max_transcript_messages: int = 100
    ui_max_entity_rows: int = 50
