"""Asset-only return calculations and the Performance chart."""

import plotly.express as px

LABEL_COLORS = {
    "Performing": "#0E9C8F",
    "Stagnant": "#E0A019",
    "Losing": "#D8524F",
    "Cash – not rated": "#9AA5B1",
}


def asset_performance(holdings, benchmark):
    assets = holdings.loc[holdings["category"].eq("Asset")].copy()
    purchase = assets["purchase_value_base"]
    current = assets["current_value_base"]
    assets["gain_loss_base"] = current - purchase
    assets["gain_pct"] = (current - purchase) / purchase.where(purchase.gt(0)) * 100
    assets["years_held"] = (
        assets["last_valued_on"] - assets["purchase_date"]
    ).dt.days / 365.25

    years = assets["years_held"]
    calculable = (
        purchase.gt(0) & purchase.lt(float("inf"))
        & current.ge(0) & current.lt(float("inf")) & years.gt(0)
    )
    assets["cagr_pct"] = (
        (current.where(calculable) / purchase.where(calculable))
        ** (1 / years.where(calculable)) - 1
    ) * 100
    assets["cagr_pct"] = assets["cagr_pct"].replace(
        [float("inf"), -float("inf")], float("nan")
    )
    cagr = assets["cagr_pct"]
    assets["label"] = "N/A"
    assets.loc[cagr.ge(benchmark), "label"] = "Performing"
    assets.loc[cagr.ge(0) & cagr.lt(benchmark), "label"] = "Stagnant"
    assets.loc[cagr.lt(0), "label"] = "Losing"
    cash_unrated = (
        assets["asset_type"].eq("Cash")
        & assets["interest_rate_pct"].isna()
        & cagr.notna()
    )
    assets.loc[cash_unrated, "label"] = "Cash – not rated"
    return assets


def performance_chart(assets, benchmark):
    chart_rows = assets.loc[assets["cagr_pct"].notna()].sort_values("cagr_pct")
    if chart_rows.empty:
        return None
    figure = px.bar(
        chart_rows, x="cagr_pct", y="item_name", color="label",
        orientation="h", color_discrete_map=LABEL_COLORS,
        category_orders={"label": list(LABEL_COLORS)},
        labels={"cagr_pct": "CAGR %", "item_name": "Asset", "label": "Label"},
    )
    figure.update_yaxes(
        categoryorder="array", categoryarray=chart_rows["item_name"].tolist()
    )
    figure.update_xaxes(ticksuffix="%")
    figure.update_traces(
        hovertemplate="%{y}<br>CAGR: %{x:.2f}%<extra>%{fullData.name}</extra>"
    )
    figure.add_vline(
        x=benchmark, line_dash="dash", line_color="#5B6B7F",
        annotation_text=f"Benchmark {benchmark}%",
        annotation_position="top",
    )
    figure.update_layout(
        height=max(360, len(chart_rows) * 28 + 120),
        margin=dict(t=40, b=20, l=10, r=10),
    )
    return figure
