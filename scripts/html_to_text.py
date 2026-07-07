#!/usr/bin/env python
"""Minimal ar5iv/HTML -> plain-text extractor for reading papers offline.

Strips scripts/styles/markup, keeps heading structure and math alt-text where
present, and collapses whitespace. Not a general HTML renderer — just enough to
read an arXiv ar5iv page as text.
"""
import re
import sys
from html import unescape


def convert(html: str) -> str:
    # Drop script/style/head noise
    html = re.sub(r"<(script|style|head)\b[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    # Prefer MathML/img alt text for equations
    html = re.sub(r'<math\b[^>]*alttext="([^"]*)"[^>]*>.*?</math>',
                  r" \1 ", html, flags=re.S | re.I)
    html = re.sub(r'<img\b[^>]*alt="([^"]*)"[^>]*>', r" [img: \1] ", html,
                  flags=re.S | re.I)
    # Headings and paragraph breaks
    html = re.sub(r"</(h[1-6]|p|div|li|tr|section)>", "\n\n", html, flags=re.I)
    html = re.sub(r"<(h[1-6])\b[^>]*>", r"\n\n### ", html, flags=re.I)
    html = re.sub(r"<li\b[^>]*>", "\n- ", html, flags=re.I)
    html = re.sub(r"<br\s*/?>", "\n", html, flags=re.I)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", "", html)
    text = unescape(text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n\s*\n\s*\n+", "\n\n", text)
    return text.strip()


if __name__ == "__main__":
    src = sys.argv[1]
    out = sys.argv[2] if len(sys.argv) > 2 else None
    text = convert(open(src, encoding="utf-8", errors="replace").read())
    if out:
        open(out, "w", encoding="utf-8").write(text)
        print(f"wrote {len(text)} chars to {out}")
    else:
        sys.stdout.write(text)
