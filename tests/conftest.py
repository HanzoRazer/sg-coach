"""
Test configuration for sg-coach.

Sprint 41: no path hacks. sg-coach depends only on installed packages
(`sg-spec`, `sg-curriculum`) plus its own `src/`. There is intentionally NO
`sys.path` injection of `string_master` here — the canonical music vocabulary
lives in `sg_spec.music` (see sg-spec docs/music_vocabulary_authority.md).

Reproducible local setup:

    pip install -e ../sg-spec
    pip install -e ../sg-curriculum
    pip install -e .
    pytest

Do not re-introduce a string_master / shared / zone_tritone path fallback here;
the hidden-dependency guard (tests/test_no_hidden_string_master_dependency.py)
exists to keep this boundary clean.
"""
