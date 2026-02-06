# sg-coach

> ⚠️ **DEPRECATED** — This repository has been superseded by [sg-agentd](https://github.com/HanzoRazer/sg-agentd).
>
> The coaching functionality is now integrated into sg-agentd's unified bundle pipeline:
> - `clip.coach.json` is generated as part of the bundle output
> - `sg_agentd/services/coach_utils.py` handles PracticeAssignment generation
> - `sg_agentd/services/ai_coach_adapter.py` provides sg-ai integration
>
> **Migration:** Use sg-agentd for all new development. This repo is archived for historical reference only.
>
> **Superseded:** 2026-02-02

---

Smart Guitar Practice Coach - Mode 1 rules-first evaluation.

> **Tip**: When a gate or CLI command fails, re-run with `--debug` to print per-vector scan details (what's missing/where).

## Overview

sg-coach provides deterministic evaluation of practice sessions and assignment planning for the Tritone-MIDI practice system. No LLM required for core functionality.

## Architecture

Three-layer schema with strict ownership boundaries:

```
SessionRecord (facts) → CoachEvaluation (interpretation) → PracticeAssignment (intent)
```

- **SessionRecord**: What happened (runtime owns, immutable facts)
- **CoachEvaluation**: What it means (coach owns, interpretation)
- **PracticeAssignment**: What's next (planner owns, intent)

## Installation

```bash
pip install sg-coach
```

Or from source:

```bash
pip install -e .
```

## Usage

### As a library

```python
from sg_coach import SessionRecord, evaluate_session, plan_assignment
from sg_coach.coach_policy import evaluate_session

# Parse a session record
session = SessionRecord.model_validate(session_dict)

# Evaluate the session (Mode 1: deterministic rules)
evaluation = evaluate_session(session)

# Plan the next assignment
assignment = plan_assignment(session=session, evaluation=evaluation)
```

### CLI

```bash
# Evaluate a session and produce an OTA bundle
sg-coach export-bundle --in session.json --out bundle.json

# Wrap bundle into OTA payload with integrity check
sg-coach ota-pack --bundle bundle.json --out payload.json

# Verify OTA payload
sg-coach ota-verify --payload payload.json
```

## Schemas

The `sg_coach.schemas` module is the single source of truth for coach-related types:

- `SessionRecord`, `SessionTiming`, `PerformanceSummary`, etc.
- `CoachEvaluation`, `CoachFinding`, `FocusRecommendation`, etc.
- `PracticeAssignment`, `AssignmentConstraints`, `SuccessCriteria`, etc.

Other packages (like zt-band) should import from this module.

## Development

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest

# Run with coverage
pytest --cov=sg_coach
```

## License

MIT
