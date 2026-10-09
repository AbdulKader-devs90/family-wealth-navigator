"""Home and shared navigation/settings for Family Wealth Navigator."""

import streamlit as st
from checkin import public_demo_enabled

from data_loader import (
    CSVNotice, DEFAULT_FX_PATH, SUPPORTED_BASE_CURRENCIES, filter_holdings, load_data,
)
from overview_charts import asset_type_colors, filter_caption

st.set_page_config(page_title="Family Wealth Navigator", layout="wide")


def home():
    st.title("Family Wealth Navigator")
    st.write("See your family's wealth in one place, across countries and currencies.")
    st.markdown(
        "**Home** — Start here for a quick guide to the app.\n\n"
        "**Overview** — See net worth, assets, debts, and how they are spread.\n\n"
        "**Holdings** — Search and filter every asset and liability.\n\n"
        "**Performance** — Compare asset growth with your chosen benchmark.\n\n"
        "**Liabilities** — Review outstanding debts, interest rates, and repayments.\n\n"
        "**Readiness Check** — Find gaps in contacts, documents, and access instructions.\n\n"
        "**Family Wealth Map** — Create an encrypted family guide, share it, and manage check-ins."
    )
    if st.session_state.get("data_error"):
        st.error(st.session_state["data_error"])
    else:
        st.info(source_notice)


st.sidebar.header("Data settings")
base_currency = st.sidebar.selectbox(
    "Base currency", SUPPORTED_BASE_CURRENCIES, key="base_currency"
)
uploaded_holdings = st.sidebar.file_uploader(
    "Replace demo holdings CSV",
    type=["csv"],
    key="holdings_upload",
    help="Upload a holdings CSV with the same required columns as the demo file.",
)
uploaded_fx = st.sidebar.file_uploader(
    "Replace demo FX rates CSV (optional)",
    type=["csv"],
    key="fx_upload",
    help=(
        "Required columns: currency, rate_to_aed, as_of. Rates are AED per "
        "1 unit of currency (AED must equal 1); use dates such as 2026-09-30. Include every "
        "holdings currency and your base currency. Remove the upload to restore demo rates."
    ),
)

if uploaded_holdings is None and uploaded_fx is None:
    source_notice = "Demo data – fictional family, with fixed demo exchange rates (not live)."
elif uploaded_holdings is None:
    source_notice = "Fictional demo holdings use your uploaded exchange rates (not live)."
elif uploaded_fx is None:
    source_notice = "Your uploaded holdings use fixed demo exchange rates (not live)."
else:
    source_notice = "Using your uploaded holdings and exchange rates (not live)."

st.session_state["data_error"] = None
st.session_state["data_notice"] = None
try:
    if uploaded_holdings is not None:
        uploaded_holdings.seek(0)
    if uploaded_fx is not None:
        uploaded_fx.seek(0)
    holdings, rates = load_data(
        base_currency=base_currency, holdings_source=uploaded_holdings,
        fx_source=uploaded_fx if uploaded_fx is not None else DEFAULT_FX_PATH,
    )
except (OSError, ValueError) as error:
    if isinstance(error, CSVNotice):
        st.session_state["data_notice"] = str(error)
    else:
        st.session_state["data_error"] = f"Could not load portfolio data: {error}"
    for key in ("holdings", "filtered_holdings", "fx_rates"):
        st.session_state.pop(key, None)
else:
    st.session_state["fx_rates"] = rates
    st.sidebar.caption(source_notice)
    with st.sidebar.expander("Valuation exchange rates and dates"):
        st.caption(
            f"Values convert through AED to {base_currency}. "
            "Each rate is AED per 1 unit of currency. Dates come from the FX CSV."
        )
        rate_details = rates[["currency", "rate_to_aed", "as_of"]].copy()
        rate_details["as_of"] = rate_details["as_of"].map(
            lambda value: f"{value.day} {value:%b %Y}"
        )
        st.table(rate_details.rename(columns={
            "currency": "Currency", "rate_to_aed": "Rate to AED", "as_of": "As of",
        }).set_index("Currency"))
    st.sidebar.header("Portfolio filters")
    selections = {}
    for column, label, all_label, key in (
        ("country", "Country", "All countries", "filter_country"),
        ("asset_type", "Asset type", "All types", "filter_asset_type"),
    ):
        values = sorted(
            (value for value in holdings[column].dropna().unique() if value),
            key=str.casefold,
        )
        options = [None, *values]
        if holdings[column].isna().any() or holdings[column].eq("").any():
            options.append("")
        if st.session_state.get(key) not in options:
            st.session_state[key] = None
        selections[column] = st.sidebar.selectbox(
            label,
            options,
            key=key,
            format_func=lambda value, all_label=all_label: (
                all_label if value is None else "Unspecified" if value == "" else value
            ),
        )
    st.sidebar.caption(
        "These filters apply to Overview, Holdings, Performance, Liabilities, and Readiness Check."
    )
    st.session_state["holdings"] = holdings
    st.session_state["filtered_holdings"] = filter_holdings(holdings, **selections)
    st.session_state["asset_type_colors"] = asset_type_colors(holdings)
    st.session_state["filter_caption"] = filter_caption(**selections)
    if selections["country"] is None and selections["asset_type"] is None:
        st.sidebar.caption("No filters selected — showing all holdings.")

st.sidebar.slider(
    "Benchmark return %", min_value=0, max_value=15, value=6,
    key="benchmark_return_pct",
)

page = st.navigation(
    [
        st.Page(home, title="Home", default=True),
        st.Page("pages/1_Overview.py", title="Overview", url_path="overview"),
        st.Page("pages/2_Holdings.py", title="Holdings", url_path="holdings"),
        st.Page("pages/3_Performance.py", title="Performance", url_path="performance"),
        st.Page("pages/4_Liabilities.py", title="Liabilities", url_path="liabilities"),
        st.Page("pages/5_Readiness_Check.py", title="Readiness Check", url_path="readiness"),
        st.Page("pages/6_Family_Wealth_Map.py", title="Family Wealth Map", url_path="wealth-map"),
    ]
)
if public_demo_enabled():
    st.warning(
        "Demo with fictional data. Please don't upload real financial information "
        "– nothing you enter is saved."
    )
if st.session_state.get("data_notice"):
    st.info(st.session_state["data_notice"])
else:
    page.run()
