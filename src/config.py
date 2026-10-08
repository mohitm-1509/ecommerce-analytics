"""
Central configuration for the Olist E-Commerce Analytics project.
Update GCP_PROJECT_ID with your own Google Cloud project ID before running.
"""
from pathlib import Path

# --- GCP Configuration ---
GCP_PROJECT_ID = "olist-analytics-507810"
BQ_DATASET_ID = "olist_ecommerce"
BQ_LOCATION = "US"

# --- Local Paths ---
PROJECT_ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = PROJECT_ROOT / "data"

# --- Kaggle ---
KAGGLE_DATASET_HANDLE = "olistbr/brazilian-ecommerce"

# --- Table Mapping: CSV filename (without extension) → BigQuery table name ---
TABLE_MAP = {
    "olist_customers_dataset": "customers",
    "olist_orders_dataset": "orders",
    "olist_order_items_dataset": "order_items",
    "olist_order_payments_dataset": "order_payments",
    "olist_order_reviews_dataset": "order_reviews",
    "olist_products_dataset": "products",
    "olist_sellers_dataset": "sellers",
    "olist_geolocation_dataset": "geolocation",
    "product_category_name_translation": "category_translation",
}
