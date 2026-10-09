"""Build the family guide and encrypt it in memory with AES-256."""

from io import BytesIO
from pathlib import Path
import re

from fpdf import FPDF
from fpdf.enums import XPos, YPos
from fpdf.fonts import FontFace
import pandas as pd
from pypdf import PdfWriter

from overview_charts import full_currency, portfolio_totals
from performance import asset_performance

FONT_DIR = Path(__file__).resolve().parent / "assets" / "fonts"


def _text(value, default="Not recorded"):
    if pd.isna(value) or not str(value).strip():
        return default
    return str(value).strip()


class WealthMapPDF(FPDF):
    def footer(self):
        self.set_y(-14)
        self.set_font("DejaVu", size=8)
        self.cell(
            0, 5,
            f"Confidential – lists where things are, never passwords.  |  {self.page_no()}",
            align="C",
        )


def _paragraph(pdf, text, bold=False, size=10):
    pdf.set_font("DejaVu", "B" if bold else "", size)
    pdf.multi_cell(
        w=0, h=5.5, text=str(text),
        new_x=XPos.LMARGIN, new_y=YPos.NEXT,
    )


def _heading(pdf, text):
    if pdf.get_y() > pdf.h - 45:
        pdf.add_page()
    pdf.ln(4)
    _paragraph(pdf, text, bold=True, size=13)
    pdf.ln(2)


def _where(item):
    return ", ".join(
        _text(item[column]) for column in ("country", "city", "held_with")
        if _text(item[column]) != "Not recorded"
    ) or "Location not recorded"


def _reasons(item, home_countries):
    reasons = []
    if _text(item["ownership"]).casefold() == "sole":
        reasons.append("Sole name")
    country = _text(item["country"], "")
    if country and country.casefold() not in {value.casefold() for value in home_countries}:
        reasons.append("Held abroad")
    if (
        _text(item["city"]).casefold() == "online"
        or _text(item["asset_type"]).casefold() == "crypto"
    ):
        reasons.append("Digital")
    details = f"{_text(item['notes'], '')} {_text(item['access_instructions'], '')}".casefold()
    for keywords, reason in (
        (("insurance",), "Linked insurance"),
        (("sealed", "envelope"), "Sealed / envelope instructions"),
        (("vault", "locker"), "Vault / locker"),
        (("wallet", "recovery"), "Wallet / recovery details"),
    ):
        if any(keyword in details for keyword in keywords):
            reasons.append(reason)
    return reasons


def _end_date(notes):
    match = re.search(
        r"\b(?:ends?|matures?)\b\s*(?:(?:on|in)\s+)?([^.;\n]+)",
        _text(notes, ""), re.IGNORECASE,
    )
    return match.group(1).strip() if match else "Not recorded"


def build_wealth_map(
    holdings, base_currency, owner_name, family_member_name, home_countries,
    personal_message, password, benchmark=6,
):
    """Return encrypted PDF bytes; never write PDF data or the password to disk."""
    if len(password) < 8:
        raise ValueError("The PDF password must be at least 8 characters.")
    owner = owner_name.strip() or "the owner"
    family_member = family_member_name.strip() or "the family"
    pdf = WealthMapPDF()
    pdf.set_margins(12, 12, 12)
    pdf.set_auto_page_break(auto=True, margin=22)
    pdf.add_font("DejaVu", fname=str(FONT_DIR / "DejaVuSans.ttf"))
    pdf.add_font("DejaVu", style="B", fname=str(FONT_DIR / "DejaVuSans-Bold.ttf"))
    pdf.add_page()
    pdf.set_title("Family Wealth Map")
    _paragraph(pdf, "Family Wealth Map", bold=True, size=20)
    _paragraph(pdf, f"A practical guide for {family_member} when {owner} is not available.")
    _paragraph(pdf, f"Home countries: {', '.join(home_countries) or 'Not recorded'}")
    _paragraph(pdf, f"Values are shown in {base_currency}.")

    _heading(pdf, "1. Our wealth at a glance")
    totals = portfolio_totals(holdings)
    for key, label in (("net_worth", "Net worth"), ("assets", "Assets"), ("liabilities", "Liabilities")):
        _paragraph(pdf, f"{label}: {full_currency(totals[key], base_currency)}")
    countries = holdings["country"].fillna("").replace("", "Unspecified")
    pdf.set_font("DejaVu", size=9)
    with pdf.table(
        col_widths=(1.3, 1.1, 1.1, 1.1), line_height=6,
        headings_style=FontFace(emphasis="BOLD"),
    ) as table:
        header = table.row()
        for value in ("Country", "Assets", "Liabilities", "Net worth"):
            header.cell(value)
        for country, rows in holdings.groupby(countries, sort=True):
            country_totals = portfolio_totals(rows)
            row = table.row()
            row.cell(country)
            for key in ("assets", "liabilities", "net_worth"):
                row.cell(full_currency(country_totals[key], base_currency))
    performance = asset_performance(holdings, benchmark)
    for label in ("Performing", "Stagnant", "Losing"):
        rows = performance.loc[performance["label"].eq(label)]
        _paragraph(
            pdf, f"{label}: {len(rows)} assets; current value "
            f"{full_currency(rows['current_value_base'].sum(), base_currency)} "
            f"(benchmark {benchmark:g}%).",
        )

    _heading(pdf, "2. Things you may not know about")
    listed = False
    for _, item in holdings.iterrows():
        reasons = _reasons(item, home_countries)
        if reasons:
            listed = True
            _paragraph(pdf, f"• {_text(item['item_name'])} ({_text(item['asset_type'])}) — "
                       f"{_where(item)} — {', '.join(reasons)}.")
    if not listed:
        _paragraph(pdf, "No items match these conditions.")

    _heading(pdf, "3. Where everything is kept")
    locations = holdings["documents_location"].map(
        lambda value: _text(value, "Location not recorded")
    )
    for location, rows in holdings.groupby(locations, sort=True):
        _paragraph(pdf, f"{location}: {', '.join(rows['item_name'].map(_text))}.")

    _heading(pdf, "4. Things that keep running")
    debts = holdings.loc[holdings["category"].eq("Liability")]
    recurring_mask = (
        holdings["category"].eq("Asset")
        & holdings["notes"].fillna("").str.contains(
            r"rent|sip|per\s+month|matures|ends", case=False, regex=True,
        )
    )
    recurring = holdings.loc[recurring_mask]
    for _, item in debts.iterrows():
        rate = (
            f"{item['interest_rate_pct']:g}%"
            if pd.notna(item["interest_rate_pct"]) else "Not recorded"
        )
        _paragraph(pdf, f"• {_text(item['item_name'])} — lender: {_text(item['held_with'])}; "
                   f"balance: {full_currency(item['current_value_base'], base_currency)}; "
                   f"rate: {rate}; end date from notes: {_end_date(item['notes'])}.")
    for _, item in recurring.iterrows():
        _paragraph(pdf, f"• {_text(item['item_name'])} — {_text(item['notes'])}")
    if debts.empty and recurring.empty:
        _paragraph(pdf, "No liabilities or recurring items recorded.")

    _heading(pdf, "5. Who to call for what")
    contacts = {}
    for _, item in holdings.iterrows():
        name, email = _text(item["contact_person"], ""), _text(item["contact_email"], "")
        if name or email:
            contacts.setdefault((name, email), []).append(_text(item["item_name"]))
    for (name, email), names in contacts.items():
        _paragraph(pdf, f"{name or 'Name not recorded'} — {email or 'Email not recorded'}: "
                   f"{', '.join(dict.fromkeys(names))}.")
    if not contacts:
        _paragraph(pdf, "No contacts recorded.")

    _heading(pdf, "6. Full list of holdings")
    for country, rows in holdings.groupby(countries, sort=True):
        _paragraph(pdf, country, bold=True, size=12)
        for _, item in rows.iterrows():
            pdf.ln(2)
            _paragraph(pdf, _text(item["item_name"]), bold=True)
            _paragraph(pdf, f"Type: {_text(item['asset_type'])} ({_text(item['category'])})")
            _paragraph(pdf, f"Where held: {_where(item)}")
            _paragraph(pdf, f"Account ref: {_text(item['account_ref'])}")
            _paragraph(pdf, f"Ownership: {_text(item['ownership'])}")
            _paragraph(pdf, f"Nominee: {_text(item['nominee'])}")
            _paragraph(pdf, f"Contact: {_text(item['contact_person'])} — {_text(item['contact_email'])}")
            _paragraph(pdf, f"Documents location: {_text(item['documents_location'], 'Location not recorded')}")
            _paragraph(pdf, f"Access instructions: {_text(item['access_instructions'])}")

    _heading(pdf, "7. If I'm not reachable")
    _paragraph(pdf, "For a few weeks", bold=True)
    _paragraph(pdf, "Keep payments running for the following liabilities and recurring items:")
    for rows in (debts, recurring):
        for _, item in rows.iterrows():
            _paragraph(pdf, f"• {_text(item['item_name'])} — {_text(item['held_with'])}")
    if debts.empty and recurring.empty:
        _paragraph(pdf, "No liabilities or recurring items recorded.")
    _paragraph(pdf, "If I'm in hospital", bold=True)
    _paragraph(pdf, "Joint items the family member can already operate:")
    joint = holdings.loc[holdings["ownership"].fillna("").str.strip().str.casefold().eq("joint")]
    for _, item in joint.iterrows():
        _paragraph(pdf, f"• {_text(item['item_name'])} — {_where(item)}")
    if joint.empty:
        _paragraph(pdf, "No joint items recorded.")
    _paragraph(pdf, "If I pass away", bold=True)
    _paragraph(pdf, "Contact the lawyer, inform each institution, check nominees, and do not close joint accounts.")

    _heading(pdf, f"8. A message from {owner}")
    _paragraph(pdf, personal_message or "No personal message provided.")

    # Both the unencrypted intermediate and encrypted result stay in memory.
    writer = PdfWriter(clone_from=BytesIO(bytes(pdf.output())))
    writer.encrypt(user_password=password, algorithm="AES-256")
    output = BytesIO()
    writer.write(output)
    return output.getvalue()
