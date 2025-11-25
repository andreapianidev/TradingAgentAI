"""
DeepSeek LLM client for trading decisions.
"""
import json
import re
from typing import Dict, Any, Optional, List

import httpx

from config.settings import settings
from config.prompts import (
    get_system_prompt,
    build_user_prompt,
    get_decision_correction_prompt
)
from utils.logger import get_logger, log_trade_decision

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
        news: List[Dict[str, Any]],
        open_positions: List[Dict[str, Any]],
        whale_flow: Dict[str, Any] = None
    ) -> Dict[str, Any]:
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
            sentiment: Market sentiment
            news: Recent news
            open_positions: Currently open positions
            whale_flow: Whale capital flow analysis

        Returns:
            Decision dictionary with action, direction, leverage, etc.
        """
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
                news=news,
                open_positions=open_positions,
                whale_flow=whale_flow
            )

            # Make API call
            response = self._call_api(system_prompt, user_prompt)

            if response is None:
                logger.error("No response from DeepSeek API")
                return self._default_hold_decision(symbol)

            # Parse response
            decision = self._parse_response(response)

            if decision is None:
                # Try to correct invalid response
                decision = self._retry_with_correction(
                    system_prompt, user_prompt, response
                )

            if decision is None:
                logger.warning("Failed to parse LLM response, defaulting to HOLD")
                return self._default_hold_decision(symbol)

            # Log the decision
            log_trade_decision(
                symbol=decision.get("symbol", symbol),
                action=decision.get("action", "hold"),
                direction=decision.get("direction"),
                confidence=decision.get("confidence", 0),
                reasoning=decision.get("reasoning", "No reasoning provided")
            )

            return decision

        except Exception as e:
            logger.error(f"Error getting trading decision: {e}")
            return self._default_hold_decision(symbol)

    def _call_api(
        self,
        system_prompt: str,
        user_prompt: str
    ) -> Optional[str]:
        """Make API call to DeepSeek."""
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

            logger.debug(f"DeepSeek response: {content[:200]}...")
            return content

        except httpx.HTTPStatusError as e:
            logger.error(f"DeepSeek API HTTP error: {e.response.status_code}")
            logger.error(f"Response: {e.response.text}")
            return None
        except Exception as e:
            logger.error(f"DeepSeek API error: {e}")
            return None

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
    ) -> Optional[Dict[str, Any]]:
        """Retry API call with correction prompt."""
        try:
            correction_prompt = get_decision_correction_prompt(
                "La risposta non era un JSON valido o mancavano campi richiesti",
                invalid_response
            )

            # Combine original prompt with correction
            combined_prompt = f"{original_user_prompt}\n\n{correction_prompt}"

            response = self._call_api(system_prompt, combined_prompt)

            if response:
                return self._parse_response(response)

            return None

        except Exception as e:
            logger.error(f"Error in retry: {e}")
            return None

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
            response = self._call_api(
                "You are a helpful assistant.",
                "Say 'OK' if you can hear me."
            )
            return response is not None and "OK" in response.upper()
        except Exception as e:
            logger.error(f"Connection test failed: {e}")
            return False


# Global client instance
llm_client = DeepSeekClient()
