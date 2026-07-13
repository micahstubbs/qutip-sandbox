#!/usr/bin/env python
"""Import queued site feedback (Cloudflare KV) into beads issues.

The feedback Worker emails each submission in real time AND queues it in a
Cloudflare KV namespace. This script drains that queue into beads issues so
feedback is tracked and triaged where beads lives (the local git repo).

For each not-yet-imported record it runs:
  br create --title "Feedback: <snippet>" --type=task --priority=2 \
     --labels=user-feedback,needs-human-review --description "<full record>"
then marks the KV record imported=true so re-runs are idempotent.

Reads Cloudflare creds from ~/keys/cloudflare/KEYS.md (API_TOKEN, ACCOUNT_ID).
The KV namespace id is read from feedback-worker/wrangler.toml.

Usage:
  scripts/import_feedback.py [--dry-run]
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
KEYS = Path.home() / "keys" / "cloudflare" / "KEYS.md"
WRANGLER = ROOT / "feedback-worker" / "wrangler.toml"
LABELS = "user-feedback,needs-human-review"


def read_kv_field(path: Path, field: str) -> str:
    for line in path.read_text().splitlines():
        m = re.match(rf"^{field}\s*=\s*(.+)$", line.strip())
        if m:
            return m.group(1).strip().strip('"').strip("'")
    raise SystemExit(f"{field} not found in {path}")


def kv_namespace_id() -> str:
    text = WRANGLER.read_text()
    m = re.search(r'id\s*=\s*"([0-9a-f]+)"', text)
    if not m:
        raise SystemExit("KV namespace id not found in wrangler.toml")
    return m.group(1)


def cf(method: str, url: str, token: str, data: bytes | None = None):
    req = urllib.request.Request(url, method=method, data=data)
    req.add_header("Authorization", f"Bearer {token}")
    if data is not None:
        req.add_header("Content-Type", "application/json")
    with urllib.request.urlopen(req, timeout=30) as r:
        body = r.read()
    return json.loads(body) if body else {}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    token = read_kv_field(KEYS, "API_TOKEN")
    account = read_kv_field(KEYS, "ACCOUNT_ID")
    ns = kv_namespace_id()
    base = f"https://api.cloudflare.com/client/v4/accounts/{account}/storage/kv/namespaces/{ns}"

    listing = cf("GET", f"{base}/keys?limit=1000", token)
    keys = [k["name"] for k in listing.get("result", []) if k["name"].startswith("fb:")]
    if not keys:
        print("no feedback in queue.")
        return 0

    imported = skipped = 0
    for key in sorted(keys):
        # KV values endpoint returns the raw stored string (our JSON record).
        rec = cf("GET", f"{base}/values/{key}", token)
        if rec.get("imported"):
            skipped += 1
            continue
        msg = (rec.get("message") or "").strip()
        snippet = re.sub(r"\s+", " ", msg)[:70]
        view = rec.get("page") or "(unknown view)"
        who = rec.get("email") or "anonymous"
        desc = (
            f"User feedback submitted from the QIF site.\n\n"
            f"- View: {view}\n- From: {who}\n- Time: {rec.get('ts')}\n"
            f"- Origin: {rec.get('origin')}\n\nMessage:\n{msg}\n"
        )
        title = f"Feedback: {snippet}" if snippet else "Feedback (no text)"
        print(f"[{'DRY' if args.dry_run else 'IMPORT'}] {title}")
        if not args.dry_run:
            subprocess.run(
                ["br", "create", "--title", title, "--type", "task",
                 "--priority", "2", "--labels", LABELS, "--description", desc,
                 "--silent"], cwd=ROOT, check=True)
            rec["imported"] = True
            cf("PUT", f"{base}/values/{key}", token, data=json.dumps(rec).encode())
        imported += 1

    print(f"done: {imported} imported, {skipped} already-imported.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
