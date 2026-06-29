# MarketMind — AI-Powered Financial Research Multi-Agent System

## 1. Track
**Agents for Business**

---

## 2. Problem Statement
Retail investors spend hours manually researching assets before making trading decisions. They must aggregate news headlines, calculate chart price trends, identify support and resistance levels, assess risk profiles, and form an investment thesis — all through separate, fragmented tools. This manual process is time-consuming, highly error-prone, and susceptible to emotional trading biases. 

MarketMind solves this by automating the entire research pipeline using a cooperative, multi-agent financial intelligence system. By delegating data extraction, sentiment analysis, and chart indicators to specialized agents, MarketMind delivers a structured, objective, and comprehensive analysis report in seconds. This democratizes institutional-grade research tools, giving retail traders objective signals and risk guardrails.

---

## 3. Solution Architecture
MarketMind implements a hybrid, quota-efficient multi-agent architecture built on the Google Agent Development Kit (ADK) 2.0:
1. **Orchestrator Agent**: Serves as the central coordinator. It accepts the ticker symbol query, invokes NewsAPI and Alpha Vantage tools to retrieve market headlines and daily OHLCV charts, and manages the execution flow.
2. **Parallel Local Analytics**: The Orchestrator delegates tasks to the `news_sentiment_agent` (extracting scores and themes via Python keyword analysis) and the `technical_analysis_agent` (calculating moving averages, support/resistance, and momentum) in parallel using asynchronous orchestration.
3. **Verification Checkpoint**: The system pauses at a Human-in-the-Loop (HITL) gate, requesting user authorization to verify extracted news sentiment and technical trends before requesting LLM synthesis.
4. **Risk & Synthesis**: Upon approval, the `risk_assessment_agent` runs local heuristics to suggest a trade action (Buy/Sell/Hold) and confidence score. Finally, the Orchestrator passes all sub-agent state data to Gemini 2.5 Flash, generating a structured, synthesized markdown report.

---

## 4. Course Concepts Demonstrated

| Course Concept | Implementation and Mapping | File Reference |
| :--- | :--- | :--- |
| **Agent/Multi-agent System** | Implemented a cooperative network composed of a central Orchestrator Agent and 3 specialized sub-agents. | [orchestrator_agent/agent.py](file:///c:/Users/adity/Documents/antigravity/marketmind/orchestrator_agent/agent.py) |
| **MCP & Tool Integration** | Replaced unstable MCP connections with direct, resilient REST API tool calls with graceful fallbacks. | [tools/fetch_price_data.py](file:///c:/Users/adity/Documents/antigravity/marketmind/tools/fetch_price_data.py) |
| **Agent Skills** | Configured `SKILL.md` instruction files matching custom workspace roots. | [technical_analysis_agent/SKILL.md](file:///c:/Users/adity/Documents/antigravity/marketmind/.agents/skills/technical_analysis_agent/SKILL.md) |
| **Human-in-the-Loop (HITL)** | Intercepts sub-agent state updates via an interrupt gate (`adk_request_input`) to prevent unchecked LLM execution. | [orchestrator_agent/agent.py#L248-L270](file:///c:/Users/adity/Documents/antigravity/marketmind/orchestrator_agent/agent.py#L248-L270) |
| **Antigravity IDE** | Leveraged Antigravity's context rehydration, file search tools, and sandbox terminal execution to engineer and debug the workspace. | Project Root |

---

## 5. Technical Highlights
* **Asynchronous Concurrency**: Utilizes `asyncio.gather` to fetch news and chart data and run extraction agents concurrently.
* **Hybrid Local/LLM Design**: Bypasses LLM API calls for extraction and assessment (using keyword counting, SMA averages, and rule matrices), conserving Gemini free tier quota.
* **Pydantic Schemas**: Enforces strict typing and validation across all agents using Pydantic output models.
* **Resilient Fallbacks**: Gracefully generates partial reports if NewsAPI or Alpha Vantage endpoints encounter network or key issues.
* **Zero Hardcoded Secrets**: Securely manages developer keys using environment variables and `.env` profiles.

---

## 6. Project Journey
During development, our primary challenge was encountering `429 RESOURCE_EXHAUSTED` errors on the Gemini API free tier due to multiple sub-agents invoking the model per run. We solved this by refactoring our sub-agents to subclass `BaseAgent` and execute their mathematical and string analysis directly in local Python, reserving the LLM solely for the final report layout. We also resolved Alpha Vantage SSE 405 errors by replacing the MCP gateway with a direct `httpx` REST interface, and bypassed Pydantic property constraints on custom agents by declaring the `output_key` as a read-only property.

---

## 7. Links
* **GitHub Repository**: https://github.com/Aaditya-menon/marketmind
* **Video Demonstration**: [to be added]
