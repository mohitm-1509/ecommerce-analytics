"""
Explicit BigQuery schemas for all 9 Olist tables.

Why explicit schemas instead of autodetect:
1. Autodetect samples ~100 rows and guesses types — it can misclassify
   zip codes as INTEGER (losing semantic meaning), or timestamps as STRING.
2. Explicit schemas act as a contract: if the source CSV changes shape,
   the load job fails loudly instead of silently ingesting garbage.
3. Self-documenting: anyone reading this file knows every column and its type.

Type decisions documented inline where non-obvious.
"""
from google.cloud.bigquery import SchemaField

SCHEMAS = {
    "customers": [
        SchemaField("customer_id", "STRING", mode="REQUIRED"),
        SchemaField("customer_unique_id", "STRING", mode="REQUIRED"),
        # ZIP as STRING: zip codes are identifiers, not quantities.
        # You never do arithmetic on them. STRING preserves leading zeros
        # if any future dataset includes them.
        SchemaField("customer_zip_code_prefix", "STRING", mode="REQUIRED"),
        SchemaField("customer_city", "STRING"),
        SchemaField("customer_state", "STRING"),
    ],
    "orders": [
        SchemaField("order_id", "STRING", mode="REQUIRED"),
        SchemaField("customer_id", "STRING", mode="REQUIRED"),
        SchemaField("order_status", "STRING"),
        # TIMESTAMP not DATE: source includes time component (HH:MM:SS).
        # Keeping full precision lets us analyse intra-day patterns later.
        SchemaField("order_purchase_timestamp", "TIMESTAMP"),
        SchemaField("order_approved_at", "TIMESTAMP"),
        SchemaField("order_delivered_carrier_date", "TIMESTAMP"),
        SchemaField("order_delivered_customer_date", "TIMESTAMP"),
        SchemaField("order_estimated_delivery_date", "TIMESTAMP"),
    ],
    "order_items": [
        SchemaField("order_id", "STRING", mode="REQUIRED"),
        # Sequence number within an order (1, 2, 3…). INTEGER is correct.
        SchemaField("order_item_id", "INTEGER", mode="REQUIRED"),
        SchemaField("product_id", "STRING", mode="REQUIRED"),
        SchemaField("seller_id", "STRING", mode="REQUIRED"),
        SchemaField("shipping_limit_date", "TIMESTAMP"),
        # FLOAT64 for monetary values in an analytics project is acceptable.
        # For payment processing systems, use NUMERIC/BIGNUMERIC instead.
        SchemaField("price", "FLOAT64"),
        SchemaField("freight_value", "FLOAT64"),
    ],
    "order_payments": [
        SchemaField("order_id", "STRING", mode="REQUIRED"),
        SchemaField("payment_sequential", "INTEGER"),
        SchemaField("payment_type", "STRING"),
        SchemaField("payment_installments", "INTEGER"),
        SchemaField("payment_value", "FLOAT64"),
    ],
    "order_reviews": [
        SchemaField("review_id", "STRING", mode="REQUIRED"),
        SchemaField("order_id", "STRING", mode="REQUIRED"),
        SchemaField("review_score", "INTEGER"),
        SchemaField("review_comment_title", "STRING"),
        SchemaField("review_comment_message", "STRING"),
        SchemaField("review_creation_date", "TIMESTAMP"),
        SchemaField("review_answer_timestamp", "TIMESTAMP"),
    ],
    "products": [
        SchemaField("product_id", "STRING", mode="REQUIRED"),
        SchemaField("product_category_name", "STRING"),
        # Typo ("lenght") is in the original CSV headers. We preserve it
        # here so the schema matches the CSV. A VIEW can alias it later.
        SchemaField("product_name_lenght", "INTEGER"),
        SchemaField("product_description_lenght", "INTEGER"),
        SchemaField("product_photos_qty", "INTEGER"),
        SchemaField("product_weight_g", "INTEGER"),
        SchemaField("product_length_cm", "INTEGER"),
        SchemaField("product_height_cm", "INTEGER"),
        SchemaField("product_width_cm", "INTEGER"),
    ],
    "sellers": [
        SchemaField("seller_id", "STRING", mode="REQUIRED"),
        SchemaField("seller_zip_code_prefix", "STRING", mode="REQUIRED"),
        SchemaField("seller_city", "STRING"),
        SchemaField("seller_state", "STRING"),
    ],
    "geolocation": [
        SchemaField("geolocation_zip_code_prefix", "STRING", mode="REQUIRED"),
        SchemaField("geolocation_lat", "FLOAT64"),
        SchemaField("geolocation_lng", "FLOAT64"),
        SchemaField("geolocation_city", "STRING"),
        SchemaField("geolocation_state", "STRING"),
    ],
    "category_translation": [
        SchemaField("product_category_name", "STRING", mode="REQUIRED"),
        SchemaField("product_category_name_english", "STRING"),
    ],
}
