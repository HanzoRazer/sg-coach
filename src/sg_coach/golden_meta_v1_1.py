"""
v1.1 Golden Metadata: Per-vector seed and provenance tracking.

Provides:
- VectorMetaV1_1: structured per-vector metadata
- read_vector_meta(): read existing meta from vector directory
- ensure_vector_meta(): create or update vector metadata
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional


META_FILENAME = "vector_meta_v1.json"


@dataclass
class VectorMetaV1_1:
    """
    Per-vector metadata (auditable + stable).
    """
    schema_id: str = "sg_coach_golden_vector_meta"
    schema_version: str = "v1"
    seed: int = 123
    notes: str = ""
    created_at_utc: str = "2000-01-01T00:00:00Z"
    updated_at_utc: str = "2000-01-01T00:00:00Z"

    def to_json(self) -> Dict[str, Any]:
        return {
            "schema_id": self.schema_id,
            "schema_version": self.schema_version,
            "seed": int(self.seed),
            "notes": self.notes,
            "created_at_utc": self.created_at_utc,
            "updated_at_utc": self.updated_at_utc,
        }

    @staticmethod
    def from_json(d: Dict[str, Any]) -> "VectorMetaV1_1":
        return VectorMetaV1_1(
            schema_id=str(d.get("schema_id", "sg_coach_golden_vector_meta")),
            schema_version=str(d.get("schema_version", "v1")),
            seed=int(d.get("seed", 123)),
            notes=str(d.get("notes", "")),
            created_at_utc=str(d.get("created_at_utc", "2000-01-01T00:00:00Z")),
            updated_at_utc=str(d.get("updated_at_utc", "2000-01-01T00:00:00Z")),
        )


def _load_json(p: Path) -> Dict[str, Any]:
    return json.loads(p.read_text(encoding="utf-8"))


def _write_json(p: Path, data: Dict[str, Any]) -> None:
    p.write_text(json.dumps(data, indent=2, sort_keys=True, ensure_ascii=False) + "\n", encoding="utf-8")


def read_vector_meta(vector_dir: Path) -> Optional[VectorMetaV1_1]:
    """Read vector metadata from vector_meta_v1.json if it exists."""
    fp = vector_dir / META_FILENAME
    if not fp.exists():
        return None
    return VectorMetaV1_1.from_json(_load_json(fp))


def ensure_vector_meta(
    vector_dir: Path,
    *,
    seed: int,
    now_utc_iso: str,
    notes: str = "",
) -> VectorMetaV1_1:
    """
    If meta exists: keep existing created_at_utc; update seed only if missing; update updated_at_utc.
    If meta missing: create it with provided seed + now.
    """
    existing = read_vector_meta(vector_dir)
    if existing is None:
        m = VectorMetaV1_1(seed=int(seed), notes=notes, created_at_utc=now_utc_iso, updated_at_utc=now_utc_iso)
        _write_json(vector_dir / META_FILENAME, m.to_json())
        return m

    # keep created_at_utc, notes unless new notes provided
    if not existing.seed:
        existing.seed = int(seed)
    if notes and not existing.notes:
        existing.notes = notes
    existing.updated_at_utc = now_utc_iso
    _write_json(vector_dir / META_FILENAME, existing.to_json())
    return existing


__all__ = [
    "META_FILENAME",
    "VectorMetaV1_1",
    "read_vector_meta",
    "ensure_vector_meta",
]
