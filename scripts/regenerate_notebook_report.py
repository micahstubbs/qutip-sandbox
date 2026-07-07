#!/usr/bin/env python
"""Regenerate a markdown notebook-run report from a results JSONL.

Also supports patching specific notebooks to a new status (e.g. after a
targeted foreground retry) via --set-pass. Keeps the report reproducible and
consistent with run_tutorial_notebooks.py's format.

Usage:
    python scripts/regenerate_notebook_report.py output/notebook-runs/results-v4.jsonl \
        docs/notebook-run-results-v4.md --label "v4 (local)" \
        --set-pass heom-1a-spin-bath-model-basic.md=20.2 ...
"""

import argparse
import json
from pathlib import Path


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("jsonl")
    ap.add_argument("report")
    ap.add_argument("--label", default="")
    ap.add_argument("--set-pass", nargs="*", default=[],
                    help="substr=seconds entries to force to pass")
    args = ap.parse_args()

    rows = [json.loads(l) for l in open(args.jsonl) if l.strip()]
    patches = {}
    for item in args.set_pass:
        key, _, secs = item.partition("=")
        patches[key] = float(secs) if secs else None

    for r in rows:
        for key, secs in patches.items():
            if key in r["notebook"]:
                r["status"] = "pass"
                r["error"] = None
                if secs is not None:
                    r["seconds"] = secs

    # rewrite the (patched) jsonl in place so it stays the source of truth
    with open(args.jsonl, "w") as f:
        for r in sorted(rows, key=lambda r: r["notebook"]):
            f.write(json.dumps(r) + "\n")

    rows.sort(key=lambda r: r["notebook"])
    n_pass = sum(r["status"] == "pass" for r in rows)
    n_fail = sum(r["status"] == "fail" for r in rows)
    n_to = sum(r["status"] == "timeout" for r in rows)

    lines = [
        f"# qutip-tutorials run results{(' — ' + args.label) if args.label else ''}",
        "",
        f"- Total: {len(rows)}  |  pass: {n_pass}  |  fail: {n_fail}  |  timeout: {n_to}",
        "",
        "| Notebook | Status | Seconds | Error |",
        "|---|---|---|---|",
    ]
    for r in rows:
        err = (r["error"] or "").replace("\n", " ").replace("|", "\\|")[:200]
        lines.append(
            f"| {r['notebook']} | {r['status']} | {r['seconds']} | {err} |")
    Path(args.report).write_text("\n".join(lines) + "\n")
    print(f"{args.report}: {n_pass} pass, {n_fail} fail, {n_to} timeout")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
