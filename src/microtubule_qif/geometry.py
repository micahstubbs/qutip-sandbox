"""Tryptophan network geometry for the microtubule QIF model.

Implements the site geometry of

    Gassab, Pusuluk & Craddock, "Quantum Information Flow in Microtubule
    Tryptophan Networks", arXiv:2602.02868v1 (2026).

Two responsibilities:

1. Extract the eight tryptophan sites of a tubulin dimer from PDB 1JFF — each
   site's *position* (CD2/CE2 midpoint) and *transition-dipole orientation* (the
   ¹La moment, taken in the indole plane).

2. Build ordered microtubule assemblies (dimers, spirals, filaments) by the
   rigid-body construction of Appendix A.

Dipole-orientation convention
-----------------------------
The paper takes site positions and dipole orientations "from structural data"
and cites the microtubule construction code used by Patwa et al.  Their Methods
define the Trp chromophore position as the midpoint of the CD2 and CE2 atoms,
and the 1La transition dipole as an in-plane vector pointing ``la_angle_deg``
above the axis from that midpoint to CD1, toward NE1.  The default angle is
46.2 degrees, matching that convention.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

import numpy as np

# The eight tryptophan sites, in the Trp1..Trp8 order of Fig. 1.
# (chain, residue number) — chain A = alpha-tubulin, chain B = beta-tubulin.
TRP_SITES = [
    ("A", 21),    # Trp1  alpha21
    ("A", 346),   # Trp2  alpha346
    ("A", 388),   # Trp3  alpha388
    ("A", 407),   # Trp4  alpha407
    ("B", 21),    # Trp5  beta21
    ("B", 103),   # Trp6  beta103
    ("B", 346),   # Trp7  beta346
    ("B", 407),   # Trp8  beta407
]

INDOLE_ATOMS = ["CG", "CD1", "CD2", "NE1", "CE2", "CE3", "CZ2", "CZ3", "CH2"]

DATA_DIR = Path(__file__).resolve().parent.parent.parent / "data"


@dataclass
class Dipole:
    """A single chromophore: position (nm) and unit transition-dipole vector."""

    name: str
    position: np.ndarray          # shape (3,), nanometres
    mu: np.ndarray                # shape (3,), unit vector
    residue: tuple = field(default=None)

    def transformed(self, R: np.ndarray, t: np.ndarray) -> "Dipole":
        """Return a copy under rigid motion x -> R x + t (mu rotates only)."""
        return Dipole(
            name=self.name,
            position=R @ self.position + t,
            mu=R @ self.mu,
            residue=self.residue,
        )


def _parse_pdb_atoms(pdb_path: Path) -> dict:
    """Return {(chain, resseq, atomname): xyz_angstrom} for ATOM records."""
    atoms = {}
    with open(pdb_path) as fh:
        for line in fh:
            if not line.startswith("ATOM"):
                continue
            atom = line[12:16].strip()
            resname = line[17:20].strip()
            chain = line[21].strip()
            resseq = int(line[22:26])
            if resname != "TRP":
                continue
            x = float(line[30:38])
            y = float(line[38:46])
            z = float(line[46:54])
            atoms[(chain, resseq, atom)] = np.array([x, y, z])
    return atoms


def _best_fit_plane_normal(points: np.ndarray) -> np.ndarray:
    """Unit normal of the best-fit plane through points (SVD)."""
    centred = points - points.mean(axis=0)
    _, _, vh = np.linalg.svd(centred)
    normal = vh[-1]
    return normal / np.linalg.norm(normal)


def load_tubulin_dipoles(pdb_path: Path | None = None,
                         la_angle_deg: float = 46.2) -> list[Dipole]:
    """Load the eight Trp dipoles of the 1JFF tubulin dimer.

    Positions are converted to nanometres (PDB is in angstrom). Dipoles are
    unit 1La transition moments per the convention documented in the module
    docstring.
    """
    pdb_path = Path(pdb_path) if pdb_path else DATA_DIR / "1JFF.pdb"
    atoms = _parse_pdb_atoms(pdb_path)
    la_angle = np.deg2rad(la_angle_deg)

    dipoles = []
    for idx, (chain, resseq) in enumerate(TRP_SITES, start=1):
        ring = np.array([atoms[(chain, resseq, a)] for a in INDOLE_ATOMS])
        cd2 = atoms[(chain, resseq, "CD2")]
        ce2 = atoms[(chain, resseq, "CE2")]
        cd1 = atoms[(chain, resseq, "CD1")]
        ne1 = atoms[(chain, resseq, "NE1")]

        midpoint = 0.5 * (cd2 + ce2)
        axis = cd1 - midpoint
        axis /= np.linalg.norm(axis)

        # Rotate within the indole plane toward NE1 by la_angle.  The NE1
        # projection defines the positive in-plane perpendicular direction.
        normal = _best_fit_plane_normal(ring)
        toward_ne1 = ne1 - midpoint
        toward_ne1 -= np.dot(toward_ne1, axis) * axis
        toward_ne1 -= np.dot(toward_ne1, normal) * normal
        toward_ne1 /= np.linalg.norm(toward_ne1)

        mu = np.cos(la_angle) * axis + np.sin(la_angle) * toward_ne1
        mu /= np.linalg.norm(mu)

        dipoles.append(Dipole(
            name=f"Trp{idx}",
            position=midpoint / 10.0,   # angstrom -> nm
            mu=mu,
            residue=(chain, resseq),
        ))
    return dipoles


# --------------------------------------------------------------------------
# Appendix A: rigid-body microtubule assembly
# --------------------------------------------------------------------------

def _rot(axis: np.ndarray, angle_deg: float) -> np.ndarray:
    """Rotation matrix about ``axis`` (need not be unit) by angle in degrees."""
    axis = np.asarray(axis, float)
    axis = axis / np.linalg.norm(axis)
    a = np.deg2rad(angle_deg)
    c, s = np.cos(a), np.sin(a)
    x, y, z = axis
    return np.array([
        [c + x * x * (1 - c),     x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
        [y * x * (1 - c) + z * s, c + y * y * (1 - c),     y * z * (1 - c) - x * s],
        [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)],
    ])


def build_dimer(la_angle_deg: float = 46.2,
                pdb_path: Path | None = None) -> list[Dipole]:
    """A single tubulin dimer: the eight Trp dipoles, centred at the origin."""
    dips, _ = _centered_dimer_and_beta346_cd2(la_angle_deg, pdb_path)
    return dips


def _centered_dimer_and_beta346_cd2(la_angle_deg: float = 46.2,
                                    pdb_path: Path | None = None):
    """Return centered dimer dipoles and the centered beta Trp346 CD2 pivot."""
    pdb_path = Path(pdb_path) if pdb_path else DATA_DIR / "1JFF.pdb"
    dips = load_tubulin_dipoles(pdb_path, la_angle_deg)
    centre = np.mean([d.position for d in dips], axis=0)
    atoms = _parse_pdb_atoms(pdb_path)
    beta346_cd2 = atoms[("B", 346, "CD2")] / 10.0 - centre
    return [d.transformed(np.eye(3), -centre) for d in dips], beta346_cd2


def _transform_about_pivot(dipoles: list[Dipole], R: np.ndarray,
                           pivot: np.ndarray) -> list[Dipole]:
    """Rotate dipoles by R around an axis passing through ``pivot``."""
    out: list[Dipole] = []
    for d in dipoles:
        out.append(Dipole(
            name=d.name,
            position=pivot + R @ (d.position - pivot),
            mu=R @ d.mu,
            residue=d.residue,
        ))
    return out


# Rigid-motion parameters from Appendix A (nanometres, degrees).
_LONG_AXIS = np.array([1.0, 0.0, 0.0])   # protofilament / longitudinal = x
_SPIRAL_ROT_LONG = -55.38                # about longitudinal axis
_SPIRAL_ROT_TILT = 11.7                  # about axis through beta Trp346 CD2
_SPIRAL_TRANS = np.array([0.0, 11.2, 0.3])   # y, z translation (nm)
_TURN_ROT_X = 27.69                      # about x for successive dimers in a turn
_TURN_TRANS_X = np.array([0.9, 0.0, 0.0])
_SPIRAL_STACK_X = np.array([8.0, 0.0, 0.0])  # between spirals along x
DIMERS_PER_SPIRAL = 13


def build_spiral(n_dimers: int = DIMERS_PER_SPIRAL,
                 la_angle_deg: float = 46.2,
                 pdb_path: Path | None = None) -> list[Dipole]:
    """One circumferential turn: ``n_dimers`` dimers around the cylinder.

    Follows the left-handed spiral construction of Appendix A: the centered
    dimer is first rotated about its longitudinal axis, then tilted about an
    x-parallel axis passing through beta-tubulin Trp346 CD2, translated
    radially, and copied around the turn by an additional rotation about x and
    a small longitudinal step.
    """
    base, beta346_cd2 = _centered_dimer_and_beta346_cd2(la_angle_deg, pdb_path)
    R_base = _rot(_LONG_AXIS, _SPIRAL_ROT_LONG)
    base = [d.transformed(R_base, np.zeros(3)) for d in base]
    beta346_cd2 = R_base @ beta346_cd2

    R_tilt = _rot(_LONG_AXIS, _SPIRAL_ROT_TILT)
    base = _transform_about_pivot(base, R_tilt, beta346_cd2)

    sites: list[Dipole] = []
    for k in range(n_dimers):
        R_turn = _rot(_LONG_AXIS, _TURN_ROT_X * k)
        t = R_turn @ _SPIRAL_TRANS + _TURN_TRANS_X * k
        for d in base:
            moved = d.transformed(R_turn, t)
            moved.name = f"S0-D{k}-{d.name}"
            sites.append(moved)
    return sites


def build_segment(n_spirals: int = 1,
                  dimers_per_spiral: int = DIMERS_PER_SPIRAL,
                  la_angle_deg: float = 46.2,
                  pdb_path: Path | None = None) -> list[Dipole]:
    """A microtubule segment of ``n_spirals`` stacked circumferential turns."""
    spiral = build_spiral(dimers_per_spiral, la_angle_deg, pdb_path)
    sites: list[Dipole] = []
    for s in range(n_spirals):
        t = _SPIRAL_STACK_X * s
        for d in spiral:
            moved = d.transformed(np.eye(3), t)
            moved.name = f"S{s}-" + d.name.split("-", 1)[1]
            sites.append(moved)
    return sites


def positions_array(dipoles: list[Dipole]) -> np.ndarray:
    return np.array([d.position for d in dipoles])


def mu_array(dipoles: list[Dipole]) -> np.ndarray:
    return np.array([d.mu for d in dipoles])
