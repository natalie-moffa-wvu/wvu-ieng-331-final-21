"""Pipeline orchestration entry point for the Olist supply chain data product.

Run with:
    uv run wvu-ieng-331-final-21
    uv run wvu-ieng-331-final-21 --start-date 2026-01-01 --seller-state SP
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import altair as alt
import polars as pl
from loguru import logger

from wvu_ieng_331_final_21 import queries, report, validation

_DB_DEFAULT = Path(__file__).parent.parent.parent.parent / "data" / "olist.duckdb"
_OUTPUT_DIR = Path(__file__).parent.parent.parent.parent / "output"


def _parse_args() -> argparse.Namespace:
    """Parse command-line arguments.

    Returns:
        Namespace with start_date, end_date, seller_state, and db_path.
    """
    p = argparse.ArgumentParser(
        prog="wvu-ieng-331-final-21",
        description="Olist supply chain data product — Team 21",
    )
    p.add_argument(
        "--start-date",
        default="",
        help="Filter orders on or after this date (YYYY-MM-DD). Default: no filter.",
    )
    p.add_argument(
        "--end-date",
        default="",
        help="Filter orders on or before this date (YYYY-MM-DD). Default: no filter.",
    )
    p.add_argument(
        "--seller-state",
        default="",
        help="Filter by two-letter Brazilian seller state code (e.g. SP). Default: all states.",
    )
    p.add_argument(
        "--db-path",
        default=str(_DB_DEFAULT),
        help="Path to the olist.duckdb file. Default: data/olist.duckdb.",
    )
    return p.parse_args()


def _validate_date(value: str, name: str) -> None:
    """Raise ValueError if value is non-empty and not a valid ISO date.

    Args:
        value: The date string to validate, or '' to skip.
        name: Parameter name for the error message.

    Raises:
        ValueError: If value is non-empty and not parseable as YYYY-MM-DD.
    """
    if not value:
        return
    from datetime import datetime
    try:
        datetime.strptime(value, "%Y-%m-%d")
    except ValueError:
        raise ValueError(f"--{name} must be in YYYY-MM-DD format, got: {value!r}")


def _build_altair_chart(revenue_df: pl.DataFrame, output_dir: Path) -> None:
    """Generate an Altair exploratory visualisation and save as self-contained HTML.

    Args:
        revenue_df: Monthly revenue Polars DataFrame.
        output_dir: Directory to write chart.html into.

    Raises:
        OSError: If the file cannot be written.
    """
    if revenue_df.is_empty():
        logger.warning("Revenue data is empty — skipping Altair chart.")
        return

    pandas_df = revenue_df.with_columns(
        pl.col("month").dt.strftime("%Y-%m").alias("month_str")
    ).to_pandas()

    line = (
        alt.Chart(pandas_df)
        .mark_line(point=True, color="#2E75B6", strokeWidth=2.5)
        .encode(
            x=alt.X("month_str:O", title="Month", axis=alt.Axis(labelAngle=-45)),
            y=alt.Y("revenue:Q", title="Revenue (R$)", axis=alt.Axis(format=",.0f")),
            tooltip=[
                alt.Tooltip("month_str:O", title="Month"),
                alt.Tooltip("revenue:Q", title="Revenue (R$)", format=",.2f"),
                alt.Tooltip("order_count:Q", title="Orders"),
                alt.Tooltip("mom_growth_pct:Q", title="MoM Growth %", format=".1f"),
            ],
        )
    )

    chart = (
        line.properties(
            title="Monthly Revenue — Olist Platform",
            width=700,
            height=350,
        )
        .configure_title(fontSize=16, font="Arial", anchor="start", color="#1F3864")
        .configure_axis(labelFont="Arial", titleFont="Arial")
    )

    try:
        path = output_dir / "chart.html"
        chart.save(str(path))
        logger.info(f"Altair chart saved to {path}")
    except OSError as exc:
        logger.error(f"Failed to write chart.html: {exc}")
        raise


def main() -> None:
    """Run the full pipeline: validate → query → process → output."""
    args = _parse_args()

    try:
        _validate_date(args.start_date, "start-date")
        _validate_date(args.end_date, "end-date")
    except ValueError as exc:
        logger.error(str(exc))
        sys.exit(1)

    db_path = Path(args.db_path)

    # ── Validate ──────────────────────────────────────────────────────────────
    logger.info("Running validation...")
    try:
        validation.validate(db_path)
    except FileNotFoundError as exc:
        logger.error(str(exc))
        logger.error("Place olist.duckdb in the data/ directory and retry.")
        sys.exit(1)

    # ── Query ─────────────────────────────────────────────────────────────────
    kwargs = dict(
        db_path=db_path,
        start_date=args.start_date,
        end_date=args.end_date,
        seller_state=args.seller_state,
    )

    logger.info("Running seller scorecard query...")
    try:
        seller_df = queries.get_seller_scorecard(**kwargs)
    except Exception as exc:
        logger.error(f"Seller scorecard query failed: {exc}")
        seller_df = pl.DataFrame()

    logger.info("Running ABC classification query...")
    try:
        abc_df = queries.get_abc_classification(**kwargs)
    except Exception as exc:
        logger.error(f"ABC classification query failed: {exc}")
        abc_df = pl.DataFrame()

    logger.info("Running cohort retention query...")
    try:
        cohort_df = queries.get_cohort_retention(**kwargs)
    except Exception as exc:
        logger.error(f"Cohort retention query failed: {exc}")
        cohort_df = pl.DataFrame()

    logger.info("Running delivery analysis query...")
    try:
        delivery_df = queries.get_delivery_analysis(**kwargs)
    except Exception as exc:
        logger.error(f"Delivery analysis query failed: {exc}")
        delivery_df = pl.DataFrame()

    logger.info("Running monthly revenue query...")
    try:
        revenue_df = queries.get_monthly_revenue(**kwargs)
    except Exception as exc:
        logger.error(f"Monthly revenue query failed: {exc}")
        revenue_df = pl.DataFrame()

    # ── Output directory ──────────────────────────────────────────────────────
    _OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    # ── M2 outputs ────────────────────────────────────────────────────────────
    logger.info("Writing summary.csv...")
    try:
        if not seller_df.is_empty():
            seller_df.head(50).write_csv(str(_OUTPUT_DIR / "summary.csv"))
    except OSError as exc:
        logger.error(f"Failed to write summary.csv: {exc}")

    logger.info("Writing detail.parquet...")
    try:
        if not abc_df.is_empty():
            abc_df.write_parquet(str(_OUTPUT_DIR / "detail.parquet"))
    except OSError as exc:
        logger.error(f"Failed to write detail.parquet: {exc}")

    _build_altair_chart(revenue_df, _OUTPUT_DIR)

    # ── Final deliverable: Excel report ───────────────────────────────────────
    params = {
        "start_date": args.start_date,
        "end_date": args.end_date,
        "seller_state": args.seller_state,
    }
    try:
        report.build_report(
            output_path=_OUTPUT_DIR / "report.xlsx",
            seller_df=seller_df,
            abc_df=abc_df,
            cohort_df=cohort_df,
            delivery_df=delivery_df,
            revenue_df=revenue_df,
            params=params,
        )
    except OSError as exc:
        logger.error(f"Report generation failed: {exc}")
        sys.exit(1)

    logger.info("Pipeline complete. Outputs in output/")


if __name__ == "__main__":
    main()
    
