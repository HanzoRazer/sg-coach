# String Guitar Governance Audit: Developer Handoff

Sprint 39: Cross-Repository Governance Authority Mapping.

## Executive Summary

This document maps ownership, provenance, execution boundaries, and experimental risk across the String Guitar system. It answers four interrogation questions for each subsystem and provides actionable governance guidance for developers.

---

## Authority Hierarchy (Descending)

```
┌─────────────────────────────────────────────────────────────────┐
│  TEACHER AUTHORITY (Override Layer)                             │
│  - Teacher overrides all adaptive recommendations               │
│  - teacher_override: True marks human authority                 │
│  - No AI system can countermand teacher decisions               │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  sg-spec (Schema Contracts)                                     │
│  - Defines canonical truth via Pydantic schemas                 │
│  - ID formats (prefixes: session_, diag_, evt_, etc.)           │
│  - Immutable once published in a sprint                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  sg-curriculum (Content Authority)                              │
│  - Owns all pedagogical content definitions                     │
│  - Read-only registries for exercises, progressions             │
│  - No runtime mutations                                         │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  sg-coach (Evaluation Authority)                                │
│  - Deterministic rule-based evaluation (Mode 1)                 │
│  - Policy functions for recommendations                         │
│  - Append-only evidence stores                                  │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  sg-ai (Generation Layer)                                       │
│  - Groove/rhythm model outputs                                  │
│  - All outputs are PROVISIONAL until approved                   │
│  - Governance checks block unsafe content                       │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│  sg-agentd (HTTP Boundary)                                      │
│  - Explicit request-based mutations only                        │
│  - No autonomous state changes                                  │
│  - Exposes policy decisions over HTTP                           │
└─────────────────────────────────────────────────────────────────┘
```

---

## Repository: sg-spec

### Ownership

| Component | Authority Claim | Justification |
|-----------|-----------------|---------------|
| `SessionRecord` | Canonical session truth | Immutable schema; all session data must conform |
| `CoachEvaluation` | Canonical evaluation truth | Defines what constitutes a valid evaluation |
| `DiagnosisCode` | Canonical diagnosis vocabulary | Closed enum; no runtime additions |
| `FrontendInteractionEvent` | Canonical UI intent | Sprint 39 contract for interaction replay |
| `WorkspaceFrontendState` | Canonical frontend projection | Sprint 38 display contract |

### Provenance

| Layer | Description | Example |
|-------|-------------|---------|
| Observation | Raw input capture | `recorded_at`, `input_hash` |
| Interpretation | Derived analysis | `diagnosis_code`, `evidence` |
| Approval | Human validation | `teacher_override`, `approved_by` |
| Canonization | Schema conformance | Pydantic validation on model creation |

### Execution

**sg-spec NEVER mutates state.** It defines contracts only. Mutations occur in consuming systems (sg-coach, sg-ai, sg-agentd).

### Boundary Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| Schema drift | Field additions without governance | Version fields on all schemas |
| Enum expansion | Adding diagnosis codes without review | Governance doc requires sprint approval |

---

## Repository: sg-curriculum

### Ownership

| Component | Authority Claim | Justification |
|-----------|-----------------|---------------|
| `ExerciseRegistry` | Canonical exercise definitions | Read-only; defines all valid exercises |
| `ProgressionRegistry` | Canonical progression paths | Read-only; defines valid learning sequences |
| `FretboardModel` | Canonical fretboard theory | Immutable music theory reference |

### Provenance

| Layer | Description | Example |
|-------|-------------|---------|
| Authorship | Content creation | Human-authored curriculum |
| Registry | Indexed lookup | `get_exercise(exercise_id)` |
| Validation | Format conformance | Schema validation on load |

### Execution

**sg-curriculum is read-only at runtime.** No mutations occur. Registry data is loaded from static YAML/JSON files.

### Boundary Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| AI generation deferred | Curriculum explicitly blocks AI content | `docs/ai_curriculum_generation.md` marks as future |
| Stale content | Curriculum may lag pedagogical research | Version tracking in curriculum metadata |

---

## Repository: sg-coach

### Ownership

| Component | Authority Claim | Justification |
|-----------|-----------------|---------------|
| `COACH_VERSION` | Evaluation policy version | Tracks rule changes |
| `PolicyFunction` | Recommendation authority | Deterministic rule evaluation |
| `EvidenceLedger` | Append-only evidence store | Immutable audit trail |
| `FrontendInteractionStore` | Append-only interaction log | Sprint 39 event replay |

### Provenance

| Layer | Description | Example |
|-------|-------------|---------|
| Capture | Raw performance data | Audio analysis results |
| Evaluation | Rule-based diagnosis | `evaluate_attempt()` returns DiagnosisCode |
| Recommendation | Policy-driven suggestions | `recommend_next_action()` |
| Override | Teacher authority | `teacher_override: True` |

### Execution

| System | Mutation Type | Constraint |
|--------|---------------|------------|
| `EvidenceLedger` | Append-only | No deletions, no updates |
| `SessionStore` | Append-only | Sessions immutable after creation |
| `FrontendInteractionStore` | Append-only | Events immutable after append |
| `apply_frontend_interaction()` | State transform | Deterministic, reversible via replay |

### Boundary Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| Policy drift | Rule changes affect evaluations | `COACH_VERSION` tracks policy |
| Recommendation confusion | Users may treat recommendations as commands | Clear UI labeling of suggestions |
| Mode 1 determinism | Rule-based only; no LLM | Explicit governance in architecture |

---

## Repository: sg-ai

### Ownership

| Component | Authority Claim | Justification |
|-----------|-----------------|---------------|
| `GrooveLayerModel` | Rhythm generation authority | Produces groove patterns |
| `GovernanceCheck` | Safety gate | Blocks PII, requires evidence |

### Provenance

| Layer | Description | Example |
|-------|-------------|---------|
| Input | Structured prompt data | Exercise context, student level |
| Generation | AI model output | Groove pattern, feedback text |
| Validation | Governance checks | PII scan, citation verification |
| Provisional | Awaiting approval | `provisional: True` on all outputs |

### Execution

| System | Mutation Type | Constraint |
|--------|---------------|------------|
| `SessionStore` | Write via sg-ai | Only through explicit store calls |
| `GrooveLayerModel` | Stateless | No internal state; pure function |
| `GovernanceCheck` | Blocking gate | Rejects non-compliant outputs |

### Boundary Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| Provisional confusion | AI outputs may be treated as authoritative | Explicit `provisional` flag on all outputs |
| Hallucination | Model may generate incorrect feedback | Evidence citation requirement |
| PII leak | Model may echo student data | Governance PII blocking |

---

## Repository: sg-agentd

### Ownership

| Component | Authority Claim | Justification |
|-----------|-----------------|---------------|
| `ProgressionPolicy` | Progression decision authority | Deterministic advancement rules |
| HTTP Endpoints | Mutation boundary | All state changes require explicit requests |

### Provenance

| Layer | Description | Example |
|-------|-------------|---------|
| Request | Inbound HTTP | `POST /session/advance` |
| Policy | Rule evaluation | `can_advance()` returns boolean |
| Mutation | State change | Session advanced to next exercise |
| Response | Outbound HTTP | Success/failure with evidence |

### Execution

| System | Mutation Type | Constraint |
|--------|---------------|------------|
| All mutations | Explicit HTTP request | No autonomous state changes |
| Policy functions | Read-only evaluation | Policies never mutate directly |

### Boundary Risks

| Risk | Description | Mitigation |
|------|-------------|------------|
| Collapsed approval | `/feedback_and_regen` combines feedback + regeneration | Document as single atomic operation |
| Autonomous drift | Agents may evolve to autonomous behavior | Architecture explicitly forbids |

---

## Cross-System Provenance Chain

```
┌─────────────┐     ┌─────────────┐     ┌─────────────┐
│   Student   │────▶│  sg-agentd  │────▶│  sg-coach   │
│   Input     │     │  (HTTP)     │     │  (Eval)     │
└─────────────┘     └─────────────┘     └─────────────┘
                                               │
                                               ▼
                    ┌─────────────┐     ┌─────────────┐
                    │  sg-ai      │◀────│  sg-spec    │
                    │  (Generate) │     │  (Schema)   │
                    └─────────────┘     └─────────────┘
                           │
                           ▼
                    ┌─────────────┐
                    │  Teacher    │
                    │  Override   │
                    └─────────────┘
```

### Provenance Labels

| Label | Meaning | Trust Level |
|-------|---------|-------------|
| `observed` | Raw capture | High (direct measurement) |
| `evaluated` | Rule-based diagnosis | High (deterministic) |
| `recommended` | Policy suggestion | Medium (advisory only) |
| `generated` | AI output | Low (provisional) |
| `approved` | Teacher validated | Highest (human authority) |
| `canonical` | Schema-conformant | High (contract adherence) |

---

## Mutation Boundary Map

| System | Can Create | Can Update | Can Delete | Constraint |
|--------|------------|------------|------------|------------|
| sg-spec | ❌ | ❌ | ❌ | Schemas only |
| sg-curriculum | ❌ | ❌ | ❌ | Read-only registry |
| sg-coach | ✅ (append) | ❌ | ❌ | Append-only stores |
| sg-ai | ✅ (provisional) | ❌ | ❌ | All outputs provisional |
| sg-agentd | ✅ (via request) | ✅ (via request) | ❌ | Explicit HTTP only |

---

## Experimental Output Identification

### Markers for Provisional Content

```python
# sg-ai outputs MUST include:
{
    "provisional": True,
    "generated_by": "sg-ai:GrooveLayerModel:1.0",
    "requires_approval": True,
    "evidence_citations": ["evt_...", "diag_..."],
}
```

### Markers for Recommendations (Not Commands)

```python
# sg-coach recommendations MUST include:
{
    "recommendation_type": "suggestion",  # NOT "command"
    "policy_version": "1.2.3",
    "override_allowed": True,
}
```

### Markers for Teacher Authority

```python
# Teacher override markers:
{
    "teacher_override": True,
    "approved_by": "teacher_id",
    "approved_at": "2026-05-22T10:00:00Z",
}
```

---

## Actionable Governance Checklist

### For Schema Changes (sg-spec)

- [ ] Increment version field
- [ ] Update governance doc
- [ ] Sprint approval required
- [ ] Backward compatibility assessment
- [ ] Consumer notification (sg-coach, sg-ai, sg-agentd)

### For Policy Changes (sg-coach)

- [ ] Increment `COACH_VERSION`
- [ ] Document rule change rationale
- [ ] Regression test existing evaluations
- [ ] Teacher notification if behavior changes

### For AI Model Changes (sg-ai)

- [ ] Update `generated_by` version
- [ ] Governance check validation
- [ ] Evidence citation requirement maintained
- [ ] PII blocking verified

### For API Changes (sg-agentd)

- [ ] Document mutation boundaries
- [ ] No autonomous behavior added
- [ ] Explicit request requirement maintained
- [ ] Teacher override path preserved

---

## Governance Violations to Watch

| Violation | Symptom | Resolution |
|-----------|---------|------------|
| Silent authority | System makes decisions without audit trail | Add append-only logging |
| Collapsed provenance | Can't distinguish observation from interpretation | Add provenance labels |
| Autonomous mutation | State changes without explicit request | Require HTTP boundary |
| Provisional confusion | AI output treated as canonical | Enforce `provisional` flag |
| Override bypass | AI countermands teacher decision | Architectural review |

---

## Version History

| Version | Date | Author | Changes |
|---------|------|--------|---------|
| 0.1 | 2026-05-22 | Sprint 39 | Initial governance audit |

