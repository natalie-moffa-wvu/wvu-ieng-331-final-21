Design Rationale

Parameter Flow 
When a user runs:
uv run wvu-ieng-331-final-21 --seller-state SP --start-date 2026-01-01
pipeline.main() calls _parse_args(), which uses argparse.ArgumentParser to parse --seller-state into args.seller_state = "SP" and --start-date into args.start_date = "2026-01-01".
_validate_date(args.start_date, "start-date") checks the string parses as YYYY-MM-DD and raises ValueError (caught immediately) if not.
pipeline.main() builds a kwargs dict: {"db_path": ..., "start_date": "2026-01-01", "end_date": "", "seller_state": "SP"}.
This dict is passed with **kwargs to each query function, e.g. queries.get_seller_scorecard(**kwargs).
Inside get_seller_scorecard, _load_sql("seller_scorecard.sql") reads the file and conn.execute(sql, ["2026-01-01", "", "SP"]) passes the three values as positional parameters $1, $2, $3 in the SQL.
DuckDB substitutes them at the engine level, so the WHERE clause becomes order_purchase_timestamp >= '2026-01-01'::TIMESTAMP AND seller_state = 'SP'.
The same kwargs dict flows identically through get_abc_classification, get_cohort_retention, get_delivery_analysis, and get_monthly_revenue. No function has to know what the other functions are doing with the parameters.

SQL Parameterization
What the raw SQL looks like
In sql/seller_scorecard.sql, the filter block reads:
WHERE order_status = 'delivered'
  AND ($1 = '' OR order_purchase_timestamp >= $1::TIMESTAMP)
  AND ($2 = '' OR order_purchase_timestamp <= $2::TIMESTAMP)
$1 and $2 are DuckDB positional placeholders. When the value is an empty string '', the OR short-circuits the filter so no date restriction is applied. This means running without --start-date and running with --start-date '' are identical — the full dataset is returned.
How queries.py reads the file and passes values
sql = _load_sql("seller_scorecard.sql")          # pathlib read_text
conn = _connect(db_path)
result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
_load_sql uses Path(__file__).parent.parent.parent / "sql" / "seller_scorecard.sql" so the path resolves correctly regardless of the working directory when the pipeline is invoked.
Why parameterized queries instead of f-strings
An f-string like f"WHERE seller_state = '{seller_state}'" allows SQL injection — a value like SP' OR '1'='1 would change the query logic entirely. Parameterized queries send the value as data, never as SQL text, so the engine never interprets it as code. This also means DuckDB can cache the query plan across different parameter values.
Why SQL lives in .sql files rather than inline Python strings
Inline SQL inside Python strings loses syntax highlighting, is harder to test in isolation (you can't paste it into a DuckDB CLI session directly), and mixes two languages in one file. Separate .sql files can be opened and run standalone, diffed cleanly in git, and handed to a SQL analyst without requiring them to read Python.

Validation Logic
Table presence (_check_tables)
Queries information_schema.tables and computes the set difference against EXPECTED_TABLES. If any of the nine Olist tables are missing the downstream queries will fail with a confusing DuckDB error rather than a clear message. This check surfaces the problem immediately. It logs a WARNING rather than halting so that a partial database (e.g. a test fixture) still produces whatever output it can.
Key column non-null (_check_key_columns)
Runs SELECT COUNT(col) FROM table — COUNT excludes NULLs, so a result of 0 means the column is entirely NULL. Join keys like order_id being entirely NULL would silently produce empty DataFrames from every query, which looks like "no data" rather than "broken database". Threshold is 1 non-NULL value (not a percentage) because even a partially loaded database should pass.
Minimum row counts (_check_row_counts)
Threshold is 1,000 rows, chosen to be low enough that the holdout extended dataset always passes (it has more data, not less) while still catching a clearly truncated or corrupted file. A threshold of, say, 90,000 would fail the holdout test if the extended file has a slightly different row count.
Date range sanity (_check_date_range)
Checks that MIN(order_purchase_timestamp) is not NULL and not in the future. A future minimum date most likely indicates a date-shifted dataset where the shifting went wrong (all dates pushed to 2099, for example). This would not prevent queries from running, but it would produce charts with incomprehensible axes. Logging a warning lets the grader know to check the dataset.

Error Handling
FileNotFoundError in _connect (queries.py)
if not db_path.exists():
    raise FileNotFoundError(f"Database not found: {db_path}")
    FileNotFoundError is caught in pipeline.main():
except FileNotFoundError as exc:
    logger.error(str(exc))
    sys.exit(1)
We raise FileNotFoundError specifically (not a bare Exception) because it carries a clear semantic meaning — the file is missing, not malformed — and lets the caller decide whether to exit or try a fallback path. With bare except:, a KeyboardInterrupt or SystemExit would also be caught, preventing the user from stopping the pipeline with Ctrl-C.
duckdb.Error in query functions (queries.py)
try:
    result = conn.execute(sql, [start_date, end_date, seller_state]).pl()
finally:
    conn.close()
The finally block ensures the connection is always closed even if the query raises. In pipeline.main(), each query call is wrapped in a broad except Exception that logs the error and substitutes an empty DataFrame, so one failing query does not abort the entire pipeline. We use duckdb.Error in documentation and validation rather than catching it broadly in the query functions themselves, because the query functions are data access primitives — they should surface errors, not swallow them.

Scaling & Adaptation
If the Olist dataset grew to 10 million orders
The first bottleneck would be the cohort retention query — it performs a self-join on all purchases per customer to find the second purchase timestamp, which is O(n²) in the worst case. At 10 million orders, this would likely time out or exhaust memory.
The fix would be to pre-aggregate at the DuckDB level using a lateral join or by materialising a customer_purchases intermediate table with CREATE TABLE AS SELECT, then joining against it. Polars lazy evaluation (scan_parquet on exported chunks) could also replace the in-memory .pl() call for the largest result sets.
The geolocation table (1 million rows) is already the largest table and is only used indirectly through the customers join — it would not need to change.
Adding a third output format (JSON API response)
The output logic lives entirely in pipeline.main(), specifically in the block after the queries complete. Adding JSON output would mean:
Adding a --output-json flag to _parse_args().
In pipeline.main(), after the existing summary.csv write, adding:
if args.output_json:
    import json
    payload = {
        "seller_scorecard": seller_df.to_dicts(),
        "abc_summary": abc_df.group_by("abc_class").agg(...).to_dicts(),
    }
    (output_dir / "api_response.json").write_text(json.dumps(payload, default=str))
No changes to queries.py, validation.py, or report.py would be needed — the query functions return plain Polars DataFrames that serialize to any format. The separation between data access (queries.py) and presentation (report.py, pipeline.py output block) is what makes this straightforward.
