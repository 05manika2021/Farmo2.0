import logging
import re
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.profit_service import profit_service
from app.services.price_service import price_service
from app.services.market_service import market_service
from app.services.recommendation_service import recommendation_service
from app.services.weather_service import weather_service
from app.services.knowledge_service import knowledge_service
from app.services.llm_provider import build_provider, redact
from app.utils.language import get_language_name

logger = logging.getLogger("farmo.gemini")


def _redact_key(exc: BaseException) -> str:
    """Stringify an exception while redacting every configured API key."""
    return redact(f"{type(exc).__name__}: {exc}")


SYSTEM_INSTRUCTION = (
    "You are Farmo, an agricultural market assistant for Indian farmers. "
    "Use only verified context provided by the Farmo backend for current market information. "
    "Never invent prices, distances, transport costs, weather information, "
    "profit calculations, or market recommendations. "
    "If required information is unavailable, clearly say that it is unavailable. "
    "Do not present predicted prices as certain. "
    "Never decide scheme eligibility for the farmer; only describe the scheme and its official source."
)

FORMAT_INSTRUCTION = (
    "Answer format: keep it short and simple, two to four sentences or a short bullet list. "
    "Use plain farmer-friendly wording. No markdown headings, no tables, no code, no emoji. "
    "Quote money as INR figures. Do not add greetings or sign-offs."
)

# P1: the response language is stated explicitly per language so Gemini never
# has to infer it, and never answers in English for a non-English request.
LANGUAGE_INSTRUCTIONS = {
    "en": (
        "The user's selected language is English. Respond ONLY in English. "
        "Do not respond in any other language."
    ),
    "hi": (
        "The user's selected language is Hindi. Respond ONLY in Hindi written in the Devanagari script. "
        "Do not respond in English. Use simple farmer-friendly Hindi. "
        "Do not translate the response into English."
    ),
    "pa": (
        "The user's selected language is Punjabi. Respond ONLY in Punjabi written in the Gurmukhi script. "
        "Do not respond in English or Hindi. Use simple farmer-friendly Punjabi. "
        "Do not translate the response into English."
    ),
    "gu": (
        "The user's selected language is Gujarati. Respond ONLY in Gujarati script. "
        "Do not respond in English or Hindi. Use simple farmer-friendly Gujarati. "
        "Do not translate the response into English."
    ),
    "mr": (
        "The user's selected language is Marathi. Respond ONLY in Marathi written in the Devanagari script. "
        "Do not respond in English or Hindi. Use simple farmer-friendly Marathi. "
        "Do not translate the response into English."
    ),
    "bn": (
        "The user's selected language is Bengali. Respond ONLY in Bengali script. "
        "Do not respond in English or Hindi. Use simple farmer-friendly Bengali. "
        "Do not translate the response into English."
    ),
}

INTENT_KEYWORDS = {
    "price": [
        "price", "bhav", "daam", "rate", "kimat", "keemat",
        "what is the price", "current price", "aaj ka bhav", "aaj ka rate",
        # P3: native-script keywords so a question asked in Indian English or a
        # regional language is classified the same way as its English wording.
        "भाव", "दाम", "कीमत", "मूल्य",
        "ਭਾਵ", "ਦਾਮ", "ਕੀਮਤ", "ਮੁੱਲ",
        "ભાવ", "દામ", "કિંમત", "મૂલ્ય",
        "भाव", "दाम", "किंमत", "मूल्य",
        "দাম", "মূল্য",
    ],
    "market": [
        "market", "mandi", "kahan bechna", "where should i sell",
        "which market", "kaunsi mandi", "pass ki mandi", "best mandi",
        "मंडी", "मण्डी", "कहाँ बेच", "कहां बेच", "कौन सी मंडी",
        "ਮੰਡੀ", "ਕਿੱਥੇ ਵੇਚ", "ਕਿਹੜੀ ਮੰਡੀ",
        "મંડી", "ક્યાં વેચ", "કઈ મંડી",
        "मंडी", "कुठे विक", "कोणती मंडी",
        "মণ্ডি", "মান্ডি", "কোথায় বিক্রি",
    ],
    "recommendation": [
        "sell now", "abhi bechu", "abhi bechna", "kab bechna",
        "when should i sell", "should i sell", "bechun", "what should i do", "kya karun",
        "ruk jaun", "ruku", "sell or wait", "bechu ya", "storage",
        "बेचूं", "बेचें", "कब बेच", "रुकूं", "रुक जाऊं", "क्या करूं", "सलाह",
        "ਵੇਚਾਂ", "ਵੇਚਣਾ", "ਕਦੋਂ ਵੇਚ", "ਰੁਕਾਂ", "ਸਲਾਹ",
        "વેચું", "ક્યારે વેચ", "રોકાઉં", "સલાહ",
        "विकू", "कधी विक", "थांबू", "सल्ला",
        "বিক্রি", "কখন বিক্রি", "অপেক্ষা", "পরামর্শ",
    ],
    "profit": [
        "profit", "kitna milega", "kitna fayda", "kitna profit",
        "how much will i earn", "expected income", "net profit",
        "how much can i earn", "earn", "income",
        "लाभ", "मुनाफा", "कमाई", "कितना मिलेगा",
        "ਨਫ਼ਾ", "ਲਾਭ", "ਕਮਾਈ", "ਕਿੰਨਾ ਮਿਲੇਗਾ",
        "નફો", "લાભ", "કમાણી",
        "नफा", "लाभ", "कमाई", "किती मिळेल",
        "লাভ", "মুনাফা", "কত পাব",
    ],
    "transport": [
        "transport", "transport cost", "delivery",
        "truck", "bhada", "transport kharcha", "how far", "distance",
        "ढुलाई", "भाड़ा", "ट्रक", "परिवहन", "किराया", "दूरी",
        "ਭਾੜਾ", "ਟਰਕ", "ਆਵਾਜਾਈ", "ਦੂਰੀ",
        "ભાડું", "ટ્રક", "વાહન ખર્ચ", "અંતર",
        "भाडे", "ट्रक", "वाहतूक", "अंतर",
        "ভাড়া", "পরিবহন", "দূরত্ব",
    ],
    "weather": [
        "weather", "mausam", "barish", "baarish", "rain", "rainfall",
        "temperature", "garmi", "thandi", "forecast", "storm",
        "मौसम", "बारिश", "बरसात", "वर्षा", "तापमान", "गर्मी", "सर्दी", "बादल",
        "ਮੌਸਮ", "ਵਰਖਾ", "ਬਰਸਾਤ", "ਤਾਪਮਾਨ", "ਗਰਮੀ",
        "હવામાન", "વરસાદ", "તાપમાન", "ગરમી", "થંડી",
        "हवामान", "पाऊस", "तापमान", "उन्हाळा",
        "আবহাওয়া", "বৃষ্টি", "তাপমান", "গরমী",
    ],
    "scheme": [
        "scheme", "yojana", "yojna", "yojana", "subsidy", "subsidies",
        "pm-kisan", "pm kisan", "kisan samman", "insurance", "bima",
        "fasal bima", "loan", "kcc", "credit card", "soil health",
        "enam", "e-nam", "eligib", "apply for", "how to apply", "government benefit",
        "योजना", "सरकारी", "सब्सिडी", "बीमा", "ऋण", "पीएम",
        "ਯੋਜਨਾ", "ਸਰਕਾਰੀ", "ਸਬਸਿਡੀ", "ਬੀਮਾ", "ਉਧਾਰ", "ਪੀਐਮ",
        "યોજના", "સરકારી", "સબસિડી", "વીમો", "લોન", "પીએમ",
        "योजना", "सरकारी", "सबसिडी", "विमा", "कर्ज", "पीएम",
        "সরকারি", "সহায়তা", "বিমা", "ঋণ", "পিএম",
    ],
}

# P2/P9: fallback replies in all six supported languages.
TEXT = {
    "need_info": {
        "en": "I need more information to answer your question. Please tell me your crop name and where you are.",
        "hi": "मुझे आपके सवाल का जवाब देने के लिए और जानकारी चाहिए। कृपया बताइए आपकी फसल का नाम और आप कहाँ हैं।",
        "pa": "ਮੈਨੂੰ ਤੁਹਾਡੇ ਸਵਾਲ ਦਾ ਜਵਾਬ ਦੇਣ ਲਈ ਹੋਰ ਜਾਣਕਾਰੀ ਚਾਹੀਦੀ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਦੱਸੋ ਤੁਹਾਡੀ ਫ਼ਸਲ ਦਾ ਨਾਮ ਅਤੇ ਤੁਸੀਂ ਕਿੱਥੇ ਹੋ।",
        "gu": "મને તમારા પ્રશ્નનો જવાબ આપવા માટે વધુ માહિતી જોઈએ. કૃપા કરીને કહો તમારા પાકનું નામ અને તમે ક્યાં છો.",
        "mr": "मला तुमच्या प्रश्नाचे उत्तर देण्यासाठी अजून माहिती हवी आहे. कृपया सांगा तुमच्या पिकाचे नाव आणि तुम्ही कुठे आहात.",
        "bn": "আমাকে আপনার প্রশ্নের উত্তর দিতে আরও তথ্য দরকার। অনুগ্রহ করে বলুন আপনার ফসলের নাম এবং আপনি কোথায় আছেন।",
    },
    "no_data": {
        "en": "I don't have verified data for that yet.",
        "hi": "इसके लिए मेरे पास अभी पुष्ट आँकड़े नहीं हैं।",
        "pa": "ਇਸ ਲਈ ਮੇਰੇ ਕੋਲ ਅਜੇ ਪੁਸ਼ਟੀ ਕੀਤੇ ਆਂਕੜੇ ਨਹੀਂ ਹਨ।",
        "gu": "આ માટે મારી પાસે હજુ ચકાસાયેલા આંકડા નથી.",
        "mr": "यासाठी माझ्याकडे अद्याप पडताळलेले आकडे नाहीत.",
        "bn": "এর জন্য আমার কাছে এখনো যাচাই করা তথ্য নেই।",
    },
    "price_header": {
        "en": "Current prices:", "hi": "आज के भाव:", "pa": "ਅੱਜ ਦੇ ਭਾਵ:",
        "gu": "આજના ભાવ:", "mr": "आजचे भाव:", "bn": "আজকের দাম:",
    },
    "market_header": {
        "en": "Available markets:", "hi": "उपलब्ध मंडियाँ:", "pa": "ਉਪਲਬਧ ਮੰਡੀਆਂ:",
        "gu": "ઉપલબ્ધ મંડીઓ:", "mr": "उपलब्ध मंड्या:", "bn": "উপলব্ধ হাটসমূহ:",
    },
    "recommendation_label": {
        "en": "Farmo recommendation:", "hi": "फ़ार्मो की सलाह:", "pa": "ਫਾਰਮੋ ਦੀ ਸਲਾਹ:",
        "gu": "ફાર્મોની સલાહ:", "mr": "फार्मोचा सल्ला:", "bn": "ফার্মোর পরামর্শ:",
    },
    "reason_label": {
        "en": "Reason:", "hi": "कारण:", "pa": "ਕਾਰਨ:", "gu": "કારણ:", "mr": "कारण:", "bn": "কারণ:",
    },
    "source_label": {"en": "Source", "hi": "स्रोत", "pa": "ਸਰੋਤ", "gu": "સ્રોત", "mr": "स्रोत", "bn": "উৎস"},
    "status_label": {"en": "Status", "hi": "स्थिति", "pa": "ਸਥਿਤੀ", "gu": "સ્થિતિ", "mr": "स्थिती", "bn": "অবস্থা"},
    # Shown only when the answer is backed by existing DEMO records (P8).
    "demo_notice": {
        "en": "This is demo data.", "hi": "यह डेमो डेटा है।",
        "pa": "ਇਹ ਡੈਮੋ ਡੇਟਾ ਹੈ।", "gu": "આ ડેમો ડેટા છે.",
        "mr": "हा डेमो डेटा आहे.", "bn": "এটি ডেমো ডেটা।",
    },
    "error_generic": {
        "en": "Sorry, I could not process your request right now. Please try again.",
        "hi": "माफ़ कीजिए, अभी आपका अनुरोध संसाधित नहीं हो पाया। कृपया फिर से कोशिश करें।",
        "pa": "ਮਾਫ਼ ਕਰਨਾ, ਹੁਣ ਤੁਹਾਡੀ ਬੇਨਤੀ ਪ੍ਰਕਿਰਿਆ ਨਹੀਂ ਹੋ ਸਕੀ। ਕਿਰਪਾ ਕਰਕੇ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
        "gu": "માફ કરશો, હમણાં તમારી વિનંતી પ્રક્રિયા થઈ શકી નથી. કૃપા કરીને ફરી પ્રયાસ કરો.",
        "mr": "क्षमस्व, आत्ता तुमची विनंती प्रक्रिया करता आली नाही. कृपया पुन्हा प्रयत्न करा.",
        "bn": "দুঃখিত, এখন আপনার অনুরোধ প্রক্রিয়া করা যায়নি। অনুগ্রহ করে আবার চেষ্টা করুন।",
    },
    # Shown verbatim to the farmer whenever Gemini cannot generate an answer
    # (quota exhausted, timeout, or unconfigured). Kept in sync with the
    # `voice.aiUnavailable` key in src/locales/*.json.
    "ai_unavailable": {
        "en": "AI service is temporarily unavailable. Please try again.",
        "hi": "AI सेवा अभी उपलब्ध नहीं है। कृपया थोड़ी देर बाद फिर कोशिश करें।",
        "pa": "AI ਸੇਵਾ ਇਸ ਵੇਲੇ ਉਪਲਬਧ ਨਹੀਂ ਹੈ। ਕਿਰਪਾ ਕਰਕੇ ਥੋੜ੍ਹੀ ਦੇਰ ਬਾਅਦ ਦੁਬਾਰਾ ਕੋਸ਼ਿਸ਼ ਕਰੋ।",
        "gu": "AI સેવા હાલ ઉપલબ્ધ નથી. કૃપા કરીને થોડી વાર પછી ફરી પ્રયાસ કરો.",
        "mr": "AI सेवा आत्ता उपलब्ध नाही. कृपया थोडी वेळ नंतर पुन्हा प्रयत्न करा.",
        "bn": "AI সেবা এখন উপলব্ধ নয়। অনুগ্রহ করে কিছুক্ষণ পরে আবার চেষ্টা করুন।",
    },
}

# Shared value labels so every language renders the same numbers.
LABELS = {
    "en": {"price": "price", "distance": "distance", "transport": "transport", "net": "net profit", "qty": "quintal"},
    "hi": {"price": "भाव", "distance": "दूरी", "transport": "परिवहन", "net": "शुद्ध लाभ", "qty": "क्विंटल"},
    "pa": {"price": "ਭਾਵ", "distance": "ਦੂਰੀ", "transport": "ਆਵਾਜਾਈ", "net": "ਸ਼ੁੱਧ ਲਾਭ", "qty": "ਕਿੰਟਲ"},
    "gu": {"price": "ભાવ", "distance": "અંતર", "transport": "વાહન ખર્ચ", "net": "ચોખ્ખો નફો", "qty": "ક્વિન્ટલ"},
    "mr": {"price": "भाव", "distance": "अंतर", "transport": "वाहतूक", "net": "निव्वळ नफा", "qty": "क्विंटल"},
    "bn": {"price": "দাম", "distance": "দূরত্ব", "transport": "পরিবহন", "net": "নিট লাভ", "qty": "কুইন্টাল"},
}


def _t(key: str, language: str) -> str:
    """Localized fallback text; English is the safety net for every key."""
    table = TEXT.get(key, {})
    return table.get(language) or table.get("en", "")


def _labels(language: str) -> dict:
    return LABELS.get(language) or LABELS["en"]


def failure_message(language: str) -> str:
    """Localized 'could not process' reply used when generation blows up."""
    return _t("error_generic", language)


def ai_unavailable_message(language: str) -> str:
    """Localized 'AI is temporarily unavailable' reply shown on provider failure."""
    return _t("ai_unavailable", language)


def classify_ai_error(exc: BaseException) -> str:
    """Map a provider exception to a safe, non-sensitive error code.

    Only coarse categories are exposed so no key, quota detail, stack trace or
    provider-internal message ever reaches the client.
    """
    status = None
    for attr in ("code", "status_code"):
        value = getattr(exc, attr, None)
        if isinstance(value, int):
            status = value
            break

    text = str(exc).upper()
    name = type(exc).__name__.upper()

    if (
        status == 429
        or "RESOURCE_EXHAUSTED" in text
        or "RESOURCEEXHAUSTED" in name
        or "EXCEEDED YOUR CURRENT QUOTA" in text
        or "QUOTA" in text and "429" in text
        or "'CODE': 429" in text
        or "CODE=429" in text
    ):
        return "AI_QUOTA_EXHAUSTED"

    if (
        isinstance(exc, (TimeoutError, ConnectionError))
        or "TIMEOUT" in name
        or "TIMEOUT" in text
        or "TIMED OUT" in text
        or "DEADLINE_EXCEEDED" in text
        or "DEADLINEEXCEEDED" in name
    ):
        return "AI_TIMEOUT"

    return "AI_UNAVAILABLE"


# Crop names understood in the farmer's own language, mapped to the canonical
# name used by market_prices.crop_name (seeded values are lower-case ASCII).
# English aliases are matched on word boundaries so "price" never matches "rice".
CROP_ALIASES = {
    "onion": ("onion", "onions", "प्याज", "प्याज़", "ਪਿਆਜ਼", "ડુંગળી", "कांदा", "कांद्या", "পেঁয়াজ"),
    "tomato": ("tomato", "tomatoes", "टमाटर", "टोमॅटर", "ਟਮਾਟਰ", "ટમેટું", "टोमॅटो", "टोमॅट्या", "টমেটো"),
    "potato": ("potato", "potatoes", "आलू", "ਆਲੂ", "બટાટા", "बटाटा", "बटाट्या", "আলু"),
    "wheat": ("wheat", "गेहूं", "गेहू", "ਕਣਕ", "ઘઉં", "गहू", "गव्ह", "গম"),
    "rice": ("rice", "rices", "चावल", "चावळ", "ਚੌਲ", "ચોખા", "तांदूळ", "तांदुळ", "চাল"),
    # Crops the UI actually offers on the graph / mandi / home tabs.
    "cotton": ("cotton", "कपास", "કપાસ", "कापूस", "पाहू", "কাপাস"),
    "soybean": ("soybean", "soy beans", "soya", "सोयाबीन", "સોયાબીન", "सोया", "সয়াবিন"),
    "maize": ("maize", "corn", "मक्का", "મકાઈ", "मका", "ভুট্টা"),
}

# Fixed DEMO location, used only when the browser gave us no coordinates and
# DEMO_MODE is on, so market / profit / weather answers stay possible.
DEMO_FALLBACK_LAT = 22.7196
DEMO_FALLBACK_LON = 75.8577
DEMO_LOCATION_NAME = "Indore, Madhya Pradesh"
_DEMO_LOCATION_INTENTS = {"market", "recommendation", "profit", "transport", "weather"}


def resolve_crop_from_message(message: str, requested_crop: Optional[str]) -> Optional[str]:
    """Pick the crop the farmer actually asked about, else keep the request value.

    The request body carries the farmer's selected crop (default 'Wheat'), but
    the question may be about a different crop ("आज प्याज का भाव क्या है?").
    Without this the price lookup runs against the wrong crop, finds no rows and
    the answer falls back to UNAVAILABLE even though DEMO data exists.
    """
    if not message:
        return requested_crop
    lowered = message.lower()
    for canonical, aliases in CROP_ALIASES.items():
        for alias in aliases:
            if alias.isascii():
                if re.search(rf"(?<!\w){re.escape(alias)}(?!\w)", lowered):
                    return canonical
            elif alias in message:
                return canonical
    return requested_crop


class GeminiService:
    def __init__(self):
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not settings.GEMINI_API_KEY:
                return None
            try:
                from google import genai
                self._client = genai.Client(api_key=settings.GEMINI_API_KEY)
            except Exception as e:
                logger.error("Failed to initialize Gemini client: %s", _redact_key(e))
                return None
        return self._client

    def is_configured(self) -> bool:
        return settings.GEMINI_API_KEY is not None and len(settings.GEMINI_API_KEY) > 0

    def detect_intent(self, message: str) -> str:
        lower_msg = message.lower()
        scores = {}
        for intent, keywords in INTENT_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in lower_msg)
            if score > 0:
                scores[intent] = score
        if not scores:
            return "general"
        return max(scores, key=scores.get)

    # ── Context building ──────────────────────────────────────────────────────

    def build_context(
        self, intent, message, language, crop, quantity,
        farmer_lat, farmer_lon, db, weather=None,
    ):
        context = {
            "intent": intent,
            "language": language,
            "crop": crop,
            "quantity": quantity,
            "message": message,
            "data_points": [],
        }

        if intent == "price" and crop:
            self._add_price_context(context, crop, db)
        elif intent == "market" and crop and farmer_lat and farmer_lon:
            self._add_market_context(context, crop, quantity or 5, farmer_lat, farmer_lon, db)
        elif intent == "recommendation" and crop and farmer_lat and farmer_lon:
            self._add_recommendation_context(context, crop, quantity or 5, farmer_lat, farmer_lon, db)
        elif intent == "profit" and crop and farmer_lat and farmer_lon:
            self._add_profit_context(context, crop, quantity or 5, farmer_lat, farmer_lon, db)
        elif intent == "transport" and farmer_lat and farmer_lon:
            self._add_transport_context(context, crop, quantity or 5, farmer_lat, farmer_lon, db)
        elif intent == "weather":
            self._add_weather_context(context, weather)
        elif intent == "scheme":
            self._add_scheme_context(context, message)

        # General questions still get real, answerable data when it exists.
        if not context["data_points"] and intent == "general":
            self._add_faq_context(context, message)
            if not context["data_points"]:
                self._add_advisory_context(context, message)
            if not context["data_points"] and crop and farmer_lat and farmer_lon:
                self._add_profit_context(context, crop, quantity or 5, farmer_lat, farmer_lon, db)

        return context

    def _market_source_label(self, data_status: Optional[str]) -> str:
        return "Live Market Data" if data_status == "LIVE" else "Farmo Demo Market Data"

    def _add_price_context(self, context, crop, db):
        prices = price_service.get_current_prices_for_crop(crop, db)
        if not prices:
            context["data_points"].append({
                "type": "price_unavailable",
                "detail": f"No current price data available for {crop}.",
                "source_label": "Farmo",
                "data_status": "UNAVAILABLE",
            })
            return
        for p in prices[:6]:
            market = market_service.get_market_by_id(p.market_id, db)
            context["data_points"].append({
                "type": "current_price",
                "market": market.name if market else f"Market #{p.market_id}",
                "crop": crop,
                "price_per_quintal": p.price_per_quintal,
                "data_status": p.data_status,
                "source_label": self._market_source_label(p.data_status),
            })

    def _add_market_context(self, context, crop, quantity, lat, lon, db):
        profit_data = profit_service.calculate_for_all_markets(
            crop=crop, quantity=quantity, quantity_unit="quintal",
            farmer_lat=lat, farmer_lon=lon, db=db,
        )
        if not profit_data["markets"]:
            context["data_points"].append({
                "type": "market_unavailable",
                "detail": f"No market data available for {crop}.",
                "source_label": "Farmo",
                "data_status": "UNAVAILABLE",
            })
            return
        for m in profit_data["markets"][:4]:
            context["data_points"].append({
                "type": "market_comparison",
                "market": m["market_name"],
                "price": m["price_per_quintal"],
                "distance_km": m["distance_km"],
                "transport_cost": m["transport_cost"],
                "net_profit": m["net_profit"],
                "data_status": m.get("data_status"),
                "source_label": self._market_source_label(m.get("data_status")),
            })

    def _add_recommendation_context(self, context, crop, quantity, lat, lon, db):
        result = recommendation_service.evaluate_sell_wait(
            crop=crop, quantity=quantity, quantity_unit="quintal",
            farmer_lat=lat, farmer_lon=lon, storage_available=True, db=db,
        )
        context["data_points"].append({
            "type": "recommendation",
            "recommendation": result["recommendation"],
            "reason": result["reason"],
            "best_market": result["best_market_name"],
            "best_net_profit": result["best_market_net_profit"],
            "factors": [{"factor": f["factor"], "detail": f["detail"]} for f in result["factors"]],
            "data_status": "DEMO",
            "source_label": "Farmo Demo Market Data",
        })

    def _add_profit_context(self, context, crop, quantity, lat, lon, db):
        profit_data = profit_service.calculate_for_all_markets(
            crop=crop, quantity=quantity, quantity_unit="quintal",
            farmer_lat=lat, farmer_lon=lon, db=db,
        )
        if not profit_data["markets"]:
            context["data_points"].append({
                "type": "profit_unavailable",
                "detail": f"No profit data available for {crop}.",
                "source_label": "Farmo",
                "data_status": "UNAVAILABLE",
            })
            return
        best = profit_data["markets"][0]
        context["data_points"].append({
            "type": "profit_summary",
            "crop": crop,
            "quantity": quantity,
            "best_market": best["market_name"],
            "price_per_quintal": best["price_per_quintal"],
            "transport_cost": best["transport_cost"],
            "gross_revenue": best["gross_revenue"],
            "net_profit": best["net_profit"],
            "data_status": best.get("data_status"),
            "source_label": self._market_source_label(best.get("data_status")),
        })

    def _add_transport_context(self, context, crop, quantity, lat, lon, db):
        profit_data = profit_service.calculate_for_all_markets(
            crop=crop or "onion", quantity=quantity, quantity_unit="quintal",
            farmer_lat=lat, farmer_lon=lon, db=db,
        )
        if not profit_data["markets"]:
            return
        best = profit_data["markets"][0]
        context["data_points"].append({
            "type": "transport_info",
            "market": best["market_name"],
            "distance_km": best["distance_km"],
            "transport_cost": best["transport_cost"],
            "quantity": quantity,
            "data_status": best.get("data_status"),
            "source_label": self._market_source_label(best.get("data_status")),
        })

    def _add_weather_context(self, context, weather: Optional[dict]):
        if not weather or weather.get("data_status") != "LIVE":
            context["data_points"].append({
                "type": "weather_unavailable",
                "detail": weather.get("note") if weather else "Weather data unavailable.",
                "source_label": "Farmo",
                "data_status": "UNAVAILABLE",
            })
            return
        context["data_points"].append({
            "type": "weather",
            "temperature": weather.get("temperature"),
            "condition": weather.get("condition"),
            "rain_probability": weather.get("rain_probability"),
            "weather_risk": weather.get("weather_risk"),
            "forecast": weather.get("forecast"),
            "warning": weather.get("warning"),
            "data_status": "LIVE",
            "source_label": "Open-Meteo",
        })

    def _add_scheme_context(self, context, message):
        for scheme in knowledge_service.find_schemes(message)[:3]:
            context["data_points"].append({
                "type": "scheme",
                "name": scheme.get("name"),
                "category": scheme.get("category"),
                "description": scheme.get("description"),
                "eligibility_summary": scheme.get("eligibility_summary"),
                "benefits": scheme.get("benefits"),
                "application_instructions": scheme.get("application_instructions"),
                "official_url": scheme.get("official_url"),
                "verification": scheme.get("verification"),
                "data_status": "LIVE",
                "source_label": "Official scheme source",
            })

    def _add_faq_context(self, context, message):
        item = knowledge_service.find_faq(message)
        if not item:
            return
        context["data_points"].append({
            "type": "faq",
            "question": item.get("question"),
            "answer": item.get("answer"),
            "verification": item.get("verification"),
            "data_status": "LIVE",
            "source_label": "Farmo Help",
        })

    def _add_advisory_context(self, context, message):
        item = knowledge_service.find_advisory(message)
        if not item:
            return
        context["data_points"].append({
            "type": "advisory",
            "topic": item.get("topic"),
            "guidance": item.get("guidance"),
            "verification": item.get("verification"),
            "data_status": "LIVE",
            "source_label": "Farmo Advisory",
        })

    # ── Prompt formatting ─────────────────────────────────────────────────────

    def _format_context_for_prompt(self, context):
        lines = []
        lines.append(f"Intent: {context['intent']}")
        lines.append(f"Language: {get_language_name(context['language'])} (code: {context['language']})")
        if context.get("crop"):
            lines.append(f"Crop: {context['crop']}")
        if context.get("quantity"):
            lines.append(f"Quantity: {context['quantity']} quintal")
        lines.append("")
        lines.append("Verified Data from Farmo Backend:")
        for dp in context["data_points"]:
            if dp["type"] == "current_price":
                lines.append(f"- {dp['market']}: {dp['crop']} at INR {dp['price_per_quintal']}/quintal (status: {dp['data_status']})")
            elif dp["type"] == "market_comparison":
                lines.append(f"- {dp['market']}: price INR {dp['price']}/quintal, distance {dp['distance_km']}km, transport INR {dp['transport_cost']}, net profit INR {dp['net_profit']} (status: {dp.get('data_status')})")
            elif dp["type"] == "recommendation":
                lines.append(f"- Recommendation: {dp['recommendation']}")
                lines.append(f"  Reason: {dp['reason']}")
                lines.append(f"  Best market: {dp['best_market']} (net profit INR {dp['best_net_profit']})")
            elif dp["type"] == "profit_summary":
                lines.append(f"- Best option: {dp['best_market']}")
                lines.append(f"  Price: INR {dp['price_per_quintal']}/quintal for {dp['quantity']} quintal")
                lines.append(f"  Transport: INR {dp['transport_cost']}")
                lines.append(f"  Gross revenue: INR {dp['gross_revenue']}")
                lines.append(f"  Net profit: INR {dp['net_profit']} (status: {dp.get('data_status')})")
            elif dp["type"] == "transport_info":
                lines.append(f"- Distance to {dp['market']}: {dp['distance_km']}km")
                lines.append(f"  Transport cost for {dp['quantity']} quintal: INR {dp['transport_cost']}")
            elif dp["type"] == "weather":
                lines.append(f"- Current: {dp['condition']}, {dp['temperature']}C")
                lines.append(f"  Rain probability: {dp['rain_probability']}%, risk: {dp['weather_risk']}")
                if dp.get("warning"):
                    lines.append(f"  Warning: {dp['warning']}")
                if dp.get("forecast"):
                    for day in dp["forecast"]:
                        lines.append(f"  {day.get('date')}: {day.get('condition')}, rain {day.get('rain_probability')}%")
            elif dp["type"] == "scheme":
                lines.append(f"- Scheme: {dp['name']} ({dp['category']})")
                lines.append(f"  Benefits: {dp['benefits']}")
                lines.append(f"  Eligibility: {dp['eligibility_summary']}")
                lines.append(f"  How to apply: {dp['application_instructions']}")
                lines.append(f"  Official source: {dp['official_url']}")
                lines.append("  Do NOT decide the farmer's eligibility.")
            elif dp["type"] == "faq":
                lines.append(f"- Answer to '{dp['question']}': {dp['answer']}")
            elif dp["type"] == "advisory":
                lines.append(f"- {dp['topic']}: {dp['guidance']} ({dp['verification']})")
            elif dp["type"] in ("price_unavailable", "market_unavailable", "profit_unavailable", "weather_unavailable"):
                lines.append(f"- {dp['detail']}")
        return "\n".join(lines)

    # ── Data status (P8) ──────────────────────────────────────────────────────

    def _compute_data_status(self, context) -> str:
        """LIVE -> DEMO -> UNAVAILABLE.

        As long as any verified record exists the answer is never UNAVAILABLE;
        UNAVAILABLE is reserved for a context with no records at all.
        """
        points = context.get("data_points", [])
        if not points:
            return "UNAVAILABLE"
        statuses = {p.get("data_status") for p in points if p.get("data_status")}
        if not statuses:
            return "DEMO"
        if "LIVE" in statuses:
            return "LIVE"
        if "DEMO" in statuses:
            return "DEMO"
        return "UNAVAILABLE"

    def _source_label(self, context) -> str:
        for p in context.get("data_points", []):
            if p.get("source_label"):
                return p["source_label"]
        return "Farmo"

    def _with_source(self, answer: str, context, language: str) -> str:
        status = self._compute_data_status(context)
        source = self._source_label(context)
        line = f"{_t('source_label', language)}: {source} · {_t('status_label', language)}: {status}"
        if status == "DEMO":
            # State plainly, in the farmer's language, that this is demo data.
            return f"{answer}\n{_t('demo_notice', language)}\n{line}"
        return f"{answer}\n{line}"

    # ── Main entry ────────────────────────────────────────────────────────────

    async def generate_response(
        self, message, language, crop, quantity,
        farmer_lat, farmer_lon, db,
    ):
        # The question's crop wins over the farmer's standing selection so the
        # price lookup runs against the crop actually being asked about.
        crop = resolve_crop_from_message(message, crop)

        intent = self.detect_intent(message)

        # DEMO_MODE: a missing browser location must not turn a market or
        # weather answer into UNAVAILABLE. Substitute one fixed demo location
        # and label it, instead of silently answering about nowhere.
        demo_location_used = False
        if (farmer_lat is None or farmer_lon is None) and settings.DEMO_MODE:
            farmer_lat, farmer_lon = DEMO_FALLBACK_LAT, DEMO_FALLBACK_LON
            demo_location_used = True

        weather = None
        if intent == "weather" and farmer_lat and farmer_lon:
            weather = await weather_service.get_weather(farmer_lat, farmer_lon)

        context = self.build_context(
            intent, message, language, crop, quantity,
            farmer_lat, farmer_lon, db, weather=weather,
        )

        if demo_location_used and intent in _DEMO_LOCATION_INTENTS:
            context["data_points"].append({
                "type": "demo_location",
                "detail": (
                    f"No location supplied by the app; using the DEMO location "
                    f"{DEMO_LOCATION_NAME}."
                ),
                "location": DEMO_LOCATION_NAME,
                "data_status": "DEMO",
                "source_label": "Farmo Demo Market Data",
            })
        formatted_context = self._format_context_for_prompt(context)
        data_status = self._compute_data_status(context)

        language_instruction = LANGUAGE_INSTRUCTIONS.get(language) or LANGUAGE_INSTRUCTIONS["en"]
        system_instruction = "\n\n".join([SYSTEM_INSTRUCTION, language_instruction, FORMAT_INSTRUCTION])

        prompt = (
            f"{formatted_context}\n\n"
            f"Farmer's question: {message}\n\n"
            f"Answer the farmer's question using ONLY the verified data above. "
            f"Keep the reply short. "
            f"Respond in {get_language_name(language)}. "
            f"Reply in that language only, never in English."
        )

        # The only vendor-specific step: intent, context, instructions and
        # fallbacks above are Farmo logic and stay provider-independent.
        provider = build_provider(gemini_client_factory=self._get_client)

        if provider is None:
            fallback = self._generate_fallback(intent, context, language)
            return {
                "answer": fallback,
                "language": language,
                "intent": intent,
                "context_used": [dp["type"] for dp in context["data_points"]],
                "data_status": data_status,
                "source": "fallback",
                "error_code": "AI_UNAVAILABLE",
                "error_message": ai_unavailable_message(language),
            }

        try:
            answer = await provider.generate(
                system_instruction=system_instruction,
                prompt=prompt,
            )
            return {
                "answer": self._with_source(answer, context, language),
                "language": language,
                "intent": intent,
                "context_used": [dp["type"] for dp in context["data_points"]],
                "data_status": data_status,
                "source": provider.name,
                "error_code": None,
                "error_message": None,
            }
        except Exception as e:
            # Never surface the raw exception: classify it, then answer from
            # verified local data instead of leaving the farmer with nothing.
            error_code = classify_ai_error(e)
            logger.error(
                "LLM provider '%s' error [%s]: %s", provider.name, error_code, _redact_key(e)
            )
            fallback = self._generate_fallback(intent, context, language)
            return {
                "answer": fallback,
                "language": language,
                "intent": intent,
                "context_used": [dp["type"] for dp in context["data_points"]],
                "data_status": data_status,
                "source": "fallback",
                "error_code": error_code,
                "error_message": ai_unavailable_message(language),
            }

    # ── Fallback rendering (P2: answer from real data, in the right language) ──

    def _generate_fallback(self, intent, context, language):
        data_points = context.get("data_points", [])
        if not data_points:
            return _t("need_info", language)

        rendered = self._render_data(data_points, language)
        if rendered is None:
            return _t("no_data", language)
        return self._with_source(rendered, context, language)

    def _render_data(self, data_points, language) -> Optional[str]:
        lab = _labels(language)

        prices = [dp for dp in data_points if dp["type"] == "current_price"]
        if prices:
            lines = [f"- {p['market']}: INR {p['price_per_quintal']}/quintal" for p in prices]
            return _t("price_header", language) + "\n" + "\n".join(lines)

        markets = [dp for dp in data_points if dp["type"] == "market_comparison"]
        if markets:
            lines = []
            for m in markets:
                lines.append(
                    f"- {m['market']}: {lab['price']} INR {m['price']}/quintal, "
                    f"{lab['distance']} {m['distance_km']}km, "
                    f"{lab['transport']} INR {m['transport_cost']:.0f}, "
                    f"{lab['net']} INR {m['net_profit']:.0f}"
                )
            return _t("market_header", language) + "\n" + "\n".join(lines)

        recs = [dp for dp in data_points if dp["type"] == "recommendation"]
        if recs:
            r = recs[0]
            return (
                f"{_t('recommendation_label', language)} {r['recommendation']}\n"
                f"{_t('reason_label', language)} {r['reason']}"
            )

        profits = [dp for dp in data_points if dp["type"] == "profit_summary"]
        if profits:
            p = profits[0]
            if language == "en":
                return (
                    f"Best net value at {p['best_market']}: INR {p['net_profit']:.0f}.\n"
                    f"{lab['price']}: INR {p['price_per_quintal']}/quintal, "
                    f"{lab['transport']}: INR {p['transport_cost']:.0f}."
                )
            return (
                f"{p['best_market']} · {lab['net']}: INR {p['net_profit']:.0f}\n"
                f"{lab['price']}: INR {p['price_per_quintal']}/quintal, "
                f"{lab['transport']}: INR {p['transport_cost']:.0f}"
            )

        transports = [dp for dp in data_points if dp["type"] == "transport_info"]
        if transports:
            t = transports[0]
            return (
                f"{t['market']}: {lab['distance']} {t['distance_km']}km, "
                f"{lab['transport']} INR {t['transport_cost']:.0f} "
                f"({t['quantity']} {lab['qty']})"
            )

        weather_points = [dp for dp in data_points if dp["type"] == "weather"]
        if weather_points:
            w = weather_points[0]
            parts = [f"{w['condition']}, {w['temperature']}C"]
            if w.get("rain_probability") is not None:
                parts.append(f"rain {w['rain_probability']}%")
            parts.append(f"risk {w['weather_risk']}")
            body = ", ".join(parts)
            if w.get("warning"):
                body += f"\n{w['warning']}"
            return body

        faqs = [dp for dp in data_points if dp["type"] == "faq"]
        if faqs:
            return faqs[0]["answer"]

        advisories = [dp for dp in data_points if dp["type"] == "advisory"]
        if advisories:
            a = advisories[0]
            return f"{a['topic']}: {a['guidance']}"

        schemes = [dp for dp in data_points if dp["type"] == "scheme"]
        if schemes:
            s = schemes[0]
            body = f"{s['name']}\n{s['benefits']}"
            if s.get("official_url"):
                body += f"\n{_t('source_label', language)}: {s['official_url']}"
            return body

        return None


gemini_service = GeminiService()
