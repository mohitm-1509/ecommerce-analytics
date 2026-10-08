"""
Download the Olist Brazilian E-Commerce dataset from Kaggle using kagglehub.

Why kagglehub over alternatives:
- Official Kaggle Python library (replaces the older kaggle CLI wrapper)
- Built-in caching: skips re-download if files already exist locally
- Returns the local path directly — no subprocess calls or shell commands
- Programmatic: integrates cleanly into a Python pipeline

Prerequisites:
    1. pip install kagglehub
    2. Place your Kaggle API token at ~/.kaggle/kaggle.json
       (Download from https://www.kaggle.com/settings → "Create New Token")
"""
import logging
import shutil
from pathlib import Path

import kagglehub

from src.config import DATA_DIR, KAGGLE_DATASET_HANDLE, TABLE_MAP

logger = logging.getLogger(__name__)


def download_dataset() -> Path:
    """
    Download the Olist dataset and copy CSVs into the project's data/ directory.
    Returns the path to data/.
    """
    logger.info("Downloading dataset: %s", KAGGLE_DATASET_HANDLE)
    cache_path = Path(kagglehub.dataset_download(KAGGLE_DATASET_HANDLE))
    logger.info("Kaggle cache path: %s", cache_path)

    DATA_DIR.mkdir(parents=True, exist_ok=True)

    expected_files = {f"{name}.csv" for name in TABLE_MAP}
    found = []
    missing = []

    for csv_name in sorted(expected_files):
        src = cache_path / csv_name
        dst = DATA_DIR / csv_name
        if src.exists():
            shutil.copy2(src, dst)
            size_mb = dst.stat().st_size / (1024 * 1024)
            logger.info("  %-50s  %.2f MB", csv_name, size_mb)
            found.append(csv_name)
        else:
            logger.warning("  MISSING: %s", csv_name)
            missing.append(csv_name)

    logger.info("Downloaded %d / %d files", len(found), len(expected_files))
    if missing:
        logger.warning("Missing files: %s", missing)

    return DATA_DIR


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    download_dataset()
