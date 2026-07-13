#!/usr/bin/env bash
# Deploy the interactive QIF UI to GitHub Pages.
#
# Publishes docs/paper-2602.02868/ui/ to the root of a `gh-pages` branch so the
# site loads at https://<owner>.github.io/<repo>/ with the UI's relative paths
# (vendor/, data.json, styles.css) intact. Uses a temporary worktree so the
# working tree and current branch are untouched.
#
# Usage: scripts/deploy_ui_gh_pages.sh
set -euo pipefail

REPO_ROOT="$(git rev-parse --show-toplevel)"
UI_DIR="$REPO_ROOT/docs/paper-2602.02868/ui"
BRANCH="gh-pages"
WORKTREE="$(mktemp -d)/gh-pages"

if [ ! -f "$UI_DIR/index.html" ] || [ ! -f "$UI_DIR/data.json" ]; then
  echo "error: UI or data.json missing under $UI_DIR (run scripts/export_viz_data.py)" >&2
  exit 1
fi

cd "$REPO_ROOT"

# Create or reuse an orphan gh-pages branch in an isolated worktree.
if git show-ref --verify --quiet "refs/heads/$BRANCH"; then
  git worktree add "$WORKTREE" "$BRANCH"
else
  git worktree add --detach "$WORKTREE"
  git -C "$WORKTREE" checkout --orphan "$BRANCH"
  git -C "$WORKTREE" rm -rf . >/dev/null 2>&1 || true
fi

# Sync UI contents to the branch root (delete stale files, keep .git).
rsync -a --delete --exclude ".git" "$UI_DIR"/ "$WORKTREE"/
# Jekyll would ignore vendor/ dotfiles etc.; disable it.
touch "$WORKTREE/.nojekyll"

git -C "$WORKTREE" add -A
if git -C "$WORKTREE" diff --cached --quiet; then
  echo "gh-pages already up to date."
else
  git -C "$WORKTREE" commit -q -m "Deploy interactive QIF UI ($(git rev-parse --short HEAD))"
fi
git -C "$WORKTREE" push -q origin "$BRANCH"

git worktree remove --force "$WORKTREE" 2>/dev/null || true

# Enable Pages from the gh-pages branch root (idempotent).
OWNER_REPO="$(gh repo view --json nameWithOwner -q .nameWithOwner)"
if gh api "repos/$OWNER_REPO/pages" >/dev/null 2>&1; then
  gh api -X PUT "repos/$OWNER_REPO/pages" \
    -f "source[branch]=$BRANCH" -f "source[path]=/" >/dev/null 2>&1 || true
else
  gh api -X POST "repos/$OWNER_REPO/pages" \
    -f "source[branch]=$BRANCH" -f "source[path]=/" >/dev/null 2>&1 || true
fi

echo "pushed $BRANCH. Site: https://${OWNER_REPO%%/*}.github.io/${OWNER_REPO##*/}/"
