"""Readiness rules and scoring for every filtered asset and liability."""

import re

import pandas as pd

SEVERITIES = ("Critical", "High", "Medium", "Low")
DEDUCTIONS = {"High": 30, "Medium": 15, "Low": 5}
SECRET_MARKERS = re.compile(r"\b(?:password|pin|pwd|seed):", re.IGNORECASE)
LOWERCASE_SEQUENCE = re.compile(
    r"(?<![A-Za-z0-9_])(?:[a-z]+\s+){11,}[a-z]+(?![A-Za-z0-9_])"
)
SAFE_REFERENCE = re.compile(r"\b(?:password manager|sealed envelope)\b", re.IGNORECASE)


def _blank(value):
    return pd.isna(value) or not str(value).strip()


def contains_secret(value):
    if _blank(value):
        return False
    text = str(value)
    if SECRET_MARKERS.search(text):
        return True
    # A benign storage-location sentence is not a seed phrase, regardless of
    # capitalization. Separate word sequences elsewhere in the field still count.
    for match in LOWERCASE_SEQUENCE.finditer(text):
        before = re.split(r"[.!?;\n]", text[:match.start()])[-1]
        after = re.split(r"[.!?;\n]", text[match.end():], maxsplit=1)[0]
        if not SAFE_REFERENCE.search(before + match.group() + after):
            return True
    return False


def readiness_label(score):
    if score >= 90:
        return "Ready"
    if score >= 70:
        return "Needs work"
    return "At risk"


def check_readiness(holdings):
    cutoff = pd.Timestamp.today().normalize() - pd.DateOffset(months=12)
    item_results = []
    issue_results = []
    for _, item in holdings.iterrows():
        issues = []

        def add_issue(issue, severity, suggested_fix):
            issues.append({
                "item_name": item["item_name"],
                "issue": issue,
                "severity": severity,
                "suggested_fix": suggested_fix,
            })

        if item["category"] == "Asset" and _blank(item["nominee"]):
            add_issue("No nominee", "High", "Record a nominee for this asset.")
        if _blank(item["contact_person"]):
            add_issue("No contact person", "Medium", "Record who the family should contact.")
        if _blank(item["documents_location"]):
            add_issue(
                "No documents location", "High",
                "Record where the relevant documents can be found.",
            )
        if _blank(item["access_instructions"]):
            add_issue(
                "No access instructions", "High",
                "Describe how to gain access without recording secrets.",
            )
        valued_on = item["last_valued_on"]
        if pd.notna(valued_on) and valued_on < cutoff:
            add_issue(
                "Value is out of date", "Low",
                "Update the current value and last valuation date.",
            )
        if contains_secret(item["access_instructions"]) or contains_secret(item["notes"]):
            add_issue(
                "Never store secrets here – say WHERE to find them instead", "Critical",
                "Remove the secret and refer to its location, such as a password manager or sealed envelope.",
            )

        score = (
            0 if any(issue["severity"] == "Critical" for issue in issues)
            else max(0, 100 - sum(DEDUCTIONS[issue["severity"]] for issue in issues))
        )
        item_results.append({
            "item_name": item["item_name"], "score": score, "issue_count": len(issues),
        })
        issue_results.extend(issues)

    items = pd.DataFrame(item_results, columns=["item_name", "score", "issue_count"])
    issues = pd.DataFrame(
        issue_results, columns=["item_name", "issue", "severity", "suggested_fix"]
    )
    order = {severity: index for index, severity in enumerate(SEVERITIES)}
    issues = issues.sort_values(
        "severity", key=lambda values: values.map(order), kind="stable", ignore_index=True
    )
    return items, issues
