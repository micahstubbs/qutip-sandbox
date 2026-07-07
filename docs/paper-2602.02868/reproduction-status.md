# Reproduction status — arXiv:2602.02868v1 dynamics

Status of the local reproduction of *Quantum Information Flow in Microtubule
Tryptophan Networks* (Gassab, Pusuluk & Craddock), focused on the dynamics.
Updated 2026-07-07.

## Reproduced

| Paper figure | What | Script | Output |
|---|---|---|---|
| Fig. 2 | Superradiant dynamics: fast synchronous population decay, rapid L1-coherence loss, transient log-negativity | `run_microtubule_qif.py` | `output/microtubule-qif/dynamics-superradiant.png` |
| Fig. 3 | Subradiant dynamics: slow 80 ns decay, persistent L1 coherence, sustained entanglement | `run_microtubule_qif.py` | `dynamics-subradiant.png` |
| Fig. 4a-c | Coherent uniform state: oscillatory population exchange, sustained pair coherence/entanglement | `run_microtubule_qif.py` | `dynamics-coherent.png` |
| Fig. 4d | Coherent state self-selects into the dark/subradiant sector (bright→dark crossover ≈ 670 ps) | `run_microtubule_qif.py` | `mode-projection-coherent.png` |
| Fig. 5a-c | Mixed uniform state: monotonic decay, ~zero coherence, ~zero entanglement | `run_microtubule_qif.py` | `dynamics-mixed.png` |
| Fig. 5d | Mixed state: non-preferential bright/dark projection | `run_microtubule_qif.py` | `mode-projection-mixed.png` |
| Fig. 6 | Eight site-localized injections; site-dependent decay (Trp4/Trp7 slow, Trp1/Trp5 fast) | `run_microtubule_qif.py` | `localized-injections.png` |
| Fig. 8 | Embedding sweep: top-4 focal-tubulin L1 coherences across single/two/three-tubulin × 4 preparations; amplitudes drop and oscillate as the environment grows | `run_embeddings_backflow.py` | `output/microtubule-qif-embeddings/embeddings-fig8.png` |
| Fig. 9 | Non-Markovian backflow: trace-distance revivals on X = T1∪Tk with a third tubulin as structured reservoir; phase-contrast backflow > population-contrast | `run_embeddings_backflow.py` | `backflow-fig9.png` |
| Fig. 12 | Radiative lifetime scaling vs size for ordered / static-disorder / structural-jitter; ordered subradiant reaches the ms range, disorder collapses the contrast | `run_lifetime_scaling.py` | `output/microtubule-qif-lifetimes/lifetimes-fig12.png` |

All model equations (Eqs. 1, 6-13, 30-33) and the Appendix-A geometry are
implemented in `src/microtubule_qif/` and covered by `tests/test_model_measures.py`.

**Interactive walkthrough.** `docs/paper-2602.02868/ui/` is a self-contained
D3 + Three.js single-page app with one interactive view per step: a 3D WebGL
geometry (Trp sites + dipole arrows, dimer/spiral toggle), Δ/G heatmaps, the
bright/dark spectrum, the dynamics with a play/scrub timeline driving four
synchronized charts, the embedding sweep, the trace-distance backflow, and the
lifetime scaling. Data is exported by `scripts/export_viz_data.py`; run with any
static server (see `ui/README.md`).

## Key implementation note (numerical stability)

The eigenmode analysis uses the **excitonic eigenstates** — eigenvectors of the
Hermitian H0 + Delta, each with collective rate Gamma_j = ⟨v_j|G|v_j⟩ — rather
than `np.linalg.eig` on the effective non-Hermitian H_eff. In the Trp near field
the coherent coupling dominates (Delta ~ 1e4 × gamma), so H_eff is strongly
non-normal and a direct complex eigensolve returns garbage imaginary parts
(|Gamma|/gamma ~ 1e4, even negative). To first order in G/Delta the two agree, so
the excitonic route is both the correct perturbative limit and numerically
stable. This gives the physical spectrum Gamma_j/gamma ∈ [0.11, 2.04] for the
single dimer.

## Not reproduced (needs HPC or non-public author data)

| Paper figure | Why not | Route |
|---|---|---|
| Figs. 4-9 at full one/two-spiral scale (104 / 208 sites) | Lindblad dynamics on 105-209-dim Hilbert spaces with strong stiffness is out of workstation reach; the paper used the Digital Research Alliance of Canada HPC | Embeddings/backflow are shown at the tractable three-tubulin (24-site) scale, which already exhibits the qualitative trends |
| Figs. 10-11 | Correlated-coherence matrices for a 13-filament × 100-spiral assembly (10400 sites) | Spectral-only; needs HPC-scale eigensolves |
| Fig. 12 at 100 spirals | 10400-site build + eigensolve; the O(N²) Python coupling loop and dense eigensolve are impractical past ~2000 sites here | Shown to 20 spirals (2080 sites); trend is already clear |
| Structural-disorder panels (MD ensemble) | The authors' AMBER trajectory / 3100 snapshots are not public (data available from the author on request) | A Gaussian positional-jitter proxy is used and clearly labelled; exact MD reproduction needs the trajectory (tracked in GitHub issues 3-4) |

See `reproduction-gap-report.md` for the full public-source search and the
tracker issues for author-data requests.
