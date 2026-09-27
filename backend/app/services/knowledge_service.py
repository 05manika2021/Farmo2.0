"""Small JSON knowledge layer for schemes, FAQ and crop advisory.

Content is loaded once from backend/app/data/*.json. Entries carry an explicit
`verification` field so the AI answer can say whether something is VERIFIED
(app-sourced or official-source) or GENERAL GUIDANCE (not a prescription).
"""
import json
import logging
from functools import lru_cache
from pathlib import Path
from typing import Optional

logger = logging.getLogger("farmo.knowledge")

DATA_DIR = Path(__file__).resolve().parent.parent / "data"

VERIFIED = "VERIFIED"
GENERAL = "GENERAL GUIDANCE"


@lru_cache(maxsize=1)
def _load(name: str) -> dict:
    path = DATA_DIR / f"{name}.json"
    try:
        with path.open(encoding="utf-8") as fh:
            return json.load(fh)
    except FileNotFoundError:
        logger.error("Knowledge file missing: %s", path)
        return {}
    except json.JSONDecodeError as e:
        logger.error("Knowledge file invalid JSON %s: %s", path, e)
        return {}


def _matches(needle: str, haystack) -> bool:
    if not needle:
        return False
    text = " ".join(haystack).lower()
    return any(token in text for token in needle.lower().split() if len(token) > 2)


class KnowledgeService:
    def get_schemes(self) -> list[dict]:
        return _load("schemes").get("schemes", [])

    def get_faq(self) -> list[dict]:
        return _load("faq").get("faq", [])

    def get_advisories(self) -> list[dict]:
        return _load("crop_advisory").get("advisories", [])

    def find_schemes(self, query: str) -> list[dict]:
        schemes = self.get_schemes()
        if not query:
            return schemes[:3]
        hits = [s for s in schemes if _matches(query, [
            s.get("name", ""), s.get("category", ""), s.get("description", ""),
            s.get("eligibility_summary", ""), s.get("benefits", ""),
        ])]
        return hits or schemes[:3]

    def find_faq(self, query: str) -> Optional[dict]:
        for item in self.get_faq():
            haystack = [item.get("question", ""), item.get("answer", "")]
            haystack.extend(item.get("question_variants", []))
            if _matches(query, haystack):
                return item
        return None

    def find_advisory(self, query: str) -> Optional[dict]:
        for item in self.get_advisories():
            haystack = [item.get("topic", ""), item.get("guidance", "")]
            haystack.extend(item.get("question_variants", []))
            if _matches(query, haystack):
                return item
        return None

    def sources(self) -> list[str]:
        return sorted({s.get("official_url") for s in self.get_schemes() if s.get("official_url")})


knowledge_service = KnowledgeService()
