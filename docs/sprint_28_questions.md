# Sprint 28 — Clarification Questions

## Longitudinal Progress Review Implementation

---

## 1. Recent vs Historical Split Definition

The spec says "Split recent vs historical counts" for diagnosis trends.

**Question:** What defines "recent"?

Options:

| Option | Description |
|--------|-------------|
| A | Last N sessions vs older (configurable N) |
| B | Last N days vs older (configurable N) |
| C | First half vs second half of reports (by time) |
| D | Fixed split (e.g., last 3 sessions = recent) |

---

## 2. Diagnosis Code Aggregation Source

RuntimeReviewReport has `diagnosis_code: Optional[DiagnosisCode]` from the assignment.

**Question:** Should I also aggregate diagnosis codes from `evaluation.findings`?

Options:

| Option | Description |
|--------|-------------|
| A | Only assignment-level diagnosis_code |
| B | Only evaluation.findings codes |
| C | Both (union of assignment + findings) |

If C, how to handle duplicates within a session?

---

## 3. Improvement Ratio Calculation (DiagnosisTrendSummary)

**Question:** What formula for `improvement_ratio`?

Options:

| Option | Formula | Meaning |
|--------|---------|---------|
| A | `(historical - recent) / historical` | Reduction ratio |
| B | `sessions_without / total_sessions` | Clean session ratio |
| C | `1 - (recent / historical)` | Normalized reduction |

---

## 4. Outcome Ratio Calculations (OutcomeTrajectorySummary)

**Question:** What formulas for ratios?

### completion_ratio

| Option | Formula |
|--------|---------|
| A | `completed / total_sessions` |
| B | `(completed + improved) / total_sessions` |

### improvement_ratio

| Option | Formula |
|--------|---------|
| A | `improved / total_sessions` |
| B | `improved / (total - abandoned)` |

---

## 5. Deterministic Notes Format

Examples given:
- "Timing issues decreased over recent sessions."
- "Pitch instability remains recurring."
- "Insufficient evidence for stable trend analysis."

**Question:** What format/vocabulary?

Options:

| Option | Description |
|--------|-------------|
| A | Template strings with diagnosis names inserted |
| B | Fixed vocabulary of pre-defined messages |
| C | Hybrid (templates for trends, fixed for edge cases) |

**Additional:** Maximum number of notes to generate?

---

## 6. NDJSON Input Handling

The spec mentions support for:
- JSON array of RuntimeReviewReport
- Newline-delimited JSON (NDJSON)

**Question:** How to handle format detection?

Options:

| Option | Description |
|--------|-------------|
| A | Auto-detect based on file content |
| B | Require explicit `--ndjson` flag |
| C | Auto-detect, with optional `--format` override |

---

## 7. Evidence Review IDs

The schema has `evidence_review_ids: list[str]`.

**Question:** What identifier to collect?

Options:

| Option | Source |
|--------|--------|
| A | `runtime_session_id` from each RuntimeReviewReport |
| B | A separate review ID if one exists |
| C | Generated hash/composite ID |

---

## 8. Strongest Improvements / Recurring Challenges

These are `list[str]` fields.

**Questions:**

### Content format

| Option | Description |
|--------|-------------|
| A | DiagnosisCode enum values as strings (e.g., "timing_grid_deviation") |
| B | Human-readable names (e.g., "Timing Grid Deviation") |

### List limits

| Option | Description |
|--------|-------------|
| A | Top 3 items |
| B | Top 5 items |
| C | Unlimited (all qualifying) |
| D | Configurable limit |

### Ordering criteria

For strongest_improvements:
- By improvement_ratio (highest first)?
- By occurrence reduction count?

For recurring_challenges:
- By total_occurrences (highest first)?
- By recent_occurrence_count?

---

## Summary

| # | Topic | Needs Answer |
|---|-------|--------------|
| 1 | Recent/historical split | Definition |
| 2 | Diagnosis source | Assignment vs findings |
| 3 | improvement_ratio | Formula |
| 4 | Outcome ratios | Formulas |
| 5 | Notes format | Template style + max count |
| 6 | NDJSON handling | Auto-detect vs flag |
| 7 | Evidence IDs | Source field |
| 8 | Lists format | Content + limits + ordering |
