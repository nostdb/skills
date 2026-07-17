#!/usr/bin/env python3
"""Run the shared conformance fixture through the Claude installation layout."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "scripts"))
from run_fixture import main  # noqa: E402


if __name__ == "__main__":
    sys.exit(main(".claude"))
