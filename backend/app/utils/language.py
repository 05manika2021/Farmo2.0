SUPPORTED_LANGUAGES = {
    "en": "English",
    "hi": "Hindi",
    "pa": "Punjabi",
    "gu": "Gujarati",
    "mr": "Marathi",
    "bn": "Bengali",
}

DEFAULT_LANGUAGE = "hi"


def is_supported_language(lang_code: str) -> bool:
    return lang_code in SUPPORTED_LANGUAGES


def get_language_name(lang_code: str) -> str:
    return SUPPORTED_LANGUAGES.get(lang_code, "Unknown")


def get_supported_language_codes() -> list[str]:
    return list(SUPPORTED_LANGUAGES.keys())
