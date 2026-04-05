import asyncio
import logging

import spacy

from sasayaki.config import Config

logger = logging.getLogger(__name__)


class EntityExtractor:
    """Extracts named entities from Japanese text using GiNZA."""

    def __init__(self, config: Config):
        self.config = config
        logger.info("Loading GiNZA model...")
        self.nlp = spacy.load(
            "ja_ginza",
            config={"components": {"compound_splitter": {"split_mode": "C"}}},
        )
        logger.info("GiNZA model loaded")
        self._seen: set[str] = set()

    async def extract(self, text: str) -> list[str]:
        """Extract unique entity terms not yet seen in this session."""
        loop = asyncio.get_event_loop()
        doc = await loop.run_in_executor(None, self.nlp, text)

        new_terms = []
        for ent in doc.ents:
            if ent.label_ not in self.config.ner_exclude_labels and ent.text not in self._seen:
                self._seen.add(ent.text)
                new_terms.append(ent.text)

        # Also extract notable nouns (proper nouns) not caught by NER
        for token in doc:
            if (
                token.pos_ == "PROPN"
                and len(token.text) >= 2
                and token.text not in self._seen
            ):
                self._seen.add(token.text)
                new_terms.append(token.text)

        return new_terms

    def reset(self):
        """Clear the seen set (e.g., for a new meeting)."""
        self._seen.clear()
