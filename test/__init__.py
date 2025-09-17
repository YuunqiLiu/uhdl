"""
Test package bootstrap: ensure 'uhdl' (project root) is importable when
running tests via unittest/VS Code by prepending the repository root
to sys.path. This avoids 'ModuleNotFoundError: uhdl' without requiring
an editable install.
"""
import os
import sys

_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if _ROOT not in sys.path:
    sys.path.insert(0, _ROOT)
