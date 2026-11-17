#!/usr/bin/env python3
"""Start the focused Research Loom study from the repository or its distribution."""
from pathlib import Path
import runpy
import sys

study=Path(__file__).resolve().parent/'studies'/'research-loom'
sys.path.insert(0,str(study))
runpy.run_path(str(study/'serve.py'),run_name='__main__')
