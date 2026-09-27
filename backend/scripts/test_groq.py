"""Deterministic Groq connectivity diagnostic.

Loads GROQ_API_KEY / GROQ_MODEL from the environment (and backend/.env),
calls Groq directly over the OpenAI-compatible REST API, and prints a fixed,
machine-readable result block.

No credential value is ever printed; any accidental occurrence is redacted.

    venv\\Scripts\\python.exe scripts\\test_groq.py
"""

import json
import os
import pathlib
import sys
import time

import httpx

BACKEND_DIR = pathlib.Path(__file__).resolve().parents[1]
ENV_FILE = BACKEND_DIR / ".env"

GROQ_BASE_URL = "https://api.groq.com/openai/v1"
GROQ_CHAT_URL = f"{GROQ_BASE_URL}/chat/completions"
DEFAULT_MODEL = "qwen/qwen3.8-27b"
PROMPT = "Reply with exactly: FARMO_GROQ_OK"
EXPECTED = "FARMO_GROQ_OK"


def load_env() -> None:
    """Populate os.environ from backend/.env without overwriting real env vars."""
    if not ENV_FILE.exists():
        return
    for raw in ENV_FILE.read_text(encoding="utf-8-sig", errors="replace").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key, value = key.strip(), value.strip()
        if key and key not in os.environ:
            os.environ[key] = value


def redact(text: str, secret: str) -> str:
    return text.replace(secret, "***") if secret else text


def main() -> int:
    load_env()

    key = os.environ.get("GROQ_API_KEY", "") or ""
    model = os.environ.get("GROQ_MODEL", "").strip() or DEFAULT_MODEL
    provider = (os.environ.get("LLM_PROVIDER", "").strip() or "(auto)").lower()

    print("=" * 62)
    print("FARMO GROQ DIAGNOSTIC")
    print("=" * 62)
    print(f"GROQ_KEY_LOADED={'YES' if len(key) > 10 else 'NO'}")
    print(f"GROQ_KEY_LENGTH={len(key)}")
    print(f"GROQ_MODEL={model}")
    print(f"LLM_PROVIDER={provider}")
    print(f"GROQ_BASE_URL={GROQ_BASE_URL}")
    print(f"GEMINI_API_KEY_LOADED={'YES' if len(os.environ.get('GEMINI_API_KEY', '') or '') > 10 else 'NO'}")
    print(f"GROQ_REQUEST=START")

    if len(key) <= 10:
        print("GROQ_HTTP_STATUS=SKIPPED")
        print("GROQ_ERROR=GROQ_API_KEY is missing or empty in backend/.env")
        print("GROQ_RESULT=FAIL")
        return 1

    headers = {"Authorization": f"Bearer {key}"}
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": PROMPT}],
        "temperature": 0,
        "max_tokens": 64,
    }

    started = time.time()
    try:
        with httpx.Client(timeout=30.0) as client:
            response = client.post(GROQ_CHAT_URL, headers=headers, json=payload)
    except httpx.TimeoutException:
        print("GROQ_HTTP_STATUS=TIMEOUT")
        print(f"GROQ_ERROR=request timed out after 30s")
        print("GROQ_RESULT=FAIL")
        return 1
    except httpx.HTTPError as exc:
        print("GROQ_HTTP_STATUS=TRANSPORT_ERROR")
        print(f"GROQ_ERROR={redact(f'{type(exc).__name__}: {exc}', key)}")
        print("GROQ_RESULT=FAIL")
        return 1
    latency_ms = int((time.time() - started) * 1000)

    print(f"GROQ_HTTP_STATUS={response.status_code}")
    print(f"GROQ_LATENCY_MS={latency_ms}")

    if response.status_code != 200:
        print(f"GROQ_ERROR={redact(response.text[:300], key)}")
        print("GROQ_RESULT=FAIL")
        return 1

    try:
        data = response.json()
        content = data["choices"][0]["message"].get("content") or ""
    except Exception as exc:
        print(f"GROQ_ERROR=unreadable response: {redact(f'{type(exc).__name__}: {exc}', key)}")
        print("GROQ_RESULT=FAIL")
        return 1

    usage = data.get("usage", {}) or {}
    print(f"GROQ_PROMPT_TOKENS={usage.get('prompt_tokens', '?')}")
    print(f"GROQ_COMPLETION_TOKENS={usage.get('completion_tokens', '?')}")
    print(f"GROQ_CONTENT={content.strip()!r}")
    print(f"GROQ_EXPECTED={EXPECTED!r}")

    passed = content.strip() == EXPECTED
    print(f"GROQ_RESULT={'PASS' if passed else 'FAIL'}")
    return 0 if passed else 1


if __name__ == "__main__":
    sys.exit(main())
