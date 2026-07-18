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

### 7. Never expose pipeline models directly to product surfaces

Pipeline models represent observations. Domain models represent creator understanding. Presentation models represent communication.

- **Pipeline models** (MetricSnapshot, Finding, PipelineEvidence, etc.) are internal representations of what was observed during a single analysis run.
- **Domain models** (GrowthReview, MissionVerdict, LastMission, etc.) are typed, serializable objects that answer product questions without exposing database structure.
- **Presentation models** shape the response for a specific surface (dashboard, email, PDF, mobile notification, AI chat).

Product surfaces should never import or depend on pipeline models. Every product surface consumes a domain object; the pipeline is infrastructure behind it.

This prevents coupling between analytical internals and product experience. The pipeline can be replaced, restructured, or split without changing a single product surface.

### 8. Every insight must lead to an action. Every action must be reviewable. Every review must produce the next question.

This principle codifies the product's growth loop:

```
Observe → Understand → Act → Review → Learn → Repeat
```

- **Every insight must lead to an action.** No observation exists solely for display. If a pattern, finding, or metric doesn't suggest a concrete next action, it doesn't belong in the product surface.
- **Every action must be reviewable.** Every recommendation becomes an experiment. Every experiment has a measurable outcome. No action vanishes into the void.
- **Every review must produce the next question.** A review that ends with certainty is a missed opportunity. Every review should surface an unknown that becomes the next experiment.

When evaluating whether a new feature belongs, test it against this loop:
- Does it strengthen one stage (observe, understand, act, review, learn)?
- If yes, it probably belongs.
- Does it create a parallel workflow outside this loop?
- If yes, it probably doesn't.

This loop is what transforms the product from an analytics tool into a coaching system that compounds knowledge over time.

A practical filter for evaluating any proposed feature: ask three questions.

1. Does it create a better insight?
2. Does it create a better action?
3. Does it improve review or learning?

If the answer to all three is no, the feature doesn't belong — regardless of how technically impressive it is.

### 9. Measure the growth loop, not feature adoption

The product's success metric is **time to next meaningful decision** — after opening IQoCreator, how long does it take a creator to decide what they should do next?

If the architecture is working, this number should keep falling. Creators shouldn't leave with more information. They should leave with more clarity.

Track conversion through the loop:

```
Insight generated
    ↓  (conversion rate)
Mission accepted
    ↓
Mission completed
    ↓
Review generated
    ↓
Next mission accepted
```

If creators read reports but never complete missions, that's a product problem — not an AI problem. The funnel is the diagnostic.

### 10. Do not add another intelligence detector until a real creator completes three full growth loops

No new detectors, extractors, or analytical capabilities until a real creator can complete at least three full cycles:

```
Analyze → Mission → Implementation → Review → Next mission
```

Run that cycle with actual creators. Every insight from observing where they get stuck is worth more than another analytical capability added in isolation.

This rule prevents intelligence from becoming an end in itself. Detectors exist to power the growth loop, not to fill a dashboard.
