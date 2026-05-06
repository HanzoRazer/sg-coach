# Architecture Decision Checkpoint

**Date:** 2026-05-06  
**Milestone:** Layer 1–2 Symbolic Adaptive Coaching Spine  
**Status:** PAUSED — Awaiting product/runtime decisions

---

## Current State

### What Exists

```
Sprints 1-10 Complete:
├── sg-spec (527 tests passing)
│   ├── Coach schemas (SessionRecord, CoachEvaluation, CoachFinding)
│   ├── Action mapping (RecommendedAction, ActionRecommendationSet)
│   ├── User feedback (UserFeedbackEvent, LearningSignal, FeedbackCaptureRequest)
│   ├── Learning aggregation (ActionEffectivenessProfile)
│   ├── Learning store (LearningSignalQuery)
│   ├── Personalization (PersonalizationBlendConfig, PersonalizedActionScore)
│   ├── Drill resolution (DrillReference, DrillResolutionResult)
│   ├── Practice assignment (AssembledPracticeAssignment)
│   └── Assignment outcome (AssignmentOutcomeEvent)
│
└── sg-coach (527 tests passing)
    ├── Evaluators (diminished, timing, pitch)
    ├── Action recommender
    ├── Feedback capture
    ├── Learning weight/aggregation
    ├── Adaptive ranking
    ├── Learning store (JSONL)
    ├── Personalization blend
    ├── Drill resolver
    ├── Practice assignment assembler
    └── Assignment outcome tracking
```

### Symbolic Loop Complete

```
SessionRecord
→ CoachEvaluation + CoachFinding
→ ActionRecommendationSet
→ Ranked ActionRecommendationSet (personalized)
→ DrillResolutionResult
→ AssembledPracticeAssignment
→ AssignmentOutcomeEvent
→ FeedbackCaptureRequest
→ UserFeedbackEvent
→ LearningSignal
→ ActionEffectivenessProfile
→ (back to ranking)
```

---

## Open Decisions (Blocking Sprint 11+)

### 1. Runtime Caller

**Question:** What process currently calls `evaluate_session()`?

**Options:**
- [ ] CLI tool
- [ ] sg-agentd daemon
- [ ] Notebook/REPL
- [ ] Tests only (no production runtime)
- [ ] WebSocket service
- [ ] Other: _________

**Why it blocks:** Architecture assumes a caller exists. If it doesn't, Sprint 11 should build one.

---

### 2. Input Pipeline

**Question:** Where does normalized note/timing/pitch data come from?

**Options:**
- [ ] MIDI parser
- [ ] Audio pitch tracker
- [ ] USB guitar hardware
- [ ] DAW export
- [ ] Browser app
- [ ] Manual/simulated fixtures only
- [ ] Other: _________

**Why it blocks:** Adaptive accuracy depends on signal quality. If input is simulated, the learning loop is theoretical.

---

### 3. Product Direction

**Question:** What is Smart Guitar becoming?

**Options:**
- [ ] A. Intelligent Practice Coach (diagnose → assign → adapt)
- [ ] B. Real-Time Performance Assistant (live correction during playing)
- [ ] C. Curriculum Tutor (structured progression system)
- [ ] D. Skill Analytics Platform (long-term progress modeling)
- [ ] E. Hybrid: _________

**Why it blocks:** Next 10 sprints differ radically based on this answer.

---

### 4. Feedback Capture UX

**Question:** How does a user actually respond with helped/did_not_help/abandoned?

**Options:**
- [ ] UI buttons
- [ ] Voice command
- [ ] Passive observation (session completion detection)
- [ ] Explicit rating prompt
- [ ] Teacher input
- [ ] Not designed yet
- [ ] Other: _________

**Why it blocks:** If feedback isn't realistically collectible, the learning loop stalls.

---

### 5. Drill/Curriculum Ownership

**Question:** What is the long-term source for drill content?

**Options:**
- [ ] sg-curriculum package
- [ ] JSON content packs
- [ ] LLM-generated drills
- [ ] Hand-authored drills
- [ ] External curriculum provider
- [ ] Not decided yet

**Who owns canonical drill identity?** (e.g., `diminished_orbit_isolation_v1` must resolve to real content)

**Why it blocks:** Sprint 8 DrillReference is a pointer. It must point somewhere.

---

### 6. Live vs Post-Session Feedback

**Question:** Is real-time feedback required?

**Options:**
- [ ] Sub-100ms correction (live during playing)
- [ ] Bar-level feedback (within a few seconds)
- [ ] Session-end only (post-hoc evaluation)
- [ ] Hybrid: _________

**Why it blocks:** Live feedback requires different storage, evaluator design, and runtime topology.

---

### 7. Scale/Persistence Target

**Question:** What is the expected scale?

**Options:**
- [ ] Single local player
- [ ] Teacher studio (1 teacher, N students)
- [ ] Consumer app (thousands of users)
- [ ] Enterprise (concurrent multi-tenant)

**Storage model:**
- [ ] Local-only
- [ ] Synced to cloud
- [ ] Per-device
- [ ] Multi-device

**Why it blocks:** JSONL is fine for local, breaks at scale. Persistence model affects all Sprint 11+ work.

---

### 8. Canonical Schema Authority

**Question:** Confirm sg-spec is the single source of truth for all contracts?

- [ ] Yes — all other repos consume sg-spec schemas
- [ ] No — schema ownership is distributed
- [ ] Partially — some schemas live elsewhere: _________

**Why it blocks:** Schema drift becomes inevitable without explicit ownership.

---

### 9. False-Positive Tolerance

**Question:** Is false-positive coaching acceptable?

**Options:**
- [ ] Coach too often (better to over-diagnose than miss issues)
- [ ] Coach conservatively (better to miss issues than misdiagnose)
- [ ] Balanced (tune per-finding type)

**Why it blocks:** Affects all thresholds, ranking weights, and confidence requirements.

---

### 10. Teacher Replacement vs Augmentation

**Question:** Is Smart Guitar replacing a human teacher or augmenting one?

**Options:**
- [ ] Augment teacher (explainability, traceability, deterministic rules preferred)
- [ ] Replace teacher (adaptation aggressiveness, autonomy, ML preferred)
- [ ] Both contexts supported

**Why it blocks:** These are architecturally different systems.

---

## Why These Block Sprint 11

The codebase is healthy. The symbolic loop is complete. The next bottleneck is **product/runtime truth, not engineering capacity**.

Possible Sprint 11+ directions (all blocked until decisions above):

| If Product Is... | Sprint 11 Would Be... |
|------------------|----------------------|
| Practice Coach | Runtime integration + real input pipeline |
| Real-Time Assistant | Streaming evaluator + sub-100ms path |
| Curriculum Tutor | sg-curriculum content system |
| Analytics Platform | Progress modeling + weakness detection |
| Augment Teacher | Explainability layer + teacher dashboard |
| Replace Teacher | ML adaptation + autonomous curriculum |

Building any of these without knowing the product direction risks optimizing the wrong system.

---

## Next Steps

1. **Stakeholder answers the 10 questions above**
2. **Architecture review based on answers**
3. **Sprint 11 scope defined**
4. **Implementation resumes**

No new implementation work until decisions are made.

---

## Appendix: Test Coverage

```
sg-spec:  ~150 schema tests
sg-coach: ~377 behavior tests
Total:    527 tests passing
```

All Layer 1 diagnosis codes have:
- Evaluator coverage
- Action mapping
- Drill resolution
- Assignment assembly
- Outcome tracking
