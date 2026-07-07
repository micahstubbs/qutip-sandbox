"""Quantum information measures (Appendix C of arXiv:2602.02868v1).

All functions operate on QuTiP Qobj density matrices in the ground+excitation
space produced by :mod:`model`. Reductions "respect the single-excitation
model": population outside a chosen subsystem is traced into that subsystem's
local ground state, so every reduced state lives in a (k+1)-dimensional
ground+excitation space of its own.
"""

from __future__ import annotations

import numpy as np
import qutip as qt


def l1_coherence(rho: qt.Qobj) -> float:
    """l1-norm of coherence: sum of absolute off-diagonal elements (Eq. 30)."""
    m = rho.full()
    return float(np.sum(np.abs(m)) - np.sum(np.abs(np.diag(m))))


def pair_l1_coherence(rho: qt.Qobj, i: int, j: int) -> float:
    """l1 coherence carried by the (i, j) site pair: 2|rho_{i+1,j+1}|.

    Sites are 0-indexed; the +1 offset skips the ground state. This is the
    per-pair contribution to the network l1 coherence used to rank the "most
    coherent chromophore pairs" in Figs 2-5, 8.
    """
    m = rho.full()
    return float(2.0 * np.abs(m[i + 1, j + 1]))


def reduce_to_sites(rho: qt.Qobj, sites: list[int]) -> qt.Qobj:
    """Reduced density matrix on a subset of sites (0-indexed).

    Builds a (k+1)-dim ground+excitation state: index 0 is the local ground
    (all population not on the chosen sites, incl. the global ground), and
    indices 1..k are the chosen single-excitation site states. This is the
    single-excitation-consistent partial trace of Appendix C.3.
    """
    m = rho.full()
    k = len(sites)
    idx = [s + 1 for s in sites]          # excitation rows/cols in full space
    red = np.zeros((k + 1, k + 1), dtype=complex)
    # excitation block
    for a, ia in enumerate(idx):
        for b, ib in enumerate(idx):
            red[a + 1, b + 1] = m[ia, ib]
    for a, ia in enumerate(idx):
        red[0, a + 1] = m[0, ia]
        red[a + 1, 0] = m[ia, 0]
    # local ground = everything else (trace is preserved)
    kept = np.real(np.trace(red[1:, 1:]))
    red[0, 0] = np.real(np.trace(m)) - kept
    return qt.Qobj(red)


def correlated_coherence(rho: qt.Qobj, sites_a: list[int],
                         sites_b: list[int]) -> float:
    """Correlated coherence C_corr = C(rho_AB) - C(rho_A) - C(rho_B) (Eq. 31).

    rho_AB is reduced to the union of the two site groups; rho_A, rho_B to each.
    """
    ab = reduce_to_sites(rho, list(sites_a) + list(sites_b))
    a = reduce_to_sites(rho, list(sites_a))
    b = reduce_to_sites(rho, list(sites_b))
    return l1_coherence(ab) - l1_coherence(a) - l1_coherence(b)


def logarithmic_negativity(rho: qt.Qobj, sites_a: list[int],
                           sites_b: list[int]) -> float:
    """Logarithmic negativity E_N = log2(2N+1) across A|B (Eqs 32-33).

    The two groups are reduced to a bipartite ground+excitation space and the
    partial transpose is taken on A. N(rho) is the sum of |negative eigenvalues|
    of the partial transpose.
    """
    a = list(sites_a)
    b = list(sites_b)
    # Build a bipartite state on (ground+A) x (ground+B) consistent with the
    # single-excitation manifold: basis |gA,gB>, |eA_i,gB>, |gA,eB_j>.
    m = rho.full()
    da, db = len(a) + 1, len(b) + 1
    idx_a = [s + 1 for s in a]
    idx_b = [s + 1 for s in b]

    # Map full-space indices to bipartite (alpha, beta) product indices.
    # ground of the pair -> (0,0); excitation on A_i -> (i,0); on B_j -> (0,j).
    def prod(alpha, beta):
        return alpha * db + beta

    full_to_prod = {0: prod(0, 0)}
    for i, ia in enumerate(idx_a):
        full_to_prod[ia] = prod(i + 1, 0)
    for j, jb in enumerate(idx_b):
        full_to_prod[jb] = prod(0, j + 1)

    dim = da * db
    rho_pair = np.zeros((dim, dim), dtype=complex)
    keep = [0] + idx_a + idx_b
    for r in keep:
        for c in keep:
            rho_pair[full_to_prod[r], full_to_prod[c]] = m[r, c]
    # leftover population (excitation elsewhere) folds into the pair ground
    kept_trace = np.real(np.trace(rho_pair))
    rho_pair[prod(0, 0), prod(0, 0)] += np.real(np.trace(m)) - kept_trace

    q = qt.Qobj(rho_pair, dims=[[da, db], [da, db]])
    pt = qt.partial_transpose(q, [1, 0])
    evals = np.linalg.eigvalsh(pt.full())
    negativity = float(np.sum(np.abs(evals[evals < 0.0])))
    return float(np.log2(2.0 * negativity + 1.0))


def von_neumann_entropy(rho: qt.Qobj) -> float:
    return float(qt.entropy_vn(rho, base=2))


def mutual_information(rho: qt.Qobj, sites_a: list[int],
                       sites_b: list[int]) -> float:
    """Quantum mutual information I(A:B) = S(A)+S(B)-S(AB) (Appendix C.3)."""
    ab = reduce_to_sites(rho, list(sites_a) + list(sites_b))
    a = reduce_to_sites(rho, list(sites_a))
    b = reduce_to_sites(rho, list(sites_b))
    return (von_neumann_entropy(a) + von_neumann_entropy(b)
            - von_neumann_entropy(ab))


def trace_distance(rho1: qt.Qobj, rho2: qt.Qobj) -> float:
    """D = 1/2 || rho1 - rho2 ||_1 (Eq. for D_k(t))."""
    return float(qt.tracedist(rho1, rho2))


def non_markovianity(times: np.ndarray, distances: np.ndarray) -> float:
    """Integrated backflow N = integral over dD/dt>0 of dD/dt dt.

    Discrete version: sum of positive increments of the trace distance, which
    equals the integral of the positive part of dD/dt (Ref. [55]).
    """
    d = np.diff(distances)
    return float(np.sum(d[d > 0]))
