"""Liability-only calculations and grouped balance chart."""

from math import isfinite

import plotly.graph_objects as go

from ui import CHART_PRIMARY, CHART_SECONDARY, style_chart


def liability_data(holdings):
    liabilities = holdings.loc[holdings["category"].eq("Liability")].copy()
    original = liabilities["purchase_value_base"]
    outstanding = liabilities["current_value_base"]
    liabilities["repaid_pct"] = (
        (original - outstanding) / original.where(original.gt(0)) * 100
    )
    return liabilities


def debt_summary(liabilities):
    balances = liabilities["current_value_base"]
    total = float(balances.sum(skipna=False))
    weighted_rate = None
    if total > 0:
        rate = float(
            (balances * liabilities["interest_rate_pct"]).sum(skipna=False) / total
        )
        if isfinite(rate):
            weighted_rate = rate
    return total, len(liabilities), weighted_rate


def liability_chart(liabilities, currency):
    figure = go.Figure()
    for column, label, color in (
        ("purchase_value_base", "Original amount", CHART_SECONDARY),
        ("current_value_base", "Outstanding balance", CHART_PRIMARY),
    ):
        figure.add_trace(go.Bar(
            name=label, y=liabilities["item_name"], x=liabilities[column],
            orientation="h", marker_color=color, marker_cornerradius=4,
            hovertemplate=f"<b>%{{y}}</b><br>{label}: {currency} %{{x:,.2f}}<extra></extra>",
        ))
    figure.update_layout(
        barmode="group",
        xaxis_title=f"Amount ({currency})",
        yaxis=dict(showgrid=False),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
        height=max(360, len(liabilities) * 70 + 100),
        margin=dict(t=40, b=20, l=10, r=10),
    )
    return style_chart(figure)
