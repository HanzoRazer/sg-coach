"""
sg-coach: Smart Guitar Practice Coach (Mode 1 rules-first).

Provides deterministic evaluation of practice sessions and assignment planning.
No LLM required for core functionality.
"""
from .schemas import (
    ProgramType,
    Severity,
    ClaveKind,
    CoachMode,
    ProgramRef,
    SessionRecord,
    CoachEvaluation,
    PracticeAssignment,
)
from .assignment_policy import plan_assignment
from .assignment_serializer import serialize_bundle, dump_json_file, dumps_json
from .cli import build_parser, main

__version__ = "0.1.0"

__all__ = [
    # Version
    "__version__",
    # Schemas
    "ProgramType",
    "Severity",
    "ClaveKind",
    "CoachMode",
    "ProgramRef",
    "SessionRecord",
    "CoachEvaluation",
    "PracticeAssignment",
    # Assignment
    "plan_assignment",
    # Serialization
    "serialize_bundle",
    "dumps_json",
    "dump_json_file",
    # CLI
    "build_parser",
    "main",
]
