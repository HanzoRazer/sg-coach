# Golden Vectors for sg_coach Mode-1

This directory contains the canonical "golden vector" triple that defines
the deterministic behavior of the Mode-1 coaching pipeline.

## Purpose

These fixtures serve as:
1. **Regression tests** - Any change to the pipeline must produce identical output
2. **Contract anchors** - Defines what the coach "should" do for a given input
3. **OTA validation** - Reference for verifying bundle integrity

## Files

### vector_001/
The primary golden vector triple:

- `session.json` - SessionRecord input (facts from a practice session)
- `evaluation.json` - CoachEvaluation output (deterministic interpretation)
- `assignment.json` - PracticeAssignment output (what to practice next)

## Usage

Run the golden vector test:
```bash
pytest tests/test_mode1_golden_assignment.py -v
```

To update golden vectors (after intentional changes):
```bash
UPDATE_GOLDEN=1 pytest tests/test_mode1_golden_assignment.py -v
```

## Contract

**Any change to these files is a breaking change.**

Before modifying:
1. Document the reason in CHANGELOG.md
2. Bump COACH_CONTRACT_VERSION if behavior changes
3. Notify downstream consumers (OTA, firmware)

## Vector Selection

The golden vector was chosen to be:
- "Good but not perfect" - Forces real policy decisions
- Common case - Represents typical practice session
- Stable - No edge cases or unusual conditions
