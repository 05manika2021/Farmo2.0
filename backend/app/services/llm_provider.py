"""Provider-agnostic LLM layer.

Farmo's chat and voice routes both call ``gemini_service.generate_response``,
which owns everything Farmo-specific: intent detection, verified context, the
system instruction, the answer format and the local fallback. The only
vendor-specific step is the model call itself, and that is delegated here.

    chat / voice -> generate_response -> LLMProvider.generate -> selected vendor

Selection is driven by environment variables:

    LLM_PROVIDER   "groq" | "gemini" | "" (auto)
    GROQ_MODEL     Groq chat-completions model id
    GEMINI_MODEL   Gemini model id (existing provider)

Auto mode prefers Groq and only uses it when ``GROQ_API_KEY`` is configured,
otherwise Gemini stays the provider. If the selected provider has no
credentials the other configured provider is tried, and only then does the
caller fall back to verified local data. The Groq credential is read here on
the server only and is never forwarded to the frontend.
"""

import logging
from abc import ABC, abstractmethod
from typing import Callable, Dict, Optional

import httpx

from app.core.config import settings

logger = logging.getLogger("farmo.llm")

GROQ_CHAT_URL = "https://api.groq.com/openai/v1/chat/completions"

DEFAULT_PROVIDER = "groq"
SUPPORTED_PROVIDERS = ("groq", "gemini")


def redact(text: str) -> str:
    """Strip every configured credential out of a message before it is logged."""
    for secret in (settings.GROQ_API_KEY, settings.GEMINI_API_KEY, settings.OPENAI_API_KEY):
        if secret:
            text = text.replace(secret, "***")
    return text


class LLMProviderError(Exception):
    """A provider failure described only in non-sensitive terms.

    Carries an optional HTTP status so :func:`classify_ai_error` can map it to
    the same coarse codes the frontend already understands. The message is
    deliberately generic: never the response body, never a credential.
    """

    def __init__(self, message: str, *, provider: str = "", status_code: Optional[int] = None):
        super().__init__(redact(message))
        self.provider = provider
        self.status_code = status_code


class LLMProvider(ABC):
    """Minimal contract every chat model vendor must satisfy."""

    name: str = "llm"

    @abstractmethod
    def is_configured(self) -> bool:
        """True when this provider has the credentials it needs."""

    @abstractmethod
    async def generate(self, system_instruction: str, prompt: str) -> str:
        """Return a non-blank answer, or raise. Language lives in the instruction."""


async def _chat_completion(url: str, *, headers: Dict[str, str], payload: Dict) -> httpx.Response:
    """Single HTTP seam so tests can drive the Groq provider without a network."""
    async with httpx.AsyncClient(timeout=30.0) as client:
        return await client.post(url, headers=headers, json=payload)


class GroqProvider(LLMProvider):
    name = "groq"

    def is_configured(self) -> bool:
        return bool(settings.GROQ_API_KEY)

    async def generate(self, system_instruction: str, prompt: str) -> str:
        api_key = settings.GROQ_API_KEY
        if not api_key:
            raise LLMProviderError("GROQ_API_KEY is not configured", provider=self.name)

        payload = {
            "model": settings.GROQ_MODEL,
            "messages": [
                {"role": "system", "content": system_instruction},
                {"role": "user", "content": prompt},
            ],
            "temperature": 0.3,
            "max_tokens": 1024,
        }

        try:
            response = await _chat_completion(
                GROQ_CHAT_URL,
                headers={"Authorization": f"Bearer {api_key}"},
                payload=payload,
            )
        except httpx.TimeoutException as e:
            raise LLMProviderError("Groq request timed out", provider=self.name, status_code=408) from e
        except httpx.HTTPError as e:
            raise LLMProviderError(
                f"Groq request failed ({type(e).__name__})", provider=self.name
            ) from e

        status = getattr(response, "status_code", None)
        if status != 200:
            raise LLMProviderError(
                f"Groq API error (HTTP {status})", provider=self.name, status_code=status
            )

        try:
            data = response.json()
            choices = data.get("choices") or []
            answer = ((choices[0].get("message") or {}).get("content") or "")
        except (AttributeError, IndexError, KeyError, TypeError, ValueError) as e:
            raise LLMProviderError(
                "Groq returned an unreadable response", provider=self.name, status_code=status
            ) from e

        answer = answer.strip()
        if not answer:
            raise LLMProviderError(
                "Empty response from Groq", provider=self.name, status_code=status
            )
        return answer


class GeminiProvider(LLMProvider):
    """The original provider, kept intact and still selectable."""

    name = "gemini"

    def __init__(self, client_factory: Callable[[], object]):
        # The factory is the service's own ``_get_client`` so the lazily built
        # client (and any test seam around it) stays exactly where it was.
        self._client_factory = client_factory

    def is_configured(self) -> bool:
        try:
            return self._client_factory() is not None
        except Exception as e:
            logger.error("Gemini client check failed: %s", redact(f"{type(e).__name__}: {e}"))
            return False

    async def generate(self, system_instruction: str, prompt: str) -> str:
        client = self._client_factory()
        if client is None:
            raise LLMProviderError("Gemini client is not configured", provider=self.name)

        # Deliberately not wrapped: the original SDK exception carries the
        # status code that classify_ai_error() maps to AI_QUOTA_EXHAUSTED.
        response = client.models.generate_content(
            model=settings.GEMINI_MODEL,
            contents=prompt,
            config={
                "system_instruction": system_instruction,
                "temperature": 0.3,
                "max_output_tokens": 1024,
            },
        )
        answer = (getattr(response, "text", "") or "").strip()
        if not answer:
            raise ValueError("Empty response from Gemini")
        return answer


def resolve_provider_name() -> str:
    """Return the configured provider name, falling back to auto-selection."""
    requested = (settings.LLM_PROVIDER or "").strip().lower()
    if requested in SUPPORTED_PROVIDERS:
        return requested
    if requested:
        logger.warning(
            "Unsupported LLM_PROVIDER %r (expected one of %s); using auto selection",
            requested,
            ", ".join(SUPPORTED_PROVIDERS),
        )
    return DEFAULT_PROVIDER if settings.GROQ_API_KEY else "gemini"


def build_provider(gemini_client_factory: Optional[Callable[[], object]] = None) -> Optional[LLMProvider]:
    """Resolve the selected provider, trying the other one if it has no keys.

    Returns ``None`` when neither provider is usable; the caller then answers
    from verified local data with a localized "AI unavailable" message.
    """
    name = resolve_provider_name()
    provider = _make_provider(name, gemini_client_factory)
    if provider is not None and provider.is_configured():
        return provider

    other_name = "gemini" if name == "groq" else "groq"
    other = _make_provider(other_name, gemini_client_factory)
    if other is not None and other.is_configured():
        logger.warning("LLM provider %r is not configured; using %r instead", name, other_name)
        return other
    return None


def _make_provider(name: str, gemini_client_factory: Optional[Callable[[], object]]) -> Optional[LLMProvider]:
    if name == "groq":
        return GroqProvider()
    if name == "gemini":
        if gemini_client_factory is None:
            return None
        return GeminiProvider(gemini_client_factory)
    return None
