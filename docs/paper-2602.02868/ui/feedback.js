/* Feedback widget — a floating button + modal shown on every view.
 * Submits to the configured Cloudflare Worker (window.QIF_FEEDBACK.endpoint),
 * which emails the maintainer and queues the note for triage. Self-disables if
 * no endpoint is configured, so forks without a backend simply hide the button. */
(function () {
  var cfg = window.QIF_FEEDBACK || {};
  if (!cfg.enabled || !cfg.endpoint) return; // no backend configured → no button

  var currentView = function () {
    var active = document.querySelector(".step-btn.is-active");
    return active ? active.textContent.replace(/^0\d\s*/, "").trim() : "";
  };

  // --- launcher button ---
  var btn = document.createElement("button");
  btn.id = "fb-launch";
  btn.className = "fb-launch";
  btn.setAttribute("aria-label", "Send feedback or ask a question");
  btn.innerHTML = '<span class="fb-launch-ico">?</span><span>Feedback</span>';
  document.body.appendChild(btn);

  // --- modal ---
  var overlay = document.createElement("div");
  overlay.className = "fb-overlay";
  overlay.setAttribute("role", "dialog");
  overlay.setAttribute("aria-modal", "true");
  overlay.setAttribute("aria-label", "Feedback");
  overlay.innerHTML =
    '<div class="fb-modal">' +
    '  <button class="fb-close" aria-label="Close feedback">×</button>' +
    '  <h3>Questions or feedback?</h3>' +
    '  <p class="fb-sub">Anything unclear, technically off, or explained at the wrong ' +
    "level? Tell me what would help — the current view is noted automatically.</p>" +
    '  <form class="fb-form">' +
    '    <label class="fb-field"><span>Your message</span>' +
    '      <textarea name="message" rows="5" maxlength="4000" required ' +
    '        placeholder="e.g. The backflow chart could use a one-line explanation of what a revival means."></textarea>' +
    "    </label>" +
    '    <label class="fb-field"><span>Email <em>(optional, for a reply)</em></span>' +
    '      <input type="email" name="email" maxlength="200" placeholder="you@example.com" autocomplete="email">' +
    "    </label>" +
    // honeypot (hidden from humans, bots fill it)
    '    <input type="text" name="website" class="fb-hp" tabindex="-1" autocomplete="off" aria-hidden="true">' +
    '    <div class="fb-row">' +
    '      <span class="fb-view mono"></span>' +
    '      <button type="submit" class="fb-submit">Send</button>' +
    "    </div>" +
    '    <p class="fb-status" role="status"></p>' +
    "  </form>" +
    "</div>";
  document.body.appendChild(overlay);

  var form = overlay.querySelector(".fb-form");
  var statusEl = overlay.querySelector(".fb-status");
  var viewEl = overlay.querySelector(".fb-view");
  var submitBtn = overlay.querySelector(".fb-submit");

  function open() {
    viewEl.textContent = currentView() ? "view: " + currentView() : "";
    statusEl.textContent = "";
    statusEl.className = "fb-status";
    overlay.classList.add("is-open");
    setTimeout(function () { var t = overlay.querySelector("textarea"); if (t) t.focus(); }, 40);
  }
  function close() { overlay.classList.remove("is-open"); }

  btn.addEventListener("click", open);
  overlay.querySelector(".fb-close").addEventListener("click", close);
  overlay.addEventListener("click", function (e) { if (e.target === overlay) close(); });
  document.addEventListener("keydown", function (e) { if (e.key === "Escape") close(); });

  form.addEventListener("submit", function (e) {
    e.preventDefault();
    var fd = new FormData(form);
    var payload = {
      message: (fd.get("message") || "").toString(),
      email: (fd.get("email") || "").toString(),
      website: (fd.get("website") || "").toString(), // honeypot
      page: currentView(),
    };
    if (payload.message.trim().length < 2) {
      statusEl.textContent = "Please enter a message.";
      statusEl.className = "fb-status is-err";
      return;
    }
    submitBtn.disabled = true;
    statusEl.textContent = "Sending…";
    statusEl.className = "fb-status";
    fetch(cfg.endpoint, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    })
      .then(function (r) { return r.json().catch(function () { return {}; }).then(function (j) { return { ok: r.ok, j: j }; }); })
      .then(function (res) {
        if (res.ok && res.j && res.j.ok) {
          statusEl.textContent = "Thanks — your feedback was sent.";
          statusEl.className = "fb-status is-ok";
          form.reset();
          setTimeout(close, 1400);
        } else {
          throw new Error((res.j && (res.j.error || res.j.queueError)) || "send failed");
        }
      })
      .catch(function (err) {
        statusEl.textContent = "Couldn't send (" + err.message + "). Please try again.";
        statusEl.className = "fb-status is-err";
      })
      .finally(function () { submitBtn.disabled = false; });
  });
})();
