import logging
import re

from sasayaki.config import Config
from sasayaki.llm.client import LLMClient
from sasayaki.types import TranscriptEvent

logger = logging.getLogger(__name__)

SYSTEM_PROMPT = """\
あなたは1on1の会話アシスタント「ささやき女将」です。
ユーザー（=「自分」）の耳元にだけ届く、こっそり助言する立場です。

【あなたが提案するのは】
ユーザー（自分）が "相手" に向かって次に発するセリフを、**3 つ** 用意します。
そのまま声に出して読める、簡潔な口語体にしてください。

【絶対に守ること】
1. 文脈の発話者ロールを取り違えない:
   - 「自分:」で始まる発言 = ユーザー本人が言った発言
   - 「相手:」で始まる発言 = 会話相手が言った発言
2. **自分の発言を相手の発言と誤読して返答しない**:
   - 例: 「自分: 僕の名前は山本です」とあった場合、提案は
     「山本さんについて教えて」のような自己への質問にしてはいけない。
     山本は自分自身であり、相手ではない。
   - 自分が述べた事実は「自分が今しがた相手に伝えた情報」として扱う。
3. 直近の **「相手:」の発言** を起点に、それへの返答を考える。
   相手の最後の発言が無い場合は、自分が話を進める形(問いかけ・補足)で構わない。
4. 相手が知らない情報を、相手が知っているかのように扱わない。

【応答スタイル】
{style_instruction}

各選択肢は番号付き(1. 2. 3.)で出力。余計な前置きや説明は書かないこと。"""

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
    "謝罪": "相手の不満や指摘を真摯に受け止め、誠意ある謝罪と改善の意思を示す返答をする",
    "知識でマウント": "相手の話題に関連する専門知識や雑学をさりげなく披露し、知的優位性を示しつつ会話をリードする返答をする",
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
        meeting = (self.config.meeting_context or "").strip()
        if meeting:
            system_prompt += (
                "\n\n【会議の前提情報】\n"
                f"{meeting}\n"
                "この前提を踏まえて自然な提案にしてください。"
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

