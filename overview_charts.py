"""Reusable portfolio summaries, display formatting, and Plotly charts."""

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go

from ui import (
    CHART_COLORS, CHART_NEUTRAL, CHART_PRIMARY, DEBT_COLORS, MUTED, NAVY, style_chart,
)

PALETTE = CHART_COLORS


def asset_type_colors(holdings):
    types = holdings["asset_type"].fillna("").replace("", "Unspecified")
    # Types that only ever appear as debts share a quiet grey family, so the
    # main palette stays for assets.
    asset_types = set(types.loc[holdings["category"].eq("Asset")])
    colors, asset_index, debt_index = {}, 0, 0
    for name in sorted(types.unique()):
        if name in asset_types:
            colors[name] = PALETTE[asset_index % len(PALETTE)]
            asset_index += 1
        else:
            colors[name] = DEBT_COLORS[debt_index % len(DEBT_COLORS)]
            debt_index += 1
    return colors


def filter_caption(country=None, asset_type=None):
    country_label = "All countries" if country is None else country or "Unspecified"
    type_label = "All asset types" if asset_type is None else asset_type or "Unspecified"
    return f"Filters: {country_label} · {type_label}"


def portfolio_totals(holdings):
    assets = float(holdings.loc[holdings["category"].eq("Asset"), "current_value_base"].sum())
    liabilities = float(holdings.loc[holdings["category"].eq("Liability"), "current_value_base"].sum())
    return {
        "net_worth": float(holdings["signed_value_base"].sum()),
        "assets": assets,
        "liabilities": liabilities,
        "debt_ratio": liabilities / assets * 100 if assets > 0 else None,
    }


def compact_currency(value, currency):
    for divisor, suffix in ((1e12, "T"), (1e9, "B"), (1e6, "M"), (1e3, "K")):
        if abs(value) >= divisor:
            return f"{currency} {value / divisor:.2f}{suffix}"
    return f"{currency} {value:,.0f}"


def full_currency(value, currency):
    return f"{currency} {value:,.2f}"


def _chart_data(holdings):
    data = holdings.copy()
    for column in ("country", "asset_type", "item_name"):
        data[column] = data[column].fillna("").replace("", "Unspecified")
    return data


def assets_donut(holdings, currency, colors):
    data = _chart_data(holdings)
    data = data.loc[data["category"].eq("Asset") & data["current_value_base"].gt(0)]
    if data.empty:
        return None
    totals = data.groupby("asset_type", as_index=False)["current_value_base"].sum()
    figure = px.pie(
        totals, names="asset_type", values="current_value_base",
        color="asset_type", color_discrete_map=colors, hole=0.55,
    )
    figure.update_traces(
        textinfo="label+percent", sort=True,
        marker=dict(line=dict(color="#F6F7F9", width=2)),
        hovertemplate=(
            f"<b>%{{label}}</b><br>{currency} %{{value:,.2f}}<br>"
            "%{percent} of assets<extra></extra>"
        ),
    )
    figure.add_annotation(
        text=(
            f"<span style='color:{MUTED};font-size:13px'>Total assets</span><br>"
            f"<b>{compact_currency(float(totals['current_value_base'].sum()), currency)}</b>"
        ),
        showarrow=False, font=dict(size=20, color=NAVY),
    )
    figure.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=430)
    return style_chart(figure)


def country_net_worth(holdings, currency):
    data = _chart_data(holdings)
    totals = data.groupby("country", as_index=False)["signed_value_base"].sum()
    totals = totals.sort_values("signed_value_base")
    figure = px.bar(
        totals, x="signed_value_base", y="country", orientation="h",
        labels={"signed_value_base": f"Net worth ({currency})", "country": "Country"},
        color_discrete_sequence=[CHART_PRIMARY],
    )
    figure.update_traces(
        marker_cornerradius=4,
        hovertemplate=f"<b>%{{y}}</b><br>Net worth: {currency} %{{x:,.2f}}<extra></extra>",
    )
    figure.update_xaxes(zeroline=True, tickformat="~s")
    figure.update_yaxes(title_text=None, showgrid=False)
    figure.update_layout(margin=dict(t=20, b=20, l=10, r=10), height=430, bargap=0.35)
    return style_chart(figure)


def holdings_treemap(holdings, currency, colors):
    data = _chart_data(holdings)
    data = data.loc[data["current_value_base"].gt(0)]
    if data.empty:
        return None
    ids, labels, parents, values, tile_colors = [], [], [], [], []
    for country_index, (country, country_rows) in enumerate(data.groupby("country", sort=True)):
        country_id = f"country-{country_index}"
        ids.append(country_id)
        labels.append(country)
        parents.append("")
        values.append(float(country_rows["current_value_base"].sum()))
        tile_colors.append(CHART_NEUTRAL)
        for type_index, (asset_type, type_rows) in enumerate(country_rows.groupby("asset_type", sort=True)):
            type_id = f"{country_id}-type-{type_index}"
            ids.append(type_id)
            labels.append(asset_type)
            parents.append(country_id)
            values.append(float(type_rows["current_value_base"].sum()))
            tile_colors.append(colors[asset_type])
            for item_index, (_, row) in enumerate(type_rows.iterrows()):
                ids.append(f"{type_id}-item-{item_index}")
                labels.append(row["item_name"])
                parents.append(type_id)
                values.append(float(row["current_value_base"]))
                tile_colors.append(colors[asset_type])
    figure = go.Figure(go.Treemap(
        ids=ids, labels=labels, parents=parents, values=values,
        branchvalues="total",
        marker=dict(colors=tile_colors, line=dict(color="#F6F7F9", width=1)),
        textinfo="label",
        hovertemplate=f"<b>%{{label}}</b><br>{currency} %{{value:,.2f}}<extra></extra>",
    ))
    figure.update_layout(margin=dict(t=10, b=10, l=0, r=0), height=520)
    return style_chart(figure)
