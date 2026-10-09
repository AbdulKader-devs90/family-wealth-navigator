# Family Wealth Navigator

A Streamlit personal net worth tracker for family assets and liabilities held across countries and currencies.

## Run & Operate

- Run the **Family Wealth Navigator** workflow to start the Streamlit app on port 5000.
- Python dependencies are managed in `pyproject.toml` and `uv.lock`.
- Run regression checks with `python -m unittest discover -s tests -v`.
  The suite uses Streamlit AppTest for shared navigation/settings and independent
  data assertions for currency conversion, debt ratios, and Plotly totals.

## Stack

- Python 3.13
- Streamlit, pandas, and Plotly

## Where things live

- `app.py` — Home, multipage router, and shared sidebar controls
- `overview_charts.py` — portfolio totals, number formatting, and Plotly chart builders
- `data_loader.py` — CSV validation, date parsing, and currency conversion
- `data/holdings.csv` — fictional demo holdings
- `data/fx_rates.csv` — fixed demo rates expressed in AED
- `pages/1_Overview.py` — filtered KPIs and portfolio charts
- `pages/2_Holdings.py` — searchable holdings table and category filter

## Architecture decisions

- Convert source values to AED, then from AED to the selected base currency.
- Liability balances remain positive in the table; `signed_value_base` is negative for net worth calculations.

## Product

Home introduces the app. Overview shows filtered net worth, assets, liabilities, debt-to-asset ratio, and portfolio charts. Holdings retains search and category filtering. Base currency, holdings/FX uploads, country, and asset-type controls are shared across pages.

## User preferences

- Keep the app modular, with UI in `app.py`, data loading in `data_loader.py`, and future pages in `pages/`.

## Gotchas

- FX rates default to fixed fictional demo values, not live exchange rates.
- Users can optionally upload FX CSVs with `currency`, `rate_to_aed`, and `as_of`.
  Rates must be finite positive AED-per-unit values with nonblank valid dates
  and unique three-letter currency codes; AED must equal 1. Every holdings currency and the selected
  base currency need a rate; custom files never fall back to demo rows.
- The shared sidebar shows the active rate source and each currency's rate date.
  Clearing the FX upload restores the demo rate file.

## Pointers

- See `data_loader.py` for the exact required CSV columns.
