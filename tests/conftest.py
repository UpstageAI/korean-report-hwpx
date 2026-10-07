import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path[:0] = [str(ROOT / "press_release_hwpx" / "engine"), str(Path(__file__).parent)]
