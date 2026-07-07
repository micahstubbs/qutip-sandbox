# Implementation notes for arXiv:2602.02868v1

Paper: Lea Gassab, Onur Pusuluk, Travis J.A. Craddock, "Quantum Information Flow in Microtubule Tryptophan Networks" (2026).

Local entry points:

- `src/microtubule_qif/geometry.py`
- `src/microtubule_qif/couplings.py`
- `src/microtubule_qif/model.py`
- `src/microtubule_qif/measures.py`
- `scripts/run_microtubule_qif.py`

## Geometry

The dimer model extracts the eight tryptophan residues identified in Fig. 1:

1. alpha 21
2. alpha 346
3. alpha 388
4. alpha 407
5. beta 21
6. beta 103
7. beta 346
8. beta 407

The Trp chromophore position is the midpoint of CD2 and CE2. The transition dipole is the in-plane 1La direction: 46.2 degrees above the axis from that midpoint to CD1, toward NE1. This convention is stated in the microtubule construction work cited by the paper.

Ordered assemblies use the Appendix A parameters:

- 13 dimers per spiral
- -55.38 degree initial rotation about the longitudinal axis
- 11.7 degree tilt about an x-parallel axis through beta Trp346 CD2
- 11.2 nm radial y translation and 0.3 nm z translation
- 27.69 degree rotation and 0.9 nm x translation per dimer around a spiral
- 8.0 nm x translation between spirals

The local geometry test checks that this construction produces a one-spiral
mean radius near 11.2 nm and that the beta Trp346 CD2 pivot is taken from the
raw 1JFF atom coordinates before centering.

The exact author MD trajectory is not in the arXiv source. The runner therefore supports only reproducible 1JFF ordered geometry plus optional random positional/dipole jitter as a local proxy for structural disorder.

## Dynamics

`couplings.py` implements Eq. 9 and Eq. 10 for the coherent dipole matrix `Delta` and collective decay matrix `G`, with `lambda0 = 280 nm`.

The QuTiP model uses the paper's single-excitation-plus-ground-state space:

- basis index 0 is the ground/sink state
- basis indices 1..N are single-site excitations
- Hamiltonian block is `H = H0 + Delta`
- collective jump operators come from `G = V Lambda V^dagger`
- `L_j = sqrt(gamma_j) sum_n v_n^(j) |0><n|`

The optical carrier is removed as a rotating-frame global phase. Static energetic disorder is represented as diagonal site-energy shifts.

The default single-Trp radiative rate is `gamma = 2.73e-3 cm^-1`, converted to angular `ps^-1` using

```text
rate_rad_per_ps = 2*pi*c_cm_per_s*rate_cm / 1e12
```

This matches the paper's lifetime relation `tau = 1/(2*pi*c*Gamma_cm)`.

For the dimer and two-dimer cases, the default propagator diagonalizes the time-independent Liouvillian exactly. This avoids stiff adaptive ODE integration caused by near-field coherent couplings that are much faster than radiative decay. `mesolve` remains available with `method="mesolve"` for direct QuTiP integration.

## Measures

`measures.py` implements Appendix C:

- `l1_coherence`
- pair contribution `2|rho_ij|`
- `correlated_coherence = C_l1(rho_AB) - C_l1(rho_A) - C_l1(rho_B)`
- logarithmic negativity from an explicit partial transpose
- quantum mutual information
- trace distance and positive-variation non-Markovianity

All reductions respect the single-excitation model: excitation population outside a chosen subsystem is traced into that subsystem's local ground state.

## Reproduction boundary

The implementation reproduces the model equations and qualitative single-dimer behaviors from the paper:

- superradiant preparation rapidly exports excitation
- subradiant preparation retains excitation longer
- coherent preparation starts with large `L1` coherence and nonzero pair entanglement
- mixed preparation has much weaker coherence/entanglement
- localized injections are site selective; in the local run, Trp4 and Trp7 retain the most excitation at 15 ns

It is not a bit-for-bit reproduction of the paper figures because the arXiv source contains the manuscript and rendered figures, but not the original simulation code, exact dipole extraction code, or MD structural-disorder ensemble.
See `reproduction-gap-report.md` for the current web-search findings and the
remaining information needed for a full reproduction.
