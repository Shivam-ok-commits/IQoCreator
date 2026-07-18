# IQoCreator

> AI Growth Coach for YouTube Creators

IQoCreator is an AI-powered coaching platform that helps creators understand **why their channel grows**, recommends evidence-backed experiments, reviews their progress, and continuously improves future recommendations.

Unlike traditional analytics dashboards, IQoCreator is designed as a **continuous coaching system**, guiding creators through an ongoing growth loop instead of simply displaying metrics.

---

# Vision

Most creator tools answer:

> What happened?

IQoCreator answers:

> Why did it happen?
>
> What should I do next?
>
> Did my last experiment work?
>
> What should I learn from it?

The goal isn't better dashboards.

The goal is better decisions.

---

# Growth Loop

```text
Observe
    ↓
Understand
    ↓
Act
    ↓
Review
    ↓
Learn
    ↓
Repeat
```

Every analysis produces a mission.

Every mission gets reviewed.

Every review generates the next question.

---

# Core Features

## Executive Summary

A consultant-style overview explaining the single biggest thesis behind channel performance.

---

## Growth Review

Instead of comparing numbers, IQoCreator reviews:

- What happened
- Why it happened
- Whether the previous mission worked
- What remains unknown
- What to do next

---

## AI Recommendations

Recommendations include:

- Headline
- Supporting examples
- Recommended mission
- Expected outcome
- Confidence
- Why this comes first

---

## Visual Proof

Every recommendation references real channel videos with performance comparisons.

---

## Mission Tracking

Each recommendation becomes an experiment that can later be reviewed.

---

## Coaching System

IQoCreator evolves from:

Analytics

↓

Consulting

↓

Coaching

---

# Architecture

```text
YouTube Data
        ↓
Import Pipeline
        ↓
Metrics
        ↓
Feature Extraction
        ↓
Pattern Detection
        ↓
Evidence
        ↓
Creator Intelligence
        ↓
Growth Review
        ↓
Experiments
        ↓
Growth Memory (Planned)
```

---

# Tech Stack

## Backend

- FastAPI
- SQLAlchemy
- Alembic
- PostgreSQL
- Python 3.12

## Frontend

- Next.js
- React
- TypeScript
- TailwindCSS

---

# Product Philosophy

IQoCreator follows ten constitutional principles.

Highlights:

- Every recommendation must be traceable.
- Every recommendation must be measurable.
- Pipeline models never reach product surfaces.
- Every insight creates an action.
- Every action is reviewable.
- Every review creates the next question.
- Measure creator clarity—not feature usage.
- Validate with real creators before adding intelligence.

---

# Roadmap

## ✅ Completed

- Analytics Pipeline
- Intelligence Engine
- Recommendation Engine
- Executive Summary
- Growth Review
- Experiment System

---

## Next

- Growth Memory
- Prediction Validation
- AI Coach

---

# Development

Backend

```bash
cd backend
uvicorn app.main:app --reload
```

Frontend

```bash
cd frontend
npm install
npm run dev
```

---

# Contributing

Contributions are welcome.

Please open an issue before proposing large architectural changes.

---

# License

MIT License
