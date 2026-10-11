"""Filtered portfolio KPIs and charts."""

import streamlit as st

from insights import smart_insights
from overview_charts import (
    assets_donut, compact_currency, country_net_worth, full_currency,
    holdings_treemap, portfolio_totals,
)
from ui import NEGATIVE

st.title("Overview")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

holdings = st.session_state["filtered_holdings"]
currency = st.session_state["base_currency"]
colors = st.session_state["asset_type_colors"]
totals = portfolio_totals(holdings)

insights = smart_insights(holdings, currency, st.session_state["benchmark_return_pct"])
if insights:
    with st.container(border=True, key="smart_insights"):
        st.subheader(":material/lightbulb: Smart insights")
        for icon, label, text in insights:
            st.markdown(f":material/{icon}: **{label}** · {text}")
        st.caption("Worked out from your own numbers and current filters. Not financial advice.")

# Scope the requested red liability value to this card only.
st.html(f"""
<style>
.st-key-liabilities_kpi [data-testid="stMetricValue"] {{ color: {NEGATIVE}; }}
</style>
""")
net_col, assets_col, liabilities_col, ratio_col = st.columns(4)
for column, label, value in (
    (net_col, ":material/account_balance: Net worth", totals["net_worth"]),
    (assets_col, ":material/savings: Total assets", totals["assets"]),
):
    column.metric(
        label, compact_currency(value, currency),
        help=f"Full value: {full_currency(value, currency)}", border=True,
    )
with liabilities_col:
    with st.container(key="liabilities_kpi"):
        st.metric(
            ":material/credit_card: Total liabilities", compact_currency(totals["liabilities"], currency),
            help=f"Full value: {full_currency(totals['liabilities'], currency)}",
            border=True,
        )
ratio = totals["debt_ratio"]
ratio_col.metric(
    ":material/percent: Debt-to-asset ratio", f"{ratio:.1f}%" if ratio is not None else "N/A",
    help=(
        f"Liabilities ÷ assets × 100 = {ratio:.2f}%"
        if ratio is not None else "Undefined because the filtered portfolio has no asset value."
    ),
    border=True,
)
st.caption(st.session_state["filter_caption"])

if holdings.empty:
    st.info("No holdings match these filters")
    st.stop()

donut_col, country_col = st.columns(2)
with donut_col:
    st.subheader("Assets by asset type")
    donut = assets_donut(holdings, currency, colors)
    if donut is None:
        st.info("No positive asset values are available for these filters.")
    else:
        st.plotly_chart(donut, width="stretch", key="assets_donut")
with country_col:
    st.subheader("Net worth by country")
    st.plotly_chart(
        country_net_worth(holdings, currency), width="stretch", key="country_net_worth"
    )
    st.caption("Assets minus liabilities in each country.")

st.subheader("Holdings by country and asset type")
st.caption(
    "Tile size shows current value, including outstanding debt balances. "
    "Colours match the asset-type chart above; debts are grey."
)
treemap = holdings_treemap(holdings, currency, colors)
if treemap is None:
    st.info("No positive current values are available for these filters.")
else:
    st.plotly_chart(treemap, width="stretch", key="holdings_treemap")
