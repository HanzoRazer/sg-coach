# Coaching Method Governance

Sprint 40: Governance rules for the composite coaching method.

## Overview

This document governs how the sg-coach layer participates in the integrated,
four-layer coaching method defined in
[`sg-spec/docs/coaching_method_architecture.md`](../../sg-spec/docs/coaching_method_architecture.md).
It is a governance document: it states the rules sg-coach must obey, not new
features. No new evaluators, runtime code, or schemas are introduced in
Sprint 40.

Smart Guitar is one deliberate-practice navigation system, not four products.
sg-coach is the **Coaching** layer — the diagnosis-and-prescription engine that
explains *why* the practice queue chose what it chose.

## Governance Rules

### Rule 1: Diagnosis Before Prescription

The coach **must diagnose before it prescribes**. A recommendation is only valid
if it is traceable to a diagnosis, and a diagnosis is only valid if it is
traceable to measured evidence. The loop is fixed:

```
Measure -> Observe -> Diagnose -> Recommend -> Practice -> Re-measure -> Track Progress
```

No prescription may be emitted that skips the diagnosis step.

### Rule 2: Measurable Outcomes

Every assignment the coach produces **must target a measurable outcome**. If an
outcome cannot be measured by a deterministic evaluator (timing, pitch,
technique), the coach must not claim the assignment improves it. Unmeasurable
goals are documented as future learning domains, not asserted as outcomes.

### Rule 3: Evidence-Backed Assignment Logic

Assignment selection **must be evidence-backed**. Each recommended drill carries
the evidence (the metrics and the diagnosis code) that justified it. Assignments
without an evidence trail are governance violations.

### Rule 4: Recommendations Remain Advisory; Teacher Authority Is Preserved

Coach recommendations are **suggestions, not commands**. **Teacher authority is
preserved**: a teacher may override, approve, or reject any coach output, and AI
contributions remain provisional until a teacher reviews them. The coach never
promotes its own output to "approved." See
[`sg-spec/docs/solo_practice_authority.md`](../../sg-spec/docs/solo_practice_authority.md).

### Rule 5: Rhythm and Song Performance Are Integration Tests

**Rhythm and song performance are treated as integration tests of the method**,
not as isolated evaluators. They exercise multiple Domain Layer skills at once
(timing + coordination + technique), so the coach uses them to validate that the
lower-layer diagnoses compose correctly — not as standalone scored features in
Sprint 40.

### Rule 6: Ear Training Is a Future Musicianship Layer

**Ear training is a future musicianship-learning layer.** The coach does not
diagnose or prescribe ear-training outcomes in Sprint 40. It is documented here
so the roadmap is explicit, but it remains out of scope until a future sprint
adds the corresponding deterministic measurement. Rhythm, song performance, and
ear training are all future learning domains of the musicianship layer.

## Mapping to User Outcomes

| sg-coach role | User benefit |
|---------------|--------------|
| Diagnose | Understand *why* something is hard |
| Recommend | Get the right next drill |
| Evidence trail | Trust the recommendation |
| Defer to teacher | Stay human-guided |

## Out of Scope (Sprint 40)

- New evaluators
- Audio DSP
- AI generation
- New runtime code or schemas

## Related Documents

- [`sg-spec` Coaching Method Architecture](../../sg-spec/docs/coaching_method_architecture.md)
- [`sg-curriculum` Curriculum Domain Roadmap](../../sg-curriculum/docs/curriculum_domain_roadmap.md)
- [Assignment Outcome Governance](assignment_outcome_governance.md)
- [Teacher Review Governance](teacher_review_governance.md)
