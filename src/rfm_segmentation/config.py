from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
DATA_DIR = PROJECT_ROOT / "data"
OUTPUT_DIR = PROJECT_ROOT / "outputs" / "rfm_segmentation"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

REFERENCE_DATE = "2018-10-18"

K_RANGE = range(2, 11)

RANDOM_STATE = 42
