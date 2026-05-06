# Smart Guitar Direction

**Date:** 2026-05-06  
**Status:** CONFIRMED — Architectural direction established  
**Scope:** Directional architecture commitment (not irreversible platform lock)

---

## Executive Summary

Smart Guitar is an **Intelligent Practice Coach** with **Teacher Augmentation** capabilities.

The system provides explainable, post-session coaching powered by a deterministic symbolic adaptive spine. It prioritizes MIDI input, local-first persistence, and traceable learning signals over real-time streaming, audio DSP, or cloud-scale infrastructure.

This direction leverages the architecture already built (Sprints 1–10) rather than pivoting toward complexity the system is not yet optimized for.

---

## The 10 Decisions

### 1. Runtime Caller

**Decision:** sg-agentd daemon + CLI tooling

**Rationale:**  
The coaching spine needs a lightweight runtime that can:
- Receive session data after practice
- Call `evaluate_session()` and downstream pipeline
- Persist learning signals locally
- Expose results for UI consumption

sg-agentd becomes the orchestration layer. CLI provides developer/power-user access.

**Architectural Consequence:**  
Sprint 11 introduces a minimal runtime harness in sg-agentd that consumes sg-coach APIs.

---

### 2. Input Pipeline

**Decision:** MIDI-first

**Rationale:**  
- MIDI provides clean, timestamped note events
- No pitch detection ambiguity
- Signal quality is high enough for adaptive learning to be meaningful
- Audio DSP can layer on later without architectural distortion

**Architectural Consequence:**  
Session ingestion assumes MIDI note events. Audio-to-MIDI conversion is a future preprocessing layer, not a core dependency.

**Deferred:**  
- Audio pitch tracking
- Real-time DSP pipelines
- Polyphonic audio analysis

---

### 3. Product Direction

**Decision:** Hybrid — Primary: Intelligent Practice Coach, Secondary: Teacher Augmentation Platform

**Rationale:**  
The current architecture is:
- Deterministic and explainable
- Evidence-linked and traceable
- Adaptive but inspectable
- Contract-governed

This is the shape of educational tooling and teacher-assist systems, not real-time performance correction.

**Architectural Consequence:**  
All Sprint 11+ work optimizes for:
- Post-session diagnosis quality
- Actionable assignment generation
- Learning signal collection
- Teacher visibility into student progress

**Not optimized for:**  
- Sub-100ms live correction
- Real-time visual/audio feedback during playing
- Autonomous performance intervention

---

### 4. Feedback Capture UX

**Decision:** Passive observation + explicit rating prompts

**Rationale:**  
- Session completion detection provides implicit signals (completed, abandoned, repeated)
- Explicit prompts capture helped/did_not_help when user engagement allows
- Teacher input provides high-confidence signals in augmentation scenarios

**Architectural Consequence:**  
UI surfaces optional feedback prompts. Outcome events are captured regardless of explicit user response. Learning pipeline tolerates sparse explicit feedback.

**Deferred:**  
- Voice command feedback
- Real-time sentiment detection

---

### 5. Drill/Curriculum Ownership

**Decision:** sg-curriculum package (future) with hand-authored drills

**Rationale:**  
- DrillReference pointers must resolve to real content
- Hand-authored drills provide quality control
- sg-curriculum becomes the canonical content source
- LLM-generated drills are a future augmentation, not a replacement

**Architectural Consequence:**  
Sprint 8 DrillReference remains valid. sg-curriculum package is created when drill content authoring begins. Static catalog in sg-coach serves as bootstrap until then.

**Deferred:**  
- LLM-generated drill creation
- External curriculum provider integration
- Adaptive drill sequencing

---

### 6. Live vs Post-Session Feedback

**Decision:** Post-session first

**Rationale:**  
- Current symbolic adaptive architecture is optimized for post-hoc evaluation
- Post-session allows full-context diagnosis
- Learning signals require completed practice outcomes
- Live feedback requires streaming evaluators, latency budgets, and different runtime topology

**Architectural Consequence:**  
All evaluators assume complete session data. No streaming or incremental evaluation in Sprint 11–15.

**Deferred:**  
- Sub-100ms live correction
- Bar-level real-time feedback
- Streaming evaluator redesign

---

### 7. Scale/Persistence Target

**Decision:** Local-first, single player / teacher studio

**Rationale:**  
- JSONL + governed schemas work well for local persistence
- No cloud complexity until product-market fit is validated
- Teacher studio (1 teacher, N students) is achievable with local + sync later

**Architectural Consequence:**  
LearningSignalStore remains JSONL-based. No database, no multi-tenant infrastructure. Sync is a future layer, not a foundation dependency.

**Deferred:**  
- Cloud multi-tenant architecture
- Consumer app scale (thousands of users)
- Real-time sync infrastructure

---

### 8. Canonical Schema Authority

**Decision:** sg-spec is the single source of truth

**Rationale:**  
- Already established in Sprints 1–10
- All other repos consume sg-spec schemas
- Prevents schema drift and contract fragmentation

**Architectural Consequence:**  
No schema definitions in sg-coach, sg-agentd, or UI layers. All contracts originate in sg-spec.

**Invariant:** Runtime integrations must not bypass schema governance.

---

### 9. False-Positive Tolerance

**Decision:** Balanced — tune per-finding type

**Rationale:**  
- Over-coaching creates noise and erodes trust
- Under-coaching misses learning opportunities
- Different diagnosis types have different tolerance profiles

**Architectural Consequence:**  
Each DiagnosisCode may have its own confidence threshold. Ranking incorporates confidence. Low-confidence findings may be suppressed or deprioritized rather than shown.

**Guidance:**  
- Timing: moderate tolerance (timing errors are measurable)
- Harmony: conservative (wrong orbit diagnosis is disruptive)
- Pitch: moderate tolerance (pitch deviation is measurable)

---

### 10. Teacher Replacement vs Augmentation

**Decision:** Augment teacher

**Rationale:**  
- Explainability matters most
- Traceability matters most
- Deterministic rules preferred over black-box ML
- Teacher retains authority; system provides visibility and suggestions

**Architectural Consequence:**  
All coaching decisions remain inspectable. Learning signals are explainable. No autonomous overrides of teacher judgment. Future teacher dashboard shows "why" for every recommendation.

**Deferred:**  
- Fully autonomous curriculum
- Black-box ML adaptation
- Teacher-free operation mode

---

## Architectural Consequences Summary

### What Sprint 11–15 Optimizes For

| Priority | Focus |
|----------|-------|
| 1 | End-to-end coaching orchestration (sg-agentd runtime) |
| 2 | MIDI session ingestion |
| 3 | Practice history persistence |
| 4 | Teacher review surfaces |
| 5 | Assignment progression tracking |

### What Sprint 11–15 Does NOT Optimize For

| Deferred | Reason |
|----------|--------|
| Real-time streaming evaluation | Post-session first |
| Audio DSP ingestion | MIDI-first |
| Cloud-scale infrastructure | Local-first |
| Autonomous curriculum generation | Hand-authored first |
| Black-box ML adaptation | Explainable first |

---

## Deferred But Preserved Futures

These capabilities remain architecturally possible but are not allowed to distort Sprint 11–15 priorities:

### Real-Time Assistant (Future)

**Preserved by:**
- Evaluators are stateless functions (can be called incrementally later)
- Schemas support TargetSpan for temporal localization
- DiagnosisCode vocabulary is extensible

**Would require:**
- Streaming evaluator wrappers
- Latency budget enforcement
- Incremental aggregation
- Event bus architecture

**Status:** Deferred until post-session coaching is validated.

### Audio Ingestion (Future)

**Preserved by:**
- SessionRecord accepts normalized pitch/timing data
- Input source is abstracted from evaluation
- PitchEvaluationInput supports flexible event shapes

**Would require:**
- Audio-to-MIDI preprocessing layer
- Pitch detection confidence handling
- Polyphonic disambiguation

**Status:** Deferred until MIDI pipeline is production-stable.

### Cloud Persistence (Future)

**Preserved by:**
- All state is serializable (Pydantic models)
- Learning signals are append-only events
- User/session IDs support multi-user scenarios

**Would require:**
- Database migration from JSONL
- Sync conflict resolution
- Multi-tenant isolation
- Auth/identity layer

**Status:** Deferred until local-first iteration validates product.

### Teacher Dashboard (Future)

**Preserved by:**
- All findings have stable IDs
- Recommendations are traceable to findings
- Outcomes link back to assignments
- Learning signals explain their derivation

**Would require:**
- Read-only API surface
- Student/teacher relationship model
- Progress visualization

**Status:** Deferred until core coaching loop is stable.

---

## Rejected Paths (For Now)

| Path | Why Rejected |
|------|--------------|
| Real-time first | Architecture not yet optimized; post-session is lower risk |
| Audio-first | Signal quality uncertainty; MIDI provides clean baseline |
| Cloud-first | Premature infrastructure complexity; local-first validates faster |
| ML-first | Explainability matters more than adaptation aggressiveness |
| Autonomous curriculum | Quality control requires human authorship initially |
| Browser-only | No hard constraint; native runtime provides more flexibility |

These are not permanent rejections. They are sequencing decisions.

---

## Sprint 11 Scope

With direction confirmed, Sprint 11 becomes:

### End-to-End Coaching Orchestration

**Goal:** Connect the symbolic coaching spine to a minimal runtime.

**Deliverables:**
1. sg-agentd coaching orchestrator
   - Receives MIDI session data
   - Calls evaluate_session() → full pipeline
   - Persists outcomes and learning signals
   - Returns assignment set

2. CLI coaching command
   - `sg-coach evaluate <session.json>`
   - Outputs findings, recommendations, assignments

3. Session ingestion contract
   - MIDI event → SessionRecord normalization
   - Minimal viable session structure

4. Practice history persistence
   - Session → Evaluation → Assignment → Outcome chain
   - Queryable by user/session/date

**Not in Sprint 11:**
- UI
- Audio ingestion
- Cloud sync
- Teacher dashboard
- Live feedback

---

## Confirmation

This document represents the confirmed architectural direction for Smart Guitar.

**Core principle:**  
Do not optimize for hypothetical future complexity at the expense of the architecture that already works.

**Center of gravity:**  
The current symbolic adaptive spine is optimized for explainable post-session coaching and remains the architectural foundation.

**Next action:**  
Proceed to Sprint 11 — End-to-End Coaching Orchestration.
