#!/usr/bin/env python
"""Hello, quantum world — Rabi oscillations of a driven qubit.

This is the "hello world" of QuTiP: the smallest simulation that exercises the
library's core workflow end to end —

    build a Hamiltonian  ->  evolve a quantum state  ->  measure observables
                          ->  visualize on the Bloch sphere

Physics: a qubit starting in its ground state |0>, driven on resonance with
Rabi frequency Omega, flops between |0> and |1>. The analytic solution is
<sigma_z>(t) = cos(Omega * t), which makes the exercise self-verifying: the
script compares the numerical result against the closed form and reports
PASS/FAIL. It then repeats the evolution with amplitude damping (T1 decay) to
show the oscillations decohering — the part you need QuTiP for, since closed
forms get painful once dissipation enters.

Outputs (saved to output/):
  hello-rabi-oscillations.png  — <sigma_z>(t): ideal vs analytic vs damped
  hello-bloch-sphere.png       — the qubit's trajectory on the Bloch sphere
"""

import os

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import qutip

OUT = os.path.join(os.path.dirname(__file__), "..", "output")
os.makedirs(OUT, exist_ok=True)

# --- 1. Build the Hamiltonian: resonant drive with Rabi frequency Omega ----
Omega = 2 * np.pi * 1.0          # one full flop per unit time
H = Omega / 2 * qutip.sigmax()   # rotating-frame drive Hamiltonian

psi0 = qutip.basis(2, 0)         # start in the ground state |0>
times = np.linspace(0.0, 3.0, 301)
e_ops = [qutip.sigmax(), qutip.sigmay(), qutip.sigmaz()]

# --- 2. Evolve: ideal (Schrodinger) and damped (Lindblad master equation) --
ideal = qutip.sesolve(H, psi0, times, e_ops=e_ops)

gamma = 0.4                                  # T1 relaxation rate
c_ops = [np.sqrt(gamma) * qutip.sigmam()]    # amplitude damping
damped = qutip.mesolve(H, psi0, times, c_ops, e_ops=e_ops)

# --- 3. Verify against the analytic solution <sz>(t) = cos(Omega t) --------
analytic_sz = np.cos(Omega * times)
max_err = np.max(np.abs(ideal.expect[2] - analytic_sz))
tol = 1e-4
status = "PASS" if max_err < tol else "FAIL"
print("Hello, quantum world!")
print(f"Rabi frequency Omega = 2*pi * 1.0  ->  expected flop period = 1.0")
print(f"Max |numeric - analytic| for <sigma_z>: {max_err:.2e}  "
      f"(tol {tol:g})  [{status}]")

# --- 4. Plot <sigma_z>(t) --------------------------------------------------
fig, ax = plt.subplots(figsize=(7, 4))
ax.plot(times, ideal.expect[2], label="QuTiP (ideal)")
ax.plot(times, analytic_sz, "k--", lw=1, label=r"analytic $\cos(\Omega t)$")
ax.plot(times, damped.expect[2], label=f"QuTiP (T1 decay, $\\gamma$={gamma})")
ax.set_xlabel("Time")
ax.set_ylabel(r"$\langle\sigma_z\rangle$")
ax.set_title("Hello, quantum world — Rabi oscillations of a driven qubit")
ax.legend()
fig.tight_layout()
rabi_path = os.path.join(OUT, "hello-rabi-oscillations.png")
fig.savefig(rabi_path, dpi=150)
plt.close(fig)
print(f"Saved plot: {rabi_path}")

# --- 5. Visualize the damped trajectory on the Bloch sphere ----------------
bloch = qutip.Bloch()
bloch.add_points([damped.expect[0], damped.expect[1], damped.expect[2]],
                 meth="l")
bloch.add_vectors([damped.expect[0][-1],
                   damped.expect[1][-1],
                   damped.expect[2][-1]])
bloch_path = os.path.join(OUT, "hello-bloch-sphere.png")
bloch.save(bloch_path)
print(f"Saved plot: {bloch_path}")

if status != "PASS":
    raise SystemExit(1)
