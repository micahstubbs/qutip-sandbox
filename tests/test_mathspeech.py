"""Tests for the math-equation -> human-readable fallback (scripts/mathspeech.py).

The built-in rule-based backend is exercised deterministically (no network,
no optional deps). SRE and pylatexenc paths are tested only when available so
the suite passes in a minimal environment.
"""
import importlib.util
import shutil
import sys
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]


def _load(name: str):
    spec = importlib.util.spec_from_file_location(
        name, _ROOT / "scripts" / f"{name}.py")
    mod = importlib.util.module_from_spec(spec)
    sys.modules[name] = mod  # dataclass needs the module registered
    spec.loader.exec_module(mod)
    return mod


mathspeech = _load("mathspeech")


# --- Rule-based backend: the paper's real equations ---------------------

@pytest.mark.parametrize("latex, expected", [
    (r"H_{\mathrm{eff}}=H_{0}+\Delta-\frac{i}{2}G",
     "H sub eff equals H sub 0 plus capital delta minus i over 2 G"),
    (r"k_{0}=2\pi/\lambda_{0}",
     "k sub 0 equals 2 pi over lambda sub 0"),
    (r"E_{j}=\mathcal{E}_{j}-\frac{i}{2}\Gamma_{j}",
     "E sub j equals E sub j minus i over 2 capital gamma sub j"),
    (r"\Delta_{nm}",
     "capital delta sub nm"),
])
def test_rule_based_paper_equations(latex, expected):
    assert mathspeech.rule_based_speech(latex) == expected


def test_ket_bra_notation():
    out = mathspeech.rule_based_speech(r"|n\rangle\langle m|")
    assert "ket n" in out and "bra m" in out


def test_fraction_and_subscript_nesting():
    out = mathspeech.rule_based_speech(r"\frac{\omega_{0}}{2}")
    assert out == "omega sub 0 over 2"


def test_sum_with_limits_and_neq():
    out = mathspeech.rule_based_speech(r"\sum_{n\neq m}\Delta_{nm}")
    assert "sum" in out and "not equal to" in out and "capital delta sub nm" in out


def test_superscript_squared():
    assert mathspeech.rule_based_speech(r"L_{1}^{2}") == "L sub 1 squared"


def test_trace_condition():
    # \mathrm{Tr} drops the \mathrm wrapper; the reading stays sensible.
    out = mathspeech.rule_based_speech(r"\mathrm{Tr}\,\rho(t)=1")
    assert out.startswith("Tr") and "rho" in out and out.endswith("equals 1")


# --- Robustness: never raises, always returns a floor -------------------

@pytest.mark.parametrize("bad", ["", r"\frac", r"H_{", r"\undefinedmacro{x}"])
def test_malformed_input_does_not_raise(bad):
    res = mathspeech.latex_to_speech(bad, prefer="rules")
    assert isinstance(res.text, str)


def test_auto_falls_back_to_rules_without_mathml():
    res = mathspeech.latex_to_speech(r"H_{0}=1")
    assert res.backend in {"rules", "pylatexenc"}
    assert "equals" in res.text or "1" in res.text


# --- Optional backends: only when their tooling is present --------------

def test_pylatexenc_backend_when_installed():
    if importlib.util.find_spec("pylatexenc") is None:
        pytest.skip("pylatexenc not installed")
    res = mathspeech.latex_to_speech(
        r"H_{\mathrm{eff}}=H_{0}+\Delta", prefer="pylatexenc")
    assert res.backend == "pylatexenc"
    assert "Δ" in res.text  # renders Greek to Unicode


@pytest.mark.slow
def test_sre_backend_when_node_present():
    if shutil.which("npx") is None:
        pytest.skip("npx/Node not available")
    mathml = ("<math><msub><mi>H</mi><mi>0</mi></msub>"
              "<mo>=</mo><mn>1</mn></math>")
    out = mathspeech._sre_speech(mathml)
    if out is None:
        pytest.skip("SRE not fetchable (offline npx)")
    assert "equals" in out.lower()


# --- Pipeline integration: html_to_text uses the fallback ---------------

def test_html_to_text_speaks_math():
    h2t = _load("html_to_text")
    html = (
        '<p>The generator <math alttext="H_{\\mathrm{eff}}=H_{0}+\\Delta">'
        '<mi>x</mi></math> governs decay.</p>')
    spoken = h2t.convert(html, speak_math=True)
    raw = h2t.convert(html, speak_math=False)
    assert "H sub eff equals H sub 0 plus capital delta" in spoken
    assert "\\mathrm" in raw and "sub eff" not in raw
