import os
import re
import logging
import asyncio
import datetime
import traceback
from typing import AsyncGenerator, Any

from google.adk.agents import BaseAgent
from google.adk.agents.invocation_context import InvocationContext
from google.adk.agents.run_config import RunConfig
from google.adk.events import Event, RequestInput
from google.adk.workflow.utils._workflow_hitl_utils import create_request_input_event
from google.adk.sessions import Session
from google.adk.models import Gemini
from google.genai import types

from news_sentiment_agent.agent import create_news_sentiment_agent
from technical_analysis_agent.agent import create_technical_analysis_agent
from risk_assessment_agent.agent import create_risk_assessment_agent
from tools.fetch_news import fetch_news
from tools.fetch_price_data import fetch_price_data

logger = logging.getLogger("marketmind.orchestrator_agent")

"""
================================================================================
DESIGN DECISION: Human-In-The-Loop (HITL) in Financial Contexts
================================================================================
Human-In-The-Loop (HITL) is a critical pillar of Security and Trust in financial
agent architectures. Fully autonomous AI trading or advisory systems carry high
risks of financial loss due to market anomalies, data latency, hallucinations, 
or model misinterpretations.

By placing an interactive gate before executing the final risk assessment:
1. Trust & Oversight: The user (trader, analyst, or client) retains control,
   validating intermediate news sentiment and technical signals before executing
   a model-generated buy/sell recommendation.
2. Cost & Efficiency: Prevents expensive model syntheses on assets that fail
   initial criteria or do not align with user interest.
3. Verification: Ensures the human reviewer remains actively engaged and
   cognizant of raw data metrics rather than blindly trusting automated outputs.
================================================================================
"""

class OrchestratorAgent(BaseAgent):
    """Custom Orchestrator Agent that manages parallel execution of sub-agents and HITL checkpoints.

    Design Decisions:
    1. Derives from BaseAgent to provide deterministic custom orchestration logic.
    2. Private Pydantic attributes (prefixed with an underscore) are used for model and sub-agents
       to prevent Pydantic initialization errors.
    3. Uses model.api_client to call Gemini directly for ticker extraction.
    4. Leverages asyncio.gather to fetch news and price data, and then invoke news sentiment
       and technical analysis sub-agents in parallel.
    5. Runs sub-agents in isolated InvocationContext branches to prevent state contamination,
       passing through run_config and context_cache_config.
    6. Implements Human-in-the-Loop (HITL) via RequestInput before executing the risk assessment.
    7. Implements graceful error handling to report partial analysis if a sub-agent fails.
    """

    def __init__(self, name: str = "orchestrator_agent", model: Any = None, **kwargs):
        super().__init__(name=name, **kwargs)
        self._model = model or Gemini(model="gemini-2.5-flash")
        
        # Instantiate the specialist agents
        self._news_agent = create_news_sentiment_agent()
        self._tech_agent = create_technical_analysis_agent()
        self._risk_agent = create_risk_assessment_agent()

    async def _run_async_impl(
        self, ctx: InvocationContext
    ) -> AsyncGenerator[Event, None]:
        # 1. Extract the ticker from the initial user text prompt in the session history.
        # Since resumption sends a FunctionResponse (with no text), we scan past events for the first user text.
        user_msg = ""
        for event in ctx.session.events:
            if event.author == "user" and event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        user_msg = part.text
                        break
            if user_msg:
                break
        
        if not user_msg and ctx.user_content and ctx.user_content.parts:
            user_msg = ctx.user_content.parts[0].text
        
        if not user_msg:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Error: Could not retrieve user input.")]
                )
            )
            return

        # Use LLM to extract ticker symbol cleanly
        prompt = (
            "Extract the stock or cryptocurrency ticker symbol from the following user message. "
            "Return ONLY the ticker symbol in uppercase, with no extra characters, text, punctuation or markdown.\n"
            f"User Message: {user_msg}"
        )
        try:
            llm_response = await self._model.api_client.aio.models.generate_content(
                model=self._model.model,
                contents=prompt
            )
            ticker = llm_response.text.strip().upper()
            ticker = re.sub(r'[^A-Z0-9\-]', '', ticker)
        except Exception as e:
            logger.warning(f"Failed to extract ticker via LLM: {e}. Falling back to regex.")
            match = re.search(r'\b[A-Za-z0-9\-]{2,10}\b', user_msg.strip().upper())
            ticker = match.group(0) if match else "UNKNOWN"

        if not ticker or ticker == "UNKNOWN":
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text="Error: Could not identify a valid ticker symbol in your message.")]
                )
            )
            return

        # Yield status event ONLY if this is the first turn (no HITL response in history yet)
        hitl_id = f"hitl_confirm_{ticker}"
        user_choice = None
        
        # Scan session events for a past user response matching this interrupt ID
        for event in ctx.session.events:
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if (
                        part.function_response
                        and part.function_response.name == "adk_request_input"
                        and part.function_response.id == hitl_id
                    ):
                        resp_data = part.function_response.response
                        if isinstance(resp_data, dict):
                            user_choice = resp_data.get("result") or resp_data.get("value") or (list(resp_data.values())[0] if resp_data else None)
                        else:
                            user_choice = resp_data
                        break

        if user_choice is None:
            yield Event(
                author=self.name,
                content=types.Content(
                    role="model",
                    parts=[types.Part.from_text(text=f"Analyzing market data for **{ticker}**...")]
                )
            )

        # 2. Call news and price data tools in parallel
        news_task = fetch_news(ticker)
        price_task = fetch_price_data(ticker)
        news_result, price_result = await asyncio.gather(news_task, price_task)

        # 3. Format inputs for sub-agents
        headlines_text = ""
        if news_result.get("status") in ("success", "fallback"):
            for i, art in enumerate(news_result.get("articles", [])):
                headlines_text += f"{i+1}. {art.get('title')} (Source: {art.get('source')}, Date: {art.get('publishedAt')})\n"
        
        news_input_text = f"Analyze the news headlines for {ticker} and score the overall sentiment. Headlines:\n{headlines_text}"

        ohlcv_text = ""
        if price_result.get("status") in ("success", "fallback"):
            for date, ohlcv in list(price_result.get("time_series_30_days", {}).items())[:30]:
                ohlcv_text += f"Date: {date}, O: {ohlcv['1. open']}, H: {ohlcv['2. high']}, L: {ohlcv['3. low']}, C: {ohlcv['4. close']}, V: {ohlcv['5. volume']}\n"
        
        tech_input_text = f"Analyze the technical daily price chart for {ticker} to extract signals. OHLCV data:\n{ohlcv_text}"

        # Helper to execute a sub-agent in an isolated context
        async def execute_sub_agent(agent, input_text):
            sub_session = Session(
                id=f"{ctx.session.id}_{agent.name}",
                app_name=ctx.session.app_name,
                user_id=ctx.session.user_id,
                state=ctx.session.state.copy(),
                events=[
                    Event(
                        author="user",
                        content=types.Content(
                            role="user",
                            parts=[types.Part.from_text(text=input_text)]
                        )
                    )
                ]
            )
            sub_ctx = InvocationContext(
                session_service=ctx.session_service,
                artifact_service=ctx.artifact_service,
                memory_service=ctx.memory_service,
                credential_service=ctx.credential_service,
                invocation_id=f"{ctx.invocation_id}_{agent.name}",
                session=sub_session,
                user_content=sub_session.events[0].content,
                run_config=ctx.run_config or RunConfig(),
                context_cache_config=ctx.context_cache_config
            )
            async for event in agent.run_async(sub_ctx):
                if event.actions and event.actions.state_delta:
                    sub_ctx.session.state.update(event.actions.state_delta)
                if getattr(event, 'state', None):
                    sub_ctx.session.state.update(event.state)
            return sub_ctx.session.state.get(agent.output_key)

        async def safe_execute(agent, input_text):
            try:
                out = await execute_sub_agent(agent, input_text)
                return out, None
            except Exception as ex:
                tb_str = traceback.format_exc()
                logger.error(f"Sub-agent {agent.name} failed with traceback:\n{tb_str}")
                return None, f"{str(ex)}\nTraceback:\n{tb_str}"

        # 4. Invoke news_sentiment_agent and technical_analysis_agent in parallel
        (news_output, news_err), (tech_output, tech_err) = await asyncio.gather(
            safe_execute(self._news_agent, news_input_text),
            safe_execute(self._tech_agent, tech_input_text)
        )

        # 5. HITL Checkpoint (Human-in-the-Loop)
        # If no user response is found in the history, pause and ask the user
        if user_choice is None:
            sentiment_score = getattr(news_output, 'sentiment_score', 'N/A') if news_output else f'N/A (Error: {news_err})'
            tech_trend = getattr(tech_output, 'trend_direction', 'N/A') if tech_output else f'N/A (Error: {tech_err})'
            tech_signal = getattr(tech_output, 'momentum_signal', 'N/A') if tech_output else ''
            
            message = (
                f"### 🚦 MarketMind HITL Checkpoint\n"
                f"- **Ticker**: {ticker}\n"
                f"- **Raw Sentiment Score**: {sentiment_score}\n"
                f"- **Technical Chart Trend**: {tech_trend} {f'({tech_signal})' if tech_signal else ''}\n\n"
                f"**Proceed with full risk assessment? (yes/no)**"
            )
            
            req = RequestInput(
                interrupt_id=hitl_id,
                message=message,
                response_schema=str
            )
            yield create_request_input_event(req)
            return

        # Check if the user confirmed or rejected proceeding
        proceed = False
        if user_choice:
            choice_str = str(user_choice).strip().lower()
            if choice_str in ("yes", "y", "true"):
                proceed = True

        risk_output = None
        risk_err = None

        if proceed:
            # 6. Synthesize results and feed into risk_assessment_agent
            risk_input_text = f"Synthesize market risk for {ticker}.\n\n"
            
            if news_output:
                risk_input_text += (
                    "News Sentiment Data:\n"
                    f"- Score: {getattr(news_output, 'sentiment_score', 0.0)}\n"
                    f"- Themes: {', '.join(getattr(news_output, 'key_themes', []))}\n"
                    f"- Events: {', '.join(getattr(news_output, 'notable_events', []))}\n\n"
                )
            else:
                risk_input_text += f"News Sentiment Data: FAILED (Error: {news_err})\n\n"

            if tech_output:
                risk_input_text += (
                    "Technical Chart Data:\n"
                    f"- Trend: {getattr(tech_output, 'trend_direction', 'Neutral')}\n"
                    f"- Key Levels: {', '.join(map(str, getattr(tech_output, 'key_levels', [])))}\n"
                    f"- Momentum: {getattr(tech_output, 'momentum_signal', '')}\n\n"
                )
            else:
                risk_input_text += f"Technical Chart Data: FAILED (Error: {tech_err})\n\n"

            # Execute risk_assessment_agent
            risk_output, risk_err = await safe_execute(self._risk_agent, risk_input_text)
        else:
            risk_err = f"Risk assessment cancelled by user (Choice: '{user_choice}')."

        # 7. Build the final structured Markdown report
        timestamp = datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
        report = _build_markdown_report(ticker, timestamp, news_output, news_result, news_err, tech_output, price_result, tech_err, risk_output, risk_err)

        # Yield the final report event
        yield Event(
            author=self.name,
            content=types.Content(
                role="model",
                parts=[types.Part.from_text(text=report)]
            )
        )

def _build_markdown_report(
    ticker: str,
    timestamp: str,
    news_output: Any,
    news_result: dict,
    news_err: str,
    tech_output: Any,
    price_result: dict,
    tech_err: str,
    risk_output: Any,
    risk_err: str
) -> str:
    report = f"# MarketMind Financial Analysis Report\n\n"
    report += f"**Ticker**: {ticker}\n"
    report += f"**Timestamp**: {timestamp}\n\n"

    # Section 1: Sentiment
    report += "## 1. Sentiment Summary\n"
    if news_output:
        report += f"- **Sentiment Score**: {getattr(news_output, 'sentiment_score', 0.0):.2f} (Scale: -1.0 to 1.0)\n"
        report += f"- **Key Themes**: {', '.join(getattr(news_output, 'key_themes', []))}\n"
        report += f"- **Notable Events**: {', '.join(getattr(news_output, 'notable_events', []))}\n"
        if news_result.get("status") == "fallback":
            report += "\n*Note: News API key was missing; using simulated news fallback.*\n"
    else:
        err_msg = news_err or news_result.get("error", "Unknown error")
        report += f"❌ News Sentiment Analysis failed: {err_msg}\n"

    # Section 2: Technicals
    report += "\n## 2. Technical Summary\n"
    if tech_output:
        report += f"- **Trend Direction**: {getattr(tech_output, 'trend_direction', 'Neutral')}\n"
        report += f"- **Key Levels (Support/Resistance)**: {', '.join(map(str, getattr(tech_output, 'key_levels', [])))}\n"
        report += f"- **Momentum Signal**: {getattr(tech_output, 'momentum_signal', '')}\n"
        if price_result.get("status") == "fallback":
            report += "\n*Note: Alpha Vantage API key was missing; using simulated chart fallback.*\n"
    else:
        err_msg = tech_err or price_result.get("error", "Unknown error")
        report += f"❌ Technical Chart Analysis failed: {err_msg}\n"

    # Section 3: Risk Assessment
    report += "\n## 3. Risk Assessment & Thesis\n"
    if risk_output:
        report += f"**Trade Thesis**:\n{getattr(risk_output, 'thesis', '')}\n\n"
        report += f"- **Risk Rating**: {getattr(risk_output, 'risk_rating', 'Medium')}\n"
        report += f"- **Final Recommendation**: **{getattr(risk_output, 'suggested_action', 'Hold')}** (Confidence: {getattr(risk_output, 'confidence_score', 50)}/100)\n"
    else:
        report += f"❌ Risk Assessment synthesis failed/skipped: {risk_err}\n\n"
        report += "**Warning**: A final synthesized risk thesis could not be generated. Please evaluate the sentiment and technical outputs above."

    return report

def create_orchestrator_agent() -> BaseAgent:
    """Factory function to instantiate the OrchestratorAgent."""
    return OrchestratorAgent()
