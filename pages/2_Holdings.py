"""Existing holdings search and category filtering, with shared sidebar filters."""

import streamlit as st

from data_loader import filter_holdings

st.title("Holdings")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

holdings = st.session_state["filtered_holdings"]
st.caption(st.session_state["filter_caption"])
search_col, category_col = st.columns([3, 1])
search = search_col.text_input(
    "Search holdings", placeholder="Name, ID, city, institution, or notes",
    key="holdings_search",
)
categories = [None, "Asset", "Liability"]
category = category_col.selectbox(
    "Category", categories, key="holdings_category",
    format_func=lambda value: "All categories" if value is None else value,
)
filtered_holdings = filter_holdings(holdings, search=search, category=category)
st.caption(
    f"Showing {len(filtered_holdings)} of {len(st.session_state['holdings'])} holdings"
)
if filtered_holdings.empty:
    st.info("No holdings match these filters")
else:
    headers = {
        column: column.replace("_", " ").capitalize()
        for column in filtered_holdings.columns
    }
    headers.update({
        "item_id": "ID", "item_name": "Item", "asset_type": "Type",
        "held_with": "Held with", "account_ref": "Account reference",
        "interest_rate_pct": "Interest rate %",
        "current_value_base": f"Current value ({st.session_state['base_currency']})",
        "purchase_value_base": f"Purchase value ({st.session_state['base_currency']})",
        "signed_value_base": f"Signed value ({st.session_state['base_currency']})",
        "purchase_date": st.column_config.DateColumn("Purchase date", format="D MMM YYYY"),
        "last_valued_on": st.column_config.DateColumn("Last valued on", format="D MMM YYYY"),
    })
    st.dataframe(
        filtered_holdings, column_config=headers, width="stretch", hide_index=True,
    )
