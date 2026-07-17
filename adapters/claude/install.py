#!/usr/bin/env python3
"""Install the canonical Nostos Skills into .claude/skills."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from install_adapter import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main(".claude"))
