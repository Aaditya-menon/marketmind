---
name: technical_analysis_agent
description: Analyzes historical price data (OHLCV) and identifies trend direction, key support/resistance levels, and momentum signals.
---

# Technical Chart Analysis Skill

## 1. Discovery (Layer 1)
This skill is used when the system needs to evaluate historical price charts, determine market trend directions (Bullish, Bearish, Neutral), identify key price levels, or evaluate technical indicators (RSI, MACD, etc.).

## 2. Activation (Layer 2)
When activated, the agent performs the following steps:
1. Receives daily OHLCV (Open, High, Low, Close, Volume) data for the last 30 days.
2. Identifies the primary trend direction (Bullish, Bearish, or Neutral).
3. Spots key horizontal support and resistance levels.
4. Analyzes momentum signals (e.g. overbought/oversold, trend acceleration).

## 3. Schema & Execution (Layer 3)
The output of this skill must strictly conform to the following Pydantic schema:

```python
class TechnicalAnalysisOutput(BaseModel):
    trend_direction: Literal["Bullish", "Bearish", "Neutral"]
    key_levels: list[float]
    momentum_signal: str
```

For the active agent configuration, refer to the project file [technical_analysis_agent/agent.py](file:///c:/Users/adity/Documents/antigravity/marketmind/technical_analysis_agent/agent.py).
