"""
Project Orchestrator: Download → Load → Validate → Profile → Analyse → Views → ML

Usage:
    python main.py                  # run Module 1 (download + load + validate)
    python main.py download         # download only
    python main.py load             # load only
    python main.py validate         # validate only
    python main.py profile          # Module 2: data profiling
    python main.py analyse          # Module 3: business analysis (18 queries)
    python main.py views            # Module 4: create BigQuery views for Power BI
    python main.py features         # Module 6: build ML feature table from BigQuery
    python main.py train            # Module 6: train satisfaction prediction model
    python main.py explain          # Module 6: SHAP explainability analysis
    python main.py evaluate         # Module 6: business impact estimation
    python main.py all              # run everything (Module 1-4 + 6)
"""
import logging
import sys
import time

from src.download_data import download_dataset
from src.load_to_bigquery import load_all_tables
from src.validate_data import run_validation
from src.data_profiling import run_profiling
from src.business_analysis import run_all as run_business_analysis
from src.create_views import create_all_views
from src.feature_engineering import build_feature_table
from src.train_model import run_training
from src.explain_model import run_explanation
from src.model_evaluation import run_evaluation

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
    datefmt="%H:%M:%S",
)
logger = logging.getLogger(__name__)

STEPS = {
    "download": ("Downloading dataset from Kaggle", download_dataset),
    "load": ("Loading CSVs into BigQuery", load_all_tables),
    "validate": ("Validating loaded data", run_validation),
    "profile": ("Running data profiling (Module 2)", run_profiling),
    "analyse": ("Running business analysis (Module 3)", run_business_analysis),
    "views": ("Creating BigQuery views for Power BI (Module 4)", create_all_views),
    "features": ("Building ML feature table (Module 6, Step 1)", build_feature_table),
    "train": ("Training satisfaction model (Module 6, Steps 2-5)", run_training),
    "explain": ("Running SHAP analysis (Module 6, Step 6)", run_explanation),
    "evaluate": ("Computing business impact (Module 6, Step 7)", run_evaluation),
}

MODULE1_STEPS = ["download", "load", "validate"]
ALL_STEPS = list(STEPS.keys())


def run(steps: list[str]) -> None:
    overall_start = time.time()
    for step_name in steps:
        description, func = STEPS[step_name]
        logger.info("=" * 60)
        logger.info("STEP: %s", description)
        logger.info("=" * 60)
        start = time.time()
        func()
        elapsed = time.time() - start
        logger.info("Completed '%s' in %.1f seconds", step_name, elapsed)

    total = time.time() - overall_start
    logger.info("=" * 60)
    logger.info("Pipeline complete. Total time: %.1f seconds", total)


if __name__ == "__main__":
    requested = sys.argv[1:] if len(sys.argv) > 1 else MODULE1_STEPS
    if requested == ["all"]:
        requested = ALL_STEPS
    invalid = [s for s in requested if s not in STEPS]
    if invalid:
        print(f"Unknown steps: {invalid}. Valid: {list(STEPS.keys()) + ['all']}")
        sys.exit(1)
    run(requested)
