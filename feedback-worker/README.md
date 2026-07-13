# Feedback Worker

A tiny Cloudflare Worker that backs the site's feedback widget. On each POST it:

1. **Emails** the submission to a maintainer address (via Resend), and
2. **Queues** it in a Cloudflare KV namespace for triage.

A local importer (`../scripts/import_feedback.py`) later drains the KV queue into
beads issues labeled `user-feedback, needs-human-review`. Beads lives in the git
repo, so issue creation happens locally — the Worker holds no GitHub token.

## Why this shape

- Static site stays on GitHub Pages (reliable HTTPS on the custom domain).
- Only the dynamic bit is a Worker — free tier, HTTPS built in, no custom domain
  needed (the page POSTs cross-origin with CORS).
- The **only secret** in the Worker is a Resend **send-only** API key. No GitHub
  token, no broad credentials.

## Deploy (fork-friendly)

Everything non-secret is in `wrangler.toml` `[vars]`; edit those for your fork.

```bash
export CLOUDFLARE_API_TOKEN=...      # a token with Workers + KV edit
export CLOUDFLARE_ACCOUNT_ID=...

# 1. create a KV namespace and paste its id into wrangler.toml
npx wrangler kv namespace create FEEDBACK

# 2. set the Resend send-only key as a secret (never committed)
printf '%s' "$RESEND_KEY" | npx wrangler secret put RESEND_API_KEY

# 3. deploy
npx wrangler deploy
```

Then set the printed Worker URL in the site's `feedback.config.js`
(see `../docs/paper-2602.02868/ui/feedback.config.example.js`) and redeploy the site.

## Config (`wrangler.toml [vars]`)

| var | meaning |
|-----|---------|
| `FEEDBACK_TO` | recipient email |
| `FEEDBACK_FROM` | a Resend-verified sender, e.g. `Name <feedback@yourdomain>` |
| `SITE_NAME` | label used in the email subject |
| `ALLOWED_ORIGINS` | comma-separated CORS origins allowed to POST |

## Secrets & privacy

- `RESEND_API_KEY` — Cloudflare Worker **secret** (`wrangler secret put`), never
  in git. Use a Resend **send-only** key (least privilege).
- The site's real endpoint lives in `feedback.config.js`, which is **gitignored**;
  only `feedback.config.example.js` is committed. A private copy of the real
  config is kept outside the public repo (this maintainer: `~/keys/qutip-sandbox/`).

## Endpoint contract

`POST /` with JSON `{ message, email?, page?, website? }` where `website` is a
honeypot (leave empty). Returns `{ ok, emailed, queued }`. CORS-restricted to
`ALLOWED_ORIGINS`.
