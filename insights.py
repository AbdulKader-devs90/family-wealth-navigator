"""Plain-English, rule-based insights built from the existing portfolio numbers."""

from liabilities import liability_data
from overview_charts import compact_currency
from performance import asset_performance
from readiness import check_readiness


def _name(value):
    text = value.strip() if isinstance(value, str) else ""
    # Keep item names literal inside Markdown.
    return (text or "Unspecified").replace("$", "\\$").replace("*", "\\*")


def _concentration(holdings):
    assets = holdings.loc[
        holdings["category"].eq("Asset") & holdings["current_value_base"].gt(0)
    ]
    if assets.empty:
        return None
    totals = assets.groupby(
        assets["asset_type"].fillna("").replace("", "Unspecified")
    )["current_value_base"].sum()
    share = totals.max() / totals.sum() * 100
    text = f"**{_name(totals.idxmax())}** makes up {share:.0f}% of your assets"
    if len(totals) == 1:
        text += " – everything here is in one asset type."
    elif share >= 50:
        text += " – more than half sits in one asset type."
    elif share >= 30:
        text += ", your largest asset type."
    else:
        text += ", your largest asset type – your assets are well spread."
    return "pie_chart", "Concentration", text


def _performers(holdings, benchmark):
    assets = asset_performance(holdings, benchmark)
    rated = assets.loc[assets["cagr_pct"].notna() & assets["label"].ne("Cash – not rated")]
    if rated.empty:
        return []
    best = rated.loc[rated["cagr_pct"].idxmax()]
    results = [(
        "trending_up", "Best performer",
        f"**{_name(best['item_name'])}** has grown {best['cagr_pct']:.1f}% a year "
        "since you bought it.",
    )]
    worst = rated.loc[rated["cagr_pct"].idxmin()]
    if len(rated) > 1 and worst.name != best.name:
        rate = worst["cagr_pct"]
        results.append((
            "trending_down", "Weakest performer",
            f"**{_name(worst['item_name'])}** has lost {abs(rate):.1f}% a year."
            if rate < 0 else
            f"**{_name(worst['item_name'])}** is your slowest grower at {rate:.1f}% a year.",
        ))
    return results


def _debt_to_pay_first(holdings, currency):
    liabilities = liability_data(holdings)
    if liabilities.empty:
        return "credit_score", "Debt", "No debts in this view."
    costly = liabilities.loc[
        liabilities["current_value_base"].gt(0) & liabilities["interest_rate_pct"].notna()
    ].sort_values(["interest_rate_pct", "current_value_base"], ascending=False)
    if costly.empty:
        return (
            "credit_card", "Debt to pay first",
            "Add interest rates to your debts to see which one costs you most.",
        )
    debt = costly.iloc[0]
    balance = compact_currency(float(debt["current_value_base"]), currency)
    text = (
        f"**{_name(debt['item_name'])}** charges {debt['interest_rate_pct']:g}% interest "
        f"on {balance}"
    )
    text += (
        " – the highest rate among your debts, so paying it down first saves the most."
        if len(costly) > 1 else "."
    )
    return "credit_card", "Debt to pay first", text


def _readiness_gap(holdings):
    items, issues = check_readiness(holdings)
    if issues.empty:
        return (
            "verified", "Readiness",
            "Every item has the details your family would need.",
        )
    # Issues arrive sorted most severe first.
    severity = issues.iloc[0]["severity"]
    top = issues.loc[issues["severity"].eq(severity)]
    issue = top["issue"].value_counts().idxmax()
    affected = top.loc[top["issue"].eq(issue)]
    count = len(affected)
    scope = (
        f"**{_name(affected.iloc[0]['item_name'])}**" if count == 1
        else f"{count} of {len(items)} items"
    )
    if severity == "Critical":
        text = (
            f"{scope} may contain a password, PIN or recovery phrase. "
            "Remove it and note where it is kept instead."
        )
    else:
        text = f"**{issue}** on {scope}. {affected.iloc[0]['suggested_fix']}"
    return "fact_check", "Top readiness gap", text


def smart_insights(holdings, currency, benchmark):
    """Return (icon, label, Markdown text) rows for the filtered holdings."""
    if holdings.empty:
        return []
    insights = [
        _concentration(holdings),
        *_performers(holdings, benchmark),
        _debt_to_pay_first(holdings, currency),
        _readiness_gap(holdings),
    ]
    return [insight for insight in insights if insight]
