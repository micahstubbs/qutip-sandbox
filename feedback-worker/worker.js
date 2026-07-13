/* QuTiP feedback Worker — receives feedback from the static site, emails it via
 * Resend, and queues it in KV for a local importer to turn into beads issues.
 *
 * No secrets live in this file. Configure via wrangler.toml [vars] and set the
 * Resend key as a secret:  wrangler secret put RESEND_API_KEY
 *
 * Bindings/vars (see wrangler.toml):
 *   FEEDBACK        (KV namespace)  — durable queue of submissions
 *   FEEDBACK_TO     (var)           — recipient, e.g. hi@micah.fyi
 *   FEEDBACK_FROM   (var)           — verified Resend sender, e.g. QuTiP Feedback <feedback@micahstubbs.ai>
 *   ALLOWED_ORIGINS (var)           — comma-separated allowed CORS origins
 *   SITE_NAME       (var)           — label used in the email subject
 * Secret:
 *   RESEND_API_KEY                  — Resend send-only API key
 */

const MAX_MESSAGE = 4000;
const MAX_EMAIL = 200;

function corsHeaders(origin, allowed) {
  const list = (allowed || "").split(",").map((s) => s.trim()).filter(Boolean);
  const ok = list.includes(origin) || list.includes("*");
  return {
    "Access-Control-Allow-Origin": ok ? origin : list[0] || "null",
    "Access-Control-Allow-Methods": "POST, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
    "Access-Control-Max-Age": "86400",
    "Vary": "Origin",
  };
}

function json(body, status, headers) {
  return new Response(JSON.stringify(body), {
    status,
    headers: { "Content-Type": "application/json", ...headers },
  });
}

export default {
  async fetch(request, env) {
    const origin = request.headers.get("Origin") || "";
    const cors = corsHeaders(origin, env.ALLOWED_ORIGINS);

    if (request.method === "OPTIONS") return new Response(null, { status: 204, headers: cors });
    if (request.method !== "POST") return json({ ok: false, error: "method" }, 405, cors);

    let data;
    try {
      data = await request.json();
    } catch {
      return json({ ok: false, error: "bad json" }, 400, cors);
    }

    // Honeypot: bots fill hidden "website" field; humans leave it empty.
    if (data.website) return json({ ok: true }, 200, cors); // silently accept + drop

    const message = String(data.message || "").trim().slice(0, MAX_MESSAGE);
    const email = String(data.email || "").trim().slice(0, MAX_EMAIL);
    const page = String(data.page || "").trim().slice(0, 200);
    const ua = String(request.headers.get("User-Agent") || "").slice(0, 300);
    if (message.length < 2) return json({ ok: false, error: "empty message" }, 400, cors);
    if (email && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email))
      return json({ ok: false, error: "bad email" }, 400, cors);

    const ts = new Date().toISOString();
    const site = env.SITE_NAME || "QuTiP site";
    const record = { ts, message, email, page, ua, origin, imported: false };

    // 1) durable queue in KV (key sorts by time; keep 400 days)
    const key = `fb:${ts}:${Math.abs(hash(message + ts)).toString(36)}`;
    let queued = false, queueError = null;
    try {
      if (!env.FEEDBACK) throw new Error("FEEDBACK KV binding missing");
      await env.FEEDBACK.put(key, JSON.stringify(record), { expirationTtl: 60 * 60 * 24 * 400 });
      queued = true;
    } catch (e) {
      queueError = String(e && e.message || e).slice(0, 120);
    }

    // 2) email via Resend (real-time notification)
    let emailed = false, emailError = null;
    try {
      const subject = `[${site}] feedback${page ? ` · ${page}` : ""}`;
      const text =
        `New feedback from ${site}\n\n` +
        `Page/view: ${page || "(unknown)"}\n` +
        `From:      ${email || "(anonymous)"}\n` +
        `Time:      ${ts}\n` +
        `Origin:    ${origin}\n` +
        `User-Agent:${ua}\n\n` +
        `Message:\n${message}\n`;
      const payload = {
        from: env.FEEDBACK_FROM,
        to: [env.FEEDBACK_TO],
        subject,
        text,
      };
      if (email) payload.reply_to = email;
      const res = await fetch("https://api.resend.com/emails", {
        method: "POST",
        headers: {
          "Authorization": `Bearer ${env.RESEND_API_KEY}`,
          "Content-Type": "application/json",
        },
        body: JSON.stringify(payload),
      });
      emailed = res.ok;
      if (!res.ok) emailError = `resend ${res.status}`;
    } catch (e) {
      emailError = String(e).slice(0, 120);
    }

    return json({ ok: true, emailed, queued, error: emailError, queueError }, 200, cors);
  },
};

function hash(s) {
  let h = 0;
  for (let i = 0; i < s.length; i++) h = (Math.imul(31, h) + s.charCodeAt(i)) | 0;
  return h;
}
