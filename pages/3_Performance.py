"""Asset performance against the selected benchmark."""

import streamlit as st

from overview_charts import compact_currency, full_currency
from performance import asset_performance, performance_chart
from ui import style_chart

st.title("Performance")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

currency = st.session_state["base_currency"]
benchmark = st.session_state["benchmark_return_pct"]
assets = asset_performance(st.session_state["filtered_holdings"], benchmark)

for column, (label, icon) in zip(st.columns(3), (
    ("Performing", "trending_up"), ("Stagnant", "trending_flat"), ("Losing", "trending_down"),
)):
    group = assets.loc[assets["label"].eq(label)]
    total_value = float(group["current_value_base"].sum())
    column.metric(
        f":material/{icon}: {label} — {len(group)} assets",
        compact_currency(total_value, currency),
        help=f"Total current value: {full_currency(total_value, currency)}",
        border=True,
    )
st.caption(st.session_state["filter_caption"])

if assets.empty:
    st.info("No assets match these filters")
    st.stop()

chart = performance_chart(assets, benchmark)
if chart is None:
    st.info("No assets have a calculable CAGR.")
else:
    style_chart(chart)
    chart.update_traces(
        marker_cornerradius=4,
        hovertemplate="<b>%{y}</b><br>CAGR: %{x:.2f}%<extra>%{fullData.name}</extra>",
    )
    chart.update_yaxes(title_text=None, showgrid=False)
    st.plotly_chart(chart, width="stretch", key="performance_cagr")

table = assets[[
    "item_name", "asset_type", "country",
    "purchase_value_base", "current_value_base", "gain_loss_base", "cagr_pct", "label",
]]
styled_table = table.style.format(
    {
        "purchase_value_base": lambda value: full_currency(value, currency),
        "current_value_base": lambda value: full_currency(value, currency),
        "gain_loss_base": lambda value: full_currency(value, currency),
        "cagr_pct": "{:.2f}%",
    },
    na_rep="N/A",
)
st.dataframe(
    styled_table,
    column_config={
        "item_name": "Item name", "asset_type": "Asset type", "country": "Country",
        "purchase_value_base": "Purchase value", "current_value_base": "Current value",
        "gain_loss_base": "Gain/Loss", "cagr_pct": "CAGR %", "label": "Label",
    },
    width="stretch", hide_index=True,
)
st.caption("CAGR does not include rental income, dividends or interest paid out.")
st.caption("N/A = missing or invalid purchase date / purchase value.")
