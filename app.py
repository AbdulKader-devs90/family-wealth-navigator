"""Home and shared navigation/settings for Family Wealth Navigator."""

import streamlit as st
from checkin import public_demo_enabled

from data_loader import (
    CSVNotice, DEFAULT_FX_PATH, SUPPORTED_BASE_CURRENCIES, filter_holdings, load_data,
)
from overview_charts import asset_type_colors, filter_caption
from ui import ASSETS_DIR, apply_branding, sidebar_footer

st.set_page_config(
    page_title="Family Wealth Navigator", page_icon=str(ASSETS_DIR / "icon.svg"),
    layout="wide",
)
apply_branding()


FEATURES = (
    (
        "hub", "See everything in one place",
        "Property, gold, savings, investments and debts across countries, "
        "shown together in one currency.",
        ("overview", "holdings"),
    ),
    (
        "insights", "Know what's working",
        "See which assets beat your benchmark, which are standing still, "
        "and which debt costs you the most.",
        ("performance", "liabilities"),
    ),
    (
        "family_restroom", "Keep your family ready",
        "Find missing nominees, contacts and documents, then create an encrypted "
        "guide your family can open if you're ever unreachable.",
        ("readiness", "wealth_map"),
    ),
)


def home():
    with st.container(key="hero"):
        st.html('<div class="fwn-eyebrow">Your family\'s wealth, organised</div>')
        st.title("Family Wealth Navigator")
        st.write(
            "One clear view of everything your family owns and owes, "
            "across countries and currencies."
        )
        with st.container(horizontal=True):
            if st.button(
                "Get started", type="primary", icon=":material/arrow_forward:",
                key="hero_overview",
            ):
                st.switch_page(PAGES["overview"])
            if st.button(
                "Create your Family Wealth Map", icon=":material/family_restroom:",
                key="hero_wealth_map",
            ):
                st.switch_page(PAGES["wealth_map"])
    if st.session_state.get("data_error"):
        st.error(st.session_state["data_error"])

    for index, (column, (icon, heading, text, links)) in enumerate(
        zip(st.columns(3), FEATURES)
    ):
        with column.container(border=True, height="stretch", key=f"feature_card_{index}"):
            with st.container(key=f"feature_icon_{index}"):
                st.markdown(f":material/{icon}:")
            st.subheader(heading)
            st.write(text)
            for name in links:
                st.page_link(PAGES[name])
    st.caption(
        ":material/lock: No account and no database. Files you upload stay in "
        "this browser session."
    )


st.sidebar.header("Data settings")
base_currency = st.sidebar.selectbox(
    "Base currency", SUPPORTED_BASE_CURRENCIES, key="base_currency"
)
uploaded_holdings = st.sidebar.file_uploader(
    "Upload your holdings (CSV)",
    type=["csv"],
    key="holdings_upload",
    help="Use the same columns as the sample file. Remove the upload to go back to the sample data.",
)
uploaded_fx = st.sidebar.file_uploader(
    "Upload exchange rates (CSV, optional)",
    type=["csv"],
    key="fx_upload",
    help=(
        "Required columns: currency, rate_to_aed, as_of. Rates are AED per "
        "1 unit of currency (AED must equal 1); use dates such as 2026-09-30. Include every "
        "holdings currency and your base currency. Remove the upload to restore demo rates."
    ),
)

if public_demo_enabled():
    st.sidebar.caption(
        "Public demo: please don't upload real financial information. "
        "Nothing you enter is saved."
    )

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
    with st.sidebar.expander("Valuation exchange rates and dates"):
        st.caption(
            f"Values convert through AED to {base_currency}. "
            "Each rate is AED per 1 unit of currency. Rates are fixed, not live; "
            "dates come from the FX CSV."
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

sidebar_footer(
    "Sample data – fictional family" if uploaded_holdings is None
    else "Your uploaded data – not saved"
)

PAGES = {
    "home": st.Page(home, title="Home", icon=":material/home:", default=True),
    "overview": st.Page(
        "pages/1_Overview.py", title="Overview",
        icon=":material/space_dashboard:", url_path="overview",
    ),
    "holdings": st.Page(
        "pages/2_Holdings.py", title="Holdings",
        icon=":material/account_balance_wallet:", url_path="holdings",
    ),
    "performance": st.Page(
        "pages/3_Performance.py", title="Performance",
        icon=":material/trending_up:", url_path="performance",
    ),
    "liabilities": st.Page(
        "pages/4_Liabilities.py", title="Liabilities",
        icon=":material/credit_card:", url_path="liabilities",
    ),
    "readiness": st.Page(
        "pages/5_Readiness_Check.py", title="Readiness Check",
        icon=":material/fact_check:", url_path="readiness",
    ),
    "wealth_map": st.Page(
        "pages/6_Family_Wealth_Map.py", title="Family Wealth Map",
        icon=":material/family_restroom:", url_path="wealth-map",
    ),
}
page = st.navigation({
    "": [PAGES["home"]],
    "Portfolio": [
        PAGES["overview"], PAGES["holdings"], PAGES["performance"], PAGES["liabilities"],
    ],
    "Family": [PAGES["readiness"], PAGES["wealth_map"]],
})
if st.session_state.get("data_notice"):
    st.info(st.session_state["data_notice"])
else:
    page.run()
