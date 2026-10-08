"""
Load Olist CSV files into Google BigQuery.

Method: Client.load_table_from_file() with explicit schema.

Why this method over alternatives:
┌─────────────────────────────┬──────────────────────────────────────────────┐
│ Method                      │ Trade-off                                    │
├─────────────────────────────┼──────────────────────────────────────────────┤
│ load_table_from_file (ours) │ CSV → BigQuery directly. No intermediary.    │
│                             │ Memory: O(chunk) not O(n). Schema enforced.  │
├─────────────────────────────┼──────────────────────────────────────────────┤
│ load_table_from_dataframe   │ CSV → pandas DataFrame → Parquet → BigQuery. │
│                             │ Extra step. Entire dataset in memory.        │
│                             │ Pandas dtype inference can conflict with BQ. │
├─────────────────────────────┼──────────────────────────────────────────────┤
│ load_table_from_uri         │ Requires GCS upload first. Two-step process. │
│                             │ Overkill when files are local and < 1 GB.    │
├─────────────────────────────┼──────────────────────────────────────────────┤
│ BigQuery Console UI         │ Manual. Not reproducible. No version control.│
└─────────────────────────────┴──────────────────────────────────────────────┘

Authentication:
    Uses Application Default Credentials (ADC) — the Google-recommended approach.
    Run once: gcloud auth application-default login
    No service-account key files to manage or accidentally commit.

Prerequisites:
    1. pip install google-cloud-bigquery
    2. gcloud auth application-default login
    3. Update GCP_PROJECT_ID in src/config.py
"""
import logging
from pathlib import Path

from google.cloud import bigquery

from src.config import BQ_DATASET_ID, BQ_LOCATION, DATA_DIR, GCP_PROJECT_ID, TABLE_MAP
from src.schemas import SCHEMAS

logger = logging.getLogger(__name__)


def get_client() -> bigquery.Client:
    return bigquery.Client(project=GCP_PROJECT_ID)


def create_dataset_if_not_exists(client: bigquery.Client) -> None:
    dataset_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
    dataset = bigquery.Dataset(dataset_ref)
    dataset.location = BQ_LOCATION
    client.create_dataset(dataset, exists_ok=True)
    logger.info("Dataset ready: %s", dataset_ref)


def load_table(client: bigquery.Client, csv_path: Path, table_name: str) -> int:
    """
    Load a single CSV into a BigQuery table. Returns rows loaded.

    Key LoadJobConfig settings:
    - skip_leading_rows=1: CSV has a header row; schema defines columns.
    - write_disposition=WRITE_TRUNCATE: makes the load idempotent.
      Re-running replaces data instead of appending duplicates.
    - allow_quoted_newlines=True: review comments contain newlines inside quotes.
    - source_format=CSV: explicit (not relying on file-extension sniffing).
    """
    table_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"

    job_config = bigquery.LoadJobConfig(
        schema=SCHEMAS[table_name],
        skip_leading_rows=1,
        source_format=bigquery.SourceFormat.CSV,
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        allow_quoted_newlines=True,
    )

    with open(csv_path, "rb") as f:
        load_job = client.load_table_from_file(f, table_ref, job_config=job_config)

    load_job.result()  # blocks until complete
    table = client.get_table(table_ref)
    logger.info("  %-25s  → %s rows", table_name, f"{table.num_rows:,}")
    return table.num_rows


def load_all_tables() -> dict[str, int]:
    """Load all 9 CSVs into BigQuery. Returns {table_name: row_count}."""
    client = get_client()
    create_dataset_if_not_exists(client)

    results = {}
    for csv_stem, table_name in TABLE_MAP.items():
        csv_path = DATA_DIR / f"{csv_stem}.csv"
        if not csv_path.exists():
            logger.error("CSV not found: %s — run download_data.py first", csv_path)
            continue
        try:
            row_count = load_table(client, csv_path, table_name)
            results[table_name] = row_count
        except Exception as e:
            logger.error("Failed to load %s: %s", table_name, e)
            raise

    logger.info("Loaded %d / %d tables", len(results), len(TABLE_MAP))
    return results


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    load_all_tables()
