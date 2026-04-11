import logging
import re

from sasayaki.config import Config
from sasayaki.llm.client import LLMClient
from sasayaki.types import TranscriptEvent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは会話アシスタント「ささやき女将」です。
以下の【会話の文脈】を踏まえ、ユーザー（自分）が次に発言すべき返答を3つ提示してください。
選択肢は簡潔な口語体で、そのまま読み上げられる形にしてください。

【応答スタイル】
{style_instruction}

各選択肢は番号付きで出力してください。余計な説明は不要です。"""

RESPONSE_STYLES = {
    "深堀り": "相手の発言の核心に迫る質問や、具体的な詳細を引き出す深堀り質問をする",
    "褒める": "相手の発言や考え方の良い点を具体的に褒め、ポジティブなフィードバックを返す",
    "批判的": "相手の発言の論理的な弱点やリスクを冷静に指摘し、建設的な反論を提示する",
    "矛盾指摘": "相手の発言内の矛盾点や、以前の発言との食い違いを丁寧に指摘する",
    "よいしょ": "相手を持ち上げつつ、気持ちよく話を続けてもらえるような相槌や賞賛を返す",
    "共感": "相手の感情や立場に寄り添い、理解と共感を示す温かい返答をする",
    "まとめる": "ここまでの議論を整理し、要点をまとめて確認する返答をする",
    "話題転換": "自然な流れで別の切り口や新しいトピックに話を展開する返答をする",
    "具体例を求める": "相手の主張を裏付ける具体的な事例やデータを求める質問をする",
    "ボケる": "場の空気を和ませるユーモアや、あえてとぼけた返答で笑いを誘う",
}


class ResponseSuggester:
    """Generates response suggestions using LLM."""

    def __init__(self, config: Config, client: LLMClient):
        self.config = config
        self._client = client

    async def suggest(
        self,
        transcripts: list[TranscriptEvent],
        style: str = "深堀り",
    ) -> list[str]:
        """Generate 3 suggestions based on conversation context and style."""
        if not transcripts:
            return []

        style_instruction = RESPONSE_STYLES.get(
            style, RESPONSE_STYLES["深堀り"]
        )
        system_prompt = SYSTEM_PROMPT.format(
            style_instruction=style_instruction
        )

        context = self._build_context(transcripts)
        prompt = f"【会話の文脈】\n{context}"

        try:
            response = await self._client.chat(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt},
                ],
                temperature=0.7,
                max_tokens=512,
            )
        except Exception:
            logger.exception("LLM request failed")
            return []

        return self._parse_suggestions(response.content)

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

