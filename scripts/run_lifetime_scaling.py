#!/usr/bin/env python
"""Radiative lifetime scaling with size and disorder (Fig. 12 of arXiv:2602.02868v1).

For each assembly size we build the ordered 1JFF microtubule segment, form the
collective decay matrix G, and read off the most superradiant (max Gamma) and
most subradiant (min Gamma) collective rates. The physical radiative lifetime is

    tau = 1 / (2 pi c Gamma_cm),   c = 2.99792458e10 cm/s,

with Gamma_cm the rate converted to cm^-1. We repeat under:

  * ordered              — repeated 1JFF units (paper's solid blue curve)
  * static disorder      — uniform diagonal site-energy noise, width W cm^-1
                           (paper's dashed red curve, W = 200 cm^-1)
  * structural jitter    — Gaussian positional jitter on every Trp site, a
                           workstation proxy for the paper's MD structural
                           disorder (green dotted curve), since the authors' MD
                           trajectory/snapshots are not public.

Note on decay rates: as elsewhere in this repo, the collective rates come from
the excitonic eigenstates (Gamma_j = <v_j|G|v_j>) rather than the imaginary part
of the strongly non-normal H_eff, which is numerically unstable when the
near-field coherent coupling dominates.

The paper scales to 100 spirals (1300 dimers, 10400 sites) on HPC. This runner
covers the workstation-tractable range and shows the same qualitative scaling:
superradiant lifetimes shorten and subradiant lifetimes lengthen with size in
the ordered lattice, while disorder compresses that contrast.
"""

from __future__ import annotations

import argparse
import csv
import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microtubule_qif import couplings as cp  # noqa: E402
from microtubule_qif import geometry as geo  # noqa: E402
from microtubule_qif import model as md  # noqa: E402

LIGHT_CM_S = 2.99792458e10


def assembly_for(n_spirals: int):
    """Return dipoles for a size, using a single dimer for the smallest point."""
    if n_spirals == 0:
        return geo.build_dimer(), 1          # 1 tubulin dimer
    return geo.build_segment(n_spirals=n_spirals), n_spirals * geo.DIMERS_PER_SPIRAL


def lifetimes(net: md.Network) -> tuple[float, float]:
    _, decay, _ = net.eigenmodes()
    decay_cm = np.abs(cp.rad_per_ps_to_cm(decay))
    with np.errstate(divide="ignore"):
        tau = 1.0 / (2 * np.pi * LIGHT_CM_S * decay_cm)
    tau_super = float(tau[np.argmax(decay)])   # shortest-lived / brightest
    tau_sub = float(tau[np.argmin(decay)])     # longest-lived / darkest
    return tau_super, tau_sub


def perturbed_network(dipoles, seed: int, static_cm: float,
                      jitter_nm: float) -> md.Network:
    rng = np.random.default_rng(seed)
    dips = dipoles
    if jitter_nm:
        dips = [geo.Dipole(d.name, d.position + rng.normal(scale=jitter_nm, size=3),
                           d.mu, d.residue) for d in dipoles]
    disorder = None
    if static_cm:
        disorder = rng.uniform(-static_cm / 2, static_cm / 2, size=len(dips))
    return md.build_physical_network(dips, site_energies_cm=disorder)


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--spirals", type=int, nargs="*",
                    default=[0, 1, 2, 3, 5, 10, 20],
                    help="spiral counts (0 = single tubulin dimer)")
    ap.add_argument("--static-cm", type=float, default=200.0)
    ap.add_argument("--jitter-nm", type=float, default=0.3)
    ap.add_argument("--seed", type=int, default=260202868)
    ap.add_argument("--output-dir", type=Path,
                    default=ROOT / "output" / "microtubule-qif-lifetimes")
    args = ap.parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    rows = []
    for ns in args.spirals:
        dipoles, n_dimers = assembly_for(ns)
        ordered = md.build_physical_network(dipoles)
        n_sites = ordered.N
        ts_o, tb_o = lifetimes(ordered)
        ts_s, tb_s = lifetimes(perturbed_network(dipoles, args.seed,
                                                 args.static_cm, 0.0))
        ts_j, tb_j = lifetimes(perturbed_network(dipoles, args.seed,
                                                 0.0, args.jitter_nm))
        rows.append({
            "spirals": ns, "dimers": n_dimers, "sites": n_sites,
            "tau_super_ordered": ts_o, "tau_sub_ordered": tb_o,
            "tau_super_static": ts_s, "tau_sub_static": tb_s,
            "tau_super_jitter": ts_j, "tau_sub_jitter": tb_j,
        })
        print(f"spirals={ns:>3} sites={n_sites:>5}  "
              f"ordered tau_sub={tb_o:.2e}s  static tau_sub={tb_s:.2e}s  "
              f"jitter tau_sub={tb_j:.2e}s", flush=True)

    csv_path = args.output_dir / "lifetimes.csv"
    with csv_path.open("w", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)

    sizes = [r["dimers"] for r in rows]
    fig, ax = plt.subplots(figsize=(8, 5.2))
    styles = [
        ("ordered", "-", "#1f5fbf"),
        ("static", "--", "#c1121f"),
        ("jitter", ":", "#2a9d3a"),
    ]
    for key, ls, col in styles:
        ax.plot(sizes, [r[f"tau_sub_{key}"] for r in rows], ls, marker="s",
                color=col, label=f"subradiant ({key})")
        ax.plot(sizes, [r[f"tau_super_{key}"] for r in rows], ls, marker="o",
                color=col, alpha=0.6, label=f"superradiant ({key})")
    ax.set_xscale("log")
    ax.set_yscale("log")
    ax.set_xlabel("assembly size (number of tubulin dimers)")
    ax.set_ylabel("radiative lifetime (s)")
    ax.set_title("Superradiant / subradiant lifetime scaling (Fig. 12)")
    ax.legend(fontsize=7, ncol=2)
    ax.grid(True, which="both", alpha=0.25)
    fig.tight_layout()
    fig.savefig(args.output_dir / "lifetimes-fig12.png", dpi=160)
    plt.close(fig)
    print(f"wrote {csv_path} and lifetimes-fig12.png")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
