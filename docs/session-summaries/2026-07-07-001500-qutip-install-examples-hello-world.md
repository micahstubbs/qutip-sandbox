# Session Summary: QuTiP install, examples, and hello world

## Summary

Installed QuTiP 5.3.0 in a fresh Python 3.13 venv, ran canonical examples adapted from the official docs, and built a self-verifying "hello world" exercise (Rabi oscillations of a driven qubit). Tracked as beads issue `qutip-sandbox-8mq`.

## Completed Work

- Created venv (`python3.13 -m venv .venv`) — system Python was 3.9, below QuTiP 5's ≥3.10 floor
- Installed qutip 5.3.0 + matplotlib 3.11.0; verified with `qutip.about()`
- Confirmed the pip package ships no runnable examples (official ones are notebooks in qutip/qutip-tutorials)
- `scripts/run_examples.py` — three canonical docs examples, all physically verified:
  - basics: ⟨n⟩ = |α|² = 4.0 for coherent state ✓
  - dissipative qubit (`mesolve`): decay envelope hits e⁻¹ ≈ 0.368 ✓
  - driven damped cavity: Lorentzian peak ⟨n⟩ ≈ 4.0 = (drive/(κ/2))² ✓
- `scripts/hello_qutip.py` — hello world: resonant Rabi flopping, self-verified against analytic ⟨σz⟩ = cos(Ωt) (max error 1.6e-5, PASS), plus T1-damped variant and Bloch-sphere trajectory plot
- Both output PNGs visually inspected and correct
- Added README.md, requirements.txt, .gitignore

## Key Changes

- `scripts/run_examples.py`, `scripts/hello_qutip.py` (new)
- `output/*.png` (4 plots)
- `README.md`, `requirements.txt`, `.gitignore` (new)

## Pending/Blocked

- No git remote configured — committed locally, not pushed

## Next Session Context

- Venv at `.venv/` (gitignored); rebuild with `python3.13 -m venv .venv && .venv/bin/pip install -r requirements.txt`
- Natural next steps: Jaynes–Cummings vacuum Rabi oscillations, Wigner functions, or the qutip-tutorials notebook collection
