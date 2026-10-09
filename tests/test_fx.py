"""Validation and stream-safe valuation using user-supplied FX CSVs."""

from io import BytesIO, StringIO
import unittest

import pandas as pd

from data_loader import (
    HOLDINGS_REQUIRED_COLUMNS, MissingColumnsError, load_data, load_fx_rates,
)

CUSTOM_FX = (
    "currency,rate_to_aed,as_of\n"
    "AED,1,2026-10-01\nINR,0.05,2026-10-02\n"
    "USD,4,2026-10-03\nSGD,3,2026-10-04\n"
)


def holdings_csv():
    rows = []
    for category, currency, current, purchase in (
        ("Asset", "USD", 10, 8), ("Liability", "INR", 1000, 900),
    ):
        row = dict.fromkeys(HOLDINGS_REQUIRED_COLUMNS, "")
        row.update(category=category, currency=currency,
                   current_value=current, purchase_value=purchase)
        rows.append(row)
    return pd.DataFrame(rows).to_csv(index=False)


class FxTests(unittest.TestCase):
    def test_required_columns_identify_fx_source(self):
        for column in ("currency", "rate_to_aed", "as_of"):
            frame = pd.read_csv(StringIO(CUSTOM_FX)).drop(columns=column)
            with self.subTest(column=column):
                with self.assertRaises(MissingColumnsError) as error:
                    load_fx_rates(StringIO(frame.to_csv(index=False)))
                self.assertEqual(error.exception.missing_columns, [column])
                self.assertIn("FX CSV", str(error.exception))

    def test_invalid_fx_rows(self):
        for body, message in (
            ("", "at least one exchange rate"),
            (",1,2026-10-01", "blank currency"),
            ("US,1,2026-10-01", "three letters"),
            ("USD,1,2026-10-01\n usd ,2,2026-10-02", "duplicate currency"),
            ("USD,0,2026-10-01", "finite positive"),
            ("USD,-1,2026-10-01", "finite positive"),
            ("USD,invalid,2026-10-01", "finite positive"),
            ("USD,,2026-10-01", "finite positive"),
            ("USD,inf,2026-10-01", "finite positive"),
            ("USD,-inf,2026-10-01", "finite positive"),
            ("AED,2,2026-10-01", "AED rate_to_aed must equal 1"),
            ("AED,0.5,2026-10-01", "AED rate_to_aed must equal 1"),
            ("USD,1,", "dates are required"),
            ("USD,1,not-a-date", "Invalid date"),
            ("USD,1,2026-02-30", "Invalid date"),
        ):
            with self.subTest(body=body):
                with self.assertRaisesRegex(ValueError, message):
                    load_fx_rates(StringIO("currency,rate_to_aed,as_of\n" + body))

    def test_normalized_currency_and_parsed_dates(self):
        rates = load_fx_rates(StringIO(
            "currency,rate_to_aed,as_of\n usd ,4,2026-10-03\n"
        ))
        self.assertEqual(rates.iloc[0]["currency"], "USD")
        self.assertEqual(rates.iloc[0]["as_of"], pd.Timestamp("2026-10-03"))

    def test_uploaded_streams_convert_once_and_return_rate_dates(self):
        for base, divisor in (("AED", 1), ("INR", .05), ("USD", 4)):
            with self.subTest(base=base):
                holdings, rates = load_data(
                    base, BytesIO(holdings_csv().encode()), BytesIO(CUSTOM_FX.encode())
                )
                for column, expected in (
                    ("current_value_base", [40, 50]),
                    ("purchase_value_base", [32, 45]),
                    ("signed_value_base", [40, -50]),
                ):
                    for actual, value in zip(holdings[column], expected, strict=True):
                        self.assertAlmostEqual(actual, value / divisor)
                self.assertEqual(
                    rates["as_of"].dt.strftime("%Y-%m-%d").tolist(),
                    ["2026-10-01", "2026-10-02", "2026-10-03", "2026-10-04"],
                )

    def test_missing_source_and_base_rates_fail_without_demo_fallback(self):
        for rates, message in (
            ("AED,1,2026-10-01\n", "available for: INR, USD"),
            ("INR,.05,2026-10-01\nUSD,4,2026-10-01\n", "base currency AED"),
        ):
            with self.subTest(rates=rates):
                with self.assertRaisesRegex(ValueError, message):
                    load_data(
                        holdings_source=StringIO(holdings_csv()),
                        fx_source=StringIO("currency,rate_to_aed,as_of\n" + rates),
                    )

    def test_defaults_remain_fixed_demo_rates(self):
        holdings, rates = load_data()
        self.assertEqual(len(holdings), 20)
        self.assertEqual(rates.set_index("currency").loc["INR", "rate_to_aed"], .0418)
        self.assertEqual(rates["as_of"].unique().tolist(), [pd.Timestamp("2026-09-30")])


if __name__ == "__main__":
    unittest.main()
