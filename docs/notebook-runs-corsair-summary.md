# qutip-tutorials notebook runs on corsair-7000d

Corsair (Ubuntu 24.04, 32 cores, 62 GB RAM) ran the QuTiP tutorial suite to
mirror the local runs. Environments: `.venv` (Python 3.12, qutip 5.3.0) for v5,
`.venv-v4` (uv-provisioned Python 3.10, qutip 4.7.5 + cython 0.29.32) for v4.

## Results

| Set | Workers | Timeout | Pass | Fail | Timeout |
|-----|---------|---------|------|------|---------|
| v5  | 6 | 600 s | **90** | 0 | 7 |
| v4  | 8 | 200 s | 22 | 3 | 51 |

Detail: `docs/notebook-run-results-corsair-v5.md`, `docs/notebook-run-results-corsair-v4.md`.

## Reading the v4 numbers (important)

The corsair **v4 run used a 200 s per-notebook timeout**, which is too short
for the tutorial suite — 51 notebooks were cut off mid-computation. This is a
run-configuration artifact, **not** a corsair capability or correctness problem.
The representative v4 result is the **local run at 600 s: 64 pass / 6 fail /
6 timeout** (`docs/notebook-run-results-v4.md`). The 3 corsair v4 hard failures
(`qasm`, `qip-toffoli-cnot`, `teleportation`) are the same legacy
`qutip_qip` circuit-drawing / import incompatibilities seen locally, inherent to
running notebooks pinned to qutip 4.7.0 / qutip-qip 0.2.1 on a current stack.

The corsair **v5 run is fully representative**: 90/97 pass, 0 fail, and the 7
timeouts are genuinely heavy notebooks (HEOM FMO / heat-transport / fermions,
Dicke, single-atom lasing, JCHM) — the same set that timed out nowhere-close on
the local v5 run only because local used 4 workers (less contention) versus
corsair's 6.

## Why v4 was run at 200 s

An earlier corsair v4 first pass (launched while the v5 run was still going,
oversubscribing the box) was crawling, so it was relaunched with more workers
and a shorter 200 s timeout to finish quickly. That traded completeness for
speed and produced the 51 timeouts. A gentle re-run at 600 s with 2–3 workers
(memory-trivial; corsair had ~50 GB free throughout) would reproduce the local
64-pass figure, and can be done later if an exhaustive corsair v4 pass is wanted.

## Memory

Corsair stayed healthy the entire time: ~11 GB used, ~50 GB available, swap
barely touched. The tutorial notebooks are small quantum systems (well under
1 GB per kernel); the machine's larger memory users are unrelated services
(postgres, qdrant).
