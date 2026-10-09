"""Filtered family readiness score, issues, and fully ready items."""

import plotly.graph_objects as go
import streamlit as st

from readiness import SEVERITIES, check_readiness, readiness_label

st.title("Readiness Check")
if st.session_state.get("data_error"):
    st.error(st.session_state["data_error"])
    st.stop()

holdings = st.session_state["filtered_holdings"]
st.caption(st.session_state["filter_caption"])
if holdings.empty:
    st.info("No holdings match these filters")
    st.stop()

items, issues = check_readiness(holdings)
score = float(items["score"].mean())
label = readiness_label(score)
gauge = go.Figure(go.Indicator(
    mode="gauge+number",
    value=score,
    number={"suffix": " / 100", "valueformat": ".1f"},
    gauge={
        "axis": {"range": [0, 100], "tickvals": [0, 70, 90, 100]},
        "bar": {"color": "#1F74AD"},
        "steps": [
            {"range": [0, 70], "color": "#FADBD8"},
            {"range": [70, 90], "color": "#FDECC8"},
            {"range": [90, 100], "color": "#D9EEE3"},
        ],
    },
))
gauge.update_layout(
    title={
        "text": f"Readiness Score — {label}",
        "x": 0.5, "xanchor": "center", "y": 0.98, "yanchor": "top",
    },
    height=320, margin=dict(t=60, b=10, l=30, r=30),
)
st.plotly_chart(gauge, width="stretch", key="readiness_score")

for column, severity in zip(st.columns(4), SEVERITIES):
    column.metric(
        severity, int(issues["severity"].eq(severity).sum()), border=True,
    )

st.subheader("Issues")
st.dataframe(
    issues,
    column_config={
        "item_name": "Item name", "issue": "Issue", "severity": "Severity",
        "suggested_fix": "Suggested fix",
    },
    width="stretch", hide_index=True,
)

st.subheader("Fully ready")
ready_items = items.loc[items["issue_count"].eq(0), "item_name"]
if ready_items.empty:
    st.caption("No items are fully ready yet.")
else:
    for item_name in ready_items:
        st.text(f"• {item_name}")
