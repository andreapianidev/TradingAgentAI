"""
DeepSeek LLM client for trading decisions.
"""
import json
import re
from typing import Dict, Any, Optional, List, Tuple

import httpx

from config.settings import settings
from config.prompts import (
    get_system_prompt,
    build_user_prompt,
    get_decision_correction_prompt
)
from utils.logger import get_logger, log_trade_decision, log_llm_request, log_llm_response
from core.cost_tracker import calculate_llm_cost

logger = get_logger(__name__)


class DeepSeekClient:
    """Client for DeepSeek API interactions."""

    def __init__(self):
        """Initialize the DeepSeek client."""
        self.api_key = settings.DEEPSEEK_API_KEY
        self.base_url = settings.DEEPSEEK_BASE_URL
        self.model = settings.MODEL_NAME
        self.temperature = settings.LLM_TEMPERATURE
        self.max_tokens = settings.LLM_MAX_TOKENS
        self._client = None

    def _get_client(self) -> httpx.Client:
        """Get or create HTTP client."""
        if self._client is None:
            self._client = httpx.Client(
                base_url=self.base_url,
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
                timeout=60.0
            )
        return self._client

    def close(self) -> None:
        """Close the HTTP client."""
        if self._client:
            self._client.close()
            self._client = None

    def get_trading_decision(
        self,
        symbol: str,
        portfolio: Dict[str, Any],
        market_data: Dict[str, Any],
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any],
        forecast: Dict[str, Any],
        orderbook: Dict[str, Any],
        sentiment: Dict[str, Any],
        news_data: Dict[str, Any],
        open_positions: List[Dict[str, Any]],
        whale_flow: Dict[str, Any] = None,
        coingecko: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Get trading decision from DeepSeek LLM.

        Args:
            symbol: Trading symbol
            portfolio: Portfolio information
            market_data: Current market data
            indicators: Technical indicators
            pivot_points: Pivot point levels
            forecast: Prophet forecast
            orderbook: Order book data
            sentiment: Market sentiment (Fear & Greed Index)
            news_data: Advanced news analysis data with aggregated sentiment
            open_positions: Currently open positions
            whale_flow: Whale capital flow analysis
            coingecko: CoinGecko market data (global, trending, coins)

        Returns:
            Tuple of (decision_dict, usage_metadata)
            - decision_dict: Trading decision with action, direction, leverage, etc.
            - usage_metadata: Token usage and cost information
        """
        total_usage = {
            "input_tokens": 0,
            "output_tokens": 0,
            "cached_tokens": 0,
            "cost_usd": 0.0,
            "calls": 0
        }

        try:
            # Build prompts
            system_prompt = get_system_prompt()
            user_prompt = build_user_prompt(
                symbol=symbol,
                portfolio=portfolio,
                market_data=market_data,
                indicators=indicators,
                pivot_points=pivot_points,
                forecast=forecast,
                orderbook=orderbook,
                sentiment=sentiment,
                news_data=news_data,
                open_positions=open_positions,
                whale_flow=whale_flow,
                coingecko=coingecko
            )

            # Log the LLM request with prompts
            log_llm_request(symbol, system_prompt, user_prompt)

            # Make API call
            response, usage = self._call_api(system_prompt, user_prompt)

            # Accumulate usage
            if usage:
                total_usage["input_tokens"] += usage.get("input_tokens", 0)
                total_usage["output_tokens"] += usage.get("output_tokens", 0)
                total_usage["cached_tokens"] += usage.get("cached_tokens", 0)
                total_usage["cost_usd"] += usage.get("cost_usd", 0)
                total_usage["calls"] += 1

            if response is None:
                logger.error("No response from DeepSeek API")
                log_llm_response(symbol, None, None)
                return self._default_hold_decision(symbol), total_usage

            # Parse response
            decision = self._parse_response(response)

            # Log the LLM response
            log_llm_response(symbol, response, decision)

            if decision is None:
                # Try to correct invalid response
                decision, retry_usage = self._retry_with_correction(
                    system_prompt, user_prompt, response
                )
                # Accumulate retry usage
                if retry_usage:
                    total_usage["input_tokens"] += retry_usage.get("input_tokens", 0)
                    total_usage["output_tokens"] += retry_usage.get("output_tokens", 0)
                    total_usage["cached_tokens"] += retry_usage.get("cached_tokens", 0)
                    total_usage["cost_usd"] += retry_usage.get("cost_usd", 0)
                    total_usage["calls"] += 1

            if decision is None:
                logger.warning("Failed to parse LLM response, defaulting to HOLD")
                return self._default_hold_decision(symbol), total_usage

            # Log the decision
            log_trade_decision(
                symbol=decision.get("symbol", symbol),
                action=decision.get("action", "hold"),
                direction=decision.get("direction"),
                confidence=decision.get("confidence", 0),
                reasoning=decision.get("reasoning", "No reasoning provided")
            )

            return decision, total_usage

        except Exception as e:
            logger.error(f"Error getting trading decision: {e}")
            return self._default_hold_decision(symbol), total_usage

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Tuple[Optional[str], Dict[str, Any]]:
        """
        Make API call to DeepSeek.

        Returns:
            Tuple of (content, usage_metadata)
            - content: Response text or None on error
            - usage_metadata: Token usage and cost info
        """
        try:
            client = self._get_client()

            payload = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": self.temperature,
                "max_tokens": self.max_tokens,
            }

            response = client.post("/v1/chat/completions", json=payload)
            response.raise_for_status()

            data = response.json()
            content = data["choices"][0]["message"]["content"]

            # Extract token usage from response
            usage = data.get("usage", {})
            input_tokens = usage.get("prompt_tokens", 0)
            output_tokens = usage.get("completion_tokens", 0)
            cached_tokens = usage.get("prompt_cache_hit_tokens", 0)

            # Calculate cost
            cost_usd = calculate_llm_cost(input_tokens, output_tokens, cached_tokens)

            usage_metadata = {
                "input_tokens": input_tokens,
                "output_tokens": output_tokens,
                "cached_tokens": cached_tokens,
                "total_tokens": input_tokens + output_tokens,
                "cost_usd": cost_usd,
                "model": self.model,
                "provider": "deepseek"
            }

            logger.debug(f"DeepSeek response: {content[:200]}...")
            logger.debug(f"Token usage: {input_tokens} in, {output_tokens} out, ${cost_usd:.6f}")

            return content, usage_metadata

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API HTTP error: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            return None, {}
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return None, {}

    def _parse_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from LLM."""
        try:
            # Try to extract JSON from response
            # Remove any markdown code blocks
            cleaned = response.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)

            # Try to find JSON in the response
            json_match = re.search(r'\{[^{}]*\}', cleaned, re.DOTALL)
            if json_match:
                cleaned = json_match.group()

            decision = json.loads(cleaned)

            # Validate required fields
            required_fields = ["action", "symbol", "confidence"]
            for field in required_fields:
                if field not in decision:
                    logger.warning(f"Missing required field: {field}")
                    return None

            # Validate action
            if decision["action"] not in ["open", "close", "hold"]:
                logger.warning(f"Invalid action: {decision['action']}")
                return None

            # Validate direction for open action
            if decision["action"] == "open":
                if decision.get("direction") not in ["long", "short"]:
                    logger.warning("Open action requires valid direction")
                    return None

                # Validate TP/SL fields for open action
                if not decision.get("stop_loss_pct"):
                    logger.warning("Open action requires stop_loss_pct")
                    return None

                if not decision.get("take_profit_pct"):
                    logger.warning("Open action requires take_profit_pct")
                    return None

                # Validate tp_sl_reasoning (required for tracking and audit)
                if not decision.get("tp_sl_reasoning"):
                    logger.warning(
                        "Open action requires tp_sl_reasoning - "
                        "LLM must explain why these TP/SL values were chosen"
                    )
                    return None

            return decision

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing response: {e}")
            return None

    def _retry_with_correction(
        self,
        system_prompt: str,
        original_user_prompt: str,
        invalid_response: str
    ) -> Tuple[Optional[Dict[str, Any]], Dict[str, Any]]:
        """
        Retry API call with correction prompt.

        Returns:
            Tuple of (decision, usage_metadata)
        """
        try:
            correction_prompt = get_decision_correction_prompt(
                "La risposta non era un JSON valido o mancavano campi richiesti",
                invalid_response
            )

            # Combine original prompt with correction
            combined_prompt = f"{original_user_prompt}\n\n{correction_prompt}"

            response, usage = self._call_api(system_prompt, combined_prompt)

            if response:
                return self._parse_response(response), usage

            return None, usage

        except Exception as e:
            logger.error(f"Error in retry: {e}")
            return None, {}

    def _default_hold_decision(self, symbol: str) -> Dict[str, Any]:
        """Return default HOLD decision."""
        return {
            "action": "hold",
            "symbol": symbol,
            "direction": None,
            "leverage": None,
            "position_size_pct": None,
            "stop_loss_pct": None,
            "take_profit_pct": None,
            "confidence": 0.0,
            "reasoning": "Default hold due to API error or invalid response"
        }

    def test_connection(self) -> bool:
        """Test API connection."""
        try:
            response, usage = self._call_api(
                "You are a helpful assistant.",
                "Say 'OK' if you can hear me."
            )
            return response is not None and "OK" in response.upper()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False

    def generate_market_analysis(
        self,
        symbol: str,
        price: float,
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any],
        forecast: Dict[str, Any],
        sentiment: Dict[str, Any],
        news_data: Dict[str, Any],
        whale_flow: Dict[str, Any] = None
    ) -> Tuple[Dict[str, Any], Dict[str, Any]]:
        """
        Generate a daily market analysis summary using DeepSeek.

        Args:
            symbol: Trading symbol (BTC, ETH, SOL)
            price: Current price
            indicators: Technical indicators
            pivot_points: Pivot point levels
            forecast: Prophet forecast
            sentiment: Market sentiment (Fear & Greed)
            news_data: Advanced news analysis data from news_analyzer
            whale_flow: Whale capital flow

        Returns:
            Tuple of (analysis_dict, usage_metadata)
            - analysis_dict: Analysis with summary, outlook, key levels, etc.
            - usage_metadata: Token usage and cost information
        """
        try:
            system_prompt = """Sei un analista finanziario esperto di criptovalute.
Genera un'analisi di mercato concisa e professionale in italiano.
La tua analisi deve essere oggettiva, basata sui dati forniti, e utile per i trader.
Rispondi SOLO con un JSON valido senza markdown o commenti."""

            # Build advanced news summary from analysis
            news_summary = ""
            if news_data:
                agg_sentiment = news_data.get("aggregated_sentiment", {})
                symbol_sentiment = news_data.get("symbol_sentiment", {})
                total_analyzed = news_data.get("total_analyzed", 0)
                high_impact = news_data.get("high_impact_count", 0)

                news_summary = f"""NEWS SENTIMENT (AI-analyzed):
- Articles analyzed: {total_analyzed}
- High impact news: {high_impact}
- Aggregated score: {agg_sentiment.get('score', 0):.2f} ({agg_sentiment.get('label', 'neutral')})
- {symbol} specific: {symbol_sentiment.get('score', 0):.2f} ({symbol_sentiment.get('label', 'neutral')})
- Interpretation: {agg_sentiment.get('interpretation', 'N/A')}"""

            whale_summary = ""
            if whale_flow:
                net = whale_flow.get("net_flow", 0)
                whale_summary = f"Whale Flow: ${net:,.0f} net ({whale_flow.get('interpretation', 'N/A')})"

            user_prompt = f"""Analizza {symbol}/USD e genera un report di mercato.

DATI ATTUALI:
- Prezzo: ${price:,.2f}
- RSI (14): {indicators.get('rsi', 'N/A'):.1f}
- MACD: {indicators.get('macd', 0):.4f} (Signal: {indicators.get('macd_signal', 0):.4f})
- MACD Trend: {'Bullish' if indicators.get('macd_bullish') else 'Bearish'}
- EMA2: ${indicators.get('ema2', 0):.2f} | EMA20: ${indicators.get('ema20', 0):.2f}
- Price vs EMA20: {'Above' if indicators.get('price_above_ema20') else 'Below'}

PIVOT POINTS:
- R2: ${pivot_points.get('r2', 0):.2f}
- R1: ${pivot_points.get('r1', 0):.2f}
- PP: ${pivot_points.get('pp', 0):.2f}
- S1: ${pivot_points.get('s1', 0):.2f}
- S2: ${pivot_points.get('s2', 0):.2f}

FORECAST (4h):
- Trend: {forecast.get('trend', 'N/A')}
- Target: ${forecast.get('target_price', 0):.2f}
- Change: {forecast.get('change_pct', 0):+.2f}%

SENTIMENT:
- Fear & Greed: {sentiment.get('score', 50)} ({sentiment.get('label', 'NEUTRAL')})
{news_summary}
{whale_summary}

Genera un JSON con questa struttura esatta:
{{
    "summary_text": "Analisi di 3-4 frasi concise che descrivono la situazione attuale del mercato, i livelli chiave e le prospettive a breve termine.",
    "market_outlook": "bullish|bearish|neutral|volatile",
    "confidence_score": 0.0-1.0,
    "trend_strength": "strong|moderate|weak",
    "momentum": "increasing|decreasing|stable",
    "volatility_level": "high|medium|low",
    "key_levels": {{
        "resistance_1": numero,
        "resistance_2": numero,
        "support_1": numero,
        "support_2": numero
    }},
    "risk_factors": ["rischio 1", "rischio 2"],
    "opportunities": ["opportunità 1", "opportunità 2"]
}}"""

            response, usage = self._call_api(system_prompt, user_prompt)

            if response is None:
                logger.error("No response from DeepSeek for market analysis")
                return self._default_analysis(symbol, price, indicators, pivot_points), usage

            # Parse response
            analysis = self._parse_analysis_response(response)

            if analysis is None:
                logger.warning("Failed to parse analysis response, using default")
                return self._default_analysis(symbol, price, indicators, pivot_points), usage

            logger.info(f"Generated AI analysis for {symbol}: {analysis.get('market_outlook', 'N/A')}")
            return analysis, usage

        except Exception as e:
            logger.error(f"Error generating market analysis: {e}")
            return self._default_analysis(symbol, price, indicators, pivot_points), {}

    def _parse_analysis_response(self, response: str) -> Optional[Dict[str, Any]]:
        """Parse JSON response from analysis."""
        try:
            cleaned = response.strip()
            cleaned = re.sub(r'^```json\s*', '', cleaned)
            cleaned = re.sub(r'\s*```$', '', cleaned)
            cleaned = re.sub(r'^```\s*', '', cleaned)

            # Try to find JSON in the response
            json_match = re.search(r'\{[\s\S]*\}', cleaned)
            if json_match:
                cleaned = json_match.group()

            analysis = json.loads(cleaned)

            # Validate required fields
            required_fields = ["summary_text", "market_outlook"]
            for field in required_fields:
                if field not in analysis:
                    logger.warning(f"Missing required field in analysis: {field}")
                    return None

            return analysis

        except json.JSONDecodeError as e:
            logger.warning(f"JSON parse error in analysis: {e}")
            return None
        except Exception as e:
            logger.warning(f"Error parsing analysis: {e}")
            return None

    def _default_analysis(
        self,
        symbol: str,
        price: float,
        indicators: Dict[str, Any],
        pivot_points: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Return default analysis when API fails."""
        rsi = indicators.get('rsi', 50)
        macd_bullish = indicators.get('macd_bullish', False)

        # Determine outlook based on indicators
        if rsi > 70:
            outlook = "bearish"
            summary = f"{symbol} mostra segnali di ipercomprato con RSI a {rsi:.1f}. Si consiglia cautela per nuove posizioni long."
        elif rsi < 30:
            outlook = "bullish"
            summary = f"{symbol} in zona di ipervenduto con RSI a {rsi:.1f}. Potenziale opportunità di acquisto."
        elif macd_bullish:
            outlook = "bullish"
            summary = f"{symbol} mostra momentum positivo con MACD bullish. Trend in corso potrebbe continuare."
        else:
            outlook = "neutral"
            summary = f"{symbol} in fase di consolidamento. Attendere segnali più chiari prima di operare."

        return {
            "summary_text": summary,
            "market_outlook": outlook,
            "confidence_score": 0.5,
            "trend_strength": "moderate",
            "momentum": "stable",
            "volatility_level": "medium",
            "key_levels": {
                "resistance_1": pivot_points.get('r1', price * 1.02),
                "resistance_2": pivot_points.get('r2', price * 1.05),
                "support_1": pivot_points.get('s1', price * 0.98),
                "support_2": pivot_points.get('s2', price * 0.95)
            },
            "risk_factors": ["Volatilità di mercato", "Sentiment incerto"],
            "opportunities": ["Livelli chiave da monitorare"]
        }


# Global client instance
llm_client = DeepSeekClient()
