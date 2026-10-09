"""Outstanding family debt under the shared portfolio filters."""

import streamlit as st

from liabilities import debt_summary, liability_chart, liability_data
from overview_charts import compact_currency, full_currency

st.title("Liabilities")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

currency = st.session_state["base_currency"]
liabilities = liability_data(st.session_state["filtered_holdings"])
st.caption(st.session_state["filter_caption"])

if liabilities.empty:
    st.info("No liabilities – well done!")
    st.stop()

total, count, weighted_rate = debt_summary(liabilities)
debt_col, count_col, rate_col = st.columns(3)
debt_col.metric(
    "Total outstanding debt", compact_currency(total, currency),
    help=f"Full value: {full_currency(total, currency)}", border=True,
)
count_col.metric("Number of liabilities", count, border=True)
rate_col.metric(
    "Weighted average interest rate",
    f"{weighted_rate:.2f}%" if weighted_rate is not None else "N/A",
    help=(
        "Sum of interest rate × outstanding balance, divided by total outstanding "
        "balance in the selected base currency. N/A when the total is zero or "
        "required balances or rates are missing."
    ),
    border=True,
)

for _, liability in liabilities.loc[liabilities["interest_rate_pct"].gt(15)].iterrows():
    st.warning(
        f"{liability['item_name']} at {liability['interest_rate_pct']:g}% interest "
        "– consider paying this off first."
    )

table = liabilities[[
    "item_name", "held_with", "country", "purchase_value_base",
    "current_value_base", "repaid_pct", "interest_rate_pct", "notes",
]]
styled_table = table.style.format(
    {
        "purchase_value_base": lambda value: full_currency(value, currency),
        "current_value_base": lambda value: full_currency(value, currency),
        "repaid_pct": "{:.2f}%",
        "interest_rate_pct": "{:.2f}%",
    },
    na_rep="N/A",
)
st.dataframe(
    styled_table,
    column_config={
        "item_name": "Item name", "held_with": "Lender", "country": "Country",
        "purchase_value_base": "Original amount",
        "current_value_base": "Outstanding balance", "repaid_pct": "% repaid",
        "interest_rate_pct": "Interest rate %", "notes": "Notes",
    },
    width="stretch", hide_index=True,
)

st.subheader("Original amount vs outstanding balance")
st.plotly_chart(
    liability_chart(liabilities, currency), width="stretch", key="liability_balances"
)
