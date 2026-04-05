import asyncio
import logging
from collections import OrderedDict

import wikipediaapi

from sasayaki.config import Config

logger = logging.getLogger(__name__)

_SENTINEL = object()


class WikiLookup:
    """Fetches Wikipedia summaries with LRU caching."""

    def __init__(self, config: Config):
        self.config = config
        self.wiki = wikipediaapi.Wikipedia(
            user_agent="SasayakiOkami/0.1 (https://github.com/sasayaki)",
            language="ja",
        )
        self._cache: OrderedDict[str, str | None] = OrderedDict()

    async def lookup(self, term: str) -> str | None:
        """Look up a term on Japanese Wikipedia. Returns first N sentences or None."""
        # Check cache
        cached = self._cache.get(term, _SENTINEL)
        if cached is not _SENTINEL:
            self._cache.move_to_end(term)
            return cached

        loop = asyncio.get_event_loop()
        try:
            result = await loop.run_in_executor(None, self._fetch, term)
        except Exception:
            logger.exception("Wikipedia lookup failed for: %s", term)
            result = None

        # Store in cache (including None for failed lookups)
        self._cache[term] = result
        if len(self._cache) > self.config.wiki_cache_size:
            self._cache.popitem(last=False)

        return result

    def _fetch(self, term: str) -> str | None:
        page = self.wiki.page(term)
        if not page.exists():
            return None

        summary = page.summary
        if not summary:
            return None

        # Extract first N sentences (split on Japanese period)
        sentences = summary.split("。")
        truncated = "。".join(sentences[: self.config.wiki_max_sentences])
        if truncated and not truncated.endswith("。"):
            truncated += "。"

        return truncated if truncated.strip() else None
