"""Shared look and feel: brand colours, sidebar wordmark, and global spacing."""

from pathlib import Path

import streamlit as st

ASSETS_DIR = Path(__file__).resolve().parent / "assets"

# Keep in step with [theme] in .streamlit/config.toml.
NAVY = "#14263D"
TEAL = "#0F6E6E"
ACCENT = "#D9A441"
MUTED = "#5B6B7F"

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
</style>
"""


def apply_branding():
    """Add the sidebar wordmark and the app-wide CSS. Call once per run."""
    st.logo(
        str(ASSETS_DIR / "wordmark.svg"), size="large",
        icon_image=str(ASSETS_DIR / "icon.svg"),
    )
    st.html(GLOBAL_CSS)
