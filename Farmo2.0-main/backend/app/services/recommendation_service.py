from typing import List, Tuple
from sqlalchemy.orm import Session
from app.services.profit_service import profit_service
from app.services.price_service import price_service


class RecommendationService:
    NET_PROFIT_ADVANTAGE_THRESHOLD = 0.10
    TREND_SIGNIFICANCE_THRESHOLD = 5.0

    def evaluate_sell_wait(
        self,
        crop: str,
        quantity: float,
        quantity_unit: str,
        farmer_lat: float,
        farmer_lon: float,
        storage_available: bool,
        db: Session,
        weather_risk: str | None = None,
    ) -> dict:
        profit_data = profit_service.calculate_for_all_markets(
            crop=crop,
            quantity=quantity,
            quantity_unit=quantity_unit,
            farmer_lat=farmer_lat,
            farmer_lon=farmer_lon,
            db=db,
        )

        if not profit_data["markets"]:
            return {
                "recommendation": "WAIT",
                "reason": f"No current market data available for {crop}. Cannot make a recommendation.",
                "factors": [],
                "uncertainty": "Insufficient data to provide a recommendation.",
                "data_status": "DEMO",
                "best_market_name": None,
                "best_market_net_profit": None,
            }

        best_market = profit_data["markets"][0]
        second_market = profit_data["markets"][1] if len(profit_data["markets"]) > 1 else None

        trend_data = price_service.get_price_trend(
            crop, best_market["market_id"], 30, db
        )
        trend = trend_data["trend"]

        highest_price_market = max(
            profit_data["markets"], key=lambda m: m["price_per_quintal"]
        )

        factors = []
        recommendation, reason = self._determine_recommendation(
            best_market=best_market,
            second_market=second_market,
            highest_price_market=highest_price_market,
            trend=trend,
            storage_available=storage_available,
            quantity=quantity,
            quantity_unit=quantity_unit,
            crop=crop,
            factors=factors,
            weather_risk=weather_risk,
        )

        uncertainty_parts = []
        if trend_data["current_price"] == 0:
            uncertainty_parts.append("Limited historical price data available.")
        uncertainty_parts.append("Transport costs are estimates based on straight-line distance; actual road distance may be 20-40% longer.")
        uncertainty_parts.append("Weather and demand conditions may affect actual outcomes.")
        uncertainty_parts.append("Trend analysis is based on historical data and does not guarantee future prices.")
        uncertainty = " ".join(uncertainty_parts)

        return {
            "recommendation": recommendation,
            "reason": reason,
            "factors": factors,
            "uncertainty": uncertainty,
            "data_status": "DEMO",
            "best_market_name": best_market["market_name"],
            "best_market_net_profit": best_market["net_profit"],
            "weather_risk": weather_risk,
        }

    def _determine_recommendation(
        self,
        best_market: dict,
        second_market: dict | None,
        highest_price_market: dict,
        trend: str,
        storage_available: bool,
        quantity: float,
        quantity_unit: str,
        crop: str,
        factors: list,
        weather_risk: str | None = None,
    ) -> Tuple[str, str]:

        self._add_price_factor(best_market, factors)
        self._add_trend_factor(trend, best_market, factors)
        self._add_transport_factor(best_market, quantity, quantity_unit, factors)
        self._add_storage_factor(storage_available, factors)
        self._add_weather_factor(weather_risk, factors)

        has_higher_price_market = (
            highest_price_market["market_id"] != best_market["market_id"]
        )

        if not storage_available:
            return self._no_storage_case(
                best_market, second_market, has_higher_price_market,
                highest_price_market, trend, factors,
            )

        if trend == "increasing":
            return self._increasing_trend_case(
                best_market, second_market, factors,
            )

        if trend == "decreasing":
            return self._decreasing_trend_case(
                best_market, second_market, has_higher_price_market,
                highest_price_market, factors,
            )

        return self._stable_trend_case(
            best_market, second_market, has_higher_price_market,
            highest_price_market, factors,
        )

    def _add_price_factor(self, best_market: dict, factors: list):
        impact = "positive" if best_market["net_profit"] > 0 else "negative"
        factors.append({
            "factor": "Current Price",
            "impact": impact,
            "detail": (
                f"Best market ({best_market['market_name']}) offers INR "
                f"{best_market['price_per_quintal']:.0f}/quintal with expected "
                f"net profit of INR {best_market['net_profit']:.0f}."
            ),
        })

    def _add_trend_factor(self, trend: str, best_market: dict, factors: list):
        trend_impact = (
            "positive" if trend == "increasing"
            else ("negative" if trend == "decreasing" else "neutral")
        )
        factors.append({
            "factor": "Price Trend",
            "impact": trend_impact,
            "detail": f"Prices at the best market have been {trend} over the last 30 days.",
        })

    def _add_transport_factor(self, best_market: dict, quantity: float, quantity_unit: str, factors: list):
        factors.append({
            "factor": "Transport Cost",
            "impact": "negative",
            "detail": (
                f"Estimated transport cost to {best_market['market_name']}: "
                f"INR {best_market['transport_cost']:.0f} for {quantity} {quantity_unit}."
            ),
        })

    def _add_storage_factor(self, storage_available: bool, factors: list):
        if storage_available:
            factors.append({
                "factor": "Storage",
                "impact": "positive",
                "detail": "Storage is available. Can consider waiting for better prices.",
            })
        else:
            factors.append({
                "factor": "Storage",
                "impact": "negative",
                "detail": "No storage available. Delaying sale may lead to crop spoilage.",
            })

    def _add_weather_factor(self, weather_risk: str | None, factors: list):
        if weather_risk is None or weather_risk == "unknown":
            return
        if weather_risk == "high":
            factors.append({
                "factor": "Weather Risk",
                "impact": "negative",
                "detail": "Severe weather conditions detected. Consider selling soon to avoid potential crop damage or transport disruption.",
            })
        elif weather_risk == "moderate":
            factors.append({
                "factor": "Weather Risk",
                "impact": "negative",
                "detail": "Moderate weather risk (rain/storm). Factor this into transport and storage decisions.",
            })
        else:
            factors.append({
                "factor": "Weather Risk",
                "impact": "positive",
                "detail": "Weather conditions are favorable for transport and storage.",
            })

    def _no_storage_case(
        self, best_market, second_market, has_higher_price_market,
        highest_price_market, trend, factors,
    ) -> Tuple[str, str]:
        if second_market and second_market["net_profit"] > best_market["net_profit"]:
            factors.append({
                "factor": "Better Market Available",
                "impact": "positive",
                "detail": (
                    f"{second_market['market_name']} offers higher expected net profit "
                    f"(INR {second_market['net_profit']:.0f}) than {best_market['market_name']} "
                    f"(INR {best_market['net_profit']:.0f})."
                ),
            })
            reason = (
                f"{second_market['market_name']} provides higher expected net profit of "
                f"INR {second_market['net_profit']:.0f} than {best_market['market_name']} "
                f"(INR {best_market['net_profit']:.0f}). Sell in another market."
            )
            return "SELL_IN_ANOTHER_MARKET", reason

        if has_higher_price_market and trend == "decreasing":
            factors.append({
                "factor": "Price Declining Without Storage",
                "impact": "negative",
                "detail": (
                    f"Prices are declining and no storage is available. "
                    f"Sell now at {best_market['market_name']} to avoid further losses."
                ),
            })
            reason = (
                f"Prices are declining at {best_market['market_name']} and no storage is "
                f"available. Sell now to avoid further price drops."
            )
            return "SELL_NOW", reason

        factors.append({
            "factor": "Immediate Sale Recommended",
            "impact": "positive",
            "detail": (
                f"No storage available. {best_market['market_name']} offers the best "
                f"net profit of INR {best_market['net_profit']:.0f}. Sell now."
            ),
        })
        reason = (
            f"No storage available. {best_market['market_name']} offers the best expected "
            f"net profit of INR {best_market['net_profit']:.0f}. Sell now."
        )
        return "SELL_NOW", reason

    def _increasing_trend_case(
        self, best_market, second_market, factors,
    ) -> Tuple[str, str]:
        factors.append({
            "factor": "Rising Prices With Storage",
            "impact": "positive",
            "detail": (
                "Prices are trending upward and storage is available. "
                "Waiting may yield better returns."
            ),
        })

        if second_market and second_market["net_profit"] > best_market["net_profit"]:
            factors.append({
                "factor": "Better Market Available",
                "impact": "positive",
                "detail": (
                    f"{second_market['market_name']} offers higher net profit "
                    f"(INR {second_market['net_profit']:.0f}). Consider selling there, "
                    f"or wait for better prices at the current best market."
                ),
            })
            reason = (
                f"Prices are trending upward with storage available, but "
                f"{second_market['market_name']} offers higher net profit "
                f"(INR {second_market['net_profit']:.0f}). Consider waiting or selling "
                f"at {second_market['market_name']}."
            )
            return "SELL_IN_ANOTHER_MARKET", reason

        reason = (
            f"Prices at {best_market['market_name']} are trending upward and storage is "
            f"available. Waiting may result in better returns with an expected net profit "
            f"of INR {best_market['net_profit']:.0f} currently."
        )
        return "WAIT", reason

    def _decreasing_trend_case(
        self, best_market, second_market, has_higher_price_market,
        highest_price_market, factors,
    ) -> Tuple[str, str]:
        factors.append({
            "factor": "Declining Prices",
            "impact": "negative",
            "detail": (
                "Prices are trending downward. Holding may result in lower returns."
            ),
        })

        if second_market and second_market["net_profit"] > best_market["net_profit"]:
            factors.append({
                "factor": "Better Market Available",
                "impact": "positive",
                "detail": (
                    f"{second_market['market_name']} offers higher net profit "
                    f"(INR {second_market['net_profit']:.0f})."
                ),
            })
            reason = (
                f"Prices are declining and {second_market['market_name']} offers higher "
                f"net profit (INR {second_market['net_profit']:.0f}). Sell in another market."
            )
            return "SELL_IN_ANOTHER_MARKET", reason

        factors.append({
            "factor": "Sell Now to Avoid Losses",
            "impact": "positive",
            "detail": (
                f"Declining prices make waiting risky. {best_market['market_name']} offers "
                f"the best current net profit of INR {best_market['net_profit']:.0f}."
            ),
        })
        reason = (
            f"Prices are declining at {best_market['market_name']}. "
            f"Sell now to avoid further price drops. Expected net profit: "
            f"INR {best_market['net_profit']:.0f}."
        )
        return "SELL_NOW", reason

    def _stable_trend_case(
        self, best_market, second_market, has_higher_price_market,
        highest_price_market, factors,
    ) -> Tuple[str, str]:
        factors.append({
            "factor": "Stable Prices",
            "impact": "neutral",
            "detail": "Prices have been relatively stable over the last 30 days.",
        })

        if second_market and second_market["net_profit"] > best_market["net_profit"]:
            factors.append({
                "factor": "Better Market Available",
                "impact": "positive",
                "detail": (
                    f"{second_market['market_name']} offers higher net profit "
                    f"(INR {second_market['net_profit']:.0f})."
                ),
            })
            reason = (
                f"Prices are stable but {second_market['market_name']} offers higher "
                f"net profit (INR {second_market['net_profit']:.0f}). "
                f"Sell in another market."
            )
            return "SELL_IN_ANOTHER_MARKET", reason

        factors.append({
            "factor": "Current Market is Best",
            "impact": "positive",
            "detail": (
                f"{best_market['market_name']} offers the highest expected net profit "
                f"of INR {best_market['net_profit']:.0f} among all compared markets."
            ),
        })
        reason = (
            f"Prices are stable. {best_market['market_name']} offers the best expected "
            f"net profit of INR {best_market['net_profit']:.0f}. Sell now."
        )
        return "SELL_NOW", reason


recommendation_service = RecommendationService()
