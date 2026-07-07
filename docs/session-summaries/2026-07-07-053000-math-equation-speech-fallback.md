# Session Summary: Math-Equation → Human-Readable Speech Fallback (2026-07-07)

## Summary

Implemented a fallback layer that interprets LaTeX/MathML equations into
human-readable, spoken-form English, so papers read as plain text (or piped to
TTS) no longer surface raw markup. Preceded by a web + GitHub survey of existing
math-to-speech libraries. Tracked as `qutip-sandbox-v2c`.

## Completed Work

- **qutip-sandbox-v2c** (closed): implement — commit `a7c6fd7`; beads close —
  commit `b3fc3f0`.

## Key Changes

- `scripts/mathspeech.py` (new): `latex_to_speech()` with a best-first,
  graceful-degradation backend chain:
  1. **Speech Rule Engine** (`npx speech-rule-engine`, MathML input) —
     MathSpeak/ClearSpeak quality; verified live ("trace comma rho of t equals
     1" for `\mathrm{Tr}\,\rho(t)=1`). LaTeX-to-speech is unsupported by SRE
     (Braille only), so the engine is fed MathML.
  2. **pylatexenc** — pure-Python LaTeX → readable Unicode (`H_eff=H₀+Δ−i/2G`).
  3. **built-in rule-based translator** — zero deps; handles subscripts,
     `\frac`, ket/bra, `\sum` limits, Greek, `\mathrm`/`\mathcal`, relations.
     Tuned for the paper's operators.
- `scripts/html_to_text.py` (modified): speaks equations by default;
  `--raw-math` restores the old LaTeX passthrough. `H_{\mathrm{eff}}=...` now
  reads "H sub eff equals H sub 0 plus capital delta minus i over 2 G".
- `tests/test_mathspeech.py` (new): 17 tests — paper equations, malformed-input
  robustness, pipeline integration, optional backends self-skip; SRE marked
  `slow`. All pass.
- `pytest.ini` (new): registers the `slow` marker.
- `requirements.txt`: added optional `pylatexenc>=2.10` (my line only;
  partial-staged around the peer session's `pytest>=8`).
- `docs/math-equation-speech.md` (new): backend table, library research, usage.

## Library Research (web + GitHub, 2026-07-07)

Speech Rule Engine (standard, Node) · pylatexenc (pure-Python LaTeX→Unicode) ·
latex2sympy2/SymPy (CAS, heavier) · turnkey repos Alex-Tremayne/LaTeXt,
martysweet/latex-to-speech (AWS Polly), kaieberl/paper2speech. Chose a local
layered approach over any cloud-TTS dependency.

## Concurrency Notes (peer session active in this repo)

- A second Claude session is implementing the microtubule-QIF physics package
  in the same worktree (couplings.py, geometry.py, measures.py, model.py,
  run_microtubule_qif.py, tests/test_model_measures.py, README, etc.). **None of
  those files were touched or committed by this session.**
- Shared files were partial-staged: `.beads/issues.jsonl` (only the v2c
  add/close lines), `requirements.txt` (only the pylatexenc line).
- Reconfirmed the `git commit -- <path>` gotcha: with a pathspec it commits the
  working-tree file, bypassing the partial-staged index. Fix: `git reset
  --mixed HEAD~1`, rebuild the partial index, then `git commit` with **no**
  pathspec (uses the index). Both v2c beads commits are correctly scoped.
- `tests/test_model_measures.py::test_superradiant_decays_faster_than_subradiant`
  fails on the current tree — that is the peer's in-progress physics work, not
  related to this change.

## Next Session Context

- To use the best-quality backend on a whole document, feed the actual `<math>`
  MathML blocks to SRE (currently `html_to_text` uses rules/pylatexenc per
  equation to stay fast; a `--sre` batch mode could be added).
- `output/` artifacts and `.venv-v4/` in the tree are the peer session's;
  leave them.
