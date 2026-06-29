---
name: news_sentiment_agent
description: Analyzes financial news headlines for a ticker and returns a sentiment score (-1 to 1), key themes, and notable events.
---

# News Sentiment Analysis Skill

## 1. Discovery (Layer 1)
This skill is used when the multi-agent system needs to gauge public sentiment, evaluate news headlines, or analyze market trends from media feeds for a specific stock or cryptocurrency.

## 2. Activation (Layer 2)
When activated, the agent performs the following steps:
1. Receives a list of recent headlines (retrieved via the `fetch_news` tool or other inputs).
2. Scores the sentiment of each headline individually, then aggregates them into an overall score between `-1.0` (extremely negative) and `1.0` (extremely positive).
3. Extracts major market themes (e.g., earnings growth, supply chain issues, regulatory crackdowns).
4. Identifies specific notable events (e.g., mergers, CEO announcements, product launches).

## 3. Schema & Execution (Layer 3)
The output of this skill must strictly conform to the following Pydantic schema:

```python
class NewsSentimentOutput(BaseModel):
    sentiment_score: float  # Range from -1.0 to 1.0
    key_themes: list[str]   # List of identified themes
    notable_events: list[str]  # List of specific notable events
```

For the active agent configuration, refer to the project file [news_sentiment_agent/agent.py](file:///c:/Users/adity/Documents/antigravity/marketmind/news_sentiment_agent/agent.py).
