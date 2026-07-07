#!/usr/bin/env python
"""Export the microtubule-QIF model results to a single JSON for the web UI.

Produces docs/paper-2602.02868/ui/data.json containing everything the
interactive D3/Three.js views need:

  * geometry   — 8 Trp sites (3D positions nm + unit dipoles) for the dimer,
                 and the one-spiral (104-site) point cloud for the 3D view
  * couplings  — Delta and G matrices (dimensionless, in units of gamma)
  * spectrum   — excitonic eigenmodes: energy, Gamma_j/gamma, bright/dark
  * dynamics   — per preparation: times, per-site populations, ground pop,
                 top-4 pair L1 + log-negativity, bright/dark mode projection
  * embeddings — Fig 8 top-4 L1 across single/two/three-tubulin x 4 preps
  * backflow   — Fig 9 trace-distance series + non-Markovianity
  * lifetimes  — Fig 12 tau vs size for ordered/static/jitter

Kept deliberately compact (subsampled time grids) so the JSON stays a few
hundred KB and loads instantly.
"""

from __future__ import annotations

import json
import sys
from itertools import combinations
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microtubule_qif import couplings as cp  # noqa: E402
from microtubule_qif import geometry as geo  # noqa: E402
from microtubule_qif import measures as ms  # noqa: E402
from microtubule_qif import model as md  # noqa: E402

OUT = ROOT / "docs" / "paper-2602.02868" / "ui" / "data.json"
PREP_WINDOWS_PS = {"superradiant": 5000.0, "subradiant": 80000.0,
                   "coherent": 15000.0, "mixed": 15000.0, "localized": 15000.0}
SAMPLES = 90
LIGHT_CM_S = 2.99792458e10


def r3(x):
    return [round(float(v), 5) for v in np.asarray(x).ravel()]


def geometry_block():
    dips = geo.build_dimer()
    net = md.build_physical_network(dips)
    sites = [{
        "name": d.name,
        "residue": f"{d.residue[0]}{d.residue[1]}",
        "pos": r3(d.position),
        "mu": r3(d.mu),
    } for d in dips]
    # one-spiral point cloud (positions only) for the 3D "scale" toggle
    spiral = geo.build_segment(n_spirals=1)
    spiral_pts = [r3(d.position) for d in spiral]
    return {"dimer_sites": sites, "spiral_points": spiral_pts,
            "n_spiral": len(spiral_pts)}


def couplings_block(net):
    return {
        "labels": [f"Trp{i+1}" for i in range(net.N)],
        "Delta": [[round(float(net.Delta[i, j] / net.gamma), 3)
                   for j in range(net.N)] for i in range(net.N)],
        "G": [[round(float(net.G[i, j] / net.gamma), 4)
               for j in range(net.N)] for i in range(net.N)],
    }


def spectrum_block(net):
    energies, decay, _ = net.eigenmodes()
    e_cm = cp.rad_per_ps_to_cm(energies)
    modes = []
    for j in range(net.N):
        g = float(decay[j] / net.gamma)
        modes.append({
            "index": j,
            "energy_cm": round(float(e_cm[j]), 2),
            "gamma_over_gamma": round(g, 4),
            "kind": "bright" if g > 1.0 else "dark",
        })
    return modes


def _bright_dark_series(net, states):
    _, decay, evecs = net.eigenmodes()
    inv = np.linalg.inv(evecs)
    bright_mask = decay / net.gamma > 1.0
    bright, dark = [], []
    for rho in states:
        rho_exc = rho.full()[1:, 1:]
        w = np.clip(np.real(np.diag(inv @ rho_exc @ inv.conj().T)), 0.0, None)
        tot = w.sum()
        if tot > 0:
            w = w / tot
        bright.append(round(float(w[bright_mask].sum()), 4))
        dark.append(round(float(w[~bright_mask].sum()), 4))
    return bright, dark


def dynamics_block(net):
    out = {}
    pairs = list(combinations(range(net.N), 2))
    for kind, tmax in PREP_WINDOWS_PS.items():
        times = np.linspace(0.0, tmax, SAMPLES)
        rho0 = md.initial_state(net, kind if kind != "localized" else "localized",
                                site=0)
        res = md.evolve(net, rho0, times)
        pops = np.array([md.site_populations(net, s) for s in res.states])
        l1 = np.array([[ms.pair_l1_coherence(s, i, j) for i, j in pairs]
                       for s in res.states])
        top = np.argsort(l1.mean(axis=0))[-4:][::-1]
        logneg = np.array([[ms.logarithmic_negativity(s, [pairs[t][0]], [pairs[t][1]])
                            for t in top] for s in res.states])
        bright, dark = _bright_dark_series(net, res.states)
        out[kind] = {
            "times_ps": [round(float(t), 2) for t in times],
            "site_pops": [[round(float(v), 4) for v in row] for row in pops],
            "ground": [round(float(md.ground_population(net, s)), 4)
                       for s in res.states],
            "top_pairs": [[pairs[t][0] + 1, pairs[t][1] + 1] for t in top],
            "pair_l1": [[round(float(l1[r, t]), 4) for t in top]
                        for r in range(len(times))],
            "log_neg": [[round(float(v), 4) for v in row] for row in logneg],
            "bright": bright, "dark": dark,
        }
    return out


def backflow_block(n_tubulins=3, tmax_ps=8000.0, samples=100):
    """3-tubulin trace-distance backflow series for the interactive Fig 9 view."""
    import qutip as qt
    dips = geo.build_spiral(n_dimers=n_tubulins)
    net = md.build_physical_network(dips)
    times = np.linspace(0.0, tmax_ps, samples)
    t1 = list(range(8))

    def uniform(sites):
        amp = np.zeros(net.N)
        amp[sites] = 1.0 / np.sqrt(len(sites))
        return amp

    def series(tk, contrast):
        a, b = uniform(t1), uniform(tk)
        v1, v2 = ((a, b) if contrast == "population"
                  else ((a + b) / np.sqrt(2), (a - b) / np.sqrt(2)))
        reds = []
        for v in (v1, v2):
            vec = np.zeros(net.N + 1, dtype=complex)
            vec[1:] = v
            vec /= np.linalg.norm(vec)
            res = md.evolve(net, qt.ket2dm(qt.Qobj(vec.reshape(-1, 1))), times)
            reds.append([ms.reduce_to_sites(s, t1 + tk) for s in res.states])
        return [round(float(ms.trace_distance(r1, r2)), 4)
                for r1, r2 in zip(reds[0], reds[1])]

    neighbors = []
    for k in range(1, n_tubulins):
        tk = list(range(k * 8, (k + 1) * 8))
        pop = series(tk, "population")
        pha = series(tk, "phase")
        neighbors.append({
            "label": f"T1-T{k+1}",
            "population": pop,
            "phase": pha,
            "N_population": round(ms.non_markovianity(times, np.array(pop)), 4),
            "N_phase": round(ms.non_markovianity(times, np.array(pha)), 4),
        })
    return {"times_ps": [round(float(t), 1) for t in times],
            "n_sites": net.N, "neighbors": neighbors}


def load_json(path):
    p = ROOT / path
    return json.loads(p.read_text()) if p.exists() else None


def lifetimes_block():
    p = ROOT / "output" / "microtubule-qif-lifetimes" / "lifetimes.csv"
    if not p.exists():
        return None
    import csv
    rows = list(csv.DictReader(p.open()))
    keys = ["dimers", "sites", "tau_super_ordered", "tau_sub_ordered",
            "tau_super_static", "tau_sub_static", "tau_super_jitter",
            "tau_sub_jitter"]
    return [{k: float(r[k]) for k in keys} for r in rows]


def main() -> int:
    net = md.build_physical_network(geo.build_dimer())
    data = {
        "meta": {
            "paper": "arXiv:2602.02868v1",
            "title": "Quantum Information Flow in Microtubule Tryptophan Networks",
            "gamma_cm": cp.DEFAULT_TRP_GAMMA_CM,
            "lambda0_nm": cp.LAMBDA0_NM,
            "n_dimer": net.N,
            "bright_max": round(float(net.eigenmodes()[1].max() / net.gamma), 3),
            "dark_min": round(float(net.eigenmodes()[1].min() / net.gamma), 3),
        },
        "geometry": geometry_block(),
        "couplings": couplings_block(net),
        "spectrum": spectrum_block(net),
        "dynamics": dynamics_block(net),
        "embeddings": load_json("output/microtubule-qif-embeddings/summary.json"),
        "backflow": backflow_block(),
        "lifetimes": lifetimes_block(),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(data, separators=(",", ":")) + "\n")
    kb = OUT.stat().st_size / 1024
    print(f"wrote {OUT} ({kb:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
