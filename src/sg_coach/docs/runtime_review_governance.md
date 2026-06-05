# Runtime Review Governance

Sprint 27: Runtime Evidence Review Report.

## Purpose

Runtime review transforms runtime evidence into structured review reports for:

- Teachers
- Students
- Dashboards
- Future UI layers

This is the first human-readable pedagogical reporting layer in Smart Guitar.

## Review Report Architecture

### What Runtime Review Does

1. **build_runtime_evidence_summary()**
   - Summarizes evidence attached to runtime session
   - Counts findings, recommendations, assignments
   - Reports presence of session_record and evaluation

2. **build_runtime_outcome_summary()**
   - Extracts outcome from RuntimeSessionResult
   - Reports queue_updated, curriculum_advanced
   - Extracts next_curriculum_content_id if available

3. **build_runtime_review_report()**
   - Combines evidence and outcome summaries
   - Determines status (complete/partial/missing_evidence)
   - Embeds full RuntimePracticeSession for self-contained review

### What Runtime Review Does NOT Do

- Generate AI summaries
- Mutate canonical state
- Persist reports automatically
- Make curriculum decisions
- Grade or score performance

## Evidence Summarization

```
RuntimeEvidenceSummary:
├── has_session_record: bool
├── has_evaluation: bool
├── finding_count: int (from evaluation.findings)
├── recommendation_count: int (sum of all actions across recommendation sets)
└── assignment_count: int (1 if assignment exists)
```

Graceful degradation: missing evidence → counts = 0

## Outcome Summarization

```
RuntimeOutcomeSummary:
├── outcome: PracticeOutcome (completed/improved/worsened/etc)
├── queue_updated: bool
├── curriculum_advanced: bool
├── next_curriculum_content_id: str (from curriculum_recommendation.content_id)
└── reasons: list[str]
```

If RuntimeSessionResult is None, all fields default to empty/False.

## Status Resolution

```
complete:
    has_session_record AND has_evaluation

partial:
    has one but not both

missing_evidence:
    has neither session_record nor evaluation
```

## Diagnosis Code Extraction

Diagnosis code is extracted from assignment.diagnosis_code:
- If already DiagnosisCode enum, use directly
- If string, try DiagnosisCode(value)
- If invalid or missing, return None

Schema uses strict DiagnosisCode enum, not string.

## Report Structure

```
RuntimeReviewReport:
├── runtime_session_id: str
├── status: RuntimeReviewStatus
├── student_id: str (from runtime session)
├── assignment_id: str
├── queue_id: str
├── diagnosis_code: DiagnosisCode
├── runtime_session: RuntimePracticeSession (embedded, full)
├── evidence_summary: RuntimeEvidenceSummary
├── outcome_summary: RuntimeOutcomeSummary
├── generated_at: datetime
└── version: str
```

## Deterministic Execution

Runtime review guarantees:

1. **No AI generation** — All summaries are structured extractions
2. **No state mutation** — Reports are read-only
3. **Reproducible** — Same inputs produce same outputs
4. **Inspectable** — Full runtime session embedded

## CLI Commands

```bash
# Generate review report (without result)
sg-coach runtime review \
    --runtime-session runtime.json \
    --pretty

# Generate review report (with result)
sg-coach runtime review \
    --runtime-session runtime.json \
    --runtime-result result.json \
    --pretty
```

## Governance Rules

1. Runtime review reports are derived artifacts
2. Reports must not mutate canonical state
3. Reporting must remain deterministic
4. Missing evidence must degrade gracefully
5. Reports must remain inspectable and reproducible
6. AI-generated summaries are deferred

## Future Extensions

Sprint 27 does NOT include:

- Natural language summaries
- Grading/scoring
- Teacher annotations
- Report persistence
- PDF/HTML export
- Dashboard visualization
- Playback integration

These are deferred to future sprints.

## Version

- runtime_review.py: 0.1.0
- RuntimeReviewReport schema: 0.1
- RuntimeEvidenceSummary schema: 0.1
- RuntimeOutcomeSummary schema: 0.1
