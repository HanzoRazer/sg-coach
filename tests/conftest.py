"""
Test configuration for sg-coach.

Sets up Python path to include shared modules from string_master.
This is a fallback if string_master is not installed as an editable package.
"""
import sys
from pathlib import Path

# Try relative path first (sibling directory), then absolute path
_TESTS_DIR = Path(__file__).parent
_STRING_MASTER_RELATIVE = _TESTS_DIR.parent.parent.parent / "string_master_v.4.0" / "src"
_STRING_MASTER_ABSOLUTE = Path(r"c:\Users\thepr\Downloads\string_master_v.4.0\src")

for candidate in [_STRING_MASTER_RELATIVE, _STRING_MASTER_ABSOLUTE]:
    if candidate.exists() and str(candidate) not in sys.path:
        sys.path.insert(0, str(candidate))
        break
