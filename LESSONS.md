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
