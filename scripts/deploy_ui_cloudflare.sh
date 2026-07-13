#!/usr/bin/env bash
# Deploy the interactive QIF UI to Cloudflare Pages (project: qutip-sandbox).
#
# The site is hosted directly at https://qutip.micahstubbs.ai/ (custom domain on
# the Cloudflare Pages project) and https://qutip-sandbox.pages.dev/.
#
# Reads the Cloudflare API token + account id from ~/keys/cloudflare/KEYS.md and
# uploads docs/paper-2602.02868/ui/ via wrangler. Regenerate data.json first if
# the model changed:  .venv/bin/python scripts/export_viz_data.py
#
# Usage: scripts/deploy_ui_cloudflare.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
UI_DIR="$REPO_ROOT/docs/paper-2602.02868/ui"
KEYS="$HOME/keys/cloudflare/KEYS.md"
PROJECT="qutip-sandbox"

[ -f "$UI_DIR/index.html" ] || { echo "error: $UI_DIR/index.html missing" >&2; exit 1; }
[ -f "$KEYS" ] || { echo "error: $KEYS not found (Cloudflare creds)" >&2; exit 1; }

CLOUDFLARE_API_TOKEN="$(grep -E '^API_TOKEN' "$KEYS" | head -1 | cut -d= -f2- | tr -d ' "'\''')"
CLOUDFLARE_ACCOUNT_ID="$(grep -E '^ACCOUNT_ID' "$KEYS" | head -1 | cut -d= -f2- | tr -d ' "'\''')"
export CLOUDFLARE_API_TOKEN CLOUDFLARE_ACCOUNT_ID

NPX="$(command -v npx || echo "$HOME/.local/bin/npx")"
cd "$UI_DIR"
"$NPX" --yes wrangler@latest pages deploy . \
  --project-name="$PROJECT" --branch=main --commit-dirty=true

echo "deployed. Live: https://qutip.micahstubbs.ai/  (also https://${PROJECT}.pages.dev/)"
