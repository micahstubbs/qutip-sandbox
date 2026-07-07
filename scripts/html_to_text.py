#!/usr/bin/env python
"""Minimal ar5iv/HTML -> plain-text extractor for reading papers offline.

Strips scripts/styles/markup, keeps heading structure and math alt-text where
present, and collapses whitespace. Not a general HTML renderer — just enough to
read an arXiv ar5iv page as text.
"""
import re
import sys
from html import unescape

try:
    from mathspeech import latex_to_speech  # when run from scripts/
except ImportError:  # pragma: no cover - import path when used as a package
    from scripts.mathspeech import latex_to_speech


def _speak(latex: str) -> str:
    """Render an equation's LaTeX alttext to human-readable English."""
    latex = unescape(latex).strip()
    if not latex:
        return " "
    # Rule-based/pylatexenc only here (no per-equation SRE subprocess): keeps
    # whole-document conversion fast and dependency-light.
    return f" {latex_to_speech(latex, prefer='auto').text} "


def convert(html: str, speak_math: bool = True) -> str:
    # Drop script/style/head noise
    html = re.sub(r"<(script|style|head)\b[^>]*>.*?</\1>", " ", html,
                  flags=re.S | re.I)
    # Prefer MathML/img alt text for equations. When speak_math is on, render
    # the LaTeX alttext into spoken-form English instead of leaving raw markup.
    if speak_math:
        html = re.sub(r'<math\b[^>]*alttext="([^"]*)"[^>]*>.*?</math>',
                      lambda m: _speak(m.group(1)), html, flags=re.S | re.I)
    else:
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
    args = [a for a in sys.argv[1:] if a != "--raw-math"]
    speak = "--raw-math" not in sys.argv
    src = args[0]
    out = args[1] if len(args) > 1 else None
    text = convert(open(src, encoding="utf-8", errors="replace").read(),
                   speak_math=speak)
    if out:
        open(out, "w", encoding="utf-8").write(text)
        print(f"wrote {len(text)} chars to {out}")
    else:
        sys.stdout.write(text)
