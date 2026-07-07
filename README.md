# qutip-sandbox

A sandbox for exploring [QuTiP](https://qutip.org/) (Quantum Toolbox in Python) — installation, canonical examples, and a "hello world" exercise.

## Setup

```bash
python3.13 -m venv .venv
.venv/bin/pip install -r requirements.txt
.venv/bin/python -c "import qutip; qutip.about()"
```

Requires Python ≥ 3.10 (QuTiP 5).

## Scripts

### `scripts/run_examples.py`

The pip package ships no runnable example scripts (official examples live as notebooks in [qutip-tutorials](https://github.com/qutip/qutip-tutorials)), so this script adapts three canonical examples from the QuTiP 5 docs:

1. **Basics** — states, operators, expectation values (verifies ⟨n⟩ = |α|² for a coherent state)
2. **Dissipative qubit dynamics** — the docs' front-page `mesolve` example
3. **Driven damped cavity** — steady-state Lorentzian response via `steadystate`

```bash
.venv/bin/python scripts/run_examples.py
```

### `scripts/hello_qutip.py` — the hello world exercise

**Rabi oscillations of a driven qubit.** This is the natural QuTiP hello world because it is the smallest simulation that exercises the library's whole core workflow:

build a Hamiltonian → evolve a state (`sesolve`/`mesolve`) → measure observables (`expect`) → visualize (`Bloch`)

It is also self-verifying: the ideal evolution has the closed form ⟨σz⟩(t) = cos(Ωt), and the script asserts the numerical result matches to <1e-4 (observed error ~1.6e-5). It then adds T1 amplitude damping to show the oscillations decohere — the regime where you actually need a numerical toolbox.

```bash
.venv/bin/python scripts/hello_qutip.py
```

Outputs in `output/`:

- `hello-rabi-oscillations.png` — ⟨σz⟩(t): ideal vs analytic vs damped
- `hello-bloch-sphere.png` — the damped trajectory spiraling into the Bloch sphere

### `scripts/run_microtubule_qif.py` — arXiv:2602.02868v1 implementation

Implements the published model from Gassab, Pusuluk & Craddock, *Quantum Information Flow in Microtubule Tryptophan Networks*:

- extracts the eight Trp chromophores from `data/1JFF.pdb`
- uses the CD2/CE2 midpoint and 46.2 degree in-plane Trp 1La transition-dipole convention used by the cited microtubule construction work
- builds the coherent dipole coupling matrix `Delta` and collective decay matrix `G` from Eqs. 9-10
- diagonalizes `H_eff = H0 + Delta - iG/2`
- evolves superradiant, subradiant, coherent, mixed, and localized preparations with a trace-preserving Lindblad equation in the single-excitation-plus-ground space
- computes site populations, pair `L1` coherence, correlated coherence helpers, logarithmic negativity, mutual information helpers, and trace-distance backflow helpers

```bash
.venv/bin/python scripts/run_microtubule_qif.py
.venv/bin/python -m pytest -q tests/test_model_measures.py
```

Outputs in `output/microtubule-qif/`:

- `sites.csv`, `matrices.npz`, `modes.csv`, `summary.json`
- `spectrum.png`
- `dynamics-{superradiant,subradiant,coherent,mixed}.png`
- `localized-injections.png`

Larger ordered assemblies can be built for spectral analysis:

```bash
.venv/bin/python scripts/run_microtubule_qif.py --assembly one-spiral --skip-dynamics
.venv/bin/python scripts/run_microtubule_qif.py --static-disorder-cm 200 --skip-dynamics
```

The paper's exact molecular-dynamics structural-disorder ensemble and author code are not bundled with the arXiv source, so this repo implements the ordered 1JFF reconstruction plus parameterized static disorder and random positional/dipole jitter. See `docs/paper-2602.02868/implementation-notes.md` and `docs/paper-2602.02868/reproduction-gap-report.md`.

The static walkthrough UI is `docs/paper-2602.02868/ui/index.html`; it can be opened directly in a browser and uses the generated plots in `output/microtubule-qif/`.

## Environment

Verified with QuTiP 5.3.0, NumPy 1.26.4, SciPy 1.17.1, matplotlib 3.11.0 on Python 3.13.2 (macOS arm64, Accelerate BLAS).
