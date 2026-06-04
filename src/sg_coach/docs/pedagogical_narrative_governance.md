# Pedagogical Narrative Governance

Sprint 35: Pedagogical Narrative Layer

## Overview

Pedagogical Narrative provides deterministic human-readable coaching explanations derived from governed runtime structures. The system generates textual projections from structured views without AI synthesis or probabilistic generation.

## Core Governance Rules

1. **Narratives are projections only.** Narratives do not become canonical evidence, do not mutate findings, and do not replace structured data.

2. **Structured evidence remains canonical.** Narratives derive from governed runtime structures: GuidedPracticeSessionView, RuntimeReviewReport, LongitudinalProgressReview, AdaptiveSchedulingPlan, TeacherSchedulingMediation, PedagogicalTimelineView.

3. **Narrative generation must remain deterministic.** All narrative output derives from explicit templates and mappings. No probabilistic or AI generation.

4. **AI narrative synthesis is prohibited.** No LLM summarization, no stochastic text generation, no conversational coaching in this layer.

5. **Narrative builders must remain inspectable.** Template mappings must be auditable and predictable.

6. **Narrative projections must never mutate evidence.** Read-only transformation from structured input to textual output.

## Schema Structure

### PedagogicalNarrative (Top-Level)

```
narrative_id: str (pn_<12hex>)
audience: NarrativeAudience (student, teacher, mixed)
generated_at: datetime
title: str
overview: str
sections: list[NarrativeSection]
notes: list[str]
metadata: dict
version: str
```

### NarrativeSection

```
section_id: str (pns_<12hex>)
title: str
summary: str
severity: NarrativeSeverity (informational, warning, critical)
evidence_ids: list[str]
related_ids: list[str]
metadata: dict
version: str
```

## ID Formats

- Narrative: `pn_<12hex>`
- Section: `pns_<12hex>`

## Builder Functions

### Guided Session Narrative

```python
from sg_coach import build_guided_session_narrative

narrative = build_guided_session_narrative(
    session_view=session_view,      # GuidedPracticeSessionView
    audience=NarrativeAudience.mixed,
)
```

### Runtime Review Narrative

```python
from sg_coach import build_runtime_review_narrative

narrative = build_runtime_review_narrative(
    review=review,                  # RuntimeReviewReport
    audience=NarrativeAudience.mixed,
)
```

### Longitudinal Review Narrative

```python
from sg_coach import build_longitudinal_review_narrative

narrative = build_longitudinal_review_narrative(
    review=review,                  # LongitudinalProgressReview
    audience=NarrativeAudience.teacher,
)
```

## Audience Semantics

### student

Use simpler wording, encouragement-neutral phrasing, less governance terminology.

Example:
```
"Playback is available with 3 highlighted areas."
"Practice suggestions are active with 2 recommendations."
```

### teacher

Use diagnosis terminology, governance language, adaptive scheduling references.

Example:
```
"Playback evidence is available with 3 finding overlays."
"Adaptive scheduling guidance is active with 2 recommendations."
```

### mixed

Use balanced wording appropriate for both audiences.

## Severity Mapping

| Condition | Severity |
|-----------|----------|
| Critical findings present | critical |
| Critical adaptive priority | critical |
| Teacher rejection mediation | warning |
| Teacher modification | warning |
| High adaptive priority | warning |
| Worsening longitudinal trend | warning |
| Improving or stable | informational |

## Section Ordering

Sections are sorted by severity (critical first), then alphabetically by title:

1. Critical severity sections
2. Warning severity sections
3. Informational severity sections
4. Alphabetical within same severity

## Template Categories

### Assignment Templates

```
assignment_none: "No active practice assignment is available."
assignment_active: "Practice session is currently active for {title}."
assignment_timing: "Timing-focused practice is active."
assignment_pitch: "Pitch-focused practice is active."
assignment_teacher_modified: "Teacher mediation modified this practice assignment."
```

### Playback Templates

```
playback_none: "Playback evidence is not available for this session."
playback_available: "Playback evidence is available with {count} finding overlays."
```

### Adaptive Templates

```
adaptive_none: "No adaptive scheduling guidance is active."
adaptive_active: "Adaptive scheduling guidance is active with {count} recommendations."
adaptive_critical: "Critical adaptive scheduling guidance requires review."
```

### Mediation Templates

```
mediation_none: "No teacher mediation is attached to this session."
mediation_modified: "Teacher mediation modified practice guidance."
mediation_rejected: "Teacher rejected at least one adaptive scheduling recommendation."
mediation_deferred: "Teacher deferred at least one adaptive scheduling recommendation."
```

### Timeline Templates

```
timeline_none: "No timeline evidence is available."
timeline_active: "Timeline evidence includes {count} pedagogical events."
```

## CLI Usage

```bash
# Guided session narrative
sg-coach narrative guided-session \
    --session-view session_view.json \
    --audience mixed \
    --pretty

# Runtime review narrative
sg-coach narrative runtime-review \
    --review runtime_review.json \
    --audience teacher \
    --pretty

# Longitudinal review narrative
sg-coach narrative longitudinal-review \
    --review longitudinal_review.json \
    --audience teacher \
    --pretty
```

## Notes Generation

- Maximum 5 notes per narrative
- Source view notes may be preserved in narrative.notes
- Notes provide additional context beyond sections

## Evidence ID Mapping

| Section | Evidence IDs From |
|---------|-------------------|
| Assignment | assignment metadata |
| Playback | active_finding_ids |
| Adaptive Guidance | evidence_ids |
| Teacher Mediation | (none in v1) |
| Timeline | timeline_events[].evidence_id |

| Section | Related IDs From |
|---------|------------------|
| Assignment | assignment_id |
| Playback | runtime_session_id |
| Adaptive Guidance | active_recommendation_ids |
| Teacher Mediation | latest_mediation_id |
| Timeline | (none in v1) |

## Limitations

- No conversational context
- No multi-turn dialogue
- No personalization beyond audience selection
- No voice synthesis
- No localization/i18n
- No frontend rendering

## Future Work

Future governed conversational systems may build upon this deterministic narrative foundation:

- Conversational tutoring (requires separate governance)
- Multi-turn coaching dialogue (requires separate governance)
- Personalized narrative adaptation (beyond audience)
- Voice-enabled coaching interfaces

These remain out of scope for Sprint 35 and require explicit governance approval.

## Integration Points

- **Inputs**: GuidedPracticeSessionView, RuntimeReviewReport, LongitudinalProgressReview
- **Output**: PedagogicalNarrative
- **Consumers**: Teacher review UX, student review UX, coaching dashboards
