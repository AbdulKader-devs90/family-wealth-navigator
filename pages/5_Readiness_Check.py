"""Family readiness score, quick wins, and a per-item checklist."""

from html import escape

import pandas as pd
import plotly.graph_objects as go
import streamlit as st

from readiness import SEVERITIES, check_readiness, readiness_label
from ui import TEAL, icon_html, pill, style_chart, type_icon

# Plain-language priority, pill tone, and KPI icon for each readiness level.
PRIORITIES = {
    "Critical": ("Fix now", "bad", "error"),
    "High": ("Fix first", "first", "priority_high"),
    "Medium": ("Worth doing", "worth", "task_alt"),
    "Low": ("Nice to have", "quiet", "low_priority"),
}
# Checklist label and quick-win wording for each issue readiness.py can raise.
CHECKS = (
    ("No nominee", "Nominee", "nominee"),
    ("No documents location", "Documents location", "documents"),
    ("No contact person", "Contact", "contact"),
    ("No access instructions", "Access steps", "access steps"),
    ("Value is out of date", "Value up to date", None),
)

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
        "bar": {"color": TEAL},
        "steps": [
            {"range": [0, 70], "color": "#F6D9D8"},
            {"range": [70, 90], "color": "#F8E7C2"},
            {"range": [90, 100], "color": "#D5ECE9"},
        ],
    },
))
gauge.update_layout(
    title={
        "text": f"Readiness score — {label}",
        "x": 0.5, "xanchor": "center", "y": 0.98, "yanchor": "top",
    },
    height=320, margin=dict(t=60, b=10, l=30, r=30),
)
st.plotly_chart(style_chart(gauge), width="stretch", key="readiness_score")

ready_count = int(items["issue_count"].eq(0).sum())
st.markdown(
    f"**{ready_count} of {len(items)} items are fully ready.** " + (
        "Fixing the items below would make it much easier for your family to find everything."
        if ready_count < len(items) else
        "Your family has what they need to find everything."
    )
)

for column, level in zip(st.columns(4), SEVERITIES):
    name, _, icon = PRIORITIES[level]
    column.metric(
        f":material/{icon}: {name}", int(issues["severity"].eq(level).sum()), border=True,
    )


def join_words(words):
    return words[0] if len(words) == 1 else f"{', '.join(words[:-1])} and {words[-1]}"


def fix_summary(found):
    """One short instruction covering everything an item is missing."""
    steps = []
    additions = [phrase for issue, _, phrase in CHECKS if phrase and issue in found]
    if additions:
        steps.append(f"add {join_words(additions)}")
    if "Value is out of date" in found:
        steps.append("update its value")
    if any(issue not in known_issues for issue in found):
        steps.append("remove the stored password or PIN")
    return join_words(steps)


known_issues = {issue for issue, _, _ in CHECKS}
order = {level: index for index, level in enumerate(SEVERITIES)}
todo = []
for position, (_, holding) in enumerate(holdings.iterrows()):
    item = items.iloc[position]
    if item["issue_count"] == 0:
        continue
    # Check this row on its own so two items sharing a name keep separate lists.
    _, own_issues = check_readiness(holdings.iloc[[position]])
    todo.append({
        "name": str(item["item_name"]).strip() or "Unnamed",
        "holding": holding,
        "score": float(item["score"]),
        "gain": (100 - float(item["score"])) / len(items),
        "found": set(own_issues["issue"]),
        "level": min(own_issues["severity"], key=order.get),
    })
todo.sort(key=lambda entry: entry["gain"], reverse=True)

if todo:
    with st.container(border=True, key="quick_wins"):
        st.subheader(":material/bolt: Quick wins")
        st.html('<ol class="fwn-quickwins">' + "".join(
            f"<li><b>{escape(entry['name'])}</b> – {escape(fix_summary(entry['found']))} "
            f"{pill(f'+{entry["gain"]:.1f} points', 'good')}</li>"
            for entry in todo[:3]
        ) + "</ol>")
        st.caption("Points show how much each fix would raise your overall score.")


def checklist_card(entry):
    holding, found = entry["holding"], entry["found"]
    lines = []
    for issue, check_label, _ in CHECKS:
        if issue == "No nominee" and holding["category"] != "Asset":
            continue
        done = issue not in found
        lines.append(
            f'<li class="{"fwn-done" if done else "fwn-todo"}">'
            f'{icon_html("check_box" if done else "check_box_outline_blank")}'
            f"{check_label}</li>"
        )
    if found - known_issues:
        lines.append(
            f'<li class="fwn-todo">{icon_html("check_box_outline_blank")}'
            "Remove stored password or PIN – say where to find it instead</li>"
        )
    name, tone, _ = PRIORITIES[entry["level"]]
    is_debt = holding["category"] == "Liability"
    return (
        '<div class="fwn-card">'
        '<div class="fwn-card-head">'
        f'{icon_html(type_icon(holding["asset_type"], holding["category"]), "fwn-icon-tile" + (" fwn-debt" if is_debt else ""))}'
        f'<div><div class="fwn-card-title">{escape(entry["name"])}</div></div>'
        f"{pill(name, tone)}"
        "</div>"
        "<div>"
        '<div class="fwn-row fwn-row-apart fwn-card-sub">'
        f'<span>Item score {entry["score"]:.0f} / 100</span>'
        f'<span>+{entry["gain"]:.1f} points if fixed</span></div>'
        f'<div class="fwn-bar" role="img" aria-label="Item score {entry["score"]:.0f} out of 100">'
        f'<span style="width:{entry["score"]:.0f}%"></span></div>'
        "</div>"
        f'<ul class="fwn-checklist">{"".join(lines)}</ul>'
        "</div>"
    )


if todo:
    st.subheader("What to fix")
    st.html(
        '<div class="fwn-grid fwn-grid-wide">'
        + "".join(checklist_card(entry) for entry in todo) + "</div>"
    )

st.subheader("Fully ready")
ready_items = items.loc[items["issue_count"].eq(0), "item_name"]
if ready_items.empty:
    st.caption("Nothing is fully ready yet – the quick wins above are the fastest way to start.")
else:
    st.html('<div class="fwn-chips">' + "".join(
        f'<span class="fwn-chip fwn-good">{icon_html("check_circle")}{escape(str(name))}</span>'
        for name in ready_items
    ) + "</div>")

if not issues.empty:
    with st.expander("See all details", icon=":material/list:"):
        details = issues.rename(columns={"severity": "priority"})
        details["priority"] = details["priority"].map(
            lambda level: PRIORITIES[level][0]
        )
        st.dataframe(
            details,
            column_config={
                "item_name": "Item", "issue": "What's missing", "priority": "Priority",
                "suggested_fix": "Suggested fix",
            },
            width="stretch", hide_index=True,
        )
