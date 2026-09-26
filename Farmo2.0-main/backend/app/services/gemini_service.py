import logging
from typing import Optional
from sqlalchemy.orm import Session
from app.core.config import settings
from app.services.profit_service import profit_service
from app.services.price_service import price_service
from app.services.market_service import market_service
from app.services.recommendation_service import recommendation_service
from app.utils.language import get_language_name

logger = logging.getLogger("farmo.gemini")


def _redact_key(exc: BaseException) -> str:
    """Stringify an exception while redacting the Gemini API key if present."""
    msg = f"{type(exc).__name__}: {exc}"
    key = settings.GEMINI_API_KEY
    if key:
        msg = msg.replace(key, "***")
    return msg

SYSTEM_INSTRUCTION = (
    "You are Farmo, an agricultural market assistant for Indian farmers. "
    "Use only verified context provided by the Farmo backend for current market information. "
    "Never invent prices, distances, transport costs, weather information, "
    "profit calculations, or market recommendations. "
    "If required information is unavailable, clearly say that it is unavailable. "
    "Do not present predicted prices as certain. "
    "Use simple language appropriate for farmers. "
    "Respond in the user's requested language."
)

INTENT_KEYWORDS = {
    "price": [
        "price", "bhav", "daam", "rate", "kimat", "keemat",
        "what is the price", "current price", "aaj ka bhav", "aaj ka rate",
    ],
    "market": [
        "market", "mandi", "kahan bechna", "where should i sell",
        "which market", "kaunsi mandi", "pass ki mandi",
    ],
    "recommendation": [
        "sell now", "abhi bechu", "abhi bechna", "kab bechna",
        "when should i sell", "bechun", "what should i do", "kya karun",
        "ruk jaun", "ruku",
    ],
    "profit": [
        "profit", "kitna milega", "kitna fayda", "kitna profit",
        "how much will i earn", "expected income", "net profit",
        "how much can i earn", "earn", "income",
    ],
    "transport": [
        "transport", "transport cost", "delivery",
        "truck", "bhada", "transport kharcha", "how far", "distance",
    ],
    "weather": [
        "weather", "mausam", "barish", "rain", "rainfall",
        "temperature", "garmi", "thandi",
    ],
}


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

    def build_context(
        self, intent, message, language, crop, quantity,
        farmer_lat, farmer_lon, db,
    ):
        context = {
            "intent": intent,
            "language": language,
            "crop": crop,
            "quantity": quantity,
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
        elif crop and farmer_lat and farmer_lon:
            self._add_profit_context(context, crop, quantity or 5, farmer_lat, farmer_lon, db)

        return context

    def _add_price_context(self, context, crop, db):
        prices = price_service.get_current_prices_for_crop(crop, db)
        if not prices:
            context["data_points"].append({
                "type": "price_unavailable",
                "detail": f"No current price data available for {crop}.",
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
        })

    def _format_context_for_prompt(self, context):
        lines = []
        lines.append(f"Intent: {context['intent']}")
        lines.append(f"Language: {context['language']}")
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
                lines.append(f"- {dp['market']}: price INR {dp['price']}/quintal, distance {dp['distance_km']}km, transport INR {dp['transport_cost']}, net profit INR {dp['net_profit']}")
            elif dp["type"] == "recommendation":
                lines.append(f"- Recommendation: {dp['recommendation']}")
                lines.append(f"  Reason: {dp['reason']}")
                lines.append(f"  Best market: {dp['best_market']} (net profit INR {dp['best_net_profit']})")
            elif dp["type"] == "profit_summary":
                lines.append(f"- Best option: {dp['best_market']}")
                lines.append(f"  Price: INR {dp['price_per_quintal']}/quintal for {dp['quantity']} quintal")
                lines.append(f"  Transport: INR {dp['transport_cost']}")
                lines.append(f"  Gross revenue: INR {dp['gross_revenue']}")
                lines.append(f"  Net profit: INR {dp['net_profit']}")
            elif dp["type"] == "transport_info":
                lines.append(f"- Distance to {dp['market']}: {dp['distance_km']}km")
                lines.append(f"  Transport cost for {dp['quantity']} quintal: INR {dp['transport_cost']}")
            elif dp["type"] in ("price_unavailable", "market_unavailable", "profit_unavailable"):
                lines.append(f"- {dp['detail']}")
        return "\n".join(lines)

    async def generate_response(
        self, message, language, crop, quantity,
        farmer_lat, farmer_lon, db,
    ):
        intent = self.detect_intent(message)
        context = self.build_context(
            intent, message, language, crop, quantity,
            farmer_lat, farmer_lon, db,
        )
        formatted_context = self._format_context_for_prompt(context)

        prompt = f"{formatted_context}\n\nFarmer's question: {message}\n\nAnswer the farmer's question using ONLY the verified data above. Respond in {get_language_name(language)}."

        client = self._get_client()
        if client is None:
            fallback = self._generate_fallback(intent, context, language)
            return {
                "answer": fallback,
                "language": language,
                "intent": intent,
                "context_used": [dp["type"] for dp in context["data_points"]],
                "data_status": "DEMO",
                "source": "fallback",
            }

        try:
            response = client.models.generate_content(
                model=settings.GEMINI_MODEL,
                contents=prompt,
                config={
                    "system_instruction": SYSTEM_INSTRUCTION,
                    "temperature": 0.3,
                    "max_output_tokens": 1024,
                },
            )
            answer = response.text
            return {
                "answer": answer,
                "language": language,
                "intent": intent,
                "context_used": [dp["type"] for dp in context["data_points"]],
                "data_status": "DEMO",
                "source": "gemini",
            }
        except Exception as e:
            logger.error("Gemini API error: %s", _redact_key(e))
            fallback = self._generate_fallback(intent, context, language)
            return {
                "answer": fallback,
                "language": language,
                "intent": intent,
                "context_used": [dp["type"] for dp in context["data_points"]],
                "data_status": "DEMO",
                "source": "fallback",
            }

    def _generate_fallback(self, intent, context, language):
        data_points = context.get("data_points", [])
        if not data_points:
            if language == "hi":
                return "Mujhe aapke sawaal ka jawab dene ke liye aur jaankari chahiye. Kripya batayein aapka fasal ka naam aur aap kahan hain."
            return "I need more information to answer your question. Please tell me your crop name and location."

        if intent == "price":
            prices = [dp for dp in data_points if dp["type"] == "current_price"]
            if prices:
                if language == "hi":
                    lines = [f"{p['market']}: {p['crop']} ka bhav INR {p['price_per_quintal']}/quintal hai." for p in prices]
                    return "Aaj ke bhav:\n" + "\n".join(lines)
                lines = [f"{p['market']}: {p['crop']} at INR {p['price_per_quintal']}/quintal." for p in prices]
                return "Current prices:\n" + "\n".join(lines)

        if intent == "market":
            markets = [dp for dp in data_points if dp["type"] == "market_comparison"]
            if markets:
                if language == "hi":
                    lines = []
                    for m in markets:
                        lines.append(
                            f"- {m['market']}: bhav INR {m['price']}/quintal, "
                            f"doori {m['distance_km']}km, transport INR {m['transport_cost']:.0f}, "
                            f"net profit INR {m['net_profit']:.0f}"
                        )
                    return "Mandiyan jo uplabdh hain:\n" + "\n".join(lines)
                lines = []
                for m in markets:
                    lines.append(
                        f"- {m['market']}: price INR {m['price']}/quintal, "
                        f"distance {m['distance_km']}km, transport INR {m['transport_cost']:.0f}, "
                        f"net profit INR {m['net_profit']:.0f}"
                    )
                return "Available markets:\n" + "\n".join(lines)

        if intent == "recommendation":
            recs = [dp for dp in data_points if dp["type"] == "recommendation"]
            if recs:
                r = recs[0]
                if language == "hi":
                    return f"Farmo ki salah: {r['recommendation']}\nKaran: {r['reason']}"
                return f"Farmo recommendation: {r['recommendation']}\nReason: {r['reason']}"

        if intent == "profit":
            profits = [dp for dp in data_points if dp["type"] == "profit_summary"]
            if profits:
                p = profits[0]
                if language == "hi":
                    return (
                        f"{p['best_market']} mein aapka expected net profit INR {p['net_profit']:.0f} hai.\n"
                        f"Bhav: INR {p['price_per_quintal']}/quintal, Transport: INR {p['transport_cost']:.0f}."
                    )
                return (
                    f"Expected net profit at {p['best_market']}: INR {p['net_profit']:.0f}.\n"
                    f"Price: INR {p['price_per_quintal']}/quintal, Transport: INR {p['transport_cost']:.0f}."
                )

        if language == "hi":
            return "Aapke sawaal ka jawab dene ke liye data taiyar hai. Kripya thoda aur spasht karein."
        return "Data is available to answer your question. Please be more specific."


gemini_service = GeminiService()
