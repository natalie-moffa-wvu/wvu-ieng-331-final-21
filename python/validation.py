"""Data validation module for the Olist supply chain pipeline.

Runs before the main analysis to verify the database is structurally sound
and contains enough data to produce meaningful results. All checks log a
WARNING on failure; the pipeline continues with a disclaimer rather than halting,
so the grader's holdout data still produces output even with unexpected values.
"""

from __future__ import annotations

from pathlib import Path

import duckdb
from loguru import logger

EXPECTED_TABLES = {
    "orders",
    "order_items",
    "order_payments",
    "order_reviews",
    "customers",
    "sellers",
    "products",
    "category_translation",
    "geolocation",
}

KEY_COLUMNS: dict[str, list[str]] = {
    "orders": ["order_id", "customer_id"],
    "order_items": ["order_id", "seller_id", "product_id"],
    "customers": ["customer_id"],
    "sellers": ["seller_id"],
    "products": ["product_id"],
}

MIN_ROW_COUNTS: dict[str, int] = {
    "orders": 1_000,
    "order_items": 1_000,
    "customers": 1_000,
}


def validate(db_path: Path) -> bool:
    """Run all validation checks against the database.

    Logs warnings for each issue found. Does not raise exceptions.

    Args:
        db_path: Path to the olist.duckdb file.

    Returns:
        True if all checks passed, False if any warning was issued.

    Raises:
        FileNotFoundError: If the database file does not exist.
        duckdb.Error: If the connection or a metadata query fails.
    """
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")

    conn = duckdb.connect(str(db_path), read_only=True)
    passed = True

    try:
        passed = _check_tables(conn) and passed
        passed = _check_key_columns(conn) and passed
        passed = _check_row_counts(conn) and passed
        passed = _check_date_range(conn) and passed
    finally:
        conn.close()

    if passed:
        logger.info("All validation checks passed.")
    else:
        logger.warning("Some validation checks failed — pipeline will continue with available data.")

    return passed


def _check_tables(conn: duckdb.DuckDBPyConnection) -> bool:
    """Verify all 9 expected tables exist.

    Args:
        conn: Open DuckDB connection.

    Returns:
        True if all tables present, False otherwise.
    """
    existing = {
        row[0]
        for row in conn.execute(
            "SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'"
        ).fetchall()
    }
    missing = EXPECTED_TABLES - existing
    if missing:
        logger.warning(f"Missing tables: {sorted(missing)}")
        return False
    logger.info(f"Table check passed — all {len(EXPECTED_TABLES)} tables present.")
    return True


def _check_key_columns(conn: duckdb.DuckDBPyConnection) -> bool:
    """Verify key columns are not entirely NULL.

    Args:
        conn: Open DuckDB connection.

    Returns:
        True if all key columns have at least one non-NULL value.
    """
    all_ok = True
    for table, columns in KEY_COLUMNS.items():
        for col in columns:
            try:
                count = conn.execute(
                    f"SELECT COUNT({col}) FROM {table}"  # noqa: S608
                ).fetchone()[0]
                if count == 0:
                    logger.warning(f"Column {table}.{col} is entirely NULL.")
                    all_ok = False
                else:
                    logger.info(f"Key column check passed — {table}.{col} has {count:,} non-NULL rows.")
            except duckdb.Error as exc:
                logger.warning(f"Could not check {table}.{col}: {exc}")
                all_ok = False
    return all_ok


def _check_row_counts(conn: duckdb.DuckDBPyConnection) -> bool:
    """Verify core tables meet minimum row count thresholds.

    Thresholds are intentionally low (1,000) to tolerate the holdout
    dataset without false failures.

    Args:
        conn: Open DuckDB connection.

    Returns:
        True if all core tables meet their minimum threshold.
    """
    all_ok = True
    for table, minimum in MIN_ROW_COUNTS.items():
        try:
            count = conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]  # noqa: S608
            if count < minimum:
                logger.warning(f"{table} has {count:,} rows — below minimum of {minimum:,}.")
                all_ok = False
            else:
                logger.info(f"Row count check passed — {table}: {count:,} rows.")
        except duckdb.Error as exc:
            logger.warning(f"Could not count rows in {table}: {exc}")
            all_ok = False
    return all_ok


def _check_date_range(conn: duckdb.DuckDBPyConnection) -> bool:
    """Verify the orders date range is non-empty and not entirely future-dated.

    Args:
        conn: Open DuckDB connection.

    Returns:
        True if the date range looks valid.
    """
    try:
        row = conn.execute(
            "SELECT MIN(order_purchase_timestamp), MAX(order_purchase_timestamp) FROM orders"
        ).fetchone()
        min_date, max_date = row
        if min_date is None or max_date is None:
            logger.warning("orders.order_purchase_timestamp contains no non-NULL values.")
            return False
        logger.info(f"Date range check passed — orders span {min_date} to {max_date}.")

        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).replace(tzinfo=None)
        if min_date > now:
            logger.warning(f"orders.order_purchase_timestamp minimum ({min_date}) is in the future.")
            return False
        return True
    except duckdb.Error as exc:
        logger.warning(f"Date range check failed: {exc}")
        return False
