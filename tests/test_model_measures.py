"""Verify the model and measures reproduce the paper's qualitative claims."""

import sys
from pathlib import Path

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "src"))

from microtubule_qif import geometry as geo  # noqa: E402
from microtubule_qif import measures as ms  # noqa: E402
from microtubule_qif import model as md  # noqa: E402
from microtubule_qif import couplings as cp  # noqa: E402


def _net():
    return md.build_physical_network(geo.build_dimer())


def test_geometry_eight_sites():
    dips = geo.build_dimer()
    assert len(dips) == 8
    assert all(abs(np.linalg.norm(d.mu) - 1.0) < 1e-9 for d in dips)


def test_trp_position_is_cd2_ce2_midpoint():
    pdb = geo.DATA_DIR / "1JFF.pdb"
    atoms = geo._parse_pdb_atoms(pdb)
    raw = geo.load_tubulin_dipoles(pdb_path=pdb)
    cd2 = atoms[("A", 21, "CD2")]
    ce2 = atoms[("A", 21, "CE2")]
    expected_nm = 0.5 * (cd2 + ce2) / 10.0
    assert np.allclose(raw[0].position, expected_nm)


def test_spiral_geometry_keeps_published_radius_and_pivot():
    pdb = geo.DATA_DIR / "1JFF.pdb"
    dips, pivot = geo._centered_dimer_and_beta346_cd2(pdb_path=pdb)
    atoms = geo._parse_pdb_atoms(pdb)
    raw = geo.load_tubulin_dipoles(pdb_path=pdb)
    centre = np.mean([d.position for d in raw], axis=0)
    assert len(dips) == 8
    assert np.allclose(pivot, atoms[("B", 346, "CD2")] / 10.0 - centre)

    spiral = geo.build_spiral(pdb_path=pdb)
    positions = geo.positions_array(spiral)
    mean_radius = np.mean(np.sqrt(positions[:, 1] ** 2 + positions[:, 2] ** 2))
    assert len(spiral) == 13 * 8
    assert 10.5 < mean_radius < 11.8


def test_wavenumber_rate_round_trip():
    gamma_cm = cp.DEFAULT_TRP_GAMMA_CM
    assert np.isclose(cp.rad_per_ps_to_cm(cp.cm_to_rad_per_ps(gamma_cm)), gamma_cm)


def test_G_is_psd_with_bright_dark_split():
    net = _net()
    gammas, _ = cp.decompose_decay(net.G)
    assert gammas.min() >= -1e-9
    assert gammas.max() / net.gamma > 1.0          # a bright channel exists
    assert gammas.min() / net.gamma < 0.1          # a dark channel exists


def test_trace_preserved():
    net = _net()
    times = np.linspace(0, 5000.0, 40)
    rho0 = md.initial_state(net, "coherent")
    res = md.evolve(net, rho0, times)
    traces = [abs(s.tr() - 1.0) for s in res.states]
    assert max(traces) < 1e-6


def test_superradiant_decays_faster_than_subradiant():
    net = _net()
    # gamma^-1 is about 1945 ps, so use a ps-scale horizon that captures the
    # bright-state export while the dark-state channel is still alive.
    times = np.linspace(0, 5000.0, 80)
    exc = {}
    for kind in ("superradiant", "subradiant"):
        rho0 = md.initial_state(net, kind)
        res = md.evolve(net, rho0, times)
        # total excitation population = 1 - ground population
        exc[kind] = np.array([1.0 - md.ground_population(net, s)
                              for s in res.states])
    assert exc["subradiant"][-1] > exc["superradiant"][-1] + 0.5


def test_mixed_state_has_much_weaker_coherence_than_coherent_state():
    net = _net()
    times = np.linspace(0, 2000.0, 60)
    mixed = md.evolve(net, md.initial_state(net, "mixed"), times)
    coherent = md.evolve(net, md.initial_state(net, "coherent"), times)
    mixed_coh = np.array([ms.l1_coherence(s) for s in mixed.states])
    coherent_coh = np.array([ms.l1_coherence(s) for s in coherent.states])
    assert mixed_coh[0] < 1e-12
    assert mixed_coh.max() < 0.5
    assert coherent_coh[0] > 6.0


def test_coherent_state_has_coherence_and_entanglement():
    net = _net()
    times = np.linspace(0, 2000.0, 60)
    rho0 = md.initial_state(net, "coherent")
    res = md.evolve(net, rho0, times)
    coh = np.array([ms.l1_coherence(s) for s in res.states])
    assert coh[0] > 1.0              # starts highly coherent (Fig. 4b)
    # some pair shows entanglement at early times
    en = [ms.logarithmic_negativity(s, [0], [1]) for s in res.states[:20]]
    assert max(en) > 0.0


def test_correlated_coherence_reduces_to_zero_for_product():
    net = _net()
    # localized excitation on a single site in group A -> no A:B correlation
    rho0 = md.initial_state(net, "localized", site=0)
    cc = ms.correlated_coherence(rho0, [0, 1, 2, 3], [4, 5, 6, 7])
    assert abs(cc) < 1e-9


if __name__ == "__main__":
    import pytest
    raise SystemExit(pytest.main([__file__, "-v"]))
