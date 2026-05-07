# MVP Release Checklist

Smart Guitar Coaching Platform v1.0.0

## Pre-Release Verification

### Schema Package (sg-spec)

- [x] All schemas have `extra="forbid"` for strict validation
- [x] RuntimeCoachingResult schema defined
- [x] Goal tracking schemas (WeaknessProgression, PracticeGoal)
- [x] Curriculum alignment schemas (CurriculumReference, CurriculumAlignmentResult)
- [x] All schemas exported via `sg_spec.schemas`
- [x] Version: 2.0.0

### Coaching Engine (sg-coach)

- [x] Session builder converts MIDI to SessionRecord
- [x] Three evaluators operational (timing, pitch, diminished)
- [x] Action recommender maps findings to actions
- [x] Drill resolver resolves drills from catalog
- [x] Practice assignment assembler creates assignments
- [x] Goal tracking builds progressions and goals
- [x] Curriculum alignment connects goals to drills
- [x] Runtime pipeline orchestrates full flow
- [x] Version: 1.0.0

### CLI Commands

- [x] `sg-coach evaluate <session.json>` — evaluate session file
- [x] `sg-coach evaluate --midi <midi.json>` — evaluate MIDI input
- [x] `sg-coach evaluate --midi <midi.json> --persist <history.jsonl>` — with persistence
- [x] `sg-coach review --history <history.jsonl>` — show timeline + progress
- [x] `sg-coach goals --history <history.jsonl>` — show practice goals
- [x] `sg-coach timeline --history <history.jsonl>` — show practice timeline
- [x] `sg-coach --version` — show version info
- [x] All commands output JSON
- [x] `--pretty` flag for formatted output
- [x] `--user-id` filtering where applicable

### Persistence

- [x] PracticeHistoryStore with JSONL format
- [x] Append-only history entries
- [x] User ID filtering
- [x] Date range filtering
- [x] Local-first operation (no network required)

### Testing

- [x] Schema validation tests (161)
- [x] Evaluator tests (89)
- [x] Builder tests (150+)
- [x] Goal tracking tests (60)
- [x] Curriculum alignment tests (40)
- [x] Runtime pipeline tests (22)
- [x] Golden fixture tests (8)
- [x] **Total: 758 tests passing**

### Fixtures

- [x] `fixtures/midi/timing_session.json`
- [x] `fixtures/midi/pitch_session.json`
- [x] `fixtures/midi/diminished_session.json`
- [x] `fixtures/midi/mixed_session.json`
- [x] `fixtures/golden/` — normalized outputs for all MIDI fixtures

### Documentation

- [x] `docs/ARCHITECTURE_SNAPSHOT_V1.md` — system topology
- [x] `docs/KNOWN_LIMITATIONS.md` — scope boundaries
- [x] `docs/MVP_RELEASE_CHECKLIST.md` — this file

## Release Process

### Version Tags

```bash
# Tag sg-spec
cd sg-spec
git tag -a v2.0.0 -m "sg-spec v2.0.0 - MVP schema release"

# Tag sg-coach
cd sg-coach
git tag -a v1.0.0 -m "sg-coach v1.0.0 - MVP coaching engine release"
```

### Final Verification

```bash
# Run full regression suite
cd sg-coach
python -m pytest tests/ -v

# Verify golden fixtures
python -m pytest tests/test_golden_fixtures.py -v

# Test CLI commands
sg-coach --version
sg-coach evaluate fixtures/midi/timing_session.json
sg-coach evaluate --midi fixtures/midi/timing_session.json --persist /tmp/test_history.jsonl
sg-coach review --history /tmp/test_history.jsonl --pretty
sg-coach goals --history /tmp/test_history.jsonl --pretty
sg-coach timeline --history /tmp/test_history.jsonl --pretty
```

### Package Installation

```bash
# Install sg-spec
cd sg-spec
pip install -e .

# Install sg-coach
cd sg-coach
pip install -e .

# Verify imports
python -c "from sg_spec.schemas import RuntimeCoachingResult; print('sg-spec OK')"
python -c "from sg_coach import run_coaching_pipeline; print('sg-coach OK')"
```

## Post-Release

### Known Issues

None blocking MVP release.

### Deferred Features

See `KNOWN_LIMITATIONS.md` for full list:

1. sg-curriculum service integration
2. Teacher dashboard UI
3. Scheduling and reminders (sg-agentd)
4. Cloud persistence
5. Real-time streaming evaluation
6. Audio input processing
7. ML-enhanced recommendations

### Monitoring

- No telemetry in MVP (local-first)
- Error handling via CLI exit codes
- Debug output via `--verbose` flag

## Sign-Off

| Role | Name | Date | Status |
|------|------|------|--------|
| Development | | | |
| Review | | | |
| Release | | | |
