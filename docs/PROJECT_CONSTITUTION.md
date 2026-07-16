# IQoCreator — Project Constitution

> IQoCreator exists to help YouTube creators grow through deterministic, explainable recommendations.

---

## Core Principles

### 1. Every recommendation must be traceable

```
Recommendation → Claim → Evidence → Rule → Feature → Video
```

Each recommendation must link back through its claims and evidence to the specific rules and video content that produced it. Black-box recommendations are not acceptable.

### 2. AI never performs reasoning

AI may only:
- **Explain** existing results
- **Summarize** content
- **Rewrite** text
- **Change tone**

All reasoning is deterministic. Rules, not models, drive decisions.

### 3. Every recommendation must be testable

Every recommendation should become an experiment. If it cannot be tested, it should not be made.

### 4. Every recommendation must be measurable

If success cannot be measured, the recommendation should not exist. Views, retention, engagement — define the metric before making the recommendation.

### 5. Never optimize for architecture over product

A working feature beats perfect abstractions. Build the feature first. Refactor when patterns emerge, not before.

### 6. Validation comes before sophistication

Collect evidence before building new intelligence. Prove a simple approach works before adding complexity.
