# Math-equation → human-readable fallback

`scripts/mathspeech.py` turns LaTeX / MathML equations into spoken-form English.
It exists so that when a paper is read as plain text (or piped to text-to-speech),
equations don't come through as raw markup like `H_{\mathrm{eff}}=H_{0}+\Delta-\frac{i}{2}G`.

It is wired into `scripts/html_to_text.py`: extracting an arXiv ar5iv page now
renders each equation's MathML `alttext` into English by default.

## Backend chain (best-first, all optional except the last)

The public entry `latex_to_speech(latex, mathml=None, prefer="auto")` tries
backends in order and returns the first success. The built-in translator is a
guaranteed floor, so it never raises on bad input.

| # | Backend | Needs | Quality | Notes |
|---|---------|-------|---------|-------|
| 1 | **Speech Rule Engine (SRE)** | Node (`npx speech-rule-engine`) + **MathML** input | Best — MathSpeak / ClearSpeak, same engine as MathJax & ChromeVox | LaTeX input unsupported for speech (Braille only), so feed it MathML. First run fetches the npm package. |
| 2 | **pylatexenc** | `pip install pylatexenc` | Readable Unicode (`H_eff=H₀+Δ−i/2G`) | Pure Python. Literal, not spoken-form. |
| 3 | **Built-in rules** | nothing | Spoken-form, tuned for open-quantum-systems papers | Handles subscripts, `\frac`, ket/bra, `\sum` limits, Greek, `\mathrm`/`\mathcal`, relations. |

`auto` uses SRE when MathML is supplied, otherwise the built-in rules (they read
better than pylatexenc's literal Unicode for operator-dense physics equations),
with pylatexenc as the safety net.

## Library research (2026-07-07)

Web + GitHub survey behind the design:

- **[Speech Rule Engine](https://github.com/speech-rule-engine/speech-rule-engine)**
  — the standard for math a11y; MathSpeak/ClearSpeak, i18n, Nemeth Braille. Node.
- **[pylatexenc](https://github.com/phfaist/pylatexenc)** — pure-Python
  `latex2text`; LaTeX → Unicode. Chosen as the no-Node middle tier.
- **[latex2sympy2](https://pypi.org/project/latex2sympy2/) / SymPy** — parse LaTeX
  to an expression tree; heavier, aimed at CAS not narration.
- GitHub turnkey LaTeX→speech: **[Alex-Tremayne/LaTeXt](https://github.com/Alex-Tremayne/LaTeXt)**,
  **[martysweet/latex-to-speech](https://github.com/martysweet/latex-to-speech)**
  (AWS Polly), **[kaieberl/paper2speech](https://github.com/kaieberl/paper2speech)**.
  Useful references; each pulls in a cloud TTS or narrow scope, so we kept the
  local layered approach instead of adding a hard dependency.

## Usage

```bash
# Single equation (built-in rules, zero deps)
python scripts/mathspeech.py 'H_{\mathrm{eff}}=H_{0}+\Delta-\frac{i}{2}G' --prefer rules
#   -> H sub eff equals H sub 0 plus capital delta minus i over 2 G

# Show which backend answered
python scripts/mathspeech.py '\Delta_{nm}' --show-backend

# Whole paper, equations spoken (default); --raw-math keeps the old LaTeX passthrough
python scripts/html_to_text.py docs/paper-2602.02868/ar5iv.html
python scripts/html_to_text.py --raw-math docs/paper-2602.02868/ar5iv.html
```

```python
from scripts.mathspeech import latex_to_speech
latex_to_speech(r"\mathrm{Tr}\,\rho(t)=1").text   # 'Tr rho (t) equals 1'
# MathML in hand -> highest quality:
latex_to_speech("", mathml="<math>...</math>", prefer="sre").text
```

## Tests

`tests/test_mathspeech.py` — rule-based backend checked against the paper's real
equations; optional backends self-skip when their tooling is absent; the SRE
path is marked `slow` (`-m "not slow"` to skip the npx call).
