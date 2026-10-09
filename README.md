# Family Wealth Navigator

## Problem statement

A family's assets and debts may be spread across countries, currencies, banks,
and physical documents. Family Wealth Navigator brings them into one CSV-based
view and helps the family find what they need if the owner is unreachable.
There is no database.

## Features

- **Home:** A short introduction and guide to every page.
- **Overview:** Filtered net worth, asset and liability totals, debt-to-asset ratio, and allocation charts.
- **Holdings:** A searchable, filterable table of every asset and liability.
- **Performance:** Asset gains, annualised growth, and comparisons with a chosen benchmark.
- **Liabilities:** Outstanding balances, repayment progress, interest rates, and high-interest warnings.
- **Readiness Check:** A readiness score, missing information, secret warnings, and suggested fixes.
- **Family Wealth Map:** An encrypted PDF guide, email sharing, check-in reminders, travel pauses, and a safe demo.

## How to run

Use Python 3.12 or newer. From the project directory:

```bash
pip install -r requirements-local.txt && streamlit run app.py
```

Run locally: pip install -r requirements-local.txt && streamlit run app.py

On Replit, dependencies are declared in `pyproject.toml` and locked in `uv.lock`;
`requirements-local.txt` is for local installation only. Start the
**Family Wealth Navigator** workflow. `.streamlit/config.toml` configures the server and `.replit` maps
internal port 5000 to external port 80. No Node.js service is needed by the app.

The bundled CSV files are used by default. The sidebar can replace holdings and
exchange rates with uploaded CSVs and select AED, INR, or USD as the base
currency. Country and asset-type filters are shared across the portfolio pages;
the Family Wealth Map uses all loaded holdings.

`PUBLIC_DEMO` defaults to `true`, including when deployed. Public demo visitors
always use practice mode, even if SMTP is configured. Settings, history, uploads,
and generated PDFs stay in each browser session's memory, not in shared files.
Example names and emails are pre-filled; do not enter real financial information.

Only for a private instance, explicitly set `PUBLIC_DEMO=false` to restore local
check-in storage and enable real email sending. Configure `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, and
`SMTP_PASSWORD` in Replit Secrets. Missing settings enable practice mode:
emails are previewed rather than sent. The demo never sends real emails or
changes real check-in delivery history. Generate the encrypted PDF before
sending a map.

## CSV format

Use UTF-8 CSV files with headers. Dates should use `YYYY-MM-DD`, numeric values
should not include currency symbols or thousands separators, and empty cells
should be left blank. Required column names must be present even when their
values are blank.

### `data/holdings.csv`

One row per asset or liability. Required headers:

```csv
item_id,category,asset_type,item_name,country,city,currency,quantity,unit,purchase_date,purchase_value,current_value,last_valued_on,interest_rate_pct,held_with,account_ref,ownership,nominee,nominee_relation,contact_person,contact_email,documents_location,access_instructions,notes
```

- `category`: `Asset` or `Liability`.
- `asset_type`: examples include Land, Real Estate, Gold, Cash, Stocks, Bonds, Crypto, Mortgage, Loan, and Credit Card.
- `currency`: a three-letter code with a matching exchange rate.
- `purchase_value` and `current_value`: values in the row's original currency.
- For liabilities, `purchase_value` is the original loan amount and `current_value` is the outstanding balance, stored as a positive number.
- `purchase_date` and `last_valued_on`: used to calculate holding periods and annualised returns.
- `interest_rate_pct`: a percentage such as `6` for 6%, or blank when unknown.
- Contact, nominee, document-location, and access fields support the readiness checks and family guide.
- Empty notes are displayed as blank.

The app adds purchase and current values in the selected base currency and a
signed current value: positive for assets, negative for liabilities.

### `data/fx_rates.csv`

Required headers and example:

```csv
currency,rate_to_aed,as_of
AED,1,2026-09-30
INR,0.0418,2026-09-30
USD,3.6725,2026-09-30
```

`rate_to_aed` is AED per one unit of that currency. Rates must be positive and
finite, each currency may appear only once, and AED must equal 1 when present.
Include every holdings currency and the selected base currency. Conversion is:

```text
base value = original value × source rate_to_aed ÷ base rate_to_aed
```

Empty uploads and missing exchange rates show a message explaining how to
continue. Clearing the filters shows all holdings.

## Security notes

- **Demo data only:** the bundled family and exchange rates are fictional. This is a demo app, not production storage for real financial information or credentials.
- **PDF encrypted in memory:** the PDF uses AES-256 encryption and remains in the current session's memory until downloaded; it is not saved to server disk. A restart or lost session requires recreating it.
- **Password never emailed:** PDF passwords are not written to the check-in file or email body. Share the password in person, separately from the PDF.
- **No secrets in CSVs:** describe where passwords or recovery details can be found, not the passwords, PINs, or seed phrases themselves.
- **Check-in state:** public demo settings, history, and delivery records stay in each browser session's memory. Only private mode (`PUBLIC_DEMO=false`) uses `state/checkin_state.json`; the `state/` folder is excluded from version control. No uploaded data, PDF, or password is written to disk.
- **Production next step:** a daily scheduled job would run the check-in decisions automatically. No scheduler is installed here; the page's check buttons run them manually. Automatic sharing must not skip either reminder and must wait at least seven days after the final reminder.
