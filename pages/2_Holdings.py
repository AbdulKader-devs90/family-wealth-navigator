"""Portfolio cards by country, with search, category filter, and a detailed table."""

from html import escape

import pandas as pd
import streamlit as st

from data_loader import filter_holdings
from liabilities import liability_data
from overview_charts import compact_currency
from performance import asset_performance
from ui import chips, icon_html, page_header, pill, type_icon

page_header("Holdings", "Everything you own and owe, grouped by country.")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

holdings = st.session_state["filtered_holdings"]
currency = st.session_state["base_currency"]
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


def text(value):
    return "" if pd.isna(value) else str(value).strip()


def count(number, singular, plural):
    return f"{number} {singular if number == 1 else plural}"


def money(value):
    return "—" if pd.isna(value) else compact_currency(float(value), currency)


def holding_card(row, gain_pct, repaid_pct):
    is_debt = row["category"] == "Liability"
    asset_type = text(row["asset_type"]) or "Unspecified"
    place = " · ".join(part for part in (asset_type, text(row["city"])) if part)

    if is_debt:
        change = "" if pd.isna(repaid_pct) else pill(f"{repaid_pct:.0f}% repaid")
    elif pd.isna(gain_pct):
        change = ""
    elif gain_pct > 0:
        change = pill(f"▲ {gain_pct:.1f}%", "good")
    elif gain_pct < 0:
        change = pill(f"▼ {abs(gain_pct):.1f}%", "bad")
    else:
        change = pill("0.0%")

    local = (
        "" if pd.isna(row["current_value"])
        else f"{text(row['currency'])} {row['current_value']:,.0f}"
    )
    badges = [pill("Debt")] if is_debt else []
    if text(row["ownership"]):
        badges.append(pill(text(row["ownership"])))
    if not is_debt:
        badges.append(
            pill("Nominee", "good", icon="check") if text(row["nominee"])
            else pill("No nominee", "first")
        )
    return (
        '<div class="fwn-card">'
        '<div class="fwn-card-head">'
        f'{icon_html(type_icon(row["asset_type"], row["category"]), "fwn-icon-tile" + (" fwn-debt" if is_debt else ""))}'
        f'<div><div class="fwn-card-title">{escape(text(row["item_name"]) or "Unnamed")}</div>'
        f'<div class="fwn-card-sub">{escape(place)}</div></div>'
        "</div>"
        f'<div><div class="fwn-card-value">{escape(money(row["current_value_base"]))}{change}</div>'
        f'<div class="fwn-card-sub">{escape(local)}{" owed" if is_debt and local else ""}</div></div>'
        f'<div class="fwn-row">{"".join(badges)}</div>'
        "</div>"
    )


if not filtered_holdings.empty:
    is_asset = filtered_holdings["category"].eq("Asset")
    countries = filtered_holdings["country"].fillna("").replace("", "Unspecified")
    summary = [
        ("account_balance_wallet", count(len(filtered_holdings), "holding", "holdings")),
        ("public", count(countries.nunique(), "country", "countries")),
    ]
    if is_asset.any():
        asset_types = filtered_holdings.loc[is_asset, "asset_type"].fillna("")
        summary.append(("category", count(asset_types.nunique(), "asset type", "asset types")))
    if (~is_asset).any():
        summary.append(("credit_card", count(int((~is_asset).sum()), "debt", "debts")))
    st.html(chips(summary))
st.caption(
    f"Showing {len(filtered_holdings)} of {len(st.session_state['holdings'])} holdings"
)

if filtered_holdings.empty:
    st.info("No holdings match these filters")
    st.caption("Try a shorter search, or clear the filters in the sidebar.")
else:
    gains = asset_performance(
        filtered_holdings, st.session_state["benchmark_return_pct"]
    )["gain_pct"]
    repaid = liability_data(filtered_holdings)["repaid_pct"]
    groups = sorted(
        filtered_holdings.groupby(countries),
        key=lambda group: group[1]["signed_value_base"].sum(), reverse=True,
    )
    for country, rows in groups:
        net_worth = float(rows["signed_value_base"].sum())
        label = (
            f"**{country}** · {count(len(rows), 'holding', 'holdings')} · "
            f"net worth {compact_currency(net_worth, currency)}"
        )
        with st.expander(label, expanded=True, icon=":material/public:"):
            ordered = rows.sort_values(
                ["category", "current_value_base"], ascending=[True, False]
            )
            st.html('<div class="fwn-grid">' + "".join(
                holding_card(row, gains.get(index), repaid.get(index))
                for index, row in ordered.iterrows()
            ) + "</div>")

    with st.expander("Detailed table", icon=":material/table_rows:"):
        text_columns = filtered_holdings.select_dtypes(exclude=["number", "datetime"]).columns
        table = filtered_holdings.copy()
        table[text_columns] = table[text_columns].astype("object").fillna("")
        headers = {
            column: column.replace("_", " ").capitalize() for column in table.columns
        }
        headers.update({
            "item_id": "ID", "item_name": "Item", "asset_type": "Type",
            "held_with": "Held with", "account_ref": "Account reference",
            "nominee_relation": "Nominee relation", "contact_person": "Contact person",
            "contact_email": "Contact email", "documents_location": "Documents location",
            "access_instructions": "Access instructions",
            "currency": "Local currency",
            "quantity": st.column_config.NumberColumn("Quantity", format="localized"),
            "interest_rate_pct": st.column_config.NumberColumn("Interest rate", format="%.2f%%"),
            "current_value": st.column_config.NumberColumn(
                "Current value (local)", format="accounting"),
            "purchase_value": st.column_config.NumberColumn(
                "Purchase value (local)", format="accounting"),
            "current_value_base": st.column_config.NumberColumn(
                f"Current value ({currency})", format="accounting"),
            "purchase_value_base": st.column_config.NumberColumn(
                f"Purchase value ({currency})", format="accounting"),
            "signed_value_base": st.column_config.NumberColumn(
                f"Net value ({currency})", format="accounting",
                help="Assets count as positive, debts as negative.",
            ),
            "purchase_date": st.column_config.DateColumn("Purchase date", format="D MMM YYYY"),
            "last_valued_on": st.column_config.DateColumn("Last valued on", format="D MMM YYYY"),
        })
        leading = [
            "item_name", "category", "asset_type", "country", "city",
            "current_value_base", "purchase_value_base", "signed_value_base",
            "currency", "current_value", "purchase_value",
        ]
        st.dataframe(
            table, column_config=headers, width="stretch", hide_index=True,
            column_order=leading + [c for c in table.columns if c not in leading],
        )
