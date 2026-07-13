# Interactive reconstruction — arXiv:2602.02868v1

**Live:** https://qutip.micahstubbs.ai/ (also https://micahstubbs.github.io/qutip-sandbox/)

A self-contained D3 + Three.js walkthrough of each step of the microtubule
quantum-information-flow implementation. Seven interactive views:

1. **Geometry** (Three.js/WebGL) — the eight 1JFF tryptophan sites in 3D with
   their ¹Lₐ dipole arrows; orbit/zoom; toggle to the 104-site one-spiral cloud.
2. **Couplings** (D3) — Δ (coherent) and G (collective decay) matrices as
   hoverable heatmaps.
3. **Spectrum** (D3) — excitonic eigenmodes split into bright/dark by Γⱼ/γ.
4. **Dynamics** (D3) — the five preparations with a play/scrub timeline driving
   populations, pair L₁ coherence, log-negativity, and bright/dark projection.
5. **Embeddings** (D3) — top-4 focal-tubulin coherences across single/two/three
   tubulin embeddings × four preparations (Fig. 8).
6. **Backflow** (D3) — trace-distance revivals with shaded backflow intervals
   (Fig. 9).
7. **Lifetimes** (D3) — super/subradiant lifetime scaling for ordered / static /
   structural disorder (Fig. 12).

## Run

The page fetches `data.json`, so serve it over HTTP (a `file://` open is blocked
by the browser's fetch policy):

```bash
# regenerate data.json from the current model (optional; a copy is committed)
.venv/bin/python scripts/export_viz_data.py

# serve and open
cd docs/paper-2602.02868/ui
http-server -p 8770 -c-1 .        # or: python3 -m http.server 8770
# then open http://localhost:8770/index.html
```

D3 v7 and Three.js r128 are vendored under `vendor/` so the page works offline.
Fonts (Syne, Space Mono) load from Google Fonts with system fallbacks.

`data.json` is produced by `scripts/export_viz_data.py`, which runs the model in
`src/microtubule_qif/` and the outputs under `output/microtubule-qif*`.
