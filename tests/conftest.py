import sys, os
from pathlib import Path

# Prepend the project root so “import src…” works
PROJECT_ROOT = Path(__file__).parent.parent.resolve()
sys.path.insert(0, str(PROJECT_ROOT))
