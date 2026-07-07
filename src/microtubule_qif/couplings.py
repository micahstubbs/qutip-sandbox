"""Dipole coupling (Delta) and collective radiative decay (G) matrices.

Implements Eqs. (9) and (10) of Gassab, Pusuluk & Craddock (arXiv:2602.02868v1):
the coherent dipole-dipole coupling Delta_nm and the collective radiative decay
matrix G_nm for a network of transition dipoles, given site positions and unit
dipole orientations.

All lengths are in nanometres; the reference wavelength is lambda0 = 280 nm
(A280 tryptophan band), so k0 = 2*pi/lambda0 and alpha_nm = k0 * r_nm.
Rates can be dimensionless multiples of the single-site rate gamma or physical
angular rates in ps^-1.  The paper's lifetime conversion uses
tau = 1 / (2*pi*c*Gamma_cm), so the helpers below convert spectroscopic
cm^-1 rates to angular ps^-1 for QuTiP time axes measured in picoseconds.
"""

from __future__ import annotations

import numpy as np

LAMBDA0_NM = 280.0
K0 = 2.0 * np.pi / LAMBDA0_NM   # 1/nm
LIGHT_SPEED_CM_S = 2.99792458e10
PS_PER_S = 1.0e12

# Used in Patwa/Babcock/Kurian tryptophan-network work and inherited by the
# present paper's 280 nm Trp radiative model.
DEFAULT_TRP_GAMMA_CM = 2.73e-3


def cm_to_rad_per_ps(wavenumber_cm: float | np.ndarray) -> float | np.ndarray:
    """Convert a spectroscopic rate in cm^-1 to angular ps^-1."""
    return 2.0 * np.pi * LIGHT_SPEED_CM_S * np.asarray(wavenumber_cm) / PS_PER_S


def rad_per_ps_to_cm(rate_rad_per_ps: float | np.ndarray) -> float | np.ndarray:
    """Convert an angular ps^-1 rate back to cm^-1."""
    return np.asarray(rate_rad_per_ps) * PS_PER_S / (2.0 * np.pi * LIGHT_SPEED_CM_S)


def trp_gamma_rad_per_ps(gamma_cm: float = DEFAULT_TRP_GAMMA_CM) -> float:
    """Default single-Trp radiative rate in angular ps^-1."""
    return float(cm_to_rad_per_ps(gamma_cm))


def _f_coeffs(alpha: np.ndarray):
    """Return the two radial kernels of the coherent coupling Delta (Eq. 9)."""
    a = alpha
    ca, sa = np.cos(a), np.sin(a)
    # coefficient of (mu_n . mu_m)
    g1 = -ca / a + sa / a**2 + ca / a**3
    # coefficient of (mu_n . r)(mu_m . r)
    g2 = -ca / a + 3 * sa / a**2 + 3 * ca / a**3
    return g1, g2


def _g_coeffs(alpha: np.ndarray):
    """Return the two radial kernels of the decay matrix G (Eq. 10)."""
    a = alpha
    ca, sa = np.cos(a), np.sin(a)
    f1 = sa / a + ca / a**2 - sa / a**3
    f2 = sa / a + 3 * ca / a**2 - 3 * sa / a**3
    return f1, f2


def coupling_matrices(positions_nm: np.ndarray,
                      mu: np.ndarray,
                      gamma: float = 1.0):
    """Compute (Delta, G) for the given geometry.

    Parameters
    ----------
    positions_nm : (N, 3) site positions in nm.
    mu           : (N, 3) unit dipole orientations.
    gamma        : single-site radiative rate (sets the overall scale).

    Returns
    -------
    Delta : (N, N) real symmetric coherent coupling, zero diagonal.
    G     : (N, N) real symmetric collective decay, diagonal = gamma.
    """
    positions_nm = np.asarray(positions_nm, float)
    mu = np.asarray(mu, float)
    n = len(positions_nm)

    Delta = np.zeros((n, n))
    G = np.eye(n) * gamma

    for i in range(n):
        for j in range(i + 1, n):
            r_vec = positions_nm[i] - positions_nm[j]
            r = np.linalg.norm(r_vec)
            if r == 0.0:
                continue
            r_hat = r_vec / r
            alpha = K0 * r

            mimj = float(mu[i] @ mu[j])
            mir = float(mu[i] @ r_hat)
            mjr = float(mu[j] @ r_hat)

            g1, g2 = _f_coeffs(alpha)
            delta = (3 * gamma / 4) * (g1 * mimj - g2 * mir * mjr)

            f1, f2 = _g_coeffs(alpha)
            gij = (3 * gamma / 2) * (f1 * mimj - f2 * mir * mjr)

            Delta[i, j] = Delta[j, i] = delta
            G[i, j] = G[j, i] = gij

    return Delta, G


def effective_hamiltonian(H0_diag: np.ndarray,
                          Delta: np.ndarray,
                          G: np.ndarray) -> np.ndarray:
    """Effective non-Hermitian Hamiltonian H_eff = H0 + Delta - (i/2) G (Eq. 1).

    ``H0_diag`` is the length-N vector of on-site energies (hbar*omega0).
    Returned in the single-excitation site basis (no ground state).
    """
    H0 = np.diag(H0_diag)
    return H0 + Delta - 0.5j * G


def decompose_decay(G: np.ndarray, tol: float = 1e-12):
    """Eigendecomposition G = V diag(gamma_j) V^dagger (Eq. 12).

    Returns (gammas, V) with eigenvalues clipped at zero (G is PSD up to
    numerical noise). Column V[:, j] is the eigenvector v^(j).
    """
    gammas, V = np.linalg.eigh(G)
    gammas = np.where(gammas < tol, 0.0, gammas)
    return gammas, V
