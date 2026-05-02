# wvu-ieng-331-final-21
Milestone Final: Supply Chain Data Product
Team 21: Natalie Moffa and Ruby Jackson
How to Run
git clone https://github.com/{username}/wvu-ieng-331-final-21.git
cd wvu-ieng-331-final-21
uv sync
# place olist.duckdb in the data/ directory
uv run wvu-ieng-331-final-21
uv run wvu-ieng-331-final-21 --start-date 2026-01-01 --seller-state SP

Parameters
Parameter	Type	Default	Description
--start-date	date (YYYY-MM-DD)	None (no filter)	Include orders on or after this date
--end-date	date (YYYY-MM-DD)	None (no filter)	Include orders on or before this date
--seller-state	string	None (all states)	Filter by two-letter Brazilian seller state (e.g. SP, RJ)
--db-path	path	data/olist.duckdb	Override the database file path

Outputs
File	Format	Description
output/summary.csv	CSV	Top 50 sellers by composite score
output/detail.parquet	Parquet	Full ABC-classified product dataset
output/chart.html	HTML (self-contained)	Interactive monthly revenue line chart (Altair)
output/report.xlsx	Excel workbook	Final deliverable — see below

Validation Checks
The pipeline runs the following checks before executing any queries.
Failures log a WARNING and the pipeline continues with available data.
Check	What it verifies	On failure
Table presence	All 9 Olist tables exist	WARNING, continue
Key column non-null	order_id, customer_id, product_id, seller_id have at least one non-NULL value	WARNING, continue
Minimum row counts	orders, order_items, customers each have ≥ 1,000 rows	WARNING, continue
Date range sanity	order_purchase_timestamp is non-empty and not entirely future-dated	WARNING, continue

Analysis Summary
Four analyses are carried forward from Milestone 1:
Seller Scorecard — Ranks all sellers on a composite 0–100 score weighted 40% revenue, 30% on-time delivery rate, and 30% average review score. Identifies which sellers drive disproportionate value and where quality gaps exist.
ABC Classification — Applies the Pareto principle to product revenue. Tier A (top 80% of revenue) typically contains ~20% of products. Tiers B and C flag which SKUs contribute marginally and may warrant rationalisation.
Cohort Retention — Assigns customers to their first-purchase month and tracks what fraction made a second purchase within 30, 60, and 90 days. Low retention rates in early cohorts indicate weak repeat-purchase dynamics.
Delivery Analysis — Compares actual vs. estimated delivery times by customer state. States with positive "avg days early" consistently beat estimates; negative values signal logistics corridors that need attention.

Final Deliverable
Format chosen: Excel workbook (output/report.xlsx)
Excel was chosen because it requires no installation beyond what a typical business analyst already has, supports embedded charts, and is trivially shareable via email or OneDrive. It is generated automatically every time the pipeline runs — no manual steps required.
Sheet contents:
Sheet What it shows
Executive Summary	Cover page with filter parameters and sheet guide
Seller Scorecard	Full ranked seller table + bar chart of top 10 composite scores
ABC Classification	Tier summary (colour-coded A/B/C) + full product detail table + bar chart 
Cohort Retention	Monthly cohort table + three-series line chart (30d / 60d / 90d retention)
Delivery Analysis	State-level delivery metrics + horizontal bar chart of avg days early
Revenue Trend	Monthly revenue table + line chart with MoM growth colouring
How to open: Double-click output/report.xlsx. No macros or add-ins required.

Limitations & Caveats
Delivery analysis requires both order_delivered_customer_date and order_estimated_delivery_date to be non-NULL; rows missing either field are excluded.
Cohort retention counts unique customers by customer_unique_id; customers who appear under multiple customer_id values are deduplicated correctly.
The --seller-state filter applies to the seller's state, not the customer's state. Delivery analysis always shows customer states regardless of the seller filter.
ABC classification revenue shares are computed within the filtered dataset, not the full catalogue. A Tier A product under a state filter may be Tier B in the unfiltered dataset.
The pipeline does not produce output if the database file is missing entirely — place olist.duckdb in data/ before running.