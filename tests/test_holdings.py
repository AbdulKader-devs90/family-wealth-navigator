"""Repeatable holdings upload validation using small, fictional CSV fixtures."""

from io import BytesIO, StringIO
import unittest

import pandas as pd

from data_loader import (
    DATE_COLUMNS, HOLDINGS_REQUIRED_COLUMNS, NUMERIC_COLUMNS,
    MissingColumnsError, load_data, load_holdings,
)


def holdings_frame():
    rows = []
    for item_id, category, current in (
        ("TEST-A", "Asset", 100), ("TEST-L", "Liability", 25),
        ("TEST-B", "Asset", 50),
    ):
        row = dict.fromkeys(HOLDINGS_REQUIRED_COLUMNS, "")
        row.update(
            item_id=item_id, category=category, asset_type="Cash",
            item_name=f"Fictional {item_id}", country="UAE", currency="AED",
            quantity=1, purchase_date="2026-09-01", purchase_value=80,
            current_value=current, last_valued_on="2026-09-30",
            interest_rate_pct=2.5,
        )
        rows.append(row)
    return pd.DataFrame(rows)


def invalid_uploads():
    """Representative real upload payloads and their actionable errors."""
    frame = holdings_frame()
    yield frame.drop(columns=["currency", "current_value"]).to_csv(index=False), (
        "holdings CSV is missing required columns"
    )
    yield "", "The CSV file is empty."
    yield frame.iloc[:0].to_csv(index=False), "at least one holding"
    yield frame.to_csv(index=False) + '"unterminated', "Could not read the CSV file"
    yield b"\xff\xfe\x00", "must be encoded as UTF-8"
    for column, value, message in (
        ("purchase_date", "2026-02-30", "Invalid date value in 'purchase_date'"),
        ("current_value", "not-a-number", "'current_value' must contain numbers"),
        ("category", "Savings", "Category must be 'Asset' or 'Liability'"),
        ("currency", "EUR", "No AED exchange rate is available for: EUR"),
        ("currency", "", "blank currency code"),
    ):
        invalid = frame.copy()
        invalid[column] = invalid[column].astype(object)
        invalid.loc[1, column] = value
        yield invalid.to_csv(index=False), message


class HoldingsValidationTests(unittest.TestCase):
    def test_each_required_column_is_reported_with_holdings_source(self):
        frame = holdings_frame()
        for column in HOLDINGS_REQUIRED_COLUMNS:
            with self.subTest(column=column):
                csv = frame.drop(columns=column).to_csv(index=False)
                with self.assertRaises(MissingColumnsError) as error:
                    load_holdings(StringIO(csv))
                self.assertEqual(error.exception.missing_columns, [column])
                self.assertIn("holdings CSV", str(error.exception))
                self.assertIn(f"- {column}", str(error.exception))

    def test_multiple_missing_columns_are_reported_in_schema_order(self):
        missing = ["category", "currency", "current_value"]
        csv = holdings_frame().drop(columns=missing).to_csv(index=False)
        with self.assertRaises(MissingColumnsError) as error:
            load_holdings(StringIO(csv))
        self.assertEqual(error.exception.missing_columns, missing)

    def test_rejected_payloads_fail_both_public_loaders(self):
        for payload, message in invalid_uploads():
            for loader in (load_holdings, load_data):
                with self.subTest(loader=loader.__name__, message=message):
                    stream = (
                        BytesIO(payload) if isinstance(payload, bytes)
                        else StringIO(payload)
                    )
                    with self.assertRaises(ValueError) as error:
                        loader(holdings_source=stream)
                    self.assertIn(message, str(error.exception))

    def test_whitespace_only_csv_is_empty(self):
        for csv in ("\n\n", "   \n\t\n"):
            with self.subTest(csv=csv):
                with self.assertRaisesRegex(ValueError, "CSV file is empty"):
                    load_holdings(StringIO(csv))

    def test_each_date_column_reports_all_invalid_csv_rows(self):
        for column in DATE_COLUMNS:
            frame = holdings_frame()
            frame.loc[1, column] = "not-a-date"
            frame.loc[2, column] = "2026-02-30"
            with self.subTest(column=column):
                with self.assertRaises(ValueError) as error:
                    load_holdings(StringIO(frame.to_csv(index=False)))
                self.assertEqual(
                    str(error.exception),
                    f"Invalid date value in '{column}' on CSV row(s): 3, 4.",
                )

    def test_each_numeric_column_reports_all_invalid_csv_rows(self):
        for column in NUMERIC_COLUMNS:
            frame = holdings_frame()
            frame[column] = frame[column].astype(object)
            frame.loc[1, column] = "not-a-number"
            frame.loc[2, column] = "1,000"
            with self.subTest(column=column):
                with self.assertRaises(ValueError) as error:
                    load_holdings(StringIO(frame.to_csv(index=False)))
                self.assertEqual(
                    str(error.exception),
                    f"'{column}' must contain numbers. Check CSV row(s): 3, 4.",
                )

    def test_invalid_and_blank_categories_are_rejected(self):
        for value, detail in (("Investment", "Investment"), ("", "blank"),
                              ("   ", "blank"), (None, "blank")):
            frame = holdings_frame()
            frame.loc[1, "category"] = value
            with self.subTest(value=value):
                with self.assertRaises(ValueError) as error:
                    load_holdings(StringIO(frame.to_csv(index=False)))
                self.assertIn("Category must be 'Asset' or 'Liability'", str(error.exception))
                self.assertIn(detail, str(error.exception))

    def test_missing_holdings_rates_list_all_normalized_codes(self):
        frame = holdings_frame()
        frame["currency"] = [" eur ", "GBP", "EUR"]
        with self.assertRaisesRegex(ValueError, "available for: EUR, GBP"):
            load_holdings(StringIO(frame.to_csv(index=False)))

    def test_valid_uploads_normalize_parse_and_convert_without_demo_rows(self):
        frame = holdings_frame()
        frame["category"] = [" asset ", "LIABILITY", "Asset"]
        frame["currency"] = [" aed ", "AED", "aed"]
        csv = frame.to_csv(index=False)
        for stream in (StringIO(csv), BytesIO(csv.encode())):
            with self.subTest(stream=type(stream).__name__):
                loaded = load_holdings(stream)
                self.assertEqual(loaded["item_id"].tolist(), ["TEST-A", "TEST-L", "TEST-B"])
                self.assertEqual(loaded["category"].tolist(), ["Asset", "Liability", "Asset"])
                self.assertEqual(loaded["currency"].tolist(), ["AED"] * 3)
                self.assertEqual(loaded["signed_value_base"].tolist(), [100, -25, 50])
                self.assertEqual(loaded["purchase_value_base"].tolist(), [80] * 3)
                for column in DATE_COLUMNS:
                    self.assertTrue(pd.api.types.is_datetime64_any_dtype(loaded[column]))
                for column in NUMERIC_COLUMNS:
                    self.assertTrue(pd.api.types.is_numeric_dtype(loaded[column]))

    def test_optional_blank_dates_and_numbers_remain_allowed(self):
        frame = holdings_frame()
        for column in (*DATE_COLUMNS, *NUMERIC_COLUMNS):
            frame[column] = ["", "   ", None]
        loaded = load_holdings(StringIO(frame.to_csv(index=False)))
        self.assertTrue(loaded[list(DATE_COLUMNS + NUMERIC_COLUMNS)].isna().all().all())


if __name__ == "__main__":
    unittest.main()
