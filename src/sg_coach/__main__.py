"""Allow running sg_coach as a module: python -m sg_coach"""
from __future__ import annotations

from .cli import main

raise SystemExit(main())
