import asyncio
import logging
import re

import ollama

from sasayaki.config import Config
from sasayaki.types import TranscriptEvent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたはビジネス会議における非常に優秀なアシスタント「ささやき女将」です。
以下の【会議の文脈】を踏まえ、ユーザー（自分）が次に発言すべき最適な返答の選択肢を3つ提示してください。
選択肢は簡潔な口語体（です・ます調）で、そのまま読み上げられる形にしてください。

1. 相手の意見に同意し、前向きに議論を進める返答
2. 相手の意見に対する鋭い質問や、深掘りをする返答
3. 情報を整理し、一旦保留または持ち帰る返答

各選択肢は番号付きで出力してください。余計な説明は不要です。"""


class ResponseSuggester:
    """Generates response suggestions using a local Ollama LLM."""

    def __init__(self, config: Config):
        self.config = config
        self._client = ollama.AsyncClient()

    async def suggest(
        self, transcripts: list[TranscriptEvent]
    ) -> list[str]:
        """Generate 3 suggestions based on recent conversation context."""
        if not transcripts:
            return []

        context = self._build_context(transcripts)
        prompt = f"【会議の文脈】\n{context}"

        try:
            response = await self._client.chat(
                model=self.config.ollama_model,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt},
                ],
                options={"temperature": 0.7, "num_predict": 512},
            )
        except Exception:
            logger.exception("Ollama request failed")
            return []

        text = response["message"]["content"]
        return self._parse_suggestions(text)

    def _build_context(self, transcripts: list[TranscriptEvent]) -> str:
        recent = transcripts[-self.config.llm_context_turns * 2 :]
        lines = []
        for t in recent:
            speaker = "自分" if t.source == "mic" else "相手"
            lines.append(f"{speaker}: 「{t.text}」")
        return "\n".join(lines)

    def _parse_suggestions(self, text: str) -> list[str]:
        """Parse numbered suggestions from LLM output."""
        lines = text.strip().split("\n")
        suggestions = []
        for line in lines:
            line = line.strip()
            # Match lines starting with 1. 2. 3. or ①②③
            match = re.match(r"^(?:\d+[.．)）]|[①②③])\s*(.*)", line)
            if match:
                content = match.group(1).strip()
                if content:
                    suggestions.append(content)
        return suggestions[:3]

    async def health_check(self) -> bool:
        """Check if Ollama is running and the model is available."""
        try:
            result = await self._client.list()
            model_list = result.models if hasattr(result, "models") else result.get("models", [])
            available = [getattr(m, "model", None) or m.get("model", "") for m in model_list]
            return any(self.config.ollama_model in m for m in available)
        except Exception:
            return False
