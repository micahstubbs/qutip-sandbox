#!/usr/bin/env python
"""Run canonical QuTiP examples adapted from the official docs (qutip.org).

The pip package ships no runnable example scripts (official examples live as
notebooks in https://github.com/qutip/qutip-tutorials), so this script adapts
three canonical examples from the QuTiP 5 documentation:

1. Basics — creating states and operators, expectation values
2. Qubit dynamics with dissipation (the docs front-page mesolve example)
3. Steady state of a driven, damped cavity

Plots are saved to output/.
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import qutip

OUT = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUT, exist_ok=True)


def example_basics():
    """States, operators, and expectation values."""
    print("=" * 60)
    print("Example 1: basics — states, operators, expectation values")
    print("=" * 60)

    # A qubit in the excited state
    up = qutip.basis(2, 0)
    print("Excited state |0>:\n", up)

    # Pauli operators
    sz = qutip.sigmaz()
    sx = qutip.sigmax()
    print("<sz> for |0> =", qutip.expect(sz, up))

    # Superposition (|0> + |1>)/sqrt(2)
    plus = (qutip.basis(2, 0) + qutip.basis(2, 1)).unit()
    print("<sz> for |+> =", qutip.expect(sz, plus))
    print("<sx> for |+> =", qutip.expect(sx, plus))

    # A harmonic-oscillator coherent state
    N = 20
    alpha = 2.0
    coh = qutip.coherent(N, alpha)
    n_op = qutip.num(N)
    print(f"Coherent state |alpha={alpha}>: <n> =", qutip.expect(n_op, coh))
    print()


def example_qubit_dissipation():
    """Qubit precession with dephasing — the docs' front-page mesolve example."""
    print("=" * 60)
    print("Example 2: dissipative qubit dynamics (mesolve)")
    print("=" * 60)

    H = 2 * np.pi * 0.1 * qutip.sigmax()
    psi0 = qutip.basis(2, 0)
    times = np.linspace(0.0, 10.0, 200)

    # Unitary evolution vs. evolution with a relaxation collapse operator
    result_unitary = qutip.sesolve(H, psi0, times, e_ops=[qutip.sigmaz()])
    c_ops = [np.sqrt(0.05) * qutip.sigmax()]
    result_dissip = qutip.mesolve(H, psi0, times, c_ops, e_ops=[qutip.sigmaz()])

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(times, result_unitary.expect[0], label="unitary")
    ax.plot(times, result_dissip.expect[0], label="with dissipation")
    ax.set_xlabel("Time")
    ax.set_ylabel(r"$\langle\sigma_z\rangle$")
    ax.set_title("Qubit precession with and without dissipation")
    ax.legend()
    fig.tight_layout()
    path = os.path.join(OUT, "example-qubit-dissipation.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    print(f"Final <sz> unitary:     {result_unitary.expect[0][-1]:+.4f}")
    print(f"Final <sz> dissipative: {result_dissip.expect[0][-1]:+.4f}")
    print(f"Saved plot: {path}")
    print()


def example_driven_cavity_steadystate():
    """Steady state photon number of a driven, damped cavity."""
    print("=" * 60)
    print("Example 3: driven damped cavity steady state")
    print("=" * 60)

    N = 15
    a = qutip.destroy(N)
    kappa = 0.5   # cavity decay rate
    drive = 0.5   # drive amplitude

    detunings = np.linspace(-2.0, 2.0, 81)
    n_ss = []
    for delta in detunings:
        H = delta * a.dag() * a + drive * (a + a.dag())
        rho_ss = qutip.steadystate(H, [np.sqrt(kappa) * a])
        n_ss.append(qutip.expect(a.dag() * a, rho_ss))

    fig, ax = plt.subplots(figsize=(7, 4))
    ax.plot(detunings, n_ss)
    ax.set_xlabel("Detuning")
    ax.set_ylabel(r"Steady-state $\langle n\rangle$")
    ax.set_title("Lorentzian response of a driven, damped cavity")
    fig.tight_layout()
    path = os.path.join(OUT, "example-driven-cavity.png")
    fig.savefig(path, dpi=150)
    plt.close(fig)
    peak = max(n_ss)
    print(f"Peak steady-state photon number: {peak:.4f} (at resonance)")
    print(f"Saved plot: {path}")
    print()


if __name__ == "__main__":
    print("QuTiP", qutip.__version__, "\n")
    example_basics()
    example_qubit_dissipation()
    example_driven_cavity_steadystate()
    print("All examples completed.")
