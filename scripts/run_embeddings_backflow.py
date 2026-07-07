#!/usr/bin/env python
"""Embeddings (Fig. 8) and non-Markovian backflow (Fig. 9) of arXiv:2602.02868v1.

Two analyses that probe how surrounding tubulins reshape a focal tubulin's
correlations:

Fig. 8 — Embedding sweep. Track the four largest pairwise L1 coherences within a
  focal tubulin (T1 = the first dimer's eight Trps) as the environment grows:
  single tubulin (8 sites), two tubulins (16), and a three-tubulin spiral segment
  (24). For each embedding we run the four initial preparations the paper
  compares (coherent, mixed, superradiant, subradiant), restricting the
  preparation to the focal tubulin.

Fig. 9 — Non-Markovian backflow. Within a small spiral segment we form the
  two-tubulin subsystem X = T1 ∪ Tk, propagate the full segment under the
  trace-preserving Lindbladian, and trace out the remaining tubulin(s). Memory
  is quantified by revivals of the trace distance between two orthogonal
  preparations (population-contrast |10> vs |01>, and phase-contrast
  (|10>±|01>)/√2), with scalar non-Markovianity N = ∫_{dD/dt>0} dD/dt.

Feasibility: the exact-Liouvillian propagator handles up to ~24 sites (three
tubulins) on a workstation. The paper's full one-spiral (13 tubulins, 104 sites)
and larger assemblies were run on HPC; those sizes are out of reach here and are
reported as such. The physics of embedding-driven redistribution and
reservoir-induced backflow is already visible at the three-tubulin scale.
"""

from __future__ import annotations

import argparse
import csv
import sys
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microtubule_qif import geometry as geo  # noqa: E402
from microtubule_qif import measures as ms  # noqa: E402
from microtubule_qif import model as md  # noqa: E402

TRP_PER_TUBULIN = 8
INIT_STATES = ["coherent", "mixed", "superradiant", "subradiant"]


def focal_initial_state(net: md.Network, kind: str,
                        focal_sites: list[int]) -> "object":
    """Preparation restricted to the focal tubulin's sites (0-indexed).

    For coherent/mixed we build a uniform (super)position over the focal sites;
    for super/subradiant we take the focal-tubulin excitonic eigenstate with the
    max/min collective rate, computed from the focal block of Delta and G.
    """
    N, dim = net.N, net.N + 1
    if kind == "coherent":
        amp = np.zeros(N)
        amp[focal_sites] = 1.0
        return _dm_from_amp(amp, dim)
    if kind == "mixed":
        rho = np.zeros((dim, dim), dtype=complex)
        for s in focal_sites:
            rho[s + 1, s + 1] = 1.0 / len(focal_sites)
        import qutip as qt
        return qt.Qobj(rho)
    if kind in ("superradiant", "subradiant"):
        block = np.ix_(focal_sites, focal_sites)
        H_coh = net.Delta[block]
        energies, V = np.linalg.eigh(H_coh)
        rates = np.array([np.real(V[:, j].conj() @ net.G[block] @ V[:, j])
                          for j in range(len(focal_sites))])
        pick = np.argmax(rates) if kind == "superradiant" else np.argmin(rates)
        amp = np.zeros(N)
        amp[focal_sites] = V[:, pick]
        return _dm_from_amp(amp, dim)
    raise ValueError(kind)


def _dm_from_amp(amp: np.ndarray, dim: int):
    import qutip as qt
    vec = np.zeros(dim, dtype=complex)
    vec[1:] = amp
    nrm = np.linalg.norm(vec)
    if nrm:
        vec /= nrm
    return qt.ket2dm(qt.Qobj(vec.reshape(-1, 1)))


def top_pairs_within(states, focal_sites: list[int], k: int = 4):
    """Return the k focal-tubulin site pairs with the largest time-averaged L1."""
    pairs = list(combinations(focal_sites, 2))
    l1 = np.array([[ms.pair_l1_coherence(s, i, j) for i, j in pairs]
                   for s in states])
    top = np.argsort(l1.mean(axis=0))[-k:][::-1]
    return [pairs[t] for t in top], l1[:, top]


def run_embeddings(out_dir: Path, tmax_ps: float, samples: int) -> dict:
    embeddings = [("single", 1), ("two-tubulin", 2), ("three-tubulin", 3)]
    focal = list(range(TRP_PER_TUBULIN))   # T1 = first tubulin
    times = np.linspace(0.0, tmax_ps, samples)

    fig, axes = plt.subplots(len(embeddings), len(INIT_STATES),
                             figsize=(15, 9), sharex=True)
    summary = {}
    for r, (label, n_dimers) in enumerate(embeddings):
        dips = geo.build_spiral(n_dimers=n_dimers)
        net = md.build_physical_network(dips)
        summary[label] = {"n_sites": net.N, "preparations": {}}
        for c, kind in enumerate(INIT_STATES):
            rho0 = focal_initial_state(net, kind, focal)
            res = md.evolve(net, rho0, times)
            top_pairs, l1_top = top_pairs_within(res.states, focal)
            ax = axes[r, c]
            for p in range(l1_top.shape[1]):
                i, j = top_pairs[p]
                ax.plot(times, l1_top[:, p], lw=1,
                        label=f"({i + 1},{j + 1})")
            ax.legend(fontsize=6, ncol=2)
            if r == 0:
                ax.set_title(kind)
            if c == 0:
                ax.set_ylabel(f"{label}\n({net.N} sites)\npair $L_1$")
            if r == len(embeddings) - 1:
                ax.set_xlabel("time (ps)")
            summary[label]["preparations"][kind] = {
                "top_pairs": [[i + 1, j + 1] for i, j in top_pairs],
                "max_pair_l1": float(l1_top.max()),
            }
    fig.suptitle("Embedding sweep: top-4 focal-tubulin $L_1$ coherences (Fig. 8)")
    fig.tight_layout()
    fig.savefig(out_dir / "embeddings-fig8.png", dpi=150)
    plt.close(fig)
    return summary


# --------------------------------------------------------------------------
# Fig. 9: non-Markovian backflow
# --------------------------------------------------------------------------

def _uniform_over(sites: list[int], N: int) -> np.ndarray:
    amp = np.zeros(N)
    amp[sites] = 1.0 / np.sqrt(len(sites))
    return amp


def _reduced_states(net, states, keep_sites):
    return [ms.reduce_to_sites(s, keep_sites) for s in states]


def backflow_for_pair(net, t1, tk, times, contrast: str):
    """Trace-distance dynamics D(t) between two preparations of X = T1 ∪ Tk,
    tracing out all other sites. contrast in {'population','phase'}."""
    import qutip as qt
    N, dim = net.N, net.N + 1
    a = _uniform_over(t1, N)   # |10>
    b = _uniform_over(tk, N)   # |01>
    if contrast == "population":
        v1, v2 = a, b
    else:  # phase contrast
        v1, v2 = (a + b) / np.sqrt(2.0), (a - b) / np.sqrt(2.0)

    keep = t1 + tk
    dists = []
    for v in (v1, v2):
        vec = np.zeros(dim, dtype=complex)
        vec[1:] = v
        vec /= np.linalg.norm(vec)
        rho0 = qt.ket2dm(qt.Qobj(vec.reshape(-1, 1)))
        res = md.evolve(net, rho0, times)
        dists.append(_reduced_states(net, res.states, keep))
    D = np.array([ms.trace_distance(r1, r2)
                  for r1, r2 in zip(dists[0], dists[1])])
    return D


def run_backflow(out_dir: Path, tmax_ps: float, samples: int,
                 n_tubulins: int = 3) -> dict:
    dips = geo.build_spiral(n_dimers=n_tubulins)
    net = md.build_physical_network(dips)
    times = np.linspace(0.0, tmax_ps, samples)
    t1 = list(range(TRP_PER_TUBULIN))

    fig, ax = plt.subplots(figsize=(8, 4.5))
    summary = {"n_sites": net.N, "n_tubulins": n_tubulins, "neighbors": {}}
    for k in range(1, n_tubulins):
        tk = list(range(k * TRP_PER_TUBULIN, (k + 1) * TRP_PER_TUBULIN))
        row = {}
        for contrast, style in (("population", "-"), ("phase", "--")):
            D = backflow_for_pair(net, t1, tk, times, contrast)
            Nmark = ms.non_markovianity(times, D)
            row[contrast] = {"non_markovianity": float(Nmark)}
            ax.plot(times, D, style, lw=1.3,
                    label=f"X({k + 1}) {contrast} (N={Nmark:.2e})")
        summary["neighbors"][f"T1-T{k + 1}"] = row
    ax.set_xlabel("time (ps)")
    ax.set_ylabel(r"trace distance $D_k(t)$")
    ax.set_title(f"Non-Markovian backflow, {n_tubulins}-tubulin segment (Fig. 9)")
    ax.legend(fontsize=7)
    fig.tight_layout()
    fig.savefig(out_dir / "backflow-fig9.png", dpi=150)
    plt.close(fig)
    return summary


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--output-dir", type=Path,
                    default=ROOT / "output" / "microtubule-qif-embeddings")
    ap.add_argument("--embed-tmax-ps", type=float, default=15000.0)
    ap.add_argument("--backflow-tmax-ps", type=float, default=8000.0)
    ap.add_argument("--samples", type=int, default=120)
    ap.add_argument("--backflow-tubulins", type=int, default=3)
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    import json
    print("running embedding sweep (Fig. 8)...", flush=True)
    emb = run_embeddings(args.output_dir, args.embed_tmax_ps, args.samples)
    print("running backflow analysis (Fig. 9)...", flush=True)
    bf = run_backflow(args.output_dir, args.backflow_tmax_ps, args.samples,
                      args.backflow_tubulins)

    summary = {
        "paper": "arXiv:2602.02868v1",
        "note": ("Embeddings and backflow at up to 3 tubulins (24 sites); the "
                 "paper's full 13-tubulin spiral (104 sites) and larger "
                 "assemblies required HPC and are out of workstation reach."),
        "embeddings_fig8": emb,
        "backflow_fig9": bf,
    }
    (args.output_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {args.output_dir / 'summary.json'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
