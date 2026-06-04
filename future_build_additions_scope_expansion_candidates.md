# Future Build Additions — Scope Expansion Candidates

## Purpose

This document captures future expansion concepts that were intentionally deferred while building the foundational Smart Guitar coaching platform.

These are not current sprint commitments.

They represent strategic future directions that may become appropriate once:

- the core runtime is stable,
- the symbolic coaching loop is mature,
- curriculum alignment is proven,
- and real user workflows are validated.

The purpose of this document is to:

- preserve architectural ideas,
- avoid forgetting valuable future directions,
- and clearly separate deferred platform evolution from the current production baseline.

---

# Current Platform Baseline

The current Smart Guitar architecture is intentionally:

- deterministic,
- explainable,
- MIDI-first,
- post-session-first,
- local-first,
- and schema-governed.

Current platform strengths:

```text
MIDI session
→ symbolic evaluation
→ recommendations
→ personalization
→ drill resolution
→ assignment assembly
→ outcome tracking
→ persistence
→ review/timeline
→ weakness progression
→ goal tracking
→ curriculum alignment
```

Future expansion work must preserve:

- explainability,
- evidence traceability,
- schema governance,
- and deterministic coaching foundations.

---

# Scope Expansion Candidate 1 — AI Curriculum Generation

## Concept

Allow the system to dynamically generate:

- drills,
- exercises,
- lesson variations,
- or adaptive practice content.

Potential future architecture:

```text
PracticeGoal
→ AI curriculum generator
→ generated drill/exercise
→ assignment pipeline
```

---

## Potential Benefits

- highly personalized exercises,
- adaptive drill generation,
- infinite practice variation,
- responsive pedagogy.

---

## Architectural Challenges

This would require:

- curriculum quality control,
- prompt governance,
- pedagogy validation,
- content safety,
- content versioning,
- reproducibility guarantees,
- generated content persistence,
- review/approval systems.

---

## Why Deferred

Current platform focus is:

```text
deterministic curriculum alignment
```

not:

```text
autonomous curriculum creation
```

Premature AI curriculum generation would introduce:

- non-determinism,
- explainability loss,
- governance complexity,
- and content validation risks.

---

## Recommended Future Timing

Only revisit after:

- curriculum alignment stabilizes,
- sg-curriculum becomes canonical,
- and teacher workflows are validated.

---

# Scope Expansion Candidate 2 — Scheduling Engine

## Concept

Automatically generate:

- daily practice plans,
- weekly schedules,
- session sequencing,
- recovery/fatigue-aware routines,
- and long-term practice calendars.

Potential future architecture:

```text
PracticeGoals
+ assignments
+ available practice time
→ scheduling engine
→ structured practice plan
```

---

## Potential Benefits

- guided progression,
- consistent practice habits,
- teacher-managed scheduling,
- balanced workload management.

---

## Architectural Challenges

Requires:

- time modeling,
- prioritization logic,
- dependency sequencing,
- fatigue modeling,
- scheduling heuristics,
- calendar integration,
- recurring assignment management.

---

## Why Deferred

The current platform does not yet have:

- stable curriculum progression,
- validated assignment effectiveness,
- or sufficient long-term user behavior data.

Scheduling before those foundations risks:

```text
optimizing unstable coaching assumptions
```

---

## Recommended Future Timing

After:

- goal tracking matures,
- curriculum alignment stabilizes,
- and assignment outcomes produce reliable trends.

---

# Scope Expansion Candidate 3 — Dynamic Difficulty Adaptation

## Concept

Automatically adjust:

- drill difficulty,
- tempo,
- complexity,
- or progression level

based on player performance.

Potential future architecture:

```text
Learning signals
→ mastery estimation
→ adaptive difficulty selection
→ personalized drill scaling
```

---

## Potential Benefits

- individualized progression,
- reduced frustration,
- improved challenge calibration,
- smoother skill development.

---

## Architectural Challenges

Requires:

- mastery estimation,
- adaptive thresholds,
- progression modeling,
- failure recovery rules,
- confidence calibration,
- pedagogical balancing.

---

## Why Deferred

Current adaptation remains intentionally:

```text
explainable and deterministic
```

Dynamic difficulty introduces:

- opaque adaptation behavior,
- unstable progression loops,
- hidden state complexity.

---

## Recommended Future Timing

After:

- longitudinal data accumulates,
- outcome tracking proves reliable,
- and curriculum progression models exist.

---

# Scope Expansion Candidate 4 — Teacher Workflow Features

## Concept

Enable teachers to:

- review sessions,
- override goals,
- assign curriculum manually,
- annotate progress,
- manage multiple students,
- and guide practice plans.

Potential future architecture:

```text
Teacher dashboard
→ student review
→ coaching overrides
→ collaborative coaching workflow
```

---

## Potential Benefits

- strong teacher augmentation,
- hybrid human + AI coaching,
- better accountability,
- real educational workflows.

---

## Architectural Challenges

Requires:

- permissions,
- multi-user ownership,
- synchronization,
- teacher/student relationship modeling,
- override auditing,
- collaborative workflows.

---

## Why Deferred

Current platform focus is:

```text
single-player local-first coaching
```

Teacher tooling becomes significantly more valuable after:

- review layers stabilize,
- goal systems mature,
- and curriculum alignment becomes reliable.

---

## Recommended Future Timing

Potentially one of the strongest future expansions.

Recommended after:

- Sprint 14+ curriculum stabilization,
- and practical player workflows are validated.

---

# Scope Expansion Candidate 5 — Cloud Sync & Multi-Device Infrastructure

## Concept

Allow:

- cross-device synchronization,
- teacher/student cloud sharing,
- backup/restore,
- and multi-user persistence.

Potential future architecture:

```text
local coaching runtime
↔ cloud synchronization layer
↔ shared coaching state
```

---

## Potential Benefits

- device continuity,
- collaboration,
- remote instruction,
- centralized progress history.

---

## Architectural Challenges

Requires:

- authentication,
- identity systems,
- conflict resolution,
- APIs,
- distributed persistence,
- synchronization logic,
- privacy/security models.

---

## Why Deferred

Current architecture intentionally optimized for:

```text
local-first reliability
```

Cloud infrastructure would dramatically increase:

- operational complexity,
- infrastructure maintenance,
- and persistence governance.

---

## Recommended Future Timing

Only after:

- local workflows are proven,
- user identity models stabilize,
- and teacher collaboration requirements become concrete.

---

# Scope Expansion Candidate 6 — Real-Time Coaching & Streaming Evaluation

## Concept

Provide:

- live correction,
- bar-level feedback,
- in-session intervention,
- and streaming evaluator behavior.

Potential future architecture:

```text
live MIDI/audio stream
→ streaming evaluators
→ low-latency coaching events
→ live intervention
```

---

## Potential Benefits

- immediate correction,
- immersive practice assistance,
- highly interactive coaching.

---

## Architectural Challenges

Requires:

- streaming evaluation architecture,
- latency budgets,
- event buses,
- buffering,
- concurrency control,
- incremental aggregation,
- runtime optimization.

Would likely require redesign of:

- evaluator flow,
- persistence flow,
- orchestration architecture.

---

## Why Deferred

The current Smart Guitar architecture is intentionally optimized for:

```text
post-session explainable coaching
```

Real-time streaming introduces:

- major runtime complexity,
- architectural instability,
- and substantially different engineering constraints.

---

## Recommended Future Timing

Only after:

- post-session coaching is mature,
- runtime workflows are stable,
- and user demand for live intervention is validated.

---

# Strategic Guidance

## What Must Remain Stable

Regardless of future expansion direction, the following architectural invariants should remain protected:

```text
1. sg-spec remains canonical contract authority.
2. Learning signals remain explainable.
3. Coaching decisions remain evidence-traceable.
4. Feedback/outcomes remain append-only.
5. Recommendation ranking may reorder but not invent actions.
6. Runtime integrations must respect schema governance.
```

---

# Recommended Near-Term Focus

The current priority remains:

```text
stable coaching runtime
+ curriculum alignment
+ longitudinal coaching intelligence
```

Not:

- cloud infrastructure,
- AI pedagogy,
- or real-time streaming.

---

# Final Principle

The Smart Guitar platform is strongest when:

```text
adaptive coaching remains explainable,
traceable,
deterministic,
and pedagogically grounded.
```

Future expansion work should extend those strengths — not replace them.

