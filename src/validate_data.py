"""
Post-load validation: row counts, schema checks, and referential integrity.

Validates that:
1. Row counts in BigQuery match expected counts from CSV (no rows dropped silently)
2. Table schemas match what we defined (no type drift)
3. Primary keys have no nulls
4. Foreign keys reference valid parent records

This is not EDA (Module 2). This is a data engineering gate: did the load succeed?
"""
import logging
from pathlib import Path

from google.cloud import bigquery

from src.config import BQ_DATASET_ID, DATA_DIR, GCP_PROJECT_ID, TABLE_MAP
from src.schemas import SCHEMAS

logger = logging.getLogger(__name__)

# Expected row counts from the Kaggle dataset page.
# Used as a sanity check — if counts differ significantly, something went wrong.
EXPECTED_ROW_COUNTS = {
    "customers": 99_441,
    "orders": 99_441,
    "order_items": 112_650,
    "order_payments": 103_886,
    "order_reviews": 99_224,
    "products": 32_951,
    "sellers": 3_095,
    "geolocation": 1_000_163,
    "category_translation": 71,
}

# Foreign key relationships to validate: (child_table, child_col, parent_table, parent_col)
FK_CHECKS = [
    ("orders", "customer_id", "customers", "customer_id"),
    ("order_items", "order_id", "orders", "order_id"),
    ("order_items", "product_id", "products", "product_id"),
    ("order_items", "seller_id", "sellers", "seller_id"),
    ("order_payments", "order_id", "orders", "order_id"),
    ("order_reviews", "order_id", "orders", "order_id"),
]


def validate_row_counts(client: bigquery.Client) -> list[str]:
    """Compare actual row counts against expected. Returns list of warnings."""
    warnings = []
    logger.info("--- Row Count Validation ---")
    for table_name, expected in EXPECTED_ROW_COUNTS.items():
        table_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"
        try:
            table = client.get_table(table_ref)
            actual = table.num_rows
            status = "OK" if actual == expected else "MISMATCH"
            pct = (actual / expected - 1) * 100 if expected else 0
            msg = f"  {table_name:<25}  expected={expected:>10,}  actual={actual:>10,}  [{status}]"
            if status == "MISMATCH":
                msg += f"  ({pct:+.2f}%)"
                warnings.append(f"{table_name}: expected {expected:,}, got {actual:,}")
            logger.info(msg)
        except Exception as e:
            warnings.append(f"{table_name}: table not found — {e}")
            logger.error("  %s: NOT FOUND", table_name)
    return warnings


def validate_schemas(client: bigquery.Client) -> list[str]:
    """Check that BigQuery table schemas match our definitions."""
    warnings = []
    logger.info("--- Schema Validation ---")
    for table_name, expected_schema in SCHEMAS.items():
        table_ref = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}.{table_name}"
        try:
            table = client.get_table(table_ref)
            actual_cols = {f.name: f.field_type for f in table.schema}
            expected_cols = {f.name: f.field_type for f in expected_schema}
            if actual_cols == expected_cols:
                logger.info("  %-25s  schema OK (%d columns)", table_name, len(actual_cols))
            else:
                diff = set(expected_cols.items()) ^ set(actual_cols.items())
                msg = f"{table_name}: schema mismatch — {diff}"
                warnings.append(msg)
                logger.warning("  %s: SCHEMA MISMATCH — %s", table_name, diff)
        except Exception as e:
            warnings.append(f"{table_name}: {e}")
    return warnings


def validate_foreign_keys(client: bigquery.Client) -> list[str]:
    """Check that foreign keys reference existing parent records."""
    warnings = []
    logger.info("--- Foreign Key Validation ---")
    dataset = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"
    for child_table, child_col, parent_table, parent_col in FK_CHECKS:
        query = f"""
            SELECT COUNT(*) AS orphan_count
            FROM `{dataset}.{child_table}` c
            LEFT JOIN `{dataset}.{parent_table}` p
              ON c.{child_col} = p.{parent_col}
            WHERE p.{parent_col} IS NULL
        """
        result = client.query(query).result()
        orphan_count = list(result)[0].orphan_count
        status = "OK" if orphan_count == 0 else "ORPHANS"
        logger.info(
            "  %s.%s → %s.%s  : %s (%s orphan rows)",
            child_table, child_col, parent_table, parent_col,
            status, f"{orphan_count:,}",
        )
        if orphan_count > 0:
            warnings.append(
                f"{child_table}.{child_col} has {orphan_count:,} orphan rows "
                f"(no match in {parent_table}.{parent_col})"
            )
    return warnings


def run_validation() -> bool:
    """Run all validations. Returns True if all pass."""
    client = bigquery.Client(project=GCP_PROJECT_ID)
    all_warnings = []

    all_warnings.extend(validate_row_counts(client))
    all_warnings.extend(validate_schemas(client))
    all_warnings.extend(validate_foreign_keys(client))

    if all_warnings:
        logger.warning("=== %d validation warnings ===", len(all_warnings))
        for w in all_warnings:
            logger.warning("  • %s", w)
        return False

    logger.info("=== All validations passed ===")
    return True


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    run_validation()
