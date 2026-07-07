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

## Environment

Verified with QuTiP 5.3.0, NumPy 2.5.1, SciPy 1.18.0, matplotlib 3.11.0 on Python 3.13.2 (macOS arm64, Accelerate BLAS).
