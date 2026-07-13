/* Feedback widget configuration — TEMPLATE.
 *
 * Copy this file to `feedback.config.js` (which is gitignored) and set your own
 * Cloudflare Worker endpoint. The widget hides itself when `enabled` is false or
 * `endpoint` is empty, so forks work out of the box with no backend.
 *
 * Deploy the backend from ../../../feedback-worker/ (see its README), then paste
 * the Worker URL below.
 */
window.QIF_FEEDBACK = {
  enabled: false,
  endpoint: "", // e.g. "https://qutip-feedback.<your-subdomain>.workers.dev"
};
