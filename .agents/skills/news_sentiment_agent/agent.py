import logging
from typing import List, AsyncGenerator, Any
from pydantic import BaseModel, Field
from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.events import Event
from google.genai import types

logger = logging.getLogger("marketmind.news_sentiment_agent")

class NewsSentimentOutput(BaseModel):
    """Pydantic model for the structured news sentiment analysis output."""
    sentiment_score: float = Field(
        description="The overall sentiment score of the asset, ranging from -1.0 (very negative) to 1.0 (very positive)."
    )
    key_themes: List[str] = Field(
        description="Key financial or market themes identified across the news headlines."
    )
    notable_events: List[str] = Field(
        description="Specific events mentioned in the headlines."
    )

class NewsSentimentAgent(BaseAgent):
    """Custom Agent performing fast keyword-based sentiment analysis directly in Python.

    Design Decision: To conserve Gemini API requests (free tier rate limits), this agent
    processes news headlines using Python string matching rather than an LLM call.
    It counts positive and negative financial terms to calculate a sentiment score
    between -1.0 and 1.0, and extracts themes and events dynamically.
    """

    def __init__(self, name: str = "news_sentiment_agent", **kwargs):
        super().__init__(name=name, **kwargs)

    @property
    def output_key(self) -> str:
        return "news_sentiment_result"

    async def _run_async_impl(self, ctx: InvocationContext) -> AsyncGenerator[Event, None]:
        input_text = ""
        if ctx.user_content and ctx.user_content.parts:
            input_text = ctx.user_content.parts[0].text or ""

        # Positive and negative keyword lists
        pos_keywords = ["up", "rise", "gain", "bullish", "growth", "profit", "beat", "positive", "partnership", "soar", "surge", "higher", "optimistic", "success"]
        neg_keywords = ["down", "fall", "loss", "bearish", "decline", "regulatory", "pressure", "drop", "lower", "cautious", "risk", "shortage", "miss", "investigation"]

        # Parse headlines (lines starting with a number e.g. "1. Headline...")
        headlines = []
        for line in input_text.split("\n"):
            cleaned = line.strip()
            # Look for number patterns like "1. ..."
            if cleaned and (cleaned[0].isdigit() or cleaned.startswith("-")):
                headlines.append(cleaned)

        pos_count = 0
        neg_count = 0
        text_lower = input_text.lower()
        
        # Simple word counter
        for word in pos_keywords:
            pos_count += text_lower.count(word)
        for word in neg_keywords:
            neg_count += text_lower.count(word)

        # Sentiment score bounded between -1.0 and 1.0
        total = pos_count + neg_count
        score = (pos_count - neg_count) / max(total, 1.0)
        score = max(-1.0, min(1.0, score))

        # Dynamically extract themes based on matches
        themes = []
        theme_keywords = {
            "Regulatory News": ["regulatory", "sec", "lawsuit", "investigation", "court", "compliance", "policy", "ban", "legal", "ruling"],
            "Market Sentiment": ["sentiment", "cautious", "optimistic", "bearish", "bullish", "outlook", "confidence", "fear", "greed", "volatility", "pressure"],
            "Institutional Adoption": ["institutional", "etf", "fund", "banks", "acquisition", "purchase", "secures", "investment", "inflow", "inflows", "outflow", "outflows"],
            "Price Action": ["price", "rise", "fall", "rally", "drop", "surge", "slump", "gain", "loss", "highs", "lows", "higher", "lower", "soar"],
            "Security/Hacks": ["security", "hack", "exploit", "breach", "vulnerability", "attack", "compromise", "scam", "phishing"],
            "Partnerships": ["partnership", "strategic", "alliance", "collaborate", "ventures", "joint venture", "collaborates"]
        }

        for category, kw_list in theme_keywords.items():
            if any(w in text_lower for w in kw_list):
                themes.append(category)

        # Fallback to general themes if none matched
        if not themes:
            themes = ["General Market Trend", "Macroeconomics", "Trading Volume"]
        themes = themes[:5]  # Cap at 5 themes

        # Extract notable events from top headlines
        events = []
        for h in headlines[:3]:
            # Clean headline number prefix e.g. "1. Headline" -> "Headline"
            clean_h = h.split(".", 1)[-1].strip() if "." in h else h.strip("- ")
            # Truncate source name suffix if present e.g. "(Source: Bloomberg...)"
            if " (source:" in clean_h.lower():
                clean_h = clean_h.split(" (Source:", 1)[0].split(" (source:", 1)[0]
            events.append(clean_h)

        if not events:
            events = ["No headlines available to parse."]

        result = NewsSentimentOutput(
            sentiment_score=round(score, 2),
            key_themes=themes,
            notable_events=events
        )

        event = Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=f"Sentiment analysis completed with score: {result.sentiment_score}")]
            )
        )
        event.actions.state_delta[self.output_key] = result
        yield event

def create_news_sentiment_agent() -> BaseAgent:
    """Factory function to create the News Sentiment Agent."""
    return NewsSentimentAgent()
