"""Defensive helper for passing HTML through st.markdown(unsafe_allow_html=True).

Verified bug: certain multi-line, indented HTML f-string blocks (typically
several levels of nested <div>s mixed with an inline <svg>) were silently
rendered as escaped literal text instead of being parsed as HTML -- no
exception, no console error, just the raw tags shown to the user. Isolated
minimal reproductions of the same nesting did NOT reproduce it, so the
exact trigger inside Streamlit's/markdown-it's HTML-block detection wasn't
pinned down -- but flattening every template to a single line with no
leading whitespace (so there is no indentation or blank-line pattern left
for a Markdown parser to ever reinterpret) reliably avoids it. Route every
piece of hand-built HTML in this app through `flatten()` before st.markdown.
"""
from __future__ import annotations


def flatten(html: str) -> str:
    lines = [line.strip() for line in html.strip().splitlines()]
    return " ".join(line for line in lines if line)
