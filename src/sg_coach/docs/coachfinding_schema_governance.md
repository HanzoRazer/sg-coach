# CoachFinding Schema Governance

## Purpose

This document defines the governance rules for CoachFinding — the contract between
coaching evaluators, UI rendering, progress tracking, and Layer 2 user-guided learning.

## Ownership Boundaries

| Component | Owner | Responsibility |
|-----------|-------|----------------|
| FeedbackDomain, FeedbackSeverity, etc. | sg-spec | Shared vocabulary enums |
| DiagnosisCode | sg-spec | Canonical diagnostic codes |
| CoachFinding, FindingEvidence | sg-spec | Contract schema definitions |
| Evaluator behavior | sg-coach | How/when to emit findings |
| Finding rendering | UI | How to display findings |

## Required Finding Fields

All new evaluators MUST emit findings with these fields:

| Field | Type | Required | Description |
|-------|------|----------|-------------|
| code | DiagnosisCode | Yes | Canonical diagnostic code |
| domain | FeedbackDomain | Yes | harmony, timing, pitch, etc. |
| message | str | Yes | Human-readable feedback |
| evidence | FindingEvidence | Yes | Machine-readable proof |
| source_evaluator | str | Yes | Evaluator that emitted this |
| severity | Severity | Yes | primary/secondary/info |
| interpretation | str | Yes | Legacy field (same as message) |
| type | str | Yes | Legacy field (maps to domain) |

Recommended but optional:
- title: Short UI-safe label (max 80 chars)
- render_hint: How UI should display
- suggested_actions: Actionable next steps
- confidence: 0.0-1.0 (1.0 for rule-based)
- target_span: Location in session

## Evidence Rules

1. **Evidence must be machine-readable.** Do not bury critical data only in message text.

2. **UI must not parse human-readable messages.** All data needed for rendering must
   be in structured evidence fields.

3. **Evidence should include:**
   - metric: What was measured
   - value: The measurement
   - unit: Unit of measurement (ms, %, etc.)
   - threshold: What threshold was violated (if applicable)
   - aggregate_stats: Summary statistics

4. **Domain-specific evidence:**
   - Harmony: key, expected_set, performed_set
   - Timing: offset_ms, direction, index, threshold

## Severity Mapping

| Legacy Severity | FeedbackSeverity | Usage |
|-----------------|------------------|-------|
| Severity.info | FeedbackSeverity.info | Informational only |
| Severity.secondary | FeedbackSeverity.warning | Needs attention |
| Severity.primary | FeedbackSeverity.error | Critical issue |

Note: FeedbackSeverity.critical is reserved for future use.

## Evaluator Requirements

Every new evaluator must have:

1. **Unit tests** covering:
   - Clean input produces no finding
   - Violation input produces finding with correct code/domain
   - Evidence fields are populated correctly

2. **Pipeline test** proving integration with evaluate_session()

3. **Documentation** in docs/ explaining:
   - What the evaluator detects
   - What evidence it provides
   - What suggested actions it recommends

4. **Example finding JSON** in docs/coachfinding_examples.md

## Backward Compatibility

1. **Keep legacy fields.** Do not rename `type` → `domain` or `interpretation` → `message`
   yet. Add new fields alongside legacy ones.

2. **Use normalization helpers.** CoachFinding has properties:
   - normalized_domain: Returns domain, or maps from type
   - normalized_message: Returns message, or falls back to interpretation
   - feedback_severity: Maps legacy Severity to FeedbackSeverity

3. **Existing tests must pass.** The 98 evaluator tests must remain green.

## Adding a New DiagnosisCode

1. Add the code to `sg_spec/schemas/adaptive_feedback.py`
2. Document in comments which domain it belongs to
3. Create evaluator in sg-coach that emits the code
4. Add tests proving correct emission
5. Add example to docs/coachfinding_examples.md

## Adding a New Evaluator

1. Create evaluator module in `src/sg_coach/`
2. Emit CoachFinding with all required governance fields
3. Add exercise classification pattern to exercise_classifier.py
4. Wire into coach_policy.py pipeline
5. Add unit tests + pipeline tests
6. Add documentation
7. Add example finding JSON

## Definition of Done

A CoachFinding implementation is complete when:

- [ ] All required fields populated
- [ ] Evidence is structured (not message-only)
- [ ] code and domain are set
- [ ] source_evaluator identifies the evaluator
- [ ] Unit tests verify field population
- [ ] Pipeline test verifies integration
- [ ] Example JSON documented
- [ ] All 98+ tests pass
