# Module 1 — Data Acquisition & BigQuery Setup: Methodology

This document explains **every technical decision** made in Module 1, why each method was chosen over alternatives, and the reasoning (including cost/performance calculations) behind those choices.

---

## 1. Why BigQuery over Local PostgreSQL?

### Decision: Google BigQuery (serverless cloud data warehouse)

| Criterion | BigQuery | PostgreSQL (local) |
|---|---|---|
| Resume signal | "Google BigQuery" is a top-5 listed skill in UK DA/DS job postings | "PostgreSQL" is common but doesn't signal cloud experience |
| Setup effort | No installation. Browser + Python SDK | Install server, configure users, ports, pg_hba.conf |
| Cost | Free tier: 10 GB storage, 1 TB queries/month | Free but requires local compute |
| Scalability signal | Shows you can work with warehouse-scale tools | Doesn't demonstrate cloud readiness |
| SQL dialect | Standard SQL (transferable to Snowflake, Redshift, Databricks SQL) | PostgreSQL-specific extensions (e.g., `::cast`, `ILIKE`) |
| Collaboration | Share dataset via IAM — interviewer can verify your work | Running on your laptop — no way to share |

### Cost calculation for this project

**Storage:**
- Total CSV size: ~120 MB
- BigQuery stores data columnar-compressed — expect ~30-40 MB actual storage
- Free tier: 10 GB → we use < 0.4% of the free allocation

**Queries:**
- Each of our 15+ queries scans at most the full dataset (~120 MB raw)
- Even 100 query runs = 12 GB scanned
- Free tier: 1 TB/month → we use ~1.2% of the free allocation

**Verdict:** This entire project costs $0.00.

---

## 2. Why `kagglehub` over Other Download Methods?

### Alternatives considered

| Method | Pros | Cons |
|---|---|---|
| **kagglehub** (chosen) | Official Kaggle Python library. Built-in caching. Returns local path. Programmatic. | Requires Kaggle API token |
| `kaggle` CLI (`kaggle datasets download`) | Well-known. Works from terminal. | Subprocess call from Python. Unzipping is manual. Older library. |
| `opendatasets` | Auto-prompts for credentials | Third-party, less maintained, adds unnecessary dependency |
| Manual download from browser | No code needed | Not reproducible. No version pinning. |
| `requests` + Kaggle API directly | Full control | Reinventing the wheel. Auth handling, pagination, error handling. |

### Decision rationale

`kagglehub` is the **current official library** maintained by Kaggle (the `kaggle` package is the older CLI wrapper). Key advantages:
1. **Caching**: Files download once to `~/.cache/kagglehub/`. Subsequent calls return the path instantly (O(1) filesystem check vs O(n) re-download).
2. **Version pinning**: `kagglehub.dataset_download("olistbr/brazilian-ecommerce/versions/2")` pins to a specific dataset version — critical for reproducibility.
3. **No subprocess**: Unlike calling `kaggle datasets download -d ...` via `subprocess.run()`, kagglehub is a native Python API. No shell injection risk, no platform-specific path issues.

---

## 3. Why `load_table_from_file` over Other BigQuery Loading Methods?

This is the most consequential technical decision in Module 1.

### Method comparison

```
CSV file ──→ BigQuery                               (load_table_from_file)
CSV file ──→ pandas DataFrame ──→ Parquet ──→ BigQuery  (load_table_from_dataframe)
CSV file ──→ GCS bucket ──→ BigQuery                 (load_table_from_uri)
CSV file ──→ BigQuery Console UI                     (manual upload)
```

### Detailed analysis

#### Option A: `load_table_from_file` (CHOSEN)

**How it works:**
1. Open CSV as a binary file handle
2. Stream bytes directly to BigQuery's load API
3. BigQuery parses CSV server-side using our schema

**Memory complexity:** O(buffer_size), typically 8 KB. The file is streamed, never loaded entirely into memory.

**Advantages:**
- Single step: CSV → BigQuery
- Memory-efficient: works for files larger than available RAM
- Schema enforced at load time — type mismatches fail immediately
- No intermediate format conversion

**Disadvantage:**
- CSV parsing happens server-side — BigQuery must handle encoding, quoting, escaping

#### Option B: `load_table_from_dataframe`

**How it works:**
1. `pd.read_csv()` reads entire CSV into memory as a DataFrame
2. Client serialises DataFrame to Parquet (in-memory)
3. Parquet bytes uploaded to BigQuery

**Memory complexity:** O(n) where n = dataset size. For the Olist dataset:
- Raw CSV: ~120 MB
- pandas DataFrame in memory: ~300-500 MB (Python objects have overhead: each string is a Python object with ~50 bytes overhead beyond the string content)
- Parquet serialisation buffer: ~40-60 MB

**Why not chosen:**
- 3x-5x memory amplification for no analytical benefit at this stage
- pandas dtype inference can conflict with BigQuery types (e.g., pandas reads "01234" as int 1234, BigQuery expects STRING)
- Extra dependency on pyarrow for Parquet serialisation
- Adding pandas as a loading intermediary is an anti-pattern in data engineering — pandas is for analysis, not ETL

#### Option C: `load_table_from_uri` (via GCS)

**How it works:**
1. Upload CSV to Google Cloud Storage bucket
2. Call `load_table_from_uri("gs://bucket/file.csv", table_ref)`
3. BigQuery reads directly from GCS (Google's internal network — very fast)

**When to use it:**
- Production pipelines where data already lands in GCS (e.g., from Airflow, Cloud Functions)
- Files > 4 GB (BigQuery's direct upload limit for `load_table_from_file`)
- When you need to keep source files in cloud storage for audit/replay

**Why not chosen:**
- Our files are local and total ~120 MB — well under the 4 GB limit
- Requires creating a GCS bucket, uploading files, then loading — two steps instead of one
- Adds GCS cost (negligible, but unnecessary complexity)
- For a portfolio project, `load_table_from_file` demonstrates the same skill with less setup

#### Option D: BigQuery Console UI

**Why not chosen:**
- Manual point-and-click — not reproducible
- Can't be version-controlled
- Doesn't demonstrate Python/SDK skills
- If you need to reload data, you repeat the manual work

### Decision summary

For **local files under 4 GB** in a **portfolio/analytics project**: `load_table_from_file` is optimal. It's the simplest path with the lowest memory footprint and no unnecessary dependencies.

For **production ETL pipelines**: use `load_table_from_uri` with data landing in GCS. This is what you'd describe in an interview when asked "how would you scale this?"

---

## 4. Why Explicit Schema over Autodetect?

### How BigQuery autodetect works

BigQuery samples **up to 500 rows** from the beginning of the CSV and infers types using these rules:
- All digits → INTEGER or FLOAT
- Parseable as date/time → TIMESTAMP
- Everything else → STRING

### Where autodetect fails for this dataset

| Column | Autodetect guess | Correct type | Problem |
|---|---|---|---|
| `customer_zip_code_prefix` | INTEGER | STRING | Zip codes are identifiers, not quantities. Leading zeros lost. |
| `order_purchase_timestamp` | Could be STRING | TIMESTAMP | Depends on date format in first 500 rows |
| `product_name_lenght` | INTEGER | INTEGER | Correct, but no validation that it's the right column |
| `review_comment_message` | STRING | STRING | Correct, but no mode (NULLABLE) guarantee |

### The schema-as-contract principle

An explicit schema is a **contract between the data producer and consumer**:

```
If the source CSV matches this schema → load succeeds
If the source CSV violates this schema → load fails with a clear error
```

With autodetect, a schema change in the source CSV (e.g., a new column, a renamed column, a type change) is **silently absorbed**. Your downstream queries may break days later with confusing errors.

With explicit schema, the **load job itself fails** — you catch the problem at ingestion, not at analysis time.

### Analogy to typed programming

```
autodetect  ≈  JavaScript (var x = infer_type(value))
explicit    ≈  TypeScript (x: string = value)
```

Both work. One catches errors at "compile time" (load), the other at "runtime" (query).

---

## 5. Why `WRITE_TRUNCATE` over `WRITE_APPEND` or `WRITE_EMPTY`?

### The three write dispositions

| Disposition | Behaviour | Use case |
|---|---|---|
| `WRITE_TRUNCATE` (chosen) | Deletes existing data, writes new data | Idempotent full reload |
| `WRITE_APPEND` | Adds rows to existing data | Incremental/streaming loads |
| `WRITE_EMPTY` | Fails if table already has data | First-time load with safety check |

### Why WRITE_TRUNCATE?

**Idempotency**: Running `python main.py load` twice produces the same result. No duplicate rows, no manual cleanup.

Mathematically, for a loading function `L(csv) → table`:
```
L(csv) = L(L(csv))    — idempotent: applying twice equals applying once
```

With `WRITE_APPEND`:
```
L₂(csv) = L₁(csv) ∪ L₁(csv)  — rows doubled after second run
```

For a one-time analytical load (not a streaming pipeline), idempotency is essential. You will re-run this script during development, after schema changes, and during debugging. `WRITE_TRUNCATE` ensures correctness every time.

---

## 6. Why `allow_quoted_newlines=True`?

The `olist_order_reviews_dataset.csv` contains customer review comments in Portuguese. These comments include:
- Line breaks within quoted fields (e.g., multi-paragraph reviews)
- Commas within quoted fields (e.g., "Good product, fast delivery")
- Special characters (accents: ç, ã, é, etc.)

Without `allow_quoted_newlines=True`, BigQuery's CSV parser treats a newline character as a row delimiter — even inside a quoted field. This causes:
1. A single review split across 2+ rows
2. Schema validation failure (wrong number of columns on the split rows)
3. Silent data loss if `max_bad_records` is set

Setting `allow_quoted_newlines=True` tells the parser: "A newline inside double quotes is part of the field value, not a row boundary."

**Performance impact:** Negligible. The parser switches from a simple newline scan to a state-machine that tracks quote open/close. For ~100K rows, the difference is < 1 second.

---

## 7. Authentication: Why Application Default Credentials (ADC)?

### Alternatives

| Method | How it works | Risk |
|---|---|---|
| **ADC** (chosen) | `gcloud auth application-default login` sets up credentials in OS keychain | No key files. Credentials tied to your Google account. |
| Service account key (JSON) | Download a JSON key file, set `GOOGLE_APPLICATION_CREDENTIALS` env var | Key file can be accidentally committed to Git. Must be rotated. |
| Embedded credentials | Hardcode project ID / API key in code | Security anti-pattern. Immediate credential leak on push. |

### ADC flow

```
gcloud auth application-default login
    → Opens browser → Google OAuth → Stores token in OS credential store
    → bigquery.Client() automatically finds and uses this token
```

**No key files in the repo. No environment variables to set. No secrets to leak.**

The same Python code works unchanged when deployed to Google Cloud (Cloud Functions, Cloud Run, GKE) because those environments provide ADC automatically via metadata server.

---

## 8. Data Model: Star Schema Relationships

The 9 tables form a **star schema** with `orders` as the central fact table:

```
                    ┌──────────────┐
                    │  customers   │
                    │  (dim)       │
                    └──────┬───────┘
                           │ customer_id
                           │
┌────────────┐    ┌────────┴────────┐    ┌────────────────┐
│  products  │    │     orders      │    │    sellers      │
│  (dim)     │    │   (fact)        │    │    (dim)        │
└─────┬──────┘    └──┬───┬────┬─────┘    └────────┬───────┘
      │              │   │    │                    │
      │ product_id   │   │    │ order_id           │ seller_id
      │              │   │    │                    │
      └──────┐  ┌────┘   │    └────┐    ┌──────────┘
             │  │        │         │    │
        ┌────┴──┴──┐  ┌──┴───┐  ┌──┴────┴──┐
        │order_items│  │order_│  │  order_   │
        │  (fact)   │  │reviews│  │ payments  │
        └───────────┘  │(fact)│  │  (fact)   │
                       └──────┘  └───────────┘

┌──────────────┐    ┌─────────────────────┐
│ geolocation  │    │ category_translation │
│ (dim, loose) │    │ (dim, lookup)        │
└──────────────┘    └─────────────────────┘
```

- **Fact tables** (events): orders, order_items, order_payments, order_reviews
- **Dimension tables** (entities): customers, products, sellers, geolocation, category_translation
- **Join path**: Most analytical queries start from `orders`, join to `order_items` (for product/seller/price), then to dimension tables

Geolocation is a "loose" dimension — it joins on `zip_code_prefix` (not a strict FK) and has many-to-many cardinality (multiple lat/lng per zip code). This is handled in Module 2.

---

## 9. Validation Strategy

### Why validate at all?

Data loading is a **lossy process**. Rows can be silently dropped due to:
- Encoding errors (invalid UTF-8 bytes)
- Schema mismatches (wrong number of columns)
- Quoted newlines parsed incorrectly
- BigQuery's `max_bad_records` silently skipping malformed rows (default=0, but worth verifying)

### Three-layer validation

1. **Row count check**: Compare `COUNT(*)` in BigQuery against known CSV row counts. If they differ, rows were dropped.

2. **Schema check**: Compare BigQuery table schema against our explicit schema definition. Catches type drift or column order issues.

3. **Foreign key check**: Verify referential integrity between tables (e.g., every `order_items.order_id` exists in `orders.order_id`). Orphan rows indicate either a data quality issue in the source or a loading problem.

### Expected findings

The geolocation table is known to have **duplicate zip code entries** (multiple coordinate readings per zip code). This is not a loading error — it's a property of the source data. Module 2 addresses this.

---

## 10. What This Module Demonstrates to an Interviewer

| Skill | Evidence |
|---|---|
| Cloud data warehousing | BigQuery dataset/table creation via Python SDK |
| ETL pipeline design | Reproducible, idempotent load with explicit schema |
| Data engineering best practices | Schema-as-contract, WRITE_TRUNCATE, ADC auth |
| Data validation | Row counts, schema checks, FK integrity |
| Python engineering | Modular code, logging, CLI interface, type hints |
| Cost awareness | Free tier calculation, method chosen for efficiency |
