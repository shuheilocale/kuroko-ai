import logging
import re
import time

import ollama

from sasayaki.config import Config
from sasayaki.types import PartnerProfile, ProfileFact

logger = logging.getLogger(__name__)

PROFILE_EXTRACT_PROMPT = """\
あなたは会話分析の専門家です。以下の会話から、「相手」について新たに判明した個人情報・特徴を抽出してください。

【既知のプロフィール】
{existing_profile}

【ルール】
- 「相手」（systemスピーカー）についてのみ抽出する。「自分」（micスピーカー）の情報は無視する。
- 既知のプロフィールと重複する情報は出力しない。
- 各事実を1行ずつ、「カテゴリ|内容」の形式で出力する。
- カテゴリ例: 名前, 仕事, 役職, 会社, スキル, 趣味, 好きな食べ物, 家族, 出身, 学歴, 性格, 価値観, 経歴, その他
- 該当する新情報がなければ「なし」と出力する。
- 推測ではなく、会話から明確に読み取れる情報のみ抽出する。"""

SUMMARY_PROMPT = """\
以下のプロフィール情報から、この人物を1〜2文で簡潔に紹介してください。余計な前置きは不要です。"""


class ProfileExtractor:
    """Extracts profile information about the conversation partner using LLM."""

    def __init__(self, config: Config):
        self.config = config
        self._client = ollama.AsyncClient()

    async def extract(
        self, new_text: str, existing_profile: PartnerProfile
    ) -> list[ProfileFact]:
        if len(new_text.strip()) < 10:
            return []

        existing_str = self._format_existing(existing_profile)
        system_prompt = PROFILE_EXTRACT_PROMPT.format(
            existing_profile=existing_str or "（なし）"
        )

        try:
            response = await self._client.chat(
                model=self.config.ollama_model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": new_text},
                ],
                options={"temperature": 0.0, "num_predict": 300},
                think=False,
            )
        except Exception:
            logger.exception("Profile extraction failed")
            return []

        msg = response["message"]
        content = getattr(msg, "content", "") or msg.get("content", "")

        if not content or "なし" in content:
            return []

        return self._parse_facts(content)

    async def generate_summary(self, profile: PartnerProfile) -> str:
        if not profile.facts:
            return ""

        facts_text = self._format_existing(profile)
        try:
            response = await self._client.chat(
                model=self.config.ollama_model,
                messages=[
                    {"role": "system", "content": SUMMARY_PROMPT},
                    {"role": "user", "content": facts_text},
                ],
                options={"temperature": 0.3, "num_predict": 150},
                think=False,
            )
        except Exception:
            logger.exception("Profile summary generation failed")
            return profile.summary

        msg = response["message"]
        return getattr(msg, "content", "") or msg.get("content", "") or ""

    def _format_existing(self, profile: PartnerProfile) -> str:
        lines = []
        if profile.name:
            lines.append(f"名前: {profile.name}")
        for fact in profile.facts:
            lines.append(f"{fact.category}: {fact.content}")
        return "\n".join(lines)

    def _parse_facts(self, content: str) -> list[ProfileFact]:
        facts = []
        now = time.monotonic()
        for line in content.strip().split("\n"):
            line = line.strip()
            if not line or "なし" in line:
                continue
            # Match "カテゴリ|内容" or "カテゴリ：内容"
            match = re.match(r"^(.+?)\s*[|｜]\s*(.+)$", line)
            if match:
                category = match.group(1).strip().strip("・-– ")
                fact_content = match.group(2).strip()
                if category and fact_content:
                    facts.append(ProfileFact(
                        category=category,
                        content=fact_content,
                        timestamp=now,
                    ))
        return facts
