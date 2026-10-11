"""Exercise the real navigation entrypoint and its shared widgets."""

from pathlib import Path
import unittest

from streamlit.testing.v1 import AppTest
from streamlit.runtime.uploaded_file_manager import UploadedFile, UploadedFileRec
from streamlit.proto.Common_pb2 import FileURLs

from test_fx import CUSTOM_FX, holdings_csv
from test_holdings import holdings_frame, invalid_uploads

ROOT = Path(__file__).resolve().parents[1]
# Recoverable upload problems are shown as a notice in place of the page.
NOTICES = (
    "This CSV is empty.", "has no holdings yet", "available for:",
)


class NavigationTests(unittest.TestCase):
    def setUp(self):
        self.app = AppTest.from_file(ROOT / "app.py", default_timeout=15).run()
        self.assert_healthy("Family Wealth Navigator")

    def assert_healthy(self, title):
        self.assertEqual(list(self.app.exception), [])
        self.assertEqual(list(self.app.error), [])
        self.assertEqual(self.app.title[0].value, title)

    def navigate(self, page):
        if page == "Home":
            # switch_page supports file pages only; Home is a callable.
            # Reset the requested page hash to select the registered default,
            # keeping this same AppTest session (and all shared widget state).
            self.app._page_hash = ""
            self.app.run()
            self.assert_healthy("Family Wealth Navigator")
        else:
            self.app.switch_page(f"pages/{1 if page == 'Overview' else 2}_{page}.py").run()
            self.assert_healthy(page)

    def select(self, key, value):
        self.app.selectbox(key=key).set_value(value).run()
        self.assertEqual(list(self.app.exception), [])

    def assert_shared_selection(self, country, asset_type):
        for key, value in (("filter_country", country), ("filter_asset_type", asset_type)):
            self.assertEqual(self.app.session_state[key], value)
            self.assertEqual(self.app.selectbox(key=key).value, value)

    def assert_ids(self, expected):
        self.assertEqual(len(self.app.dataframe), 1)
        self.assertEqual(self.app.dataframe[0].value["item_id"].tolist(), expected)

    def upload(self, key, content):
        # AppTest has no uploader interaction API. Seed the actual UploadedFile
        # widget value so the real shared controls and loader process its stream.
        self.app.session_state[key] = (
            UploadedFile(
                UploadedFileRec(
                    key, f"{key}.csv", "text/csv",
                    content if isinstance(content, bytes) else content.encode(),
                ),
                FileURLs(),
            ) if content is not None else None
        )
        self.app.run()
        self.assertEqual(list(self.app.exception), [])

    def assert_footer(self, text):
        self.assertIn(text, " ".join(m.value for m in self.app.sidebar.markdown))

    def assert_rejected_holdings(self, message, title):
        self.assertEqual(list(self.app.exception), [])
        if any(notice in message for notice in NOTICES):
            self.assertEqual(list(self.app.error), [])
            self.assertEqual(len(self.app.title), 0)
            self.assertIn(message, self.app.info[0].value)
            self.assertEqual(self.app.session_state["data_notice"], self.app.info[0].value)
            self.assertIsNone(self.app.session_state["data_error"])
        else:
            self.assertEqual(self.app.title[0].value, title)
            self.assertEqual(len(self.app.error), 1)
            self.assertTrue(
                self.app.error[0].value.startswith("Could not load portfolio data: ")
            )
            self.assertIn(message, self.app.error[0].value)
            self.assertEqual(self.app.session_state["data_error"], self.app.error[0].value)
        for key in ("holdings", "filtered_holdings", "fx_rates"):
            self.assertNotIn(key, self.app.session_state)
        self.assertEqual(len(self.app.metric), 0)
        self.assertEqual(len(self.app.dataframe), 0)
        self.assertEqual(len(self.app.get("plotly_chart")), 0)

    def test_invalid_holdings_block_all_pages_and_valid_replacement_recovers(self):
        valid_csv = holdings_frame().to_csv(index=False)
        for payload, message in invalid_uploads():
            with self.subTest(message=message):
                # Reject only after a real portfolio has populated state/charts.
                self.upload("holdings_upload", valid_csv)
                self.navigate("Overview")
                self.assertEqual(self.app.metric[0].value, "AED 125")
                self.assertEqual(len(self.app.get("plotly_chart")), 3)
                self.upload("holdings_upload", payload)
                self.assert_rejected_holdings(message, "Overview")
                self.app.switch_page("pages/2_Holdings.py").run()
                self.assert_rejected_holdings(message, "Holdings")
                self.app._page_hash = ""
                self.app.run()
                self.assert_rejected_holdings(message, "Family Wealth Navigator")

                # Replacing the rejected stream clears the error in this session.
                self.upload("holdings_upload", valid_csv)
                self.assert_healthy("Family Wealth Navigator")
                self.assertIsNone(self.app.session_state["data_error"])
                self.assert_footer("Your uploaded data")
                self.navigate("Holdings")
                self.assert_ids(["TEST-A", "TEST-L", "TEST-B"])
                self.navigate("Overview")
                self.assertEqual(
                    [m.value for m in self.app.metric[:3]], ["AED 125", "AED 150", "AED 25"],
                )
                self.assertEqual(len(self.app.get("plotly_chart")), 3)

    def test_clearing_rejected_holdings_restores_demo_on_each_active_page(self):
        for page in ("Home", "Overview", "Holdings"):
            with self.subTest(page=page):
                self.navigate(page)
                self.upload("holdings_upload", "")
                self.assert_rejected_holdings(
                    "This CSV is empty.",
                    "Family Wealth Navigator" if page == "Home" else page,
                )
                self.upload("holdings_upload", None)
                self.assert_healthy("Family Wealth Navigator" if page == "Home" else page)
                self.assertIsNone(self.app.session_state["data_error"])
                self.assertEqual(len(self.app.session_state["holdings"]), 20)
                self.assert_footer("Sample data – fictional family")
                if page == "Overview":
                    self.assertEqual(len(self.app.metric), 4)
                    self.assertEqual(len(self.app.get("plotly_chart")), 3)
                elif page == "Holdings":
                    self.assertEqual(len(self.app.dataframe[0].value), 20)

    def test_custom_fx_persists_dates_filters_and_base_currency_then_resets(self):
        self.upload("fx_upload", CUSTOM_FX)
        self.select("filter_country", "India")
        self.select("filter_asset_type", "Land")
        for page in ("Overview", "Holdings", "Home", "Overview"):
            self.navigate(page)
            self.assert_shared_selection("India", "Land")
            self.assertIsNotNone(self.app.session_state["fx_upload"])
            self.assert_footer("Sample data – fictional family")
            self.assertEqual(self.app.table[0].value.loc["INR", "As of"], "2 Oct 2026")
            if page == "Overview":
                self.assertEqual(self.app.metric[0].value, "AED 350.00K")
        self.select("base_currency", "USD")
        self.assertEqual(self.app.metric[0].value, "USD 87.50K")
        self.navigate("Holdings")
        self.assertEqual(self.app.dataframe[0].value["current_value_base"].tolist(),
                         [40000, 47500])
        self.upload("fx_upload", None)
        self.navigate("Overview")
        self.assertEqual(self.app.metric[0].value, "USD 79.67K")
        self.assertEqual(self.app.table[0].value.loc["INR", "As of"], "30 Sep 2026")
        self.navigate("Home")
        self.assertIsNone(self.app.session_state["fx_upload"])

    def test_invalid_fx_blocks_results_on_all_pages_and_recovers(self):
        for csv, message in (
            ("currency,rate_to_aed\nAED,1\n", "FX CSV is missing required columns"),
            ("currency,rate_to_aed,as_of\nAED,1,2026-10-01\n",
             "available for: INR, SGD, USD"),
            (CUSTOM_FX.replace("INR,0.05", "INR,0"), "finite positive"),
            (CUSTOM_FX.replace("AED,1,", "AED,2,"), "AED rate_to_aed must equal 1"),
            (CUSTOM_FX.replace("2026-10-02", "invalid"), "Invalid date"),
        ):
            with self.subTest(message=message):
                self.upload("fx_upload", csv)
                is_notice = any(notice in message for notice in NOTICES)
                for page in ("pages/1_Overview.py", "pages/2_Holdings.py"):
                    self.app.switch_page(page).run()
                    self.assertEqual(list(self.app.exception), [])
                    shown = self.app.info if is_notice else self.app.error
                    self.assertIn(message, shown[0].value)
                    self.assertEqual(len(self.app.metric), 0)
                    self.assertEqual(len(self.app.dataframe), 0)
                    self.assertNotIn("holdings", self.app.session_state)
                self.app._page_hash = ""
                self.app.run()
                shown = self.app.info if is_notice else self.app.error
                self.assertIn(message, shown[0].value)
                self.upload("fx_upload", None)
                self.assert_healthy("Family Wealth Navigator")

    def test_holdings_and_fx_uploads_work_together_across_navigation(self):
        self.upload("holdings_upload", holdings_csv())
        self.upload("fx_upload", CUSTOM_FX)
        self.assert_footer("Your uploaded data")
        for page in ("Overview", "Holdings", "Home"):
            self.navigate(page)
            self.assertEqual(len(self.app.session_state["holdings"]), 2)
            self.assertEqual(
                self.app.session_state["holdings"]["signed_value_base"].tolist(),
                [40, -50],
            )
            if page == "Overview":
                self.assertEqual(self.app.metric[0].value, "AED -10")

    def test_navigation_preserves_both_filters_including_home(self):
        self.select("filter_country", "India")
        self.select("filter_asset_type", "Land")
        for page in ("Overview", "Holdings", "Home", "Holdings", "Overview"):
            with self.subTest(page=page):
                self.navigate(page)
                self.assert_shared_selection("India", "Land")
                self.assertEqual(
                    self.app.session_state["filtered_holdings"]["item_id"].tolist(),
                    ["A01", "A02"],
                )
                if page == "Holdings":
                    self.assert_ids(["A01", "A02"])
                elif page == "Overview":
                    self.assertEqual(self.app.metric[0].value, "AED 292.60K")
                    self.assertEqual(len(self.app.get("plotly_chart")), 3)
                    self.assertIn("Filters: India · Land", [c.value for c in self.app.caption])

        # Resetting each filter must restore results, not leave stale data.
        self.select("filter_asset_type", None)
        self.assert_shared_selection("India", None)
        self.assertEqual(len(self.app.session_state["filtered_holdings"]), 9)
        self.select("filter_country", None)
        self.navigate("Holdings")
        self.assert_shared_selection(None, None)
        self.assertEqual(len(self.app.dataframe[0].value), 20)

    def test_no_match_on_both_pages_and_recovery(self):
        self.select("filter_country", "USA")
        self.select("filter_asset_type", "Land")
        self.navigate("Overview")
        self.assertEqual(
            [m.value for m in self.app.metric],
            ["AED 0", "AED 0", "AED 0", "N/A"],
        )
        self.assertEqual(len(self.app.get("plotly_chart")), 0)
        self.assertIn("No holdings match these filters", [i.value for i in self.app.info])
        self.navigate("Holdings")
        self.assert_shared_selection("USA", "Land")
        self.assertEqual(len(self.app.dataframe), 0)
        self.assertIn("No holdings match these filters", [i.value for i in self.app.info])
        self.assertIn("Showing 0 of 20 holdings", [c.value for c in self.app.caption])
        self.select("filter_asset_type", "Stocks")
        self.assert_ids(["A10"])
        self.navigate("Overview")
        self.assertEqual(len(self.app.get("plotly_chart")), 3)
        self.assertEqual(self.app.metric[0].value, "AED 190.97K")

    def test_base_currency_updates_values_and_persists_across_pages(self):
        self.select("filter_country", "India")
        self.select("filter_asset_type", "Land")
        for currency, expected_kpi, expected_values in (
            ("USD", "USD 79.67K", [3200000 * .0418 / 3.6725, 3800000 * .0418 / 3.6725]),
            ("INR", "INR 7.00M", [3200000, 3800000]),
            ("AED", "AED 292.60K", [133760, 158840]),
        ):
            with self.subTest(currency=currency):
                self.select("base_currency", currency)
                self.navigate("Overview")
                self.assertEqual(self.app.metric[0].value, expected_kpi)
                self.assertTrue(all(m.value.startswith(currency) for m in self.app.metric[:3]))
                self.navigate("Holdings")
                self.assert_ids(["A01", "A02"])
                for actual, expected in zip(
                    self.app.dataframe[0].value["current_value_base"], expected_values, strict=True
                ):
                    self.assertAlmostEqual(actual, expected)
                self.navigate("Home")
                self.assertEqual(self.app.session_state["base_currency"], currency)
                self.assertEqual(self.app.selectbox(key="base_currency").value, currency)
                self.assert_shared_selection("India", "Land")

    def test_holdings_search_category_and_shared_filters_intersect(self):
        self.navigate("Holdings")
        self.app.text_input(key="holdings_search").set_value("  LOAN  ").run()
        self.assert_ids(["L01", "L02", "L04"])
        self.select("filter_country", "India")
        self.assert_ids(["L04"])
        self.select("holdings_category", "Asset")
        self.assertEqual(len(self.app.dataframe), 0)
        self.assertIn("No holdings match these filters", [i.value for i in self.app.info])
        self.select("holdings_category", "Liability")
        self.assert_ids(["L04"])
        self.select("filter_asset_type", "Loan")
        self.assert_ids(["L04"])
        self.app.text_input(key="holdings_search").set_value("not-a-real-holding").run()
        self.assertEqual(len(self.app.dataframe), 0)
        self.app.text_input(key="holdings_search").set_value("").run()
        self.assert_ids(["L04"])
        self.select("holdings_category", None)
        self.select("filter_country", None)
        self.select("filter_asset_type", None)
        self.assertEqual(len(self.app.dataframe[0].value), 20)
        self.select("holdings_category", "Asset")
        self.assertEqual(len(self.app.dataframe[0].value), 16)
        self.select("holdings_category", "Liability")
        self.assert_ids(["L01", "L02", "L03", "L04"])
        self.assertEqual(list(self.app.exception), [])

    def test_liability_only_overview_has_negative_net_worth_and_no_ratio(self):
        self.select("filter_asset_type", "Mortgage")
        self.navigate("Overview")
        self.assertEqual(
            [m.value for m in self.app.metric],
            ["AED -455.00K", "AED 0", "AED 455.00K", "N/A"],
        )
        self.assertIn(
            "No positive asset values are available for these filters.",
            [i.value for i in self.app.info],
        )
        self.assertEqual(len(self.app.get("plotly_chart")), 2)

    def test_search_matches_id_city_institution_notes_and_literal_punctuation(self):
        self.navigate("Holdings")
        for query, ids in (
            ("a01", ["A01"]),
            ("thrissur", ["A01", "A06"]),
            ("SafeVault", ["A05"]),
            ("Emergency fund", ["A07"]),
            ("(DFM)", ["A12"]),
            (".*", []),
        ):
            with self.subTest(query=query):
                self.app.text_input(key="holdings_search").set_value(query).run()
                self.assert_healthy("Holdings")
                if ids:
                    self.assert_ids(ids)
                else:
                    self.assertEqual(len(self.app.dataframe), 0)
                    self.assertIn(
                        "No holdings match these filters", [i.value for i in self.app.info]
                    )


if __name__ == "__main__":
    unittest.main()
