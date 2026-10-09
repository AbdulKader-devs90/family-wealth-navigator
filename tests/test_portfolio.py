"""Independent arithmetic oracles for totals, conversion and chart aggregation."""

from io import StringIO
import unittest

import pandas as pd

from data_loader import HOLDINGS_REQUIRED_COLUMNS, filter_holdings, load_holdings
from overview_charts import (
    asset_type_colors, assets_donut, country_net_worth, holdings_treemap,
    portfolio_totals,
)


def portfolio():
    # Repeated groups, same item names, debt, zero/negative values and blanks.
    rows = [
        ("Asset", "Cash", "Savings", "UAE", 100),
        ("Asset", "Cash", "Savings", "UAE", 50),
        ("Asset", "Gold", "Gold", "India", 200),
        ("Liability", "Cash", "Debt", "UAE", 60),
        ("Liability", "Loan", "Loan", "India", 240),
        ("Asset", "Cash", "Zero", "UAE", 0),
        ("Asset", "Stocks", "Loss", "UAE", -10),
        ("Asset", None, None, None, 25),
        ("Asset", "", "", "", 15),
    ]
    frame = pd.DataFrame(
        rows, columns=["category", "asset_type", "item_name", "country", "current_value_base"]
    )
    frame["signed_value_base"] = frame["current_value_base"] * frame["category"].map(
        {"Asset": 1, "Liability": -1}
    )
    return frame


class PortfolioTests(unittest.TestCase):
    def setUp(self):
        self.holdings = portfolio()
        self.colors = asset_type_colors(self.holdings)

    def test_debt_ratio_uses_assets_not_net_worth(self):
        totals = portfolio_totals(self.holdings)
        self.assertEqual(totals["assets"], 380)
        self.assertEqual(totals["liabilities"], 300)
        self.assertEqual(totals["net_worth"], 80)
        self.assertAlmostEqual(totals["debt_ratio"], 300 / 380 * 100)
        self.assertEqual(totals["net_worth"], totals["assets"] - totals["liabilities"])
        for factor in (1 / .0418, 1 / 3.6725):
            converted = self.holdings.copy()
            converted[["current_value_base", "signed_value_base"]] *= factor
            self.assertAlmostEqual(portfolio_totals(converted)["debt_ratio"], totals["debt_ratio"])

    def test_debt_ratio_empty_zero_assets_and_debt_exceeding_assets(self):
        for frame in (
            self.holdings.iloc[:0],
            self.holdings.loc[self.holdings["category"].eq("Liability")],
            self.holdings.loc[self.holdings["item_name"].isin(["Zero", "Loss", "Debt"])],
        ):
            with self.subTest(rows=len(frame)):
                self.assertIsNone(portfolio_totals(frame)["debt_ratio"])
        debt_heavy = self.holdings.iloc[[0, 4]]
        self.assertEqual(portfolio_totals(debt_heavy)["net_worth"], -140)
        self.assertEqual(portfolio_totals(debt_heavy)["debt_ratio"], 240)
        asset_only = self.holdings.loc[self.holdings["category"].eq("Asset")]
        self.assertEqual(portfolio_totals(asset_only)["debt_ratio"], 0)

    def test_donut_aggregates_only_positive_assets(self):
        trace = assets_donut(self.holdings, "AED", self.colors).data[0]
        self.assertEqual(dict(zip(trace.labels, trace.values)), {
            "Cash": 150, "Gold": 200, "Unspecified": 40,
        })
        self.assertEqual(sum(trace.values), 390)
        for label, color in zip(trace.labels, trace.marker.colors, strict=True):
            self.assertEqual(color, self.colors[label])

    def test_country_bar_sums_signed_values_including_debt_and_blanks(self):
        trace = country_net_worth(self.holdings, "AED").data[0]
        self.assertEqual(dict(zip(trace.y, trace.x)), {
            "India": -40, "UAE": 80, "Unspecified": 40,
        })
        self.assertEqual(sum(trace.x), 80)
        self.assertEqual(list(trace.x), sorted(trace.x))

    def test_treemap_branch_and_leaf_totals_do_not_double_count(self):
        trace = holdings_treemap(self.holdings, "AED", self.colors).data[0]
        self.assertEqual(trace.branchvalues, "total")
        self.assertEqual(len(trace.ids), len(set(trace.ids)))
        nodes = dict(zip(trace.ids, zip(trace.labels, trace.parents, trace.values), strict=True))
        roots = {label: value for label, parent, value in nodes.values() if parent == ""}
        self.assertEqual(roots, {"India": 440, "UAE": 210, "Unspecified": 40})
        parent_ids = set(trace.parents) - {""}
        leaves = [value for node_id, (_, _, value) in nodes.items() if node_id not in parent_ids]
        self.assertEqual(sorted(leaves), [15, 25, 50, 60, 100, 200, 240])
        self.assertEqual(sum(leaves), sum(roots.values()))
        for node_id in parent_ids:
            child_total = sum(value for _, parent, value in nodes.values() if parent == node_id)
            self.assertEqual(nodes[node_id][2], child_total)
        # UAE Cash includes both asset balances and the positive debt balance.
        uae_id = next(node_id for node_id, (label, parent, _) in nodes.items()
                      if label == "UAE" and parent == "")
        self.assertEqual([(label, value) for label, parent, value in nodes.values()
                          if parent == uae_id], [("Cash", 210)])

    def test_filtered_chart_totals(self):
        selected = filter_holdings(self.holdings, country="UAE", asset_type="Cash")
        self.assertEqual(portfolio_totals(selected)["net_worth"], 90)
        self.assertEqual(sum(assets_donut(selected, "AED", self.colors).data[0].values), 150)
        self.assertEqual(sum(country_net_worth(selected, "AED").data[0].x), 90)
        trace = holdings_treemap(selected, "AED", self.colors).data[0]
        self.assertEqual(sum(value for parent, value in zip(trace.parents, trace.values)
                             if not parent), 210)

    def test_empty_and_nonpositive_charts(self):
        for frame in (
            self.holdings.iloc[:0],
            self.holdings.loc[self.holdings["current_value_base"].le(0)],
        ):
            self.assertIsNone(assets_donut(frame, "AED", self.colors))
            self.assertIsNone(holdings_treemap(frame, "AED", self.colors))
        debt = self.holdings.loc[self.holdings["category"].eq("Liability")]
        self.assertIsNone(assets_donut(debt, "AED", self.colors))
        self.assertIsNotNone(holdings_treemap(debt, "AED", self.colors))
        self.assertEqual(sum(country_net_worth(self.holdings.iloc[:0], "AED").data[0].x), 0)

    def test_conversion_and_liability_sign_with_known_rates(self):
        rows = []
        for category, currency, current, purchase in (
            ("Asset", "AED", 100, 80),
            ("Asset", "USD", 10, 8),
            ("Liability", "INR", 1000, 900),
        ):
            row = dict.fromkeys(HOLDINGS_REQUIRED_COLUMNS, "")
            row.update(category=category, currency=currency,
                       current_value=current, purchase_value=purchase)
            rows.append(row)
        csv = pd.DataFrame(rows).to_csv(index=False)
        for base, divisor in (("AED", 1), ("USD", 4), ("INR", .05)):
            with self.subTest(base=base):
                holdings = load_holdings(
                    StringIO(csv), base,
                    StringIO(
                        "currency,rate_to_aed,as_of\n"
                        "AED,1,2026-09-30\nUSD,4,2026-09-30\nINR,0.05,2026-09-30\n"
                    ),
                )
                for column, expected in (
                    ("current_value_base", [100, 40, 50]),
                    ("purchase_value_base", [80, 32, 45]),
                    ("signed_value_base", [100, 40, -50]),
                ):
                    for actual, value in zip(holdings[column], expected, strict=True):
                        self.assertAlmostEqual(actual, value / divisor)
                totals = portfolio_totals(holdings)
                self.assertAlmostEqual(totals["net_worth"], 90 / divisor)
                self.assertAlmostEqual(totals["debt_ratio"], 50 / 140 * 100)


if __name__ == "__main__":
    unittest.main()
