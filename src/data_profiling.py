"""
Module 2: Data Exploration & Quality Audit — SQL-based profiling.

Runs all profiling queries against BigQuery and prints a structured report.
No data is downloaded locally — all computation happens server-side.

Why SQL-based profiling over pandas / ydata-profiling:
- Demonstrates SQL proficiency (the core skill being assessed)
- Data stays in BigQuery — no memory pressure from downloading 1M+ rows
- Queries are saved, versioned, and re-runnable
- Same approach used in production data engineering teams

Usage:
    python -m src.data_profiling                 # full report
    python -m src.data_profiling --section nulls # single section
"""
import argparse
import logging
import sys

from google.cloud import bigquery

from src.config import BQ_DATASET_ID, GCP_PROJECT_ID
from src.schemas import SCHEMAS
from src import eda_queries as Q

logger = logging.getLogger(__name__)
DATASET = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"


def run_query(client: bigquery.Client, sql: str) -> list[dict]:
    rows = client.query(sql).result()
    return [dict(row) for row in rows]


def print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def print_table(rows: list[dict], indent: int = 2) -> None:
    if not rows:
        print(f"{' ' * indent}(no rows)")
        return
    keys = list(rows[0].keys())
    widths = {k: max(len(str(k)), max(len(str(r.get(k, ""))) for r in rows)) for k in keys}
    pad = " " * indent
    header = pad + " | ".join(str(k).ljust(widths[k]) for k in keys)
    sep = pad + "-+-".join("-" * widths[k] for k in keys)
    print(header)
    print(sep)
    for r in rows:
        print(pad + " | ".join(str(r.get(k, "")).ljust(widths[k]) for k in keys))


# ---------------------------------------------------------------------------
# Section runners
# ---------------------------------------------------------------------------

def section_overview(client: bigquery.Client) -> None:
    print_section("1. TABLE OVERVIEW")
    sql = Q.TABLE_OVERVIEW.format(dataset=DATASET)
    print_table(run_query(client, sql))

    print(f"\n  Column metadata:")
    sql = Q.COLUMN_METADATA.format(project=GCP_PROJECT_ID, dataset=BQ_DATASET_ID)
    rows = run_query(client, sql)
    current_table = None
    for r in rows:
        if r["table_name"] != current_table:
            current_table = r["table_name"]
            print(f"\n  {current_table}:")
        nullable = "NULLABLE" if r["is_nullable"] == "YES" else "REQUIRED"
        print(f"    {r['column_name']:<40} {r['data_type']:<15} {nullable}")


def build_null_query(table_name: str) -> str:
    """Dynamically build a null-analysis query for a table's columns."""
    schema = SCHEMAS.get(table_name, [])
    if not schema:
        return ""
    col_exprs = []
    for field in schema:
        col_exprs.append(
            Q.NULL_COLUMN_TEMPLATE.format(col=field.name)
        )
    return f"""
SELECT
    '{table_name}' AS table_name,
    COUNT(*) AS total_rows,{','.join(col_exprs)}
FROM `{DATASET}.{table_name}`
"""


def section_nulls(client: bigquery.Client) -> None:
    print_section("2. COMPLETENESS — Null Analysis")
    for table_name in SCHEMAS:
        sql = build_null_query(table_name)
        rows = run_query(client, sql)
        if not rows:
            continue
        row = rows[0]
        total = row["total_rows"]
        print(f"\n  {table_name} ({total:,} rows):")
        print(f"    {'Column':<40} {'Nulls':>10} {'Null %':>8}")
        print(f"    {'-'*40} {'-'*10} {'-'*8}")
        for field in SCHEMAS[table_name]:
            null_count = row.get(f"{field.name}_nulls", 0)
            null_pct = row.get(f"{field.name}_null_pct", 0.0)
            flag = " ⚠" if null_pct > 0 else ""
            print(f"    {field.name:<40} {null_count:>10,} {null_pct:>7.2f}%{flag}")


def section_uniqueness(client: bigquery.Client) -> None:
    print_section("3. UNIQUENESS — Duplicate Detection")

    for table_name, pk_col in Q.PRIMARY_KEYS.items():
        sql = Q.PK_DUPLICATES.format(dataset=DATASET, table=table_name, pk_col=pk_col)
        rows = run_query(client, sql)
        if rows:
            print(f"\n  ⚠ {table_name}.{pk_col}: {len(rows)} duplicate keys found")
            print_table(rows[:5], indent=4)
        else:
            print(f"  ✓ {table_name}.{pk_col}: unique (0 duplicates)")

    print(f"\n  Geolocation duplication (many lat/lng per zip code):")
    sql = Q.GEOLOCATION_DEDUP_STATS.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print(f"\n  Top duplicated zip codes:")
    sql = Q.GEOLOCATION_DUPLICATION.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)


def section_distributions(client: bigquery.Client) -> None:
    print_section("4. DISTRIBUTIONS")

    print("\n  4a. Order Status:")
    sql = Q.ORDER_STATUS_DIST.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4b. Payment Types:")
    sql = Q.PAYMENT_TYPE_DIST.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4c. Review Scores:")
    sql = Q.REVIEW_SCORE_DIST.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4d. Top 20 Product Categories:")
    sql = Q.TOP_PRODUCT_CATEGORIES.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4e. Customer States (Top 10):")
    sql = Q.CUSTOMER_STATE_DIST.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4f. Seller States (Top 10):")
    sql = Q.SELLER_STATE_DIST.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4g. Repeat Customer Rate:")
    sql = Q.REPEAT_CUSTOMER_RATE.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  4h. Numeric Summaries (5-number + mean + stddev):")
    for table, col, label in Q.NUMERIC_PROFILES:
        sql = Q.NUMERIC_SUMMARY.format(
            dataset=DATASET, table=table, col=col, col_label=label
        )
        print_table(run_query(client, sql), indent=4)


def section_temporal(client: bigquery.Client) -> None:
    print_section("5. TEMPORAL — Date Ranges & Delivery")

    print("\n  Order date range:")
    sql = Q.ORDER_DATE_RANGE.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  Orders per month:")
    sql = Q.ORDERS_PER_MONTH.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)

    print("\n  Delivery time statistics:")
    sql = Q.DELIVERY_TIME_STATS.format(dataset=DATASET)
    print_table(run_query(client, sql), indent=4)


def section_outliers(client: bigquery.Client) -> None:
    print_section("6. OUTLIERS — IQR Method")
    print("  IQR = Q3 - Q1")
    print("  Lower bound = Q1 - 1.5 × IQR")
    print("  Upper bound = Q3 + 1.5 × IQR\n")

    for table, col, label in Q.OUTLIER_PROFILES:
        sql = Q.OUTLIER_IQR.format(
            dataset=DATASET, table=table, col=col, col_label=label
        )
        print_table(run_query(client, sql), indent=4)
        print()


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------

SECTIONS = {
    "overview": section_overview,
    "nulls": section_nulls,
    "uniqueness": section_uniqueness,
    "distributions": section_distributions,
    "temporal": section_temporal,
    "outliers": section_outliers,
}


def run_profiling(sections: list[str] | None = None) -> None:
    client = bigquery.Client(project=GCP_PROJECT_ID)
    targets = sections or list(SECTIONS.keys())

    print(f"\n{'#' * 70}")
    print(f"  OLIST E-COMMERCE — DATA PROFILING REPORT")
    print(f"  Dataset: {DATASET}")
    print(f"{'#' * 70}")

    for name in targets:
        if name not in SECTIONS:
            logger.warning("Unknown section: %s", name)
            continue
        SECTIONS[name](client)

    print(f"\n{'#' * 70}")
    print(f"  END OF REPORT")
    print(f"{'#' * 70}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Olist data profiling")
    parser.add_argument(
        "--section",
        choices=list(SECTIONS.keys()),
        nargs="+",
        help="Run specific sections only",
    )
    args = parser.parse_args()
    run_profiling(args.section)
