"""QuTiP Lindblad model for the microtubule tryptophan network.

Builds the single-excitation-plus-ground-state open quantum system of
arXiv:2602.02868v1 and provides the five initial preparations and the
trace-preserving time evolution.

State-space convention
-----------------------
For N sites we use an (N+1)-dimensional Hilbert space: basis state 0 is the
collective ground state |0> (the radiative sink), and basis states 1..N are the
single-excitation site states |n>. This is the "single-excitation plus ground
state" space of Appendix B.5, in which the Lindblad equation (Eq. 29) is
trace-preserving.

Working units: whatever units are used for ``gamma`` and ``Delta``.  Use
``build_network(..., gamma=1)`` for dimensionless gamma units, or
``build_physical_network`` for angular ps^-1 rates and picosecond time axes.
The optical carrier hbar*omega0 is a global phase on the excitation manifold;
we work in that rotating frame by default and keep only relative site-energy
disorder when requested.
"""

from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import qutip as qt

from . import couplings as cp


@dataclass
class Network:
    """A built network ready for simulation."""

    positions: np.ndarray     # (N, 3) nm
    mu: np.ndarray            # (N, 3)
    Delta: np.ndarray         # (N, N)
    G: np.ndarray             # (N, N)
    gamma: float
    site_energies: np.ndarray | None = None

    @property
    def N(self) -> int:
        return len(self.positions)

    # -- operators in the (N+1)-dim ground+single-excitation space ----------

    def _dim(self) -> int:
        return self.N + 1

    def sigma_minus(self, n: int) -> qt.Qobj:
        """|0><n+1|: annihilate excitation on site n (0-indexed), -> ground."""
        op = np.zeros((self._dim(), self._dim()))
        op[0, n + 1] = 1.0
        return qt.Qobj(op)

    def hamiltonian(self, omega0: float = 0.0) -> qt.Qobj:
        """H = H0 + Delta embedded in the ground+excitation space (Eqs 6-8)."""
        d = self._dim()
        H = np.zeros((d, d), dtype=complex)
        for n, energy in enumerate(self.site_energy_vector(omega0)):
            H[n + 1, n + 1] = energy
        # coherent dipole coupling
        H[1:, 1:] += self.Delta
        return qt.Qobj(H)

    def collapse_operators(self) -> list[qt.Qobj]:
        """Collective jump operators L_j = sqrt(gamma_j) sum_n v_n^(j) sigma_n-
        from the eigendecomposition of G (Eqs 12-13, 26)."""
        gammas, V = cp.decompose_decay(self.G)
        ops = []
        for j in range(self.N):
            if gammas[j] <= 0:
                continue
            mat = np.zeros((self._dim(), self._dim()), dtype=complex)
            # sum_n v_n^(j) |0><n|
            mat[0, 1:] = V[:, j]
            ops.append(np.sqrt(gammas[j]) * qt.Qobj(mat))
        return ops

    def effective_hamiltonian(self, omega0: float = 0.0) -> np.ndarray:
        """H_eff = H0 + Delta - (i/2) G on the excitation manifold only (Eq 1)."""
        return cp.effective_hamiltonian(
            self.site_energy_vector(omega0), self.Delta, self.G
        )

    def site_energy_vector(self, omega0: float = 0.0) -> np.ndarray:
        """On-site energies in the excitation block."""
        energies = np.full(self.N, omega0, dtype=float)
        if self.site_energies is not None:
            energies = energies + np.asarray(self.site_energies, dtype=float)
        return energies

    # -- eigenmodes of the non-Hermitian generator -------------------------

    def eigenmodes(self, omega0: float = 0.0):
        """Return (energies, decay_rates, eigvecs) of the collective generator.

        Physically these are the excitonic eigenstates: eigenvectors of the
        Hermitian coherent Hamiltonian H0 + Delta, each with collective radiative
        rate Gamma_j = <v_j| G |v_j>. Sorted by decay rate ascending (subradiant
        first). Columns of the returned matrix are the (real, orthonormal)
        eigenvectors in the N-dim site basis.

        Why not diagonalize H_eff = H0 + Delta - (i/2) G directly? In the Trp
        near field the coherent coupling dominates (Delta ~ 1e4 * gamma) while the
        anti-Hermitian decay part is O(gamma), making H_eff strongly non-normal.
        `np.linalg.eig` on that complex-symmetric matrix returns numerically
        garbage imaginary parts (|Gamma_j|/gamma ~ 1e4, even negative). To first
        order in G/Delta the H_eff eigenstates ARE the excitonic eigenstates and
        their decay rates are exactly <v_j|G|v_j>, so this is both the correct
        perturbative limit and numerically stable.
        """
        H_coh = np.diag(self.site_energy_vector(omega0)) + self.Delta
        energies, evecs = np.linalg.eigh(H_coh)   # real symmetric -> orthonormal
        decay = np.array([
            float(np.real(evecs[:, j].conj() @ self.G @ evecs[:, j]))
            for j in range(self.N)
        ])
        order = np.argsort(decay)
        return energies[order], decay[order], evecs[:, order]


@dataclass
class DynamicsResult:
    """Small result object mirroring the QuTiP fields used by this project."""

    times: np.ndarray
    states: list[qt.Qobj]


def build_network(dipoles, gamma: float = 1.0,
                  site_energies: np.ndarray | None = None) -> Network:
    """Build a Network from a list of geometry.Dipole objects."""
    from . import geometry as geo
    pos = geo.positions_array(dipoles)
    mu = geo.mu_array(dipoles)
    Delta, G = cp.coupling_matrices(pos, mu, gamma=gamma)
    return Network(
        positions=pos,
        mu=mu,
        Delta=Delta,
        G=G,
        gamma=gamma,
        site_energies=site_energies,
    )


def build_physical_network(dipoles,
                           gamma_cm: float = cp.DEFAULT_TRP_GAMMA_CM,
                           site_energies_cm: np.ndarray | None = None) -> Network:
    """Build a network with rates in angular ps^-1.

    ``gamma_cm`` and optional ``site_energies_cm`` are spectroscopic cm^-1
    values.  They are converted using tau = 1/(2*pi*c*Gamma_cm), matching the
    paper's lifetime relation.
    """
    gamma = cp.trp_gamma_rad_per_ps(gamma_cm)
    site_energies = None
    if site_energies_cm is not None:
        site_energies = cp.cm_to_rad_per_ps(site_energies_cm)
    return build_network(dipoles, gamma=gamma, site_energies=site_energies)


# --------------------------------------------------------------------------
# Initial-state preparations (Sec. III)
# --------------------------------------------------------------------------

def _embed_ket(site_amplitudes: np.ndarray, dim: int) -> qt.Qobj:
    """Embed an N-vector of site amplitudes into the ground+excitation ket."""
    vec = np.zeros(dim, dtype=complex)
    vec[1:] = site_amplitudes
    nrm = np.linalg.norm(vec)
    if nrm > 0:
        vec /= nrm
    return qt.Qobj(vec.reshape(-1, 1))


def initial_state(net: Network, kind: str, omega0: float = 0.0,
                  site: int = 0) -> qt.Qobj:
    """Return one of the five preparations as a density matrix.

    kind:
      'superradiant' — eigenstate of H_eff with the largest decay rate
      'subradiant'   — eigenstate of H_eff with the smallest decay rate
      'coherent'     — uniform equal-phase superposition (Eq. 14)
      'mixed'        — maximally mixed single excitation (Eq. 15)
      'localized'    — excitation localized on ``site`` (0-indexed)
    """
    N, dim = net.N, net.N + 1
    if kind == "coherent":
        amp = np.ones(N) / np.sqrt(N)
        return qt.ket2dm(_embed_ket(amp, dim))
    if kind == "mixed":
        rho = np.zeros((dim, dim), dtype=complex)
        for n in range(N):
            rho[n + 1, n + 1] = 1.0 / N
        return qt.Qobj(rho)
    if kind == "localized":
        amp = np.zeros(N)
        amp[site] = 1.0
        return qt.ket2dm(_embed_ket(amp, dim))
    if kind in ("superradiant", "subradiant"):
        _, decay, evecs = net.eigenmodes(omega0)
        idx = -1 if kind == "superradiant" else 0
        return qt.ket2dm(_embed_ket(evecs[:, idx], dim))
    raise ValueError(f"unknown initial-state kind: {kind!r}")


PREPARATIONS = ["superradiant", "subradiant", "coherent", "mixed", "localized"]


# --------------------------------------------------------------------------
# Dynamics
# --------------------------------------------------------------------------

def evolve(net: Network, rho0: qt.Qobj, times: np.ndarray,
           omega0: float = 0.0, e_ops=None, options=None,
           method: str = "auto"):
    """Trace-preserving Lindblad evolution (Eq. 29).

    Returns an object with a ``states`` list.  For small time-independent
    networks the default uses an exact Liouvillian eigendecomposition, avoiding
    stiff ODE integration caused by strong near-field dipole couplings.  Use
    ``method="mesolve"`` to force QuTiP's adaptive ODE solver.
    """
    if method == "auto":
        method = "liouvillian" if net.N <= 24 and e_ops is None else "mesolve"
    if method == "liouvillian":
        if e_ops is not None:
            raise ValueError("liouvillian method stores states and does not accept e_ops")
        return evolve_liouvillian(net, rho0, times, omega0=omega0)
    if method != "mesolve":
        raise ValueError(f"unknown evolution method: {method!r}")
    H = net.hamiltonian(omega0)
    c_ops = net.collapse_operators()
    opts = options or {"store_states": True, "atol": 1e-10, "rtol": 1e-8,
                       "nsteps": 200_000}
    return qt.mesolve(H, rho0, times, c_ops=c_ops, e_ops=e_ops or [],
                      options=opts)


def evolve_liouvillian(net: Network, rho0: qt.Qobj, times: np.ndarray,
                       omega0: float = 0.0) -> DynamicsResult:
    """Exact propagation under the time-independent Lindbladian.

    QuTiP builds the Liouvillian superoperator; NumPy diagonalizes it once and
    evaluates exp(L t) at the requested times.  This is intended for the
    single-dimer and two-dimer models, not the 104-site spiral.
    """
    H = net.hamiltonian(omega0)
    L = qt.liouvillian(H, net.collapse_operators()).full()
    vec0 = qt.operator_to_vector(rho0).full().ravel()
    evals, evecs = np.linalg.eig(L)
    coeffs = np.linalg.solve(evecs, vec0)
    dim = net.N + 1

    states: list[qt.Qobj] = []
    for t in np.asarray(times, dtype=float):
        vec = evecs @ (np.exp(evals * t) * coeffs)
        mat = vec.reshape((dim, dim), order="F")
        # Remove tiny numerical anti-Hermitian noise from the eigensolve.
        mat = 0.5 * (mat + mat.conj().T)
        states.append(qt.Qobj(mat, dims=rho0.dims))
    return DynamicsResult(times=np.asarray(times, dtype=float), states=states)


def site_populations(net: Network, rho: qt.Qobj) -> np.ndarray:
    """Excitation population on each site for a density matrix rho."""
    m = rho.full()
    return np.real(np.diag(m)[1:])


def ground_population(net: Network, rho: qt.Qobj) -> float:
    return float(np.real(rho.full()[0, 0]))
