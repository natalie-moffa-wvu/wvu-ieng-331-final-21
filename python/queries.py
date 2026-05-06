"""Data access module for the Olist supply chain pipeline.

Reads SQL files from the sql/ directory and executes them against DuckDB,
returning Polars DataFrames. No inline SQL; all queries live in .sql files.
"""

from __future__ import annotations


_SQL_DIR = Path(__file__).parent.parent.parent / "sql"


def _load_sql(filename: str) -> str:
    """Read a SQL file from the sql/ directory.

    Args:
        filename: The .sql filename (e.g., 'seller_scorecard.sql').

    Returns:
        The SQL query string.

    Raises:
        FileNotFoundError: If the SQL file does not exist.
    """
    path = _SQL_DIR / filename
    if not path.exists():
        raise FileNotFoundError(f"SQL file not found: {path}")
    return path.read_text(encoding="utf-8")





def get_seller_scorecard(
    db_path: Path,
    start_date: str = "",
    end_date: str = "",
    seller_state: str = "",
) -> pl.DataFrame:
    """Return seller performance scorecard with composite ranking.

    Args:
        db_path: Path to the olist.duckdb file.
        start_date: ISO date string lower bound, or '' for no filter.
        end_date: ISO date string upper bound, or '' for no filter.
        seller_state: Two-letter Brazilian state code, or '' for all states.

    Returns:
        Polars DataFrame with one row per seller, sorted by composite_score desc.

    Raises:
        FileNotFoundError: If db_path or the SQL file is missing.
        duckdb.Error: If the query fails.
    """
    sql = _load_sql("seller_scorecard.sql")
    conn = _connect(db_path)
    try:
        result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
    finally:
        conn.close()
    return result


def get_abc_classification(
    db_path: Path,
    start_date: str = "",
    end_date: str = "",
    seller_state: str = "",
) -> pl.DataFrame:
    """Return product ABC classification based on Pareto revenue analysis.

    Args:
        db_path: Path to the olist.duckdb file.
        start_date: ISO date string lower bound, or '' for no filter.
        end_date: ISO date string upper bound, or '' for no filter.
        seller_state: Two-letter Brazilian state code, or '' for all states.

    Returns:
        Polars DataFrame with one row per product, including abc_class column.

    Raises:
        FileNotFoundError: If db_path or the SQL file is missing.
        duckdb.Error: If the query fails.
    """
    sql = _load_sql("abc_classification.sql")
    conn = _connect(db_path)
    try:
        result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
    finally:
        conn.close()
    return result


def get_cohort_retention(
    db_path: Path,
    start_date: str = "",
    end_date: str = "",
    seller_state: str = "",
) -> pl.DataFrame:
    """Return monthly cohort retention rates at 30, 60, and 90 days.

    Args:
        db_path: Path to the olist.duckdb file.
        start_date: ISO date string lower bound, or '' for no filter.
        end_date: ISO date string upper bound, or '' for no filter.
        seller_state: Two-letter Brazilian state code, or '' for all states.

    Returns:
        Polars DataFrame with one row per cohort month and retention columns.

    Raises:
        FileNotFoundError: If db_path or the SQL file is missing.
        duckdb.Error: If the query fails.
    """
    sql = _load_sql("cohort_retention.sql")
    conn = _connect(db_path)
    try:
        result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
    finally:
        conn.close()
    return result


def get_delivery_analysis(
    db_path: Path,
    start_date: str = "",
    end_date: str = "",
    seller_state: str = "",
) -> pl.DataFrame:
    """Return delivery performance by customer state.

    Args:
        db_path: Path to the olist.duckdb file.
        start_date: ISO date string lower bound, or '' for no filter.
        end_date: ISO date string upper bound, or '' for no filter.
        seller_state: Two-letter Brazilian state code, or '' for all states.

    Returns:
        Polars DataFrame with one row per customer state.

    Raises:
        FileNotFoundError: If db_path or the SQL file is missing.
        duckdb.Error: If the query fails.
    """
    sql = _load_sql("delivery_time_analysis.sql")
    conn = _connect(db_path)
    try:
        result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
    finally:
        conn.close()
    return result


def get_monthly_revenue(
    db_path: Path,
    start_date: str = "",
    end_date: str = "",
    seller_state: str = "",
) -> pl.DataFrame:
    """Return monthly revenue trend with MoM growth rate.

    Args:
        db_path: Path to the olist.duckdb file.
        start_date: ISO date string lower bound, or '' for no filter.
        end_date: ISO date string upper bound, or '' for no filter.
        seller_state: Two-letter Brazilian state code, or '' for all states.

    Returns:
        Polars DataFrame with one row per month.

    Raises:
        FileNotFoundError: If db_path or the SQL file is missing.
        duckdb.Error: If the query fails.
    """
    sql = _load_sql("monthly_revenue.sql")
    conn = _connect(db_path)
    try:
        result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
    finally:
        conn.close()
    return result