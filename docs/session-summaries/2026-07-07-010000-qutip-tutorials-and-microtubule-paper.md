# Session Summary: qutip-tutorials fork/runs + microtubule paper implementation

## Summary

Forked and ran the full QuTiP tutorials suite locally and on the corsair
machine, created a public-repo skill for Claude and Codex, and began a faithful
reproduction of arXiv:2602.02868v1 (Quantum Information Flow in Microtubule
Tryptophan Networks). A concurrent Claude session was found to be implementing
the same paper in the same files, so the paper work was partly yielded to avoid
corrupting its progress (see "Concurrency note").

## Completed Work

- **qutip-sandbox-j0c.1** — Forked qutip/qutip-tutorials → micahstubbs/qutip-tutorials (`gh repo fork`).
- **qutip-sandbox-j0c.2** — Cloned the fork; `/audit-clone` verdict CLEAN (`docs/security-audit-qutip-tutorials.md`). Commit ce0f58c.
- **qutip-sandbox-j0c.3 (local runs)** — `scripts/run_tutorial_notebooks.py` (jupytext + nbclient runner with `--retry`). tutorials-v5 local: **97/97 pass**. Commit 6ff69eb.
- **qutip-sandbox-zqk** — public-repo skill: `~/.claude/commands/public-repo.md` and `~/.codex/skills/public-repo/` (SKILL.md + agents/openai.yaml), based on private-repo with an added pre-publication secret scan. Committed in the respective ~/.claude and ~/.codex repos.
- **qutip-sandbox-s3i.1** — Paper foundation: `src/microtubule_qif/geometry.py` (8 Trp dipoles from PDB 1JFF + Appendix-A spiral assembly) and `couplings.py` (Delta Eq9, G Eq10). Verified G is PSD with superradiant eigenvalue 4.15γ and a subradiant mode →0. Commit c62d0da.

## Notebook run results

| Set | Machine | Pass | Fail | Timeout |
|-----|---------|------|------|---------|
| v5  | local (4w, 600s)  | 97 | 0 | 0 |
| v5  | corsair (6w, 600s) | 90 | 0 | 7 |
| v4  | local  | running | | |
| v4  | corsair | running | | |

The 7 corsair v5 timeouts are all compute-heavy notebooks (HEOM FMO/heat-transport/fermions, Dicke, single-atom lasing, JCHM) that exceed 600s under 6-way contention — not real failures; local (4 workers) ran them all green.

Env setup notes: QuTiP 5 needs Python ≥3.10 (system was 3.9 → made `.venv` with 3.13). v4 legacy notebooks need qutip 4.7.5 + numpy<1.24 + **cython 0.29.32** (the string-compiled HEOM spectral-density callbacks fail without cython) in a separate `.venv-v4` (3.10 locally, uv-provisioned 3.10 on corsair).

## Concurrency note (important)

A second live Claude session (`claude --dangerously-skip-permissions`, PID
91968) is implementing the SAME paper task in the SAME working tree, editing
`src/microtubule_qif/model.py`, `measures.py`, `tests/`, `README.md`, and adding
`scripts/run_microtubule_qif.py` + `docs/paper-2602.02868/implementation-notes.md`
in real time (uncommitted). This caused test results to change between
invocations (e.g. a superradiant-decay test read area 0.497 standalone vs 39.17
under pytest seconds apart). To avoid corrupting the other session's work I:
- committed only my geometry+couplings foundation (c62d0da),
- left model/measures/tests uncommitted for the other session to finish,
- did not overwrite its README/script/doc additions.

The other session's additions (physical ps-unit lifetime conversion, static
site-energy disorder, explicit partial-transpose negativity, a full figure
script) are good and compatible with my module layout.

## Pending / Next

- v4 runs (local + corsair) still executing; harvest reports and close j0c.3/j0c.4 when done, then rerun v4 failures with `--retry` (cython now installed in both v4 envs).
- Paper: s3i.2–s3i.6 (model, measures, dynamics figures, embeddings, lifetimes) — reconcile with the concurrent session before committing; s3i.7 (D3/Three.js visualizations) still open.
- No git remote configured — nothing pushed.

## Next Session Context

- Local venvs: `.venv` (py3.13, qutip 5.3) and `.venv-v4` (py3.10, qutip 4.7.5). Corsair: `~/wk/qutip-sandbox-corsair` with `.venv`/`.venv-v4`.
- Notebook runner: `scripts/run_tutorial_notebooks.py --set {v4,v5} [--retry]`.
- Paper model verified correct standalone: superradiant fully decays by ~t=10/γ, subradiant (Γ=0.108γ) retains ~11% at t=20/γ — matches Figs 2–3.
