"""
Module 3: Business Analysis Runner.

Executes all 18 SQL queries against BigQuery and prints formatted results.
Can run all queries, a single business question, or a specific query.

Usage:
    python -m src.business_analysis                    # all 18 queries
    python -m src.business_analysis --bq 1             # Business Question 1 only
    python -m src.business_analysis --query Q06        # single query
    python -m src.business_analysis --list              # list all queries
"""
import argparse
import logging
import time

from google.cloud import bigquery

from src.config import BQ_DATASET_ID, GCP_PROJECT_ID
from src import business_queries as BQ

logger = logging.getLogger(__name__)
DATASET_REF = f"{GCP_PROJECT_ID}.{BQ_DATASET_ID}"


def run_query(client: bigquery.Client, sql: str) -> list[dict]:
    rows = client.query(sql).result()
    return [dict(row) for row in rows]


def print_table(rows: list[dict], max_rows: int = 30) -> None:
    if not rows:
        print("    (no rows returned)")
        return
    keys = list(rows[0].keys())
    display_rows = rows[:max_rows]
    widths = {}
    for k in keys:
        col_width = max(
            len(str(k)),
            max((len(str(r.get(k, ""))) for r in display_rows), default=0)
        )
        widths[k] = min(col_width, 40)

    header = "    " + " | ".join(str(k).ljust(widths[k]) for k in keys)
    sep = "    " + "-+-".join("-" * widths[k] for k in keys)
    print(header)
    print(sep)
    for r in display_rows:
        vals = []
        for k in keys:
            v = str(r.get(k, ""))
            if len(v) > 40:
                v = v[:37] + "..."
            vals.append(v.ljust(widths[k]))
        print("    " + " | ".join(vals))
    if len(rows) > max_rows:
        print(f"    ... ({len(rows) - max_rows} more rows)")


def run_business_question(
    client: bigquery.Client, bq_name: str, queries: list[tuple]
) -> None:
    print(f"\n{'=' * 72}")
    print(f"  {bq_name}")
    print(f"{'=' * 72}")

    for query_id, description, sql in queries:
        print(f"\n  [{query_id}] {description}")
        techniques = BQ.TECHNIQUE_MAP.get(query_id, [])
        if techniques:
            print(f"  SQL: {', '.join(techniques)}")
        print(f"  {'-' * 66}")

        formatted_sql = sql.format(d=DATASET_REF)
        start = time.time()
        rows = run_query(client, formatted_sql)
        elapsed = time.time() - start

        print_table(rows)
        print(f"    ({len(rows)} rows, {elapsed:.1f}s)")


def list_queries() -> None:
    print("\n  All queries:\n")
    for bq_name, queries in BQ.ALL_QUERIES.items():
        print(f"  {bq_name}")
        for query_id, description, _ in queries:
            techniques = BQ.TECHNIQUE_MAP.get(query_id, [])
            tech_str = f"  [{', '.join(techniques)}]" if techniques else ""
            print(f"    {query_id}: {description}{tech_str}")
        print()


def run_all(bq_filter: int | None = None, query_filter: str | None = None) -> None:
    client = bigquery.Client(project=GCP_PROJECT_ID)

    print(f"\n{'#' * 72}")
    print(f"  OLIST E-COMMERCE — BUSINESS ANALYSIS REPORT")
    print(f"  Dataset: {DATASET_REF}")
    print(f"  Queries: 18 across 5 business questions")
    print(f"{'#' * 72}")

    for bq_name, queries in BQ.ALL_QUERIES.items():
        if bq_filter is not None:
            bq_num = int(bq_name.split(":")[0].replace("BQ", ""))
            if bq_num != bq_filter:
                continue

        if query_filter:
            queries = [(qid, desc, sql) for qid, desc, sql in queries if qid == query_filter]
            if not queries:
                continue

        run_business_question(client, bq_name, queries)

    print(f"\n{'#' * 72}")
    print(f"  END OF REPORT")
    print(f"{'#' * 72}\n")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s | %(message)s")
    parser = argparse.ArgumentParser(description="Olist business analysis")
    parser.add_argument("--bq", type=int, choices=[1, 2, 3, 4, 5],
                        help="Run a single business question (1-5)")
    parser.add_argument("--query", type=str,
                        help="Run a single query by ID (e.g. Q06)")
    parser.add_argument("--list", action="store_true",
                        help="List all queries without running them")
    args = parser.parse_args()

    if args.list:
        list_queries()
    else:
        run_all(bq_filter=args.bq, query_filter=args.query)
