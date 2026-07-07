# Reproduction gap report for arXiv:2602.02868v1

Generated after auditing the local implementation on 2026-07-07.

## What is implemented locally

- Ordered 1JFF dimer geometry with the eight Trp residues from Fig. 1.
- Trp site positions as CD2/CE2 midpoints and 1La dipoles 46.2 deg above the CD2/CE2-to-CD1 axis toward NE1.
- Ordered dimer, two-dimer, one-spiral, and two-spiral builders using the Appendix A transform parameters.
- The 11.7 deg spiral tilt is now applied about an x-parallel axis through beta-tubulin Trp346 CD2 after the initial -55.38 deg longitudinal rotation.
- Dipole-mediated coherent coupling Delta and collective decay matrix G from the published kernels.
- Trace-preserving Lindblad dynamics in the single-excitation-plus-ground space for dimer and two-dimer sized systems.
- Initial states: superradiant, subradiant, coherent uniform, mixed uniform, and localized site injection.
- Measures: L1 coherence, pair L1 coherence, correlated coherence, logarithmic negativity, mutual information, trace distance, and discrete backflow.
- Spectral outputs for 104-site and 208-site ordered assemblies without full density-matrix dynamics.

## Public-source findings

The paper page and HTML are public:

- https://arxiv.org/abs/2602.02868
- https://arxiv.org/html/2602.02868v1
- https://ar5iv.labs.arxiv.org/html/2602.02868v1

The arXiv source includes the manuscript and rendered figure files, but not the
original simulation notebooks, parameter files, or numeric datasets. Its data
availability statement says supporting data are available from the corresponding
author upon reasonable request.

The Appendix A geometry values are confirmed in the arXiv HTML/source: -55.38
deg initial rotation, 11.7 deg rotation through beta Trp346 CD2, 11.2 nm y and
0.3 nm z translation, 27.69 deg turn rotation, 0.9 nm x step, 13 dimers per
spiral, approximately 22.4 nm diameter, and 8 nm spacing between spirals.

Adjacent papers confirm the same construction and Trp dipole convention:

- Patwa, Babcock, and Kurian, Frontiers in Physics 2024:
  https://www.frontiersin.org/journals/physics/articles/10.3389/fphy.2024.1387271/full
- Gassab and Craddock, arXiv:2604.18604v1:
  https://arxiv.org/html/2604.18604v1

The later Gassab/Craddock preprint also provides useful MD details: AMBER 22
pmemd, 310 K, 6.2 ns production, 2 ps saved frames for 3100 frames, 1TVK
template, Swiss-Model completion, H++/PROPKA protonation, ff14SB, TIP3P, 25 A
water buffer, and cpptraj extraction.

That later preprint advertises Code S1, but its caption identifies it as the
Python script for absorbance tail fitting, quantum-yield calculation,
uncertainty propagation, and Welch tests. It is not the QIF Lindblad simulation
code needed to reproduce arXiv:2602.02868v1.

The structural entries used by the paper are public:

- 1JFF: https://www.rcsb.org/structure/1JFF
- 1TVK: https://www.rcsb.org/structure/1TVK

General web search found no public repository for the exact
arXiv:2602.02868v1 QIF simulations. Authenticated GitHub CLI searches also
found no public repository or code hit for the exact QIF paper or the
distinctive geometry constants.

## GitHub CLI search log

These searches were run with `gh` authenticated as the local GitHub account on
2026-07-07. Each returned no results.

```bash
gh search repos '"Quantum Information Flow in Microtubule Tryptophan Networks"' --limit 20
gh search repos 'microtubule tryptophan quantum Patwa Kurian Craddock' --limit 20
gh search repos '"tryptophan" "microtubule"' --limit 50
gh search repos 'Patwa Babcock Kurian tryptophan microtubule' --limit 50

gh search code '"2602.02868"' --limit 20
gh search code '"-55.38" "27.69"' --limit 50
gh search code '"Trp346" "CD2" microtubule' --limit 50
gh search code '"11.7" "27.69" "microtubule"' --limit 50
gh search code '"1JFF" "46.2" "CD2"' --limit 50
gh search code '"1JFF" "tryptophan" "microtubule"' --limit 50
```

## Information still needed for full reproduction

| Needed item | Why it matters | Public status | Best route |
| --- | --- | --- | --- |
| Author simulation code or notebooks for the QIF paper | Required for exact figure matching, pair-selection rules, plotting windows, and any numerical shortcuts used for large systems | Not public in arXiv source or general web results | Email the corresponding author; ask for QIF scripts and figure-generation notebooks |
| Exact Patwa construction code referenced by the paper | Removes ambiguity in transform order, pivot-axis convention, residue labeling after assembly, and 13-filament/spiral indexing | Not found publicly in this search | Request from Patwa/Kurian group or look for supplemental code after publication of related work |
| MD trajectory or 3100 extracted PDB frames | Required for structural-disorder panels and lifetime curves with random tubulin conformers | Not bundled with arXiv:2602.02868v1 | Request trajectory/snapshots; otherwise reproduce MD from Appendix A.2 |
| Complete MD setup files | Needed to make a regenerated trajectory defensible: exact 1TVK preparation, missing-residue model, protonation choices, nucleotide/ligand parameter files, minimization/equilibration protocol, thermostat/barostat settings, and random seeds | Only summarized in the paper | Request AMBER inputs/topologies; fallback is a documented independent AMBER reconstruction |
| Exact static-disorder ensemble seeds and sample counts | Needed for bit-for-bit disorder panels and error bars | Not public | Request seeds/raw matrices; fallback is fixed local seeds and clearly labeled independent ensembles |
| Full numerical data behind figures | Needed to verify figure-level reproduction without image digitization | Not public | Request CSV/NPZ exports; fallback is WebPlotDigitizer on embedded PDFs, marked approximate |
| Large-system compute strategy | Needed for one/two spiral Lindblad dynamics and 100-spiral spectra at practical cost | Paper mentions national HPC but no implementation details | Ask authors for solver strategy; fallback is sparse eigensolvers, block reductions, and spectral-only approximations |
| Nonradiative and quantum-yield parameters | Needed only if extending from QIF dynamics to fluorescence quantum-yield papers | Partly in later supplementary materials, not central to QIF figures | Use later preprint supplementary files or request exact parameter table |

## Tracker issues opened

Each missing-information item now has a local Beads issue and a GitHub issue.
The issue bodies include an author-request plan and an independent-estimation
fallback.

| Missing item | Bead | GitHub issue |
| --- | --- | --- |
| Author simulation code or notebooks for the QIF paper | `qutip-sandbox-obtain-qif-author-code-is6` | https://github.com/micahstubbs/qutip-sandbox/issues/1 |
| Exact Patwa construction code | `qutip-sandbox-obtain-patwa-geometry-code-oc2` | https://github.com/micahstubbs/qutip-sandbox/issues/2 |
| MD trajectory or 3100 extracted PDB frames | `qutip-sandbox-obtain-md-snapshots-nqu` | https://github.com/micahstubbs/qutip-sandbox/issues/3 |
| Complete MD setup files | `qutip-sandbox-obtain-amber-setup-files-k4h` | https://github.com/micahstubbs/qutip-sandbox/issues/4 |
| Exact static-disorder ensemble seeds and sample counts | `qutip-sandbox-recover-static-disorder-seeds-m4c` | https://github.com/micahstubbs/qutip-sandbox/issues/5 |
| Full numerical data behind figures | `qutip-sandbox-obtain-qif-figure-data-oay` | https://github.com/micahstubbs/qutip-sandbox/issues/6 |
| Large-system compute strategy | `qutip-sandbox-clarify-large-system-solver-sci` | https://github.com/micahstubbs/qutip-sandbox/issues/7 |
| Nonradiative and quantum-yield parameters | `qutip-sandbox-clarify-qy-nonradiative-params-0ki` | https://github.com/micahstubbs/qutip-sandbox/issues/8 |

## Practical options

1. Author-data route: email L.G. and T.J.A.C. with this report, asking for the
   QIF scripts, generated data, Patwa geometry code, MD snapshots, and AMBER
   inputs. This is the only route to a bit-for-bit reproduction.

2. Independent reconstruction route: use the local ordered 1JFF implementation
   as the reference, regenerate a 1TVK AMBER trajectory from the summarized MD
   protocol, and label all disorder results as independent reproductions rather
   than the authors' exact ensemble.

3. Hybrid route: keep exact ordered 1JFF figures from this repo, request only
   MD snapshots and figure data for disorder/large-system panels, and avoid
   reproducing the full MD pipeline unless the snapshots are unavailable.

4. Approximate validation route: digitize the paper PDFs for target curves and
   compare qualitative trends. This is useful for regression tests but should
   not be presented as exact reproduction.

## Current local boundary

The current repo reproduces the model equations and the qualitative ordered
single-dimer behavior. It does not yet reproduce the author-specific large
spiral Lindblad dynamics, non-Markovian backflow panels, 100-spiral correlated
coherence matrices, or MD structural-disorder panels at figure fidelity because
the necessary code/data are not public.
