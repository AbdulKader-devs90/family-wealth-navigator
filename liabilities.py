"""Liability-only calculations and grouped balance chart."""

from math import isfinite

import plotly.graph_objects as go


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
        ("purchase_value_base", "Original amount", "#61A9BD"),
        ("current_value_base", "Outstanding balance", "#1F74AD"),
    ):
        figure.add_trace(go.Bar(
            name=label, y=liabilities["item_name"], x=liabilities[column],
            orientation="h", marker_color=color,
            hovertemplate=f"%{{y}}<br>{currency} %{{x:,.2f}}<extra>{label}</extra>",
        ))
    figure.update_layout(
        barmode="group",
        xaxis_title=f"Amount ({currency})",
        yaxis_title="Liability",
        height=max(360, len(liabilities) * 70 + 100),
        margin=dict(t=20, b=20, l=10, r=10),
    )
    return figure
