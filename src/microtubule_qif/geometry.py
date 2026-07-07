"""Tryptophan network geometry for the microtubule QIF model.

Implements the site geometry of

    Gassab, Pusuluk & Craddock, "Quantum Information Flow in Microtubule
    Tryptophan Networks", arXiv:2602.02868v1 (2026).

Two responsibilities:

1. Extract the eight tryptophan sites of a tubulin dimer from PDB 1JFF — each
   site's *position* (indole ring centroid) and *transition-dipole orientation*
   (the ¹La moment, taken in the indole plane).

2. Build ordered microtubule assemblies (dimers, spirals, filaments) by the
   rigid-body construction of Appendix A.

Dipole-orientation convention
-----------------------------
The paper takes site positions and dipole orientations "from structural data"
and defers the exact extraction to the code of Patwa et al. [11]. That code is
not bundled here, so we use an explicit, documented convention for the Trp ¹La
transition dipole:

  * position  = centroid of the nine indole-ring atoms
                (CG, CD1, CD2, NE1, CE2, CE3, CZ2, CZ3, CH2)
  * ring plane = best-fit plane of those atoms (SVD; normal = smallest
                 singular vector)
  * in-plane long axis â = projection of (CG -> CH2) onto the plane
  * ¹La dipole = â rotated in-plane about the plane normal by ``la_angle_deg``
                 (default 42°, the Callis ¹La value)

``la_angle_deg`` is a free parameter so the convention can be matched to a
specific reference; the collective physics (super/subradiant splitting) is
robust to its precise value, which we verify in the tests.
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
                         la_angle_deg: float = 42.0) -> list[Dipole]:
    """Load the eight Trp dipoles of the 1JFF tubulin dimer.

    Positions are converted to nanometres (PDB is in angstrom). Dipoles are
    unit ¹La transition moments per the convention documented in the module
    docstring.
    """
    pdb_path = Path(pdb_path) if pdb_path else DATA_DIR / "1JFF.pdb"
    atoms = _parse_pdb_atoms(pdb_path)
    la_angle = np.deg2rad(la_angle_deg)

    dipoles = []
    for idx, (chain, resseq) in enumerate(TRP_SITES, start=1):
        ring = np.array([atoms[(chain, resseq, a)] for a in INDOLE_ATOMS])
        centroid = ring.mean(axis=0)
        normal = _best_fit_plane_normal(ring)

        cg = atoms[(chain, resseq, "CG")]
        ch2 = atoms[(chain, resseq, "CH2")]
        long_axis = ch2 - cg
        # project long axis into the ring plane
        long_axis = long_axis - np.dot(long_axis, normal) * normal
        long_axis /= np.linalg.norm(long_axis)

        # rotate the in-plane long axis by la_angle about the plane normal
        # (Rodrigues rotation)
        c, s = np.cos(la_angle), np.sin(la_angle)
        mu = (long_axis * c
              + np.cross(normal, long_axis) * s
              + normal * np.dot(normal, long_axis) * (1 - c))
        mu /= np.linalg.norm(mu)

        dipoles.append(Dipole(
            name=f"Trp{idx}",
            position=centroid / 10.0,   # angstrom -> nm
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


def build_dimer(la_angle_deg: float = 42.0,
                pdb_path: Path | None = None) -> list[Dipole]:
    """A single tubulin dimer: the eight Trp dipoles, centred at the origin."""
    dips = load_tubulin_dipoles(pdb_path, la_angle_deg)
    centre = np.mean([d.position for d in dips], axis=0)
    return [d.transformed(np.eye(3), -centre) for d in dips]


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
                 la_angle_deg: float = 42.0,
                 pdb_path: Path | None = None) -> list[Dipole]:
    """One circumferential turn: ``n_dimers`` dimers around the cylinder.

    Follows the left-handed spiral construction of Appendix A: each successive
    dimer is the base dimer rotated about the longitudinal axis and tilted,
    translated radially, then placed at its position in the turn by an
    additional rotation about x and a small longitudinal step.
    """
    base = build_dimer(la_angle_deg, pdb_path)
    tilt_axis = _LONG_AXIS  # about x, per "rotation about axis through Trp346"
    R_base = _rot(_LONG_AXIS, _SPIRAL_ROT_LONG)
    R_tilt = _rot(tilt_axis, _SPIRAL_ROT_TILT)
    R_dimer = R_tilt @ R_base

    sites: list[Dipole] = []
    for k in range(n_dimers):
        R_turn = _rot(_LONG_AXIS, _TURN_ROT_X * k)
        R = R_turn @ R_dimer
        t = R_turn @ _SPIRAL_TRANS + _TURN_TRANS_X * k
        for d in base:
            moved = d.transformed(R, t)
            moved.name = f"S0-D{k}-{d.name}"
            sites.append(moved)
    return sites


def build_segment(n_spirals: int = 1,
                  dimers_per_spiral: int = DIMERS_PER_SPIRAL,
                  la_angle_deg: float = 42.0,
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
