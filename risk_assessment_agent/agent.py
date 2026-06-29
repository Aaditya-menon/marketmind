import logging
import re
from typing import AsyncGenerator, Any, Literal
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

logger = logging.getLogger("marketmind.risk_assessment_agent")

class RiskAssessmentOutput(BaseModel):
    """Pydantic model for the structured risk assessment output."""
    thesis: str = Field(
        description="A synthesized investment or trading thesis combining sentiment analysis and technical analysis."
    )
    confidence_score: int = Field(
        description="Confidence score for the trade thesis, ranging from 0 to 100.",
        ge=0,
        le=100
    )
    risk_rating: str = Field(
        description="Assessed risk level based on market factors (Low, Medium, High)."
    )
    suggested_action: str = Field(
        description="Suggested action based on the thesis and risk assessment (Buy, Sell, Hold, Avoid)."
    )

class RiskAssessmentAgent(BaseAgent):
    """Custom Agent performing rule-based financial risk synthesis in Python.

    Design Decision: To conserve Gemini API requests (free tier rate limits), this agent
    processes technical indicators and sentiment scores using deterministic rules rather
    than calling an LLM. It generates a detailed 2-3 sentence trade thesis and assigns
    risk metrics.
    """

    def __init__(self, name: str = "risk_assessment_agent", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def output_key(self) -> str:
        return "risk_assessment_result"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        input_text = ""
        if ctx.user_content and ctx.user_content.parts:
            input_text = ctx.user_content.parts[0].text or ""

        sentiment = 0.0
        trend = "Neutral"
        momentum_text = ""

        # Parse sentiment score
        sent_match = re.search(r'Score:\s*([\d\.-]+)', input_text)
        if sent_match:
            sentiment = float(sent_match.group(1))

        # Parse technical trend
        trend_match = re.search(r'Trend:\s*(Bullish|Bearish|Neutral)', input_text)
        if trend_match:
            trend = trend_match.group(1)

        # Parse momentum signal
        mom_match = re.search(r'Momentum:\s*(.*)', input_text)
        if mom_match:
            momentum_text = mom_match.group(1)

        thesis = ""
        suggested_action = "Hold"
        confidence_score = 50
        risk_rating = "Medium"

        # Rule-based synthesis
        if sentiment > 0.3 and trend == "Bullish":
            thesis = (
                f"Bullish confluence: News sentiment is highly positive ({sentiment:.2f}) aligning with a strong "
                "bullish price trend. Key support levels are solid and buyer volume is robust, indicating high conviction "
                "for continued upward momentum."
            )
            suggested_action = "Buy"
            confidence_score = 80
        elif sentiment < -0.3 and trend == "Bearish":
            thesis = (
                f"Bearish confluence: News sentiment is highly negative ({sentiment:.2f}) aligning with a clear "
                "bearish chart breakdown. Institutional selling pressure combined with declining moving averages "
                "points to significant downside risk."
            )
            suggested_action = "Sell"
            confidence_score = 80
        else:
            # Mixed signals
            thesis = (
                f"Mixed signals: Sentiment is currently {sentiment:.2f} and technical trend direction is {trend}. "
                "The lack of directional alignment between public news sentiment and technical price charts suggest "
                "temporary consolidation or market uncertainty."
            )
            suggested_action = "Hold"
            confidence_score = 50

        # Assess risk rating based on momentum magnitude
        pct_match = re.search(r'(\d+\.\d+)%', momentum_text)
        if pct_match:
            pct_val = float(pct_match.group(1))
            if pct_val > 5.0:
                risk_rating = "High"
            elif pct_val > 2.0:
                risk_rating = "Medium"
            else:
                risk_rating = "Low"
        else:
            if "high" in momentum_text.lower() or "spike" in momentum_text.lower():
                risk_rating = "High"
            elif "range bound" in momentum_text.lower() or "neutral" in momentum_text.lower():
                risk_rating = "Low"

        result = RiskAssessmentOutput(
            thesis=thesis,
            confidence_score=confidence_score,
            risk_rating=risk_rating,
            suggested_action=suggested_action
        )

        event = Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"Risk assessment completed with action: {result.suggested_action}")]
            )
        )
        event.actions.state_delta[self.output_key] = result
        yield event

def create_risk_assessment_agent() -> BaseAgent:
    """Factory function to create the Risk Assessment Agent."""
    return RiskAssessmentAgent()
