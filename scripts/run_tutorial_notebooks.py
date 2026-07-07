#!/usr/bin/env python
"""Execute all qutip-tutorials jupytext notebooks and record pass/fail results.

The tutorials repo stores notebooks as jupytext markdown files. This runner:

1. Discovers <repo>/tutorials-v5/**/*.md (skipping template.md)
2. Converts each to a notebook via jupytext and executes it with nbclient
3. Records status (pass / fail / timeout), duration, and the error summary
4. Streams per-notebook results to a JSONL file and writes a markdown report

Usage:
    .venv/bin/python scripts/run_tutorial_notebooks.py [--set v5|v4] \
        [--timeout 600] [--workers 4] [--report docs/notebook-run-results-local.md]

The v4 set targets legacy QuTiP 4.7 and will largely fail under QuTiP 5; the
default is the v5 set, which matches the installed qutip.
"""

import argparse
import json
import os
import sys
import time
import traceback
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import jupytext
from nbclient import NotebookClient

ROOT = Path(__file__).resolve().parent.parent
TUTORIALS = ROOT / "qutip-tutorials"
RUNS_DIR = ROOT / "output" / "notebook-runs"


def discover(nb_set: str) -> list[Path]:
    base = TUTORIALS / f"tutorials-{nb_set}"
    return sorted(
        p for p in base.rglob("*.md") if p.name != "template.md"
    )


def run_one(path: Path, timeout: int, workdir: Path) -> dict:
    path = path.resolve()
    rel = str(path.relative_to(TUTORIALS))
    start = time.time()
    try:
        nb = jupytext.read(path)
        client = NotebookClient(
            nb,
            timeout=timeout,
            kernel_name="python3",
            resources={"metadata": {"path": str(workdir)}},
        )
        client.execute()
        return {"notebook": rel, "status": "pass",
                "seconds": round(time.time() - start, 1), "error": None}
    except Exception as exc:  # noqa: BLE001 — record every failure mode
        kind = type(exc).__name__
        status = "timeout" if "timeout" in kind.lower() or "Timeout" in str(exc)[:200] else "fail"
        first_lines = "\n".join(str(exc).strip().splitlines()[:6])[:800]
        return {"notebook": rel, "status": status,
                "seconds": round(time.time() - start, 1),
                "error": f"{kind}: {first_lines}"}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--set", dest="nb_set", default="v5", choices=["v4", "v5"])
    ap.add_argument("--timeout", type=int, default=600)
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--report", default=None,
                    help="markdown report path (default docs/notebook-run-results-<set>.md)")
    ap.add_argument("--retry", action="store_true",
                    help="rerun only the non-pass notebooks from the existing "
                         "results JSONL and merge the outcomes")
    args = ap.parse_args()

    notebooks = discover(args.nb_set)
    prior = {}
    if args.retry:
        prior_path = RUNS_DIR / f"results-{args.nb_set}.jsonl"
        with open(prior_path) as pf:
            for line in pf:
                rec = json.loads(line)
                prior[rec["notebook"]] = rec
        notebooks = [p for p in notebooks
                     if prior.get(str(p.resolve().relative_to(TUTORIALS)),
                                  {}).get("status") != "pass"]
        print(f"Retry mode: {len(notebooks)} previously non-passing notebooks")
    if not notebooks:
        print(f"No notebooks found for set {args.nb_set}", file=sys.stderr)
        return 1

    RUNS_DIR.mkdir(parents=True, exist_ok=True)
    suffix = "-retry" if args.retry else ""
    jsonl_path = RUNS_DIR / f"results-{args.nb_set}{suffix}.jsonl"
    report_path = Path(args.report) if args.report else (
        ROOT / "docs" / f"notebook-run-results-{args.nb_set}.md"
    )

    print(f"Running {len(notebooks)} notebooks from tutorials-{args.nb_set} "
          f"with {args.workers} workers, {args.timeout}s timeout each")
    results = []
    with open(jsonl_path, "w") as jf, ThreadPoolExecutor(args.workers) as pool:
        futures = {
            pool.submit(run_one, p, args.timeout, p.parent): p for p in notebooks
        }
        for i, fut in enumerate(as_completed(futures), 1):
            try:
                res = fut.result()
            except Exception:  # noqa: BLE001
                res = {"notebook": str(futures[fut]), "status": "fail",
                       "seconds": None,
                       "error": traceback.format_exc()[-800:]}
            results.append(res)
            jf.write(json.dumps(res) + "\n")
            jf.flush()
            print(f"[{i}/{len(notebooks)}] {res['status'].upper():7s} "
                  f"{res['notebook']} ({res['seconds']}s)")

    if args.retry:
        merged = dict(prior)
        for r in results:
            merged[r["notebook"]] = r
        results = list(merged.values())
        with open(RUNS_DIR / f"results-{args.nb_set}.jsonl", "w") as mf:
            for r in sorted(results, key=lambda r: r["notebook"]):
                mf.write(json.dumps(r) + "\n")

    results.sort(key=lambda r: r["notebook"])
    n_pass = sum(r["status"] == "pass" for r in results)
    n_fail = sum(r["status"] == "fail" for r in results)
    n_timeout = sum(r["status"] == "timeout" for r in results)

    lines = [
        f"# qutip-tutorials {args.nb_set} notebook run results (local)",
        "",
        f"- Total: {len(results)}  |  pass: {n_pass}  |  fail: {n_fail}  |  timeout: {n_timeout}",
        f"- Timeout per notebook: {args.timeout}s, workers: {args.workers}",
        "",
        "| Notebook | Status | Seconds | Error |",
        "|---|---|---|---|",
    ]
    for r in results:
        err = (r["error"] or "").replace("\n", " ").replace("|", "\\|")[:200]
        lines.append(f"| {r['notebook']} | {r['status']} | {r['seconds']} | {err} |")
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text("\n".join(lines) + "\n")

    print(f"\nDone: {n_pass}/{len(results)} passed. Report: {report_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
