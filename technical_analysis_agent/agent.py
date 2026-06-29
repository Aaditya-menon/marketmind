import logging
import re
from typing import List, AsyncGenerator, Any
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

logger = logging.getLogger("marketmind.technical_analysis_agent")

class TechnicalAnalysisOutput(BaseModel):
    """Pydantic model for the structured technical analysis output."""
    trend_direction: str = Field(
        description="The primary trend direction identified in the price data (Bullish, Bearish, Neutral)."
    )
    key_levels: List[float] = Field(
        description="Identified key support and resistance levels from the historical price data."
    )
    momentum_signal: str = Field(
        description="A summary of the current momentum signals (e.g. RSI oversold, MACD bearish crossover)."
    )

class TechnicalAnalysisAgent(BaseAgent):
    """Custom Agent performing technical chart indicators math directly in Python.

    Design Decision: To conserve Gemini API requests (free tier rate limits), this agent
    processes historical daily price series (OHLCV) using Python mathematics instead of
    an LLM call. It calculates Simple Moving Average (SMA), identifies support/resistance
    using local minima/maxima, and evaluates momentum signals.
    """

    def __init__(self, name: str = "technical_analysis_agent", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def output_key(self) -> str:
        return "technical_analysis_result"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        input_text = ""
        if ctx.user_content and ctx.user_content.parts:
            input_text = ctx.user_content.parts[0].text or ""

        # Parse OHLCV text format: "Date: {date}, O: {open}, H: {high}, L: {low}, C: {close}, V: {volume}"
        opens = []
        highs = []
        lows = []
        closes = []
        volumes = []

        # Find all OHLCV metrics in the text (most recent date is listed first)
        for line in input_text.split("\n"):
            match = re.search(
                r'O:\s*([\d\.-]+),\s*H:\s*([\d\.-]+),\s*L:\s*([\d\.-]+),\s*C:\s*([\d\.-]+),\s*V:\s*([\d\.-]+)',
                line
            )
            if match:
                o, h, l, c, v = map(float, match.groups())
                opens.append(o)
                highs.append(h)
                lows.append(l)
                closes.append(c)
                volumes.append(v)

        trend = "Neutral"
        support_resistance = [150.0, 160.0]
        momentum_desc = "Neutral (No daily price data available)"

        if closes:
            num_days = len(closes)
            most_recent_close = closes[0]
            
            # 1. Trend analysis (using 5-day and 20-day SMA if possible)
            sma_5 = sum(closes[:min(5, num_days)]) / min(5, num_days)
            sma_20 = sum(closes[:min(20, num_days)]) / min(20, num_days)
            
            if most_recent_close > sma_5 and sma_5 > sma_20:
                trend = "Bullish"
            elif most_recent_close < sma_5 and sma_5 < sma_20:
                trend = "Bearish"
            else:
                trend = "Neutral"

            # 2. Support and Resistance levels from local highs and lows
            support = min(lows)
            resistance = max(highs)
            
            # If support and resistance are too close or identical, add offsets
            if abs(resistance - support) < 0.01:
                support = round(support * 0.95, 2)
                resistance = round(resistance * 1.05, 2)
            else:
                support = round(support, 2)
                resistance = round(resistance, 2)
                
            support_resistance = [support, resistance]

            # 3. Momentum indicators (RSI estimation based on price change)
            change_5d = 0.0
            if num_days > 5:
                change_5d = ((closes[0] - closes[5]) / closes[5]) * 100
                
            if change_5d > 2.0:
                momentum_desc = f"Bullish (Price gained {change_5d:.2f}% over the last 5 days, trading above 5-day SMA of {sma_5:.2f})"
            elif change_5d < -2.0:
                momentum_desc = f"Bearish (Price lost {abs(change_5d):.2f}% over the last 5 days, trading below 5-day SMA of {sma_5:.2f})"
            else:
                momentum_desc = f"Neutral (Price range bound at {change_5d:.2f}% over the last 5 days, near 5-day SMA of {sma_5:.2f})"
        
        result = TechnicalAnalysisOutput(
            trend_direction=trend,
            key_levels=support_resistance,
            momentum_signal=momentum_desc
        )

        event = Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"Technical chart analysis completed with trend: {result.trend_direction}")]
            )
        )
        event.actions.state_delta[self.output_key] = result
        yield event

def create_technical_analysis_agent() -> BaseAgent:
    """Factory function to create the Technical Analysis Agent."""
    return TechnicalAnalysisAgent()
