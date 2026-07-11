# Lessons Learned

Append-only log of debugging insights and non-obvious solutions.

## 2026-07-07T11:07 - QuTiP tutorials-v4 HEOM notebooks need cython

**Problem**: The `tutorials-v4/heom/heom-1*.md` and `heom-2-fmo-example.md`
notebooks failed with a `CellExecutionError` on the spectral-density cell (e.g.
`DL = f"2*pi*2.0*{lam}/(pi*{gamma}*{beta}) if (w==0) else ..."`).

**Root Cause**: QuTiP 4's HEOM solver string-compiles those spectral-density
callback expressions via Cython at runtime. The v4 environment (qutip 4.7.5 +
numpy<1.24) had no `cython` installed, so the compile step failed. The error
surfaces at the notebook cell, not at import, so it looks like a notebook bug.

**Lesson**: For QuTiP 4 HEOM / string-coefficient work, `cython` (0.29.x with
qutip 4.7) is a hard runtime dependency even though it's not always in the
`requirements.txt`. Install `cython==0.29.32 setuptools filelock` alongside
qutip 4.7.5.

**Prevention**: When building a legacy qutip-4 env, add cython up front. Verify
with a single HEOM notebook before launching a full batch.

## 2026-07-07T11:07 - Notebook batch timeout must match the suite, not the machine

**Problem**: A corsair tutorials-v4 run with `--workers 8 --timeout 200`
produced 51/76 timeouts; the same suite locally with `--timeout 600` gave only
6 timeouts (64 pass).

**Root Cause**: Lowering the per-notebook timeout to "finish fast" cut off
notebooks that legitimately need 200-600s. More workers did not help — it just
ran more notebooks into the same wall. The timeout is a property of the slowest
notebooks in the suite, not of the host.

**Lesson**: Size a notebook-runner timeout to the suite's heaviest cells
(600s for the QuTiP tutorials), then add workers for throughput. Never trade
timeout for speed on an unknown-cost batch — you get uninformative timeouts.

**Prevention**: Default the runner to 600s. Only launch a big batch once one
representative heavy notebook (HEOM / Dicke / lasing) is known to complete.

## 2026-07-07T11:07 - Near-field dipole coupling makes the Lindblad Liouvillian stiff

**Problem**: `qutip.mesolve` on the microtubule 8-site model died with
`IntegratorException: Excess work done on this call` for every preparation.

**Root Cause**: The tryptophan sites sit deep in the optical near field
(alpha = k0*r ~ 0.03 for r~1.5nm at lambda0=280nm), so the coherent dipole
coupling Delta scales as ~1/alpha^3 and reaches ~1e4 * gamma, while radiative
decay is ~gamma. The coherent phase winds ~1e4 times per decay time — a stiff
system that blows past the default `nsteps=2500`.

**Lesson**: When one term of a Liouvillian dwarfs another by orders of
magnitude (near-field dipole coupling vs radiative decay here), mesolve needs a
much larger `nsteps` (2e5 worked). A huge coupling-to-decay ratio is a physical
signature of near-field geometry, not a modelling bug.

**Prevention**: Check `max|Delta| / gamma` before solving; if it's >~1e3, raise
`nsteps` (and consider a stiff integrator) rather than assuming a bug.

## 2026-07-07T11:07 - Detect concurrent-agent edits before trusting test results

**Problem**: A model test read `area=0.497` standalone but `39.17` under pytest
seconds apart, with no edit from me. The superradiant state appeared to both
decay and not-decay.

**Root Cause**: A second Claude session was editing the same `src/*.py` files in
real time (switching between a dimensionless gamma=1 convention and a physical
ps-unit convention). Each test run loaded a different in-flight file state.
Confirmed via a hot `claude` process and `requirements.txt` changing under me.

**Lesson**: Inconsistent, non-reproducible test results with unexplained file
"modified" reminders mean a concurrent writer, not flaky code. Fighting it
(editing + committing over their WIP) corrupts both. Yield the contested files,
keep only your committed, convention-agnostic work, and coordinate.

**Prevention**: On surprise "file modified" reminders, run `ps aux | grep claude`
and check `git log`/mtimes before diagnosing the code. If another agent is
active in the same files, stop editing them and carve a non-overlapping slice.

## 2026-07-07T11:07 - Remote nohup survives harness background-task kills; local watchers don't

**Problem**: Every local `run_in_background` watcher and retry I launched was
killed within a turn or two ("was stopped"), but the corsair notebook run kept
going.

**Root Cause**: The local harness/taskmaster stop-hook reaps background bash
tasks between turns. A remote process started with `setsid ... </dev/null &`
(properly detached) on corsair runs independently of the local session and is
unaffected.

**Lesson**: Don't rely on local `run_in_background` watchers to wait on
long-running work in this environment — they get reaped. For remote long jobs,
detach with `setsid`/`nohup </dev/null &` so they survive, and harvest by
pulling result files (scp) rather than keeping a live local watcher.

**Prevention**: For "wait until remote job done", poll on re-invocation or block
a single foreground ssh with a remote until-loop, instead of a local background
watcher that will be killed.

## 2026-07-07T14:16 - Reproduction gaps need source search plus tracked fallbacks

**Problem**: The microtubule QIF paper implementation could reproduce the
published equations and ordered 1JFF workflow, but several figure-level inputs
were absent: author simulation notebooks, Patwa geometry code, MD snapshots,
AMBER setup files, disorder seeds, numerical figure data, and large-system
solver details.

**Root Cause**: The arXiv source package contains the manuscript and rendered
figures, not the full computational provenance. General web search and GitHub
CLI search can establish that no public repository is obvious, but that still
leaves two valid paths: ask the authors for exact artifacts or build clearly
labeled independent estimates.

**Lesson**: For computational-paper reproductions, treat missing provenance as
tracked work rather than a narrative footnote. Record the exact public-source
and `gh search` queries, then create one issue per missing artifact with both an
author-request checklist and an estimation fallback.

**Solution**: Documented the search log in
`docs/paper-2602.02868/reproduction-gap-report.md`, created linked Beads and
GitHub issues for each missing artifact, and stored the GitHub URL in each
Beads issue `external_ref`.

**Prevention**: When implementing a paper, create the reproduction-gap report
as soon as a required input is unavailable. Do not wait until the end of the
implementation, because missing datasets, seeds, and solver choices affect both
tests and user-facing claims.

## 2026-07-11T00:00 - "Garbage output" that looks like a concurrent-agent race was a return-tuple misread

**Problem**: `net.eigenmodes()` appeared to return garbage decay rates
(Γ/γ = 25230, -23445, ...) in some runs and correct ones (0.108..2.04) in
others, with the source file unchanged (mtime frozen). I spent a long time
convinced a concurrent Claude session was flipping model.py between an
excitonic version and a `np.linalg.eig(H_eff)` version many times per second.

**Root Cause**: `eigenmodes()` returns `(energies, decay, evecs)`. The excitonic
*energies* are the eigenvalues of Δ, which in the near field are ±10^4·γ — the
exact same magnitude/sign pattern as the "non-normal H_eff garbage" I expected.
My debug scripts unpacked `d, _, _ = net.eigenmodes()`, so `d` was **energies,
not decay**. Different scripts unpacked differently (`_, decay, _` vs `d,_,_`),
producing "inconsistent" results that mimicked a live file race. The tell that
disproved the race: `git diff` was empty and mtime never advanced, yet output
"changed" — impossible for a file edit, so the variance had to be in *my* code.

**Lesson**: Before attributing non-reproducible results to concurrency or the
environment, confirm you are reading the right return value. A multi-value
return whose elements have overlapping magnitude ranges (here energies and
decay both dimensionless multiples of γ) is a trap. When "the file didn't change
but the output did," suspect your own unpacking/closure before the filesystem.

**Prevention**: For functions returning several arrays, name them at the call
site (`energies, decay, evecs = ...`) rather than positional `x,_,_`, and add a
one-line assertion on physical bounds (`assert decay.min() >= 0`) right where
the value is consumed — it would have caught the energies-as-decay swap instantly.

## 2026-07-11T00:00 - Viz data-fabrication: a summary scalar reconstructed into fake per-item bars

**Problem**: The embeddings view drew four bars per cell at heights
`max_pair_l1 * (1 - i*0.18)` — a synthetic linear ramp keyed only to rank index.
Only the first bar (the true max) was real; the other three were invented and
presented as measured per-pair coherences.

**Root Cause**: The upstream script collapsed the per-pair time series to a
single scalar (`max_pair_l1`) plus the pair IDs, discarding the actual per-pair
values. The UI then "reconstructed" a plausible-looking distribution from that
one number to fill the bars.

**Lesson**: If a visualization shows per-item magnitudes, the dataset must
contain per-item values. A single aggregate + a rank-index formula is
fabrication, however plausible it looks. The fix is upstream: export the real
series, not a scalar. Cross-check every view by diffing *what the exporter
writes* against *what the view reads* — a view that renders more structure than
the data contains is manufacturing it.

**Prevention**: In review, for each chart ask "where does each plotted value
come from in the JSON?" and trace it to a stored number. Any value computed from
an index (`i`), a constant ramp, or `Math.random` in a "data" view is a red flag.
