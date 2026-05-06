# Final Deliverable Grade

**Team 21 (Natalie Moffa, Ruby Jackson)**

## Final score (after regrade): 18/27

| Criterion | First pass | After regrade |
|-----------|-----------:|--------------:|
| Deliverable Quality | 0 | 6 |
| Visualizations | 0 | 6 |
| Pipeline Integration | 0 | 6 |
| Analytical Narrative | 2 | 4 |
| Rubric subtotal | 2 / 24 | 22 / 24 |
| 20% regrade reduction | — | -4 |
| Video walkthrough | 0 / 3 | 0 / 3 (not submitted) |
| **Total** | **2 / 27** | **18 / 27** |

---

## Regrade summary

After the first pass, the instructor manually applied the structural and dependency fixes the submission was missing and ran the pipeline against the extended database. The fixed copy produces a six-sheet Excel deliverable that matches the README spec. A 20% reduction is applied because the submission as turned in did not run, and the deliverable-generation module had not been written - both are real submission-quality issues that the regrade does not erase.

### Fixes the instructor made on the team's behalf

1. `pyproject.toml` line 17: `[build-system}` → `[build-system]` (one-character TOML syntax error).
2. Added missing dependencies: `xlsxwriter`, `pyarrow`, `pandas`. The first was needed for the Excel report; the latter two are required by DuckDB → Polars conversion and Altair's HTML chart writer.
3. Created `src/wvu_ieng_331_final_21/` package directory and moved `pipeline.py`, `queries.py`, `validation.py` into it. Added `__init__.py`.
4. Created `sql/` directory and moved the five `.sql` files into it.
5. Renamed `cohort_retnetion.sql` → `cohort_retention.sql` and `seller_scorecoard.sql` → `seller_scorecard.sql` so they match what `queries.py` loads.
6. Removed two stray placeholder files at the repo root (`wvu_ieng_331_final_ 21` and `wvu_ieng_331_final_ 21 .pipeline:main`) that looked like accidental directory-creation typos.
7. Adjusted path depths in `pipeline.py` lines 20-21 (one extra `.parent` after the source moved into `src/`).
8. Wrote `report.py` from scratch (~260 lines) implementing the six-sheet Excel workbook described in the README - the only substantive piece of new code.

After the fixes, `uv run wvu-ieng-331-final-21` runs end-to-end and produces `summary.csv`, `detail.parquet`, `chart.html`, and `report.xlsx`.

### Post-fix evaluation (per criterion)

**Deliverable Quality (6/6)** - Six-sheet Excel workbook (Executive Summary, Seller Scorecard, ABC Classification, Cohort Retention, Delivery Analysis, Revenue Trend). Native Excel charts on five of the six sheets. Color-coded A/B/C tier rows, three-color conditional formatting on MoM growth. Workbook opens without setup. Polished and professional.

**Visualizations (6/6)** - Five Excel charts: top-10 sellers by composite score (bar), revenue share by ABC tier (column), 30/60/90 cohort retention (multi-series line), avg days early by state (horizontal bar), monthly revenue trend (line). Required types covered (temporal + categorical). All have titles and axis labels.

**Pipeline Integration (6/6)** - `uv run wvu-ieng-331-final-21` runs end-to-end with defaults: validation, five queries, M2 outputs, and the Excel report. Output filenames match the spec.

**Analytical Narrative (4/6)** - The Executive Summary in the workbook lists filter parameters and a sheet guide but has no analytical prose, key findings, or recommendations. The README has thoughtful analytical framing of the four analyses, but that text did not make it into the deliverable itself, where the rubric scores it. Fits the "thin or disconnected" rubric pattern.

---

## Original first-pass grade (kept for reference)

The submission as delivered did not run. Three blocking issues prevented even `uv sync`:

1. `pyproject.toml` line 17 has a TOML syntax error (`[build-system}` should be `[build-system]`).
2. Project layout was flat: `pipeline.py`, `queries.py`, `validation.py`, and the `.sql` files were at the repository root rather than under `src/wvu_ieng_331_final_21/` and `sql/` as the spec requires (and as the code itself expects when computing paths via `Path(__file__).parent.parent.parent / "sql"`).
3. Two zero/one-byte placeholder files at the repo root with literal package-name-like names looked like accidental output from a typo while trying to create a directory.

The biggest gap was the missing `report.py` module: `pipeline.py` does `from wvu_ieng_331_final_21 import ... report ...` and calls `report.build_report(...)`, but no such file existed in the repo. The Excel deliverable described in the README was never implemented.

The original-pass scores were 0/6 on Deliverable Quality, Visualizations, and Pipeline Integration (no deliverable, no charts, pipeline did not run), and 2/6 on Analytical Narrative for the thoughtful README and DESIGN content.
