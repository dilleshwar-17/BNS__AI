#!/usr/bin/env python3
"""BNS AI Super Pipeline CLI - Train, Query, and Retrieve"""

import sys
import asyncio
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent / "backend"))

from pipeline.super_pipeline import main

if __name__ == "__main__":
    asyncio.run(main())
