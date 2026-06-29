---
name: risk_assessment_agent
description: Synthesizes sentiment and technical data into a trade thesis, risk rating, and suggested action.
---

# Risk Assessment & Synthesis Skill

## 1. Discovery (Layer 1)
This skill is used when the system needs to synthesize specialized outputs (sentiment analysis and technical analysis) into a final market thesis, assign a risk rating, and suggest an actionable trade or investment decision.

## 2. Activation (Layer 2)
When activated, the agent performs the following steps:
1. Receives the news sentiment result (score, themes, events) and the technical analysis result (trend, key levels, momentum).
2. Synthesizes these feeds into a logical trade thesis.
3. Evaluates overall risk and assigns a risk rating ("Low", "Medium", "High").
4. Formulates a recommended action ("Buy", "Sell", "Hold", "Avoid") along with a confidence score (0 to 100).

## 3. Schema & Execution (Layer 3)
The output of this skill must strictly conform to the following Pydantic schema:

```python
class RiskAssessmentOutput(BaseModel):
    thesis: str
    confidence_score: int  # Range 0 to 100
    risk_rating: Literal["Low", "Medium", "High"]
    suggested_action: Literal["Buy", "Sell", "Hold", "Avoid"]
```

For the active agent configuration, refer to the project file [risk_assessment_agent/agent.py](file:///c:/Users/adity/Documents/antigravity/marketmind/risk_assessment_agent/agent.py).
