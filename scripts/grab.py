#!/usr/bin/env python3
"""CLI 入口：python scripts/grab.py <login|once|schedule> -c config/local.yaml"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from robjy.cli import main

if __name__ == "__main__":
    raise SystemExit(main())
