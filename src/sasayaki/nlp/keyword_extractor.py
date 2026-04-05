import asyncio
import logging
import re

import ollama

from sasayaki.config import Config

logger = logging.getLogger(__name__)

EXTRACT_PROMPT = """\
以下のテキストから、聞き手が意味を調べたくなるような用語を抽出してください。
対象: 専門用語、業界用語、固有名詞（組織名・制度名・人名・地名）、略語、概念名など。
除外: 日常的な一般語（「仕事」「会議」「問題」など）。

カンマ区切りで用語だけを出力してください。余計な説明は不要です。
該当する用語がなければ「なし」と出力してください。"""


class KeywordExtractor:
    """Extracts keywords using LLM for better domain-specific term detection."""

    def __init__(self, config: Config):
        self.config = config
        self._client = ollama.AsyncClient()
        self._seen: set[str] = set()

    async def extract(self, text: str) -> list[str]:
        """Extract keywords from text using LLM."""
        if len(text.strip()) < 10:
            return []

        try:
            response = await self._client.chat(
                model=self.config.ollama_model,
                messages=[
                    {"role": "system", "content": EXTRACT_PROMPT},
                    {"role": "user", "content": text},
                ],
                options={"temperature": 0.0, "num_predict": 200},
                think=False,
            )
        except Exception:
            logger.exception("LLM keyword extraction failed")
            return []

        msg = response["message"]
        content = getattr(msg, "content", "") or msg.get("content", "")

        if not content or "なし" in content:
            return []

        # Parse comma-separated terms
        terms = re.split(r"[,、，\n]", content)
        new_terms = []
        for term in terms:
            term = term.strip().strip("・-– ")
            if len(term) >= 2 and term not in self._seen:
                self._seen.add(term)
                new_terms.append(term)

        return new_terms

    def reset(self):
        self._seen.clear()
