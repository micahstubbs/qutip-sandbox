# AGENTS.md — qutip-sandbox

Guidance for AI agents (Claude, Codex, etc.) working in this repository.

## What this is
A reproduction of arXiv:2602.02868 (Quantum Information Flow in Microtubule
Tryptophan Networks) plus an interactive D3/Three.js explainer at
`docs/paper-2602.02868/ui/` (live: https://qutip.micahstubbs.ai/).

- Physics/model: `src/microtubule_qif/`; tests: `tests/test_model_measures.py`.
- Figure scripts: `scripts/run_microtubule_qif.py`, `run_embeddings_backflow.py`,
  `run_lifetime_scaling.py`. UI data export: `scripts/export_viz_data.py`.
- Reproduction status & gaps: `docs/paper-2602.02868/reproduction-status.md`,
  `reproduction-gap-report.md`.

## Feedback widget (dynamic bit)
The site has a feedback button on every view that POSTs to a Cloudflare Worker
(`feedback-worker/`) which emails the maintainer (Resend) and queues to KV; a
local importer (`scripts/import_feedback.py`) turns queued feedback into beads
issues labeled `user-feedback, needs-human-review`.

### Secrets — do not commit
- The Resend key is a **Cloudflare Worker secret** (`wrangler secret put`), never
  in git.
- The live endpoint config `docs/paper-2602.02868/ui/feedback.config.js` is
  **gitignored**; only `feedback.config.example.js` is committed. The widget
  self-disables if unconfigured, so forks work with no backend.
- Also gitignored: `.wrangler/`, `node_modules/`, `.venv*/`.
- To run your own: see `feedback-worker/README.md` (set your Worker vars +
  Resend key, paste the Worker URL into a local `feedback.config.js`).

## Conventions
- Python via `.venv` (Python 3.13, QuTiP 5). Run tests before committing model changes.
- Track work with beads (`br`). Deploy the site with
  `~/.claude/scripts/deploy-gh-pages.sh docs/paper-2602.02868/ui --domain qutip.micahstubbs.ai`.
