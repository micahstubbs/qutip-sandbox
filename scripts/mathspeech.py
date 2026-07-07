#!/usr/bin/env python
"""Interpret LaTeX / MathML math into human-readable English.

Motivation
----------
``html_to_text.py`` pulls equations out of arXiv ar5iv pages as raw MathML
``alttext`` — i.e. LaTeX like ``H_{\\mathrm{eff}}=H_{0}+\\Delta-\\frac{i}{2}G``.
That is unreadable when a paper is skimmed as plain text or piped to a
text-to-speech engine. This module is a *fallback layer* that renders such
markup into spoken-form English ("H sub eff equals H sub 0 plus Delta ...").

Design: a chain of backends, tried best-first, each optional so the module
always returns *something* even with zero extra dependencies installed.

  1. Speech Rule Engine (SRE) — MathSpeak/ClearSpeak quality, the same engine
     behind MathJax and ChromeVox. Needs Node (`npx sre`) and MathML input.
     https://github.com/speech-rule-engine/speech-rule-engine
  2. pylatexenc `LatexNodes2Text` — pure-Python LaTeX -> readable Unicode.
     https://github.com/phfaist/pylatexenc
  3. Built-in rule-based translator — no dependencies, always available.
     Tuned for the operators in open-quantum-systems / QuTiP papers.

Use `latex_to_speech()` for a single string, or run this file as a CLI.
"""
from __future__ import annotations

import re
import shutil
import subprocess
from dataclasses import dataclass

# --- Greek letters and named symbols ------------------------------------

_GREEK = {
    "alpha": "alpha", "beta": "beta", "gamma": "gamma", "Gamma": "capital gamma",
    "delta": "delta", "Delta": "capital delta", "epsilon": "epsilon",
    "varepsilon": "epsilon", "zeta": "zeta", "eta": "eta", "theta": "theta",
    "Theta": "capital theta", "iota": "iota", "kappa": "kappa", "lambda": "lambda",
    "Lambda": "capital lambda", "mu": "mu", "nu": "nu", "xi": "xi", "Xi": "capital xi",
    "pi": "pi", "Pi": "capital pi", "rho": "rho", "sigma": "sigma",
    "Sigma": "capital sigma", "tau": "tau", "phi": "phi", "varphi": "phi",
    "Phi": "capital phi", "chi": "chi", "psi": "psi", "Psi": "capital psi",
    "omega": "omega", "Omega": "capital omega", "hbar": "h bar", "ell": "l",
    "nabla": "gradient", "partial": "partial", "infty": "infinity",
}

# Multi-character operators / relations, longest-match first.
_OPERATORS = [
    (r"\displaystyle", ""),
    (r"\mathrm", ""), (r"\mathcal", ""), (r"\mathbf", ""), (r"\boldsymbol", ""),
    (r"\text", ""), (r"\operatorname", ""),
    (r"\left", ""), (r"\right", ""), (r"\big", ""), (r"\Big", ""),
    (r"\quad", " "), (r"\qquad", " "), (r"\,", " "), (r"\;", " "),
    (r"\:", " "), (r"\!", ""), (r"\ ", " "),
    (r"\neq", " not equal to "), (r"\ne", " not equal to "),
    (r"\leq", " less than or equal to "), (r"\le", " less than or equal to "),
    (r"\geq", " greater than or equal to "), (r"\ge", " greater than or equal to "),
    (r"\approx", " approximately "), (r"\equiv", " defined as "),
    (r"\propto", " proportional to "), (r"\sim", " of order "),
    (r"\to", " goes to "), (r"\rightarrow", " goes to "), (r"\mapsto", " maps to "),
    (r"\otimes", " tensor "), (r"\oplus", " direct sum "),
    (r"\cdot", " times "), (r"\times", " times "), (r"\ast", " star "),
    (r"\pm", " plus or minus "), (r"\mp", " minus or plus "),
    (r"\dagger", " dagger "), (r"\prime", " prime "),
    (r"\sum", " sum "), (r"\int", " integral "), (r"\prod", " product "),
    (r"\lim", " limit "),
    (r"\in", " in "), (r"\notin", " not in "), (r"\forall", " for all "),
    (r"\exists", " there exists "),
    (r"\langle", " expectation of "), (r"\rangle", " "),
    (r"\lvert", " "), (r"\rvert", " "), (r"\vert", " "),
    (r"\%", " percent "),
]

# Bare relation/arithmetic characters handled after commands are gone.
_CHAR_WORDS = {
    "=": " equals ", "+": " plus ", "-": " minus ", "<": " less than ",
    ">": " greater than ", "/": " over ", "*": " times ",
}


@dataclass
class SpeechResult:
    text: str
    backend: str  # "sre" | "pylatexenc" | "rules"


# --- Backend 1: Speech Rule Engine (optional, best quality) --------------

def _sre_available() -> bool:
    return shutil.which("npx") is not None


def _sre_speech(mathml: str, *, style: str = "mathspeak",
                timeout: float = 60.0) -> str | None:
    """Render MathML via Speech Rule Engine. Returns None on any failure.

    SRE's CLI reads MathML from an ``-i`` file and writes to an ``-o`` file
    (positional args and stdin are rejected in current versions; its LaTeX
    input only supports Braille, so speech must come from MathML). ``style``
    selects the rule set — "mathspeak" (unambiguous) or "clearspeak" (natural).
    First run may pause while npx fetches the package.
    """
    if not mathml or not _sre_available():
        return None
    import os
    import tempfile
    in_fd, in_path = tempfile.mkstemp(suffix=".mathml")
    out_fd, out_path = tempfile.mkstemp(suffix=".txt")
    os.close(out_fd)
    try:
        with os.fdopen(in_fd, "w", encoding="utf-8") as fh:
            fh.write(mathml)
        proc = subprocess.run(
            ["npx", "--yes", "speech-rule-engine",
             "-i", in_path, "-o", out_path, "-d", style],
            capture_output=True, text=True, timeout=timeout,
        )
        if proc.returncode != 0:
            return None
        with open(out_path, encoding="utf-8") as fh:
            out = fh.read().strip()
        return out or None
    except (subprocess.TimeoutExpired, OSError):
        return None
    finally:
        for p in (in_path, out_path):
            try:
                os.unlink(p)
            except OSError:
                pass


# --- Backend 2: pylatexenc (optional, pure Python) -----------------------

def _pylatexenc_text(latex: str) -> str | None:
    try:
        from pylatexenc.latex2text import LatexNodes2Text
    except ImportError:
        return None
    try:
        out = LatexNodes2Text(math_mode="text").latex_to_text(latex).strip()
    except Exception:
        return None
    return _collapse_ws(out) or None


# --- Backend 3: built-in rule-based translator (always available) --------

def _find_group(s: str, start: int) -> tuple[str, int]:
    """Given s[start] == '{', return (inner, index_after_closing_brace)."""
    depth, i = 0, start
    while i < len(s):
        if s[i] == "{":
            depth += 1
        elif s[i] == "}":
            depth -= 1
            if depth == 0:
                return s[start + 1:i], i + 1
        i += 1
    return s[start + 1:], len(s)  # unbalanced: take the rest


def _take_atom(s: str, i: int) -> tuple[str, int]:
    """Read one 'atom' after a _ or ^: a braced group, a command, or one char."""
    if i >= len(s):
        return "", i
    if s[i] == "{":
        inner, j = _find_group(s, i)
        return _rule_based(inner), j
    if s[i] == "\\":
        m = re.match(r"\\[A-Za-z]+", s[i:])
        if m:
            tok = m.group(0)
            return _rule_based(tok), i + len(tok)
    return s[i], i + 1


def _expand_scripts(s: str) -> str:
    """Turn a_{..}/a^{..} into 'a sub ..'/'a to the .. power', recursively."""
    out, i = [], 0
    while i < len(s):
        c = s[i]
        if c == "_":
            atom, i = _take_atom(s, i + 1)
            out.append(f" sub {atom} ")
        elif c == "^":
            atom, i = _take_atom(s, i + 1)
            if atom.strip() in {"2", "3"}:
                word = {"2": "squared", "3": "cubed"}[atom.strip()]
                out.append(f" {word} ")
            elif atom.strip() in {"+", "-"}:
                out.append(f" {'plus' if atom.strip() == '+' else 'minus'} ")
            elif atom.strip() == "\\dagger" or atom.strip() == "dagger":
                out.append(" dagger ")
            else:
                out.append(f" to the {atom} power ")
        else:
            out.append(c)
            i += 1
    return "".join(out)


def _expand_frac(s: str) -> str:
    """Replace \\frac{a}{b} with '(a) over (b)', recursively, innermost first."""
    while True:
        idx = s.find("\\frac")
        if idx == -1:
            return s
        j = idx + len("\\frac")
        while j < len(s) and s[j] == " ":
            j += 1
        if j >= len(s) or s[j] != "{":
            # malformed; neutralize the token so we don't loop forever
            s = s[:idx] + " fraction " + s[idx + len("\\frac"):]
            continue
        num, j = _find_group(s, j)
        while j < len(s) and s[j] == " ":
            j += 1
        if j < len(s) and s[j] == "{":
            den, j = _find_group(s, j)
        else:
            den, j = _take_atom(s, j)
        repl = f" {_rule_based(num)} over {_rule_based(den)} "
        s = s[:idx] + repl + s[j:]


def _expand_sqrt(s: str) -> str:
    while True:
        idx = s.find("\\sqrt")
        if idx == -1:
            return s
        j = idx + len("\\sqrt")
        while j < len(s) and s[j] == " ":
            j += 1
        if j < len(s) and s[j] == "{":
            inner, j = _find_group(s, j)
            s = s[:idx] + f" square root of {_rule_based(inner)} " + s[j:]
        else:
            s = s[:idx] + " square root of " + s[j:]


def _collapse_ws(s: str) -> str:
    s = re.sub(r"\s+", " ", s)
    s = re.sub(r"\s+([,.;])", r"\1", s)
    return s.strip()


def _rule_based(latex: str) -> str:
    if not latex:
        return ""
    s = latex
    s = _expand_frac(s)
    s = _expand_sqrt(s)
    # Ket / bra notation: |x\rangle -> ket x, \langle x| -> bra x
    s = re.sub(r"\|\s*([^|\\]+?)\s*\\rangle", r" ket \1 ", s)
    s = re.sub(r"\\langle\s*([^|\\]+?)\s*\|", r" bra \1 ", s)
    # Multi-char operators/relations (longest first to avoid partial hits).
    for tok, word in sorted(_OPERATORS, key=lambda kv: -len(kv[0])):
        s = s.replace(tok, word)
    # Greek + named symbols: \alpha -> alpha
    def _greek(m: re.Match) -> str:
        name = m.group(1)
        return f" {_GREEK[name]} " if name in _GREEK else f" {name} "
    s = re.sub(r"\\([A-Za-z]+)", _greek, s)
    # Sub/superscripts.
    s = _expand_scripts(s)
    # Leftover braces.
    s = s.replace("{", " ").replace("}", " ")
    # Bare characters.
    for ch, word in _CHAR_WORDS.items():
        s = s.replace(ch, word)
    return _collapse_ws(s)


def rule_based_speech(latex: str) -> str:
    """Public entry to the dependency-free translator."""
    return _rule_based(latex)


# --- Public API ----------------------------------------------------------

def latex_to_speech(
    latex: str, *, mathml: str | None = None, prefer: str = "auto"
) -> SpeechResult:
    """Render a LaTeX (and/or MathML) equation to human-readable English.

    Backends are tried best-first and the first success wins:
    SRE (if MathML + Node) -> pylatexenc -> built-in rules. The built-in
    translator is a guaranteed floor, so this never raises for bad input.

    prefer: "auto" (default), or force one of "sre" | "pylatexenc" | "rules".
    """
    latex = (latex or "").strip()
    if prefer == "rules":
        return SpeechResult(rule_based_speech(latex), "rules")
    if prefer == "pylatexenc":
        t = _pylatexenc_text(latex)
        return SpeechResult(t, "pylatexenc") if t else SpeechResult(
            rule_based_speech(latex), "rules")
    if prefer == "sre":
        t = _sre_speech(mathml or "")
        return SpeechResult(t, "sre") if t else SpeechResult(
            rule_based_speech(latex), "rules")

    # auto
    if mathml:
        t = _sre_speech(mathml)
        if t:
            return SpeechResult(t, "sre")
    # For the operator-dense equations in physics papers the built-in rules
    # read better than pylatexenc's literal Unicode, so prefer them and keep
    # pylatexenc as the safety net if the rules produce nothing.
    r = rule_based_speech(latex)
    if r:
        return SpeechResult(r, "rules")
    t = _pylatexenc_text(latex)
    return SpeechResult(t or "", "pylatexenc" if t else "rules")


def _main(argv: list[str]) -> int:
    import argparse
    p = argparse.ArgumentParser(description="LaTeX/MathML -> spoken English.")
    p.add_argument("latex", nargs="?", help="LaTeX string (or read stdin).")
    p.add_argument("--prefer", default="auto",
                   choices=["auto", "sre", "pylatexenc", "rules"])
    p.add_argument("--show-backend", action="store_true")
    args = p.parse_args(argv)
    src = args.latex
    if src is None:
        import sys
        src = sys.stdin.read()
    res = latex_to_speech(src, prefer=args.prefer)
    if args.show_backend:
        print(f"[{res.backend}] {res.text}")
    else:
        print(res.text)
    return 0


if __name__ == "__main__":
    import sys
    raise SystemExit(_main(sys.argv[1:]))
