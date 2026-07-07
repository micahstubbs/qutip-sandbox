#!/usr/bin/env python
"""Run the microtubule tryptophan quantum-information-flow model.

This implements the reproducible core of

    Gassab, Pusuluk & Craddock,
    "Quantum Information Flow in Microtubule Tryptophan Networks",
    arXiv:2602.02868v1 (2026).

Default behavior builds the eight-site 1JFF tubulin-dimer Trp network, computes
the coherent dipole matrix Delta and collective decay matrix G, diagonalizes the
effective non-Hermitian generator, and evolves the paper's initial preparations
under the trace-preserving Lindblad equation.
"""

from __future__ import annotations

import argparse
import csv
import json
import sys
from itertools import combinations
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from microtubule_qif import couplings as cp  # noqa: E402
from microtubule_qif import geometry as geo  # noqa: E402
from microtubule_qif import measures as ms  # noqa: E402
from microtubule_qif import model as md  # noqa: E402


PREP_WINDOWS_PS = {
    "superradiant": 5000.0,
    "subradiant": 80000.0,
    "coherent": 15000.0,
    "mixed": 15000.0,
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Reproduce the Lindblad Trp-network model from arXiv:2602.02868v1."
    )
    parser.add_argument("--assembly", choices=["dimer", "two-dimer", "one-spiral", "two-spiral"],
                        default="dimer")
    parser.add_argument("--pdb", type=Path, default=ROOT / "data" / "1JFF.pdb")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "output" / "microtubule-qif")
    parser.add_argument("--gamma-cm", type=float, default=cp.DEFAULT_TRP_GAMMA_CM,
                        help="single-Trp radiative rate in cm^-1")
    parser.add_argument("--la-angle-deg", type=float, default=46.2)
    parser.add_argument("--static-disorder-cm", type=float, default=0.0,
                        help="uniform diagonal disorder width W in cm^-1")
    parser.add_argument("--structural-jitter-nm", type=float, default=0.0,
                        help="Gaussian positional jitter applied to each Trp site")
    parser.add_argument("--dipole-jitter-deg", type=float, default=0.0,
                        help="Gaussian random rotation of each dipole orientation")
    parser.add_argument("--seed", type=int, default=260202868)
    parser.add_argument("--samples", type=int, default=180,
                        help="saved samples per preparation")
    parser.add_argument("--skip-dynamics", action="store_true",
                        help="only compute geometry, coupling matrices, and eigenmodes")
    parser.add_argument("--skip-localized", action="store_true",
                        help="skip the eight localized-injection comparison")
    return parser.parse_args()


def build_assembly(args: argparse.Namespace) -> list[geo.Dipole]:
    kwargs = {"la_angle_deg": args.la_angle_deg, "pdb_path": args.pdb}
    if args.assembly == "dimer":
        return geo.build_dimer(**kwargs)
    if args.assembly == "two-dimer":
        return geo.build_spiral(n_dimers=2, **kwargs)
    if args.assembly == "one-spiral":
        return geo.build_segment(n_spirals=1, **kwargs)
    if args.assembly == "two-spiral":
        return geo.build_segment(n_spirals=2, **kwargs)
    raise ValueError(args.assembly)


def random_rotation(axis: np.ndarray, angle_deg: float) -> np.ndarray:
    axis = axis / np.linalg.norm(axis)
    angle = np.deg2rad(angle_deg)
    c, s = np.cos(angle), np.sin(angle)
    x, y, z = axis
    return np.array([
        [c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
        [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
        [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)],
    ])


def perturb_dipoles(dipoles: list[geo.Dipole], args: argparse.Namespace) -> list[geo.Dipole]:
    if args.structural_jitter_nm == 0.0 and args.dipole_jitter_deg == 0.0:
        return dipoles
    rng = np.random.default_rng(args.seed)
    out = []
    for d in dipoles:
        position = d.position.copy()
        mu = d.mu.copy()
        if args.structural_jitter_nm:
            position += rng.normal(scale=args.structural_jitter_nm, size=3)
        if args.dipole_jitter_deg:
            axis = rng.normal(size=3)
            angle = rng.normal(scale=args.dipole_jitter_deg)
            mu = random_rotation(axis, angle) @ mu
            mu /= np.linalg.norm(mu)
        out.append(geo.Dipole(d.name, position, mu, d.residue))
    return out


def static_disorder(n: int, width_cm: float, seed: int) -> np.ndarray | None:
    if width_cm == 0.0:
        return None
    rng = np.random.default_rng(seed)
    return rng.uniform(-width_cm / 2.0, width_cm / 2.0, size=n)


def write_sites(path: Path, dipoles: list[geo.Dipole]) -> None:
    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["index", "name", "chain", "residue", "x_nm", "y_nm", "z_nm",
                         "mu_x", "mu_y", "mu_z"])
        for i, d in enumerate(dipoles, start=1):
            chain, residue = d.residue if d.residue else ("", "")
            writer.writerow([i, d.name, chain, residue, *d.position, *d.mu])


def write_modes(path: Path, net: md.Network) -> dict:
    energies, decay, _ = net.eigenmodes()
    energy_cm = cp.rad_per_ps_to_cm(energies)
    decay_cm = cp.rad_per_ps_to_cm(decay)
    gamma_cm = cp.rad_per_ps_to_cm(net.gamma)
    lifetimes_ps = np.divide(1.0, decay, out=np.full_like(decay, np.inf), where=decay > 0)

    with path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["mode", "energy_cm", "decay_cm", "decay_over_gamma",
                         "lifetime_ps"])
        for i, row in enumerate(zip(energy_cm, decay_cm, decay / net.gamma, lifetimes_ps)):
            writer.writerow([i, *row])

    return {
        "gamma_cm": float(gamma_cm),
        "brightest_decay_over_gamma": float(np.max(decay / net.gamma)),
        "darkest_decay_over_gamma": float(np.min(decay / net.gamma)),
        "brightest_lifetime_ps": float(lifetimes_ps[np.argmax(decay)]),
        "darkest_lifetime_ps": float(lifetimes_ps[np.argmin(decay)]),
    }


def plot_spectrum(path: Path, net: md.Network) -> None:
    energies, decay, _ = net.eigenmodes()
    fig, ax = plt.subplots(figsize=(7, 4.2))
    ax.scatter(cp.rad_per_ps_to_cm(energies), decay / net.gamma, s=42)
    ax.axhline(1.0, color="0.35", lw=1, ls="--")
    ax.set_xlabel("mode energy shift (cm$^{-1}$)")
    ax.set_ylabel(r"$\Gamma_j / \gamma$")
    ax.set_title("Effective non-Hermitian spectrum")
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def pair_metric_tables(states, n_sites: int):
    pairs = list(combinations(range(n_sites), 2))
    l1 = np.array([[ms.pair_l1_coherence(s, i, j) for i, j in pairs] for s in states])
    logneg = np.array([[ms.logarithmic_negativity(s, [i], [j]) for i, j in pairs]
                       for s in states])
    top_idx = np.argsort(l1.mean(axis=0))[-4:][::-1]
    return pairs, l1, logneg, top_idx


def plot_dynamics(path: Path, title: str, times, states, net: md.Network,
                  pairs, l1, logneg, top_idx) -> dict:
    top_pairs = [pairs[i] for i in top_idx]
    site_pops = np.array([md.site_populations(net, s) for s in states])

    fig, axes = plt.subplots(3, 1, figsize=(8, 8), sharex=True)
    for site in range(net.N):
        axes[0].plot(times, site_pops[:, site], lw=1, label=f"Trp{site + 1}")
    axes[0].set_ylabel("site population")
    if net.N <= 8:
        axes[0].legend(ncol=4, fontsize=7)

    for idx in top_idx:
        i, j = pairs[idx]
        axes[1].plot(times, l1[:, idx], label=f"({i + 1},{j + 1})")
    axes[1].set_ylabel(r"pair $L_1$")
    axes[1].legend(ncol=4, fontsize=8)

    for idx in top_idx:
        i, j = pairs[idx]
        axes[2].plot(times, logneg[:, idx], label=f"({i + 1},{j + 1})")
    axes[2].set_xlabel("time (ps)")
    axes[2].set_ylabel("log negativity")
    axes[2].legend(ncol=4, fontsize=8)

    fig.suptitle(title)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
    return {"top_pairs": [[i + 1, j + 1] for i, j in top_pairs]}


def mode_weights(net: md.Network, rho) -> tuple[np.ndarray, np.ndarray]:
    _, decay, evecs = net.eigenmodes()
    rho_exc = rho.full()[1:, 1:]
    inv = np.linalg.inv(evecs)
    modal = inv @ rho_exc @ inv.conj().T
    weights = np.real(np.diag(modal))
    weights = np.clip(weights, 0.0, None)
    total = weights.sum()
    if total > 0:
        weights /= total
    return decay, weights


def bright_dark_series(net: md.Network, states) -> tuple:
    """Time-resolved projection onto bright (Gamma_j/gamma>1) and dark
    (Gamma_j/gamma<1) eigenmodes of H_eff (Fig. 4d / 5d).

    Returns (bright_weight, dark_weight, crossover_index) where the weights are
    fractions of the *surviving* excitation carried by each sector, and the
    crossover is the first sample where the dark weight overtakes the bright.
    """
    decay, _, evecs = net.eigenmodes()
    inv = np.linalg.inv(evecs)
    bright_mask = decay / net.gamma > 1.0
    bright, dark = [], []
    for rho in states:
        rho_exc = rho.full()[1:, 1:]
        modal = inv @ rho_exc @ inv.conj().T
        w = np.clip(np.real(np.diag(modal)), 0.0, None)
        tot = w.sum()
        if tot > 0:
            w = w / tot
        bright.append(w[bright_mask].sum())
        dark.append(w[~bright_mask].sum())
    bright = np.array(bright)
    dark = np.array(dark)
    crossover = None
    over = np.where(dark > bright)[0]
    if len(over):
        crossover = int(over[0])
    return bright, dark, crossover


def run_preparation(kind: str, net: md.Network, out_dir: Path, samples: int) -> dict:
    tmax = PREP_WINDOWS_PS[kind]
    times = np.linspace(0.0, tmax, samples)
    rho0 = md.initial_state(net, kind)
    result = md.evolve(net, rho0, times)
    pairs, l1, logneg, top_idx = pair_metric_tables(result.states, net.N)

    top_pairs = [pairs[i] for i in top_idx]
    csv_path = out_dir / f"dynamics-{kind}.csv"
    # Write with the original pair column order for compact postprocessing.
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        header = ["time_ps", "ground_population", "total_excitation", "l1_total"]
        header += [f"pair_{i+1}_{j+1}_l1" for i, j in top_pairs]
        header += [f"pair_{i+1}_{j+1}_logneg" for i, j in top_pairs]
        writer.writerow(header)
        for row, (t, state) in enumerate(zip(times, result.states)):
            ground = md.ground_population(net, state)
            vals = [t, ground, 1.0 - ground, ms.l1_coherence(state)]
            vals += [l1[row, idx] for idx in top_idx]
            vals += [logneg[row, idx] for idx in top_idx]
            writer.writerow(vals)

    plot_info = plot_dynamics(
        out_dir / f"dynamics-{kind}.png",
        f"{kind} initial state",
        times,
        result.states,
        net,
        pairs,
        l1,
        logneg,
        top_idx,
    )
    # Fig. 4d / 5d: bright/dark eigenmode-projection panel for the uniform
    # coherent and mixed preparations, which the paper analyses for self-
    # selection into the subradiant sector.
    crossover_ps = None
    if kind in ("coherent", "mixed"):
        bright, dark, cross = bright_dark_series(net, result.states)
        crossover_ps = float(times[cross]) if cross is not None else None
        plot_mode_projection(
            out_dir / f"mode-projection-{kind}.png",
            f"{kind} initial state — eigenmode projection",
            times, bright, dark, cross,
        )

    decay, weights = mode_weights(net, rho0)
    return {
        "window_ps": tmax,
        "csv": str(csv_path),
        "plot": str(out_dir / f"dynamics-{kind}.png"),
        "mode_projection_plot": (
            str(out_dir / f"mode-projection-{kind}.png")
            if kind in ("coherent", "mixed") else None),
        "bright_to_dark_crossover_ps": crossover_ps,
        "final_excitation": float(1.0 - md.ground_population(net, result.states[-1])),
        "max_l1_total": float(max(ms.l1_coherence(s) for s in result.states)),
        "top_pairs": plot_info["top_pairs"],
        "bright_initial_weight": float(weights[decay / net.gamma > 1.0].sum()),
        "dark_initial_weight": float(weights[decay / net.gamma < 1.0].sum()),
    }


def plot_mode_projection(path: Path, title: str, times, bright, dark, cross) -> None:
    """Fig. 4d / 5d: fraction of surviving excitation in bright vs dark modes."""
    fig, ax = plt.subplots(figsize=(8, 3.6))
    ax.plot(times, bright, color="#c1121f", label=r"bright ($\Gamma_j/\gamma>1$)")
    ax.plot(times, dark, color="#003049", label=r"dark ($\Gamma_j/\gamma<1$)")
    if cross is not None:
        ax.axvline(times[cross], color="0.4", ls="--", lw=1,
                   label=f"crossover {times[cross]:.0f} ps")
    ax.set_xlabel("time (ps)")
    ax.set_ylabel("projected weight")
    ax.set_ylim(-0.02, 1.02)
    ax.set_title(title)
    ax.legend(fontsize=8)
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)


def run_localized(net: md.Network, out_dir: Path, samples: int) -> dict:
    times = np.linspace(0.0, 15000.0, samples)
    fig, ax = plt.subplots(figsize=(8, 4.5))
    rows = []
    for site in range(net.N):
        rho0 = md.initial_state(net, "localized", site=site)
        result = md.evolve(net, rho0, times)
        total_exc = np.array([1.0 - md.ground_population(net, s) for s in result.states])
        decay, weights = mode_weights(net, rho0)
        ax.plot(times, total_exc, label=f"Trp{site + 1}")
        rows.append([
            site + 1,
            total_exc[-1],
            weights[decay / net.gamma > 1.0].sum(),
            weights[decay / net.gamma < 1.0].sum(),
        ])
    ax.set_xlabel("time (ps)")
    ax.set_ylabel("total excitation")
    ax.set_title("Localized site injections")
    ax.legend(ncol=4, fontsize=8)
    fig.tight_layout()
    plot_path = out_dir / "localized-injections.png"
    fig.savefig(plot_path, dpi=160)
    plt.close(fig)

    csv_path = out_dir / "localized-injections.csv"
    with csv_path.open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(["site", "final_excitation", "bright_initial_weight",
                         "dark_initial_weight"])
        writer.writerows(rows)
    return {"csv": str(csv_path), "plot": str(plot_path)}


def main() -> int:
    args = parse_args()
    args.output_dir.mkdir(parents=True, exist_ok=True)

    dipoles = perturb_dipoles(build_assembly(args), args)
    disorder = static_disorder(len(dipoles), args.static_disorder_cm, args.seed)
    net = md.build_physical_network(
        dipoles,
        gamma_cm=args.gamma_cm,
        site_energies_cm=disorder,
    )

    write_sites(args.output_dir / "sites.csv", dipoles)
    np.savez(
        args.output_dir / "matrices.npz",
        positions_nm=net.positions,
        mu=net.mu,
        Delta=net.Delta,
        G=net.G,
        site_energies=net.site_energy_vector(),
    )
    mode_summary = write_modes(args.output_dir / "modes.csv", net)
    plot_spectrum(args.output_dir / "spectrum.png", net)

    summary = {
        "paper": "arXiv:2602.02868v1",
        "assembly": args.assembly,
        "n_sites": net.N,
        "gamma_cm": args.gamma_cm,
        "gamma_rad_per_ps": net.gamma,
        "la_angle_deg": args.la_angle_deg,
        "static_disorder_cm": args.static_disorder_cm,
        "structural_jitter_nm": args.structural_jitter_nm,
        "dipole_jitter_deg": args.dipole_jitter_deg,
        "samples": args.samples,
        "mode_summary": mode_summary,
        "outputs": {
            "sites": str(args.output_dir / "sites.csv"),
            "matrices": str(args.output_dir / "matrices.npz"),
            "modes": str(args.output_dir / "modes.csv"),
            "spectrum": str(args.output_dir / "spectrum.png"),
        },
    }

    if not args.skip_dynamics:
        if net.N > 24:
            summary["dynamics_skipped"] = (
                "Assembly has more than 24 sites; use dimer/two-dimer for local "
                "Lindblad dynamics in this workstation runner."
            )
        else:
            summary["preparations"] = {}
            for kind in PREP_WINDOWS_PS:
                print(f"evolving {kind}...", flush=True)
                summary["preparations"][kind] = run_preparation(
                    kind, net, args.output_dir, args.samples
                )
            if not args.skip_localized:
                print("evolving localized injections...", flush=True)
                summary["localized"] = run_localized(net, args.output_dir, args.samples)

    summary_path = args.output_dir / "summary.json"
    summary_path.write_text(json.dumps(summary, indent=2) + "\n")
    print(f"wrote {summary_path}")
    print(f"brightest Gamma/gamma = {mode_summary['brightest_decay_over_gamma']:.3g}")
    print(f"darkest Gamma/gamma = {mode_summary['darkest_decay_over_gamma']:.3g}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
