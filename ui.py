"""Shared look and feel: brand colours, chart palette, wordmark, and global CSS."""

from html import escape
from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Keep in step with [theme] in .streamlit/config.toml.
NAVY = "#14263D"
TEAL = "#0F6E6E"
ACCENT = "#D9A441"
MUTED = "#5B6B7F"
BORDER = "#D9DEE5"
SIDEBAR_BACKGROUND = "#EDF1F4"

# One chart palette for every page. The order is checked for colour-blind
# separation, so add new colours at the end rather than reordering.
CHART_COLORS = (
    "#2A78D6", "#008300", "#E87BA4", "#EDA100",
    "#E34948", "#0E9C8F", "#EB6834", "#6250D6",
)
DEBT_COLORS = ("#5B6B7F", "#8493A5", "#A9B4C2")
CHART_PRIMARY = TEAL
CHART_SECONDARY = "#8CC5C0"
CHART_NEUTRAL = "#DDE3EA"
CHART_GRID = "#E3E7EC"
POSITIVE = "#0E9C8F"
WARNING = "#E0A019"
NEGATIVE = "#D8524F"
UNRATED = "#9AA5B1"

ASSET_TYPE_ICONS = {
    "land": "landscape", "real estate": "home_work", "gold": "diamond",
    "cash": "payments", "stocks": "show_chart", "bonds": "receipt_long",
    "crypto": "currency_bitcoin", "mortgage": "house", "loan": "request_quote",
    "credit card": "credit_card",
}

GLOBAL_CSS = f"""
<style>
/* Comfortable reading width and the same top/bottom rhythm on every page. */
[data-testid="stMainBlockContainer"] {{
    max-width: 76rem;
    padding-top: 3rem;
    padding-bottom: 4rem;
}}
h1, h2, h3 {{ letter-spacing: -0.01em; }}
h1 {{ padding-bottom: 0.25rem; }}

/* Sidebar: room for the wordmark, quieter section headings. */
[data-testid="stSidebarHeader"] {{ padding-top: 1.25rem; padding-bottom: 0.5rem; }}
[data-testid="stSidebarHeader"] img {{ height: 2rem; max-width: 100%; }}
[data-testid="stSidebarNav"] {{ padding-bottom: 0.5rem; }}
[data-testid="stSidebar"] h2 {{
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.08em;
    text-transform: uppercase;
    color: {MUTED};
    padding-top: 1rem;
}}
[data-testid="stLayoutWrapper"]:has(> .st-key-sidebar_footer) {{
    position: sticky;
    bottom: 0;
    z-index: 2;
    margin-top: 0.5rem;
    padding: 0.6rem 0 0.9rem;
    border-top: 1px solid {BORDER};
    background: {SIDEBAR_BACKGROUND};
}}
.st-key-sidebar_footer p {{ font-size: 0.8rem; color: {MUTED}; margin: 0; }}

/* KPI cards. The value shrinks with the card and wraps as a last resort,
   so it is never cut off with an ellipsis. */
[data-testid="stMetric"] {{
    container-type: inline-size;
    height: 100%;
    background: #FFFFFF;
    border-color: {BORDER};
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(20, 38, 61, 0.05);
}}
[data-testid="stMetricLabel"] {{ color: {MUTED}; }}
[data-testid="stMetricLabel"] span[role="img"] {{ color: {TEAL}; }}
[data-testid="stMetricValue"] {{
    font-size: clamp(1.1rem, 11.5cqi, 2rem);
    font-weight: 600;
    line-height: 1.3;
}}
[data-testid="stMetricLabel"], [data-testid="stMetricLabel"] *,
[data-testid="stMetricValue"], [data-testid="stMetricValue"] * {{
    white-space: normal !important;
    overflow: visible !important;
    text-overflow: clip !important;
    overflow-wrap: break-word;
}}

/* White cards. */
.st-key-smart_insights, [class*="st-key-feature_card"] {{
    background: #FFFFFF;
    border-color: {BORDER};
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(20, 38, 61, 0.05);
}}
.st-key-smart_insights h3 span[role="img"] {{ color: {ACCENT}; }}
.st-key-smart_insights p span[role="img"] {{ color: {TEAL}; }}

/* Home hero. */
.st-key-hero {{
    background: linear-gradient(120deg, {NAVY} 0%, #1A3B58 62%, {TEAL} 135%);
    border-radius: 1rem;
    padding: 2.75rem 2.5rem 2.5rem;
    margin-bottom: 0.5rem;
}}
.st-key-hero h1 {{ color: #FFFFFF; font-size: clamp(1.9rem, 4.5vw, 2.75rem); }}
.st-key-hero p {{ color: #D6DEE8; font-size: 1.125rem; max-width: 40rem; }}
.st-key-hero .fwn-eyebrow {{
    color: {ACCENT};
    font-size: 0.75rem;
    font-weight: 600;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}
.st-key-hero button p {{ font-size: 1rem; color: inherit; }}
.st-key-hero button[data-testid="stBaseButton-primary"] {{
    background: {ACCENT};
    border-color: {ACCENT};
    color: {NAVY};
}}
.st-key-hero button[data-testid="stBaseButton-primary"]:hover {{
    background: #E6B65A;
    border-color: #E6B65A;
    color: {NAVY};
}}
.st-key-hero button[data-testid="stBaseButton-secondary"] {{
    background: transparent;
    border-color: rgba(255, 255, 255, 0.55);
    color: #FFFFFF;
}}
.st-key-hero button[data-testid="stBaseButton-secondary"]:hover {{
    background: rgba(255, 255, 255, 0.12);
    border-color: #FFFFFF;
    color: #FFFFFF;
}}
.st-key-hero button:focus-visible {{ outline: 3px solid #FFFFFF; outline-offset: 2px; }}
[class*="st-key-feature_icon"] span[role="img"] {{
    font-size: 1.5rem;
    color: {TEAL};
    background: #E3F1F0;
    border-radius: 0.6rem;
    padding: 0.5rem;
}}
@media (max-width: 640px) {{
    .st-key-hero {{ padding: 1.75rem 1.25rem; }}
}}

/* Cards, chips, and pills written as HTML on Holdings and Readiness Check. */
.fwn-icon {{
    font-family: "Material Symbols Rounded";
    font-weight: 400;
    font-size: 1.25rem;
    line-height: 1;
    display: inline-block;
    white-space: nowrap;
    vertical-align: middle;
    font-feature-settings: "liga";
    user-select: none;
}}
.fwn-icon-tile {{
    flex: none;
    color: {TEAL};
    background: #E3F1F0;
    border-radius: 0.6rem;
    padding: 0.45rem;
}}
.fwn-icon-tile.fwn-debt {{ color: {MUTED}; background: #E8ECF1; }}
.fwn-chips {{ display: flex; flex-wrap: wrap; gap: 0.5rem; }}
.fwn-chip, .fwn-pill {{
    display: inline-flex;
    align-items: center;
    gap: 0.3rem;
    border-radius: 999px;
    font-size: 0.8rem;
    font-weight: 600;
    line-height: 1.2;
    padding: 0.3rem 0.7rem;
    white-space: nowrap;
}}
.fwn-chip {{ background: #FFFFFF; border: 1px solid {BORDER}; color: {NAVY}; }}
.fwn-chip .fwn-icon, .fwn-pill .fwn-icon {{ font-size: 1rem; }}
.fwn-pill {{ padding: 0.2rem 0.55rem; font-size: 0.75rem; }}
.fwn-good {{ background: #E0F2E4; color: #1E6B33; border-color: #C5E5CC; }}
.fwn-bad {{ background: #FBE3E2; color: #A32E2B; }}
.fwn-first {{ background: #FCE8D5; color: #9A4A10; }}
.fwn-worth {{ background: #FBF0CF; color: #7A5A00; }}
.fwn-quiet {{ background: #E8ECF1; color: {MUTED}; }}
.fwn-grid {{
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(min(100%, 15.5rem), 1fr));
    gap: 0.75rem;
}}
.fwn-grid-wide {{ grid-template-columns: repeat(auto-fill, minmax(min(100%, 19rem), 1fr)); }}
.fwn-card {{
    background: #FFFFFF;
    border: 1px solid {BORDER};
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(20, 38, 61, 0.05);
    padding: 0.9rem 1rem;
    display: flex;
    flex-direction: column;
    gap: 0.6rem;
    min-width: 0;
}}
.fwn-card-head {{ display: flex; align-items: center; gap: 0.65rem; min-width: 0; }}
.fwn-card-head > div {{ min-width: 0; flex: 1; }}
.fwn-card-title {{ font-weight: 600; line-height: 1.3; overflow-wrap: anywhere; }}
.fwn-card-sub {{ color: {MUTED}; font-size: 0.8rem; line-height: 1.35; }}
.fwn-card-value {{
    display: flex;
    flex-wrap: wrap;
    align-items: center;
    gap: 0.5rem;
    font-size: 1.25rem;
    font-weight: 700;
    line-height: 1.2;
}}
.fwn-row {{ display: flex; flex-wrap: wrap; align-items: center; gap: 0.4rem; }}
.fwn-row-apart {{ justify-content: space-between; }}
.fwn-bar {{ background: #E8ECF1; border-radius: 999px; height: 0.4rem; overflow: hidden; }}
.fwn-bar > span {{ display: block; height: 100%; background: {TEAL}; border-radius: 999px; }}
.fwn-checklist {{ list-style: none; margin: 0 !important; padding: 0 !important; font-size: 0.9rem; }}
.fwn-checklist li {{ display: flex; align-items: center; gap: 0.4rem; padding: 0.12rem 0; margin: 0; }}
.fwn-checklist .fwn-done {{ color: {MUTED}; }}
.fwn-checklist .fwn-done .fwn-icon {{ color: #2E8B47; }}
.fwn-checklist .fwn-todo {{ font-weight: 600; }}
.fwn-quickwins {{ margin: 0; padding-left: 1.25rem; }}
.fwn-quickwins li {{ padding: 0.2rem 0; }}
.st-key-quick_wins {{
    background: #FFFFFF;
    border-color: {BORDER};
    border-radius: 0.75rem;
    box-shadow: 0 1px 2px rgba(20, 38, 61, 0.05);
}}
.st-key-quick_wins h3 span[role="img"] {{ color: {ACCENT}; }}
</style>
"""


def apply_branding():
    """Add the sidebar wordmark and the app-wide CSS. Call once per run."""
    st.logo(
        str(ASSETS_DIR / "wordmark.svg"), size="large",
        icon_image=str(ASSETS_DIR / "icon.svg"),
    )
    st.html(GLOBAL_CSS)


def page_header(title, description):
    """The same title and one-line description at the top of every page."""
    st.title(title)
    st.markdown(f":gray[{description}]")


def sidebar_footer(text):
    """Small note pinned to the bottom of the sidebar on every page."""
    with st.sidebar.container(key="sidebar_footer"):
        st.markdown(f":material/info: {text}")


def icon_html(name, extra_class=""):
    """A Material icon for hand-written HTML (st.html)."""
    return f'<span class="fwn-icon {extra_class}" aria-hidden="true">{escape(name)}</span>'


def type_icon(asset_type, category):
    """Icon name for a holding's type, with a fallback per category."""
    key = asset_type if isinstance(asset_type, str) else ""
    fallback = "account_balance" if category == "Liability" else "category"
    return ASSET_TYPE_ICONS.get(key.strip().casefold(), fallback)


def pill(text, tone="quiet", icon=None):
    """A small rounded label. Tones: good, bad, first, worth, quiet."""
    return (
        f'<span class="fwn-pill fwn-{tone}">'
        f'{icon_html(icon) if icon else ""}{escape(str(text))}</span>'
    )


def chips(labels):
    """A wrapping row of outlined chips from (icon, text) pairs."""
    items = "".join(
        f'<span class="fwn-chip">{icon_html(icon)}{escape(str(text))}</span>'
        for icon, text in labels
    )
    return f'<div class="fwn-chips">{items}</div>'


def style_chart(figure):
    """Give a Plotly figure the shared colours, gridlines, and tooltip style."""
    figure.update_layout(
        font=dict(color=NAVY),
        paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=BORDER, font=dict(color=NAVY)),
        legend=dict(title_text="", font=dict(color=MUTED)),
    )
    for update_axes in (figure.update_xaxes, figure.update_yaxes):
        update_axes(
            gridcolor=CHART_GRID, zerolinecolor="#B8C2CE", linecolor="#B8C2CE",
            tickfont=dict(color=MUTED), title_font=dict(color=MUTED),
        )
    return figure
