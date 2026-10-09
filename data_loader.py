"""Load family holdings and convert values through AED into a chosen base currency."""

from __future__ import annotations

from pathlib import Path
from typing import IO
import math

import pandas as pd

ROOT_DIR = Path(__file__).resolve().parent
DEFAULT_HOLDINGS_PATH = ROOT_DIR / "data" / "holdings.csv"
DEFAULT_FX_PATH = ROOT_DIR / "data" / "fx_rates.csv"

HOLDINGS_REQUIRED_COLUMNS = (
    "item_id",
    "category",
    "asset_type",
    "item_name",
    "country",
    "city",
    "currency",
    "quantity",
    "unit",
    "purchase_date",
    "purchase_value",
    "current_value",
    "last_valued_on",
    "interest_rate_pct",
    "held_with",
    "account_ref",
    "ownership",
    "nominee",
    "nominee_relation",
    "contact_person",
    "contact_email",
    "documents_location",
    "access_instructions",
    "notes",
)

FX_REQUIRED_COLUMNS = ("currency", "rate_to_aed", "as_of")
DATE_COLUMNS = ("purchase_date", "last_valued_on")
NUMERIC_COLUMNS = ("quantity", "purchase_value", "current_value", "interest_rate_pct")
SUPPORTED_BASE_CURRENCIES = ("AED", "INR", "USD")
HOLDINGS_SEARCH_COLUMNS = (
    "item_id",
    "item_name",
    "asset_type",
    "country",
    "city",
    "held_with",
    "notes",
)


class MissingColumnsError(ValueError):
    """Raised when an uploaded or demo CSV is missing required columns."""

    def __init__(self, missing_columns: list[str], source_name: str = "CSV"):
        self.missing_columns = missing_columns
        details = "\n".join(f"- {column}" for column in missing_columns)
        super().__init__(f"The {source_name} is missing required columns:\n{details}")


class CSVNotice(ValueError):
    """A recoverable empty-file or missing-rate message for the upload UI."""


def _read_csv(source: str | Path | IO[bytes] | IO[str]) -> pd.DataFrame:
    try:
        return pd.read_csv(source)
    except pd.errors.EmptyDataError as exc:
        raise CSVNotice(
            "This CSV is empty. Upload a file with column headers and at least one row, "
            "or remove the upload to use the demo data."
        ) from exc
    except UnicodeDecodeError as exc:
        raise ValueError("The CSV file must be encoded as UTF-8.") from exc
    except pd.errors.ParserError as exc:
        raise ValueError(f"Could not read the CSV file: {exc}") from exc


def _require_columns(
    frame: pd.DataFrame, required: tuple[str, ...], source_name: str = "CSV"
) -> None:
    missing = [column for column in required if column not in frame.columns]
    if missing:
        raise MissingColumnsError(missing, source_name)


def _parse_dates(frame: pd.DataFrame, columns: tuple[str, ...]) -> None:
    for column in columns:
        original = frame[column]
        parsed = pd.to_datetime(original, errors="coerce")
        invalid = original.notna() & original.astype(str).str.strip().ne("") & parsed.isna()
        if invalid.any():
            rows = (frame.index[invalid] + 2).tolist()
            raise ValueError(
                f"Invalid date value in '{column}' on CSV row(s): "
                f"{', '.join(map(str, rows))}."
            )
        frame[column] = parsed


def load_fx_rates(
    fx_source: str | Path | IO[bytes] | IO[str] = DEFAULT_FX_PATH,
) -> pd.DataFrame:
    """Load and validate the table of currency-to-AED exchange rates."""
    rates = _read_csv(fx_source)
    if rates.empty:
        raise CSVNotice(
            "Your FX CSV has no exchange rates yet. Add at least one rate, "
            "or remove the upload to use the fixed demo rates."
        )
    _require_columns(rates, FX_REQUIRED_COLUMNS, "FX CSV")

    rates["currency"] = rates["currency"].astype("string").str.strip().str.upper()
    if rates["currency"].isna().any() or rates["currency"].eq("").any():
        raise ValueError("The FX table contains a blank currency code.")
    if not rates["currency"].str.fullmatch(r"[A-Z]{3}").all():
        raise ValueError("FX currency codes must contain three letters, for example AED or USD.")

    rates["rate_to_aed"] = pd.to_numeric(rates["rate_to_aed"], errors="coerce")
    invalid_rates = (
        ~rates["rate_to_aed"].map(math.isfinite) | rates["rate_to_aed"].le(0)
    )
    if invalid_rates.any():
        row_numbers = (rates.index[invalid_rates] + 2).tolist()
        raise ValueError(
            "FX rates must be finite positive numbers. Check CSV row(s): "
            f"{', '.join(map(str, row_numbers))}."
        )
    if rates["currency"].duplicated().any():
        duplicates = sorted(rates.loc[rates["currency"].duplicated(), "currency"].unique())
        raise ValueError(f"The FX table has duplicate currency codes: {', '.join(duplicates)}.")
    if rates.loc[rates["currency"].eq("AED"), "rate_to_aed"].ne(1).any():
        raise ValueError(
            "The AED rate_to_aed must equal 1 because rates are expressed in AED per unit."
        )

    _parse_dates(rates, ("as_of",))
    if rates["as_of"].isna().any():
        rows = (rates.index[rates["as_of"].isna()] + 2).tolist()
        raise ValueError(
            "FX 'as_of' dates are required. Check CSV row(s): "
            f"{', '.join(map(str, rows))}."
        )

    return rates


def load_holdings(
    holdings_source: str | Path | IO[bytes] | IO[str] | None = None,
    base_currency: str = "AED",
    fx_source: str | Path | IO[bytes] | IO[str] = DEFAULT_FX_PATH,
) -> pd.DataFrame:
    """Load holdings and add converted and signed values in the selected currency."""
    return _load_holdings_with_rates(
        holdings_source, base_currency, load_fx_rates(fx_source)
    )


def _load_holdings_with_rates(
    holdings_source: str | Path | IO[bytes] | IO[str] | None,
    base_currency: str,
    rates: pd.DataFrame,
) -> pd.DataFrame:
    """Convert holdings using an already validated FX table."""
    base_currency = base_currency.strip().upper()
    if base_currency not in SUPPORTED_BASE_CURRENCIES:
        allowed = ", ".join(SUPPORTED_BASE_CURRENCIES)
        raise ValueError(f"Base currency must be one of: {allowed}.")

    holdings = _read_csv(holdings_source or DEFAULT_HOLDINGS_PATH)
    if holdings.empty:
        raise CSVNotice(
            "Your holdings CSV has no holdings yet. Add at least one asset or liability, "
            "or remove the upload to use the demo data."
        )
    _require_columns(holdings, HOLDINGS_REQUIRED_COLUMNS, "holdings CSV")
    holdings["notes"] = holdings["notes"].fillna("").astype("string").str.strip()

    for column in DATE_COLUMNS:
        _parse_dates(holdings, (column,))

    holdings["category"] = holdings["category"].astype("string").str.strip().str.title()
    invalid_categories = ~holdings["category"].isin(("Asset", "Liability"))
    if invalid_categories.any():
        invalid = sorted(holdings.loc[invalid_categories, "category"].dropna().unique())
        raise ValueError(
            "Category must be 'Asset' or 'Liability'. "
            f"Invalid value(s): {', '.join(map(str, invalid)) or 'blank'}."
        )

    for column in ("asset_type", "country"):
        holdings[column] = holdings[column].astype("string").str.strip()

    holdings["currency"] = holdings["currency"].astype("string").str.strip().str.upper()
    if holdings["currency"].isna().any() or holdings["currency"].eq("").any():
        raise ValueError("The holdings CSV contains a blank currency code.")

    for column in NUMERIC_COLUMNS:
        original = holdings[column]
        converted = pd.to_numeric(original, errors="coerce")
        invalid = original.notna() & original.astype(str).str.strip().ne("") & converted.isna()
        if invalid.any():
            row_numbers = (holdings.index[invalid] + 2).tolist()
            raise ValueError(
                f"'{column}' must contain numbers. Check CSV row(s): "
                f"{', '.join(map(str, row_numbers))}."
            )
        holdings[column] = converted

    rate_to_aed = rates.set_index("currency")["rate_to_aed"]
    missing_currencies = sorted(set(holdings["currency"]) - set(rate_to_aed.index))
    if missing_currencies:
        raise CSVNotice(
            "No AED exchange rate is available for: "
            f"{', '.join(missing_currencies)}. Add these currencies to your FX CSV "
            "and upload it again so we can convert your holdings."
        )
    if base_currency not in rate_to_aed.index:
        raise CSVNotice(
            f"No AED exchange rate is available for base currency {base_currency}. "
            "Add its rate to your FX CSV, or select a base currency already in the table."
        )

    # Rates are expressed as AED per 1 unit of source currency. Convert through AED.
    source_rate = holdings["currency"].map(rate_to_aed)
    base_rate = rate_to_aed.loc[base_currency]
    holdings["current_value_base"] = holdings["current_value"] * source_rate / base_rate
    holdings["purchase_value_base"] = holdings["purchase_value"] * source_rate / base_rate

    sign = holdings["category"].map({"Asset": 1, "Liability": -1})
    holdings["signed_value_base"] = holdings["current_value_base"] * sign
    return holdings


def filter_holdings(
    holdings: pd.DataFrame,
    *,
    search: str = "",
    country: str | None = None,
    asset_type: str | None = None,
    category: str | None = None,
) -> pd.DataFrame:
    """Return holdings matching the selected filters and a literal text search."""
    filtered = holdings

    for column, selected_value in (
        ("country", country),
        ("asset_type", asset_type),
        ("category", category),
    ):
        if selected_value is not None:
            if selected_value == "":
                selected = filtered[column].isna() | filtered[column].eq("")
            else:
                selected = filtered[column].eq(selected_value)
            filtered = filtered.loc[selected]

    query = search.strip()
    if query:
        matches = pd.Series(False, index=filtered.index)
        for column in HOLDINGS_SEARCH_COLUMNS:
            matches |= (
                filtered[column]
                .astype("string")
                .str.contains(query, case=False, regex=False, na=False)
            )
        filtered = filtered.loc[matches]

    return filtered


def load_data(
    base_currency: str = "AED",
    holdings_source: str | Path | IO[bytes] | IO[str] | None = None,
    fx_source: str | Path | IO[bytes] | IO[str] = DEFAULT_FX_PATH,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """Load both CSVs and return (converted holdings, FX rates)."""
    rates = load_fx_rates(fx_source)
    holdings = _load_holdings_with_rates(
        holdings_source=holdings_source,
        base_currency=base_currency,
        rates=rates,
    )
    return holdings, rates
