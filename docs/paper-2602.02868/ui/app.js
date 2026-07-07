/* Microtubule QIF — interactive reconstruction of arXiv:2602.02868v1.
   D3 for 2D data views, Three.js for the 3D geometry. Driven by data.json. */

const STEPS = [
  ["geometry", "Geometry"],
  ["couplings", "Couplings"],
  ["spectrum", "Spectrum"],
  ["dynamics", "Dynamics"],
  ["embeddings", "Embeddings"],
  ["backflow", "Backflow"],
  ["lifetimes", "Lifetimes"],
];
const SITE_COLORS = d3.schemeSet2;
const BRIGHT = "#ff9e3d", DARK = "#35d0e6", INKDIM = "#8b95a6";
const tip = document.getElementById("tooltip");

function showTip(html, x, y) {
  tip.innerHTML = html;
  tip.style.opacity = 1;
  tip.style.left = Math.min(x + 14, window.innerWidth - 250) + "px";
  tip.style.top = (y + 14) + "px";
}
function hideTip() { tip.style.opacity = 0; }

let DATA = null, built = {};

d3.json("data.json").then((data) => {
  DATA = data;
  document.getElementById("foot-status").textContent =
    `data loaded · ${data.meta.n_dimer} sites · λ₀ ${data.meta.lambda0_nm} nm`;
  const m = document.getElementById("mast-readout");
  m.innerHTML = `<span data-k="λ₀">${data.meta.lambda0_nm} nm</span>` +
    `<span data-k="sites">${data.meta.n_dimer}</span>` +
    `<span data-k="Γ_max">${data.meta.bright_max}γ</span>` +
    `<span data-k="Γ_min">${data.meta.dark_min}γ</span>`;
  buildStepbar();
  activate("geometry");
}).catch((e) => {
  document.getElementById("foot-status").textContent = "failed to load data.json — serve via http-server";
  console.error(e);
});

function buildStepbar() {
  const bar = d3.select("#stepbar");
  STEPS.forEach(([id, label], i) => {
    bar.append("button").attr("class", "step-btn").attr("data-step", id)
      .html(`<span class="n">0${i + 1}</span>${label}`)
      .on("click", () => activate(id));
  });
}

function activate(id) {
  d3.selectAll(".step-btn").classed("is-active", function () {
    return this.getAttribute("data-step") === id;
  });
  d3.selectAll(".panel").classed("is-active", function () {
    return this.getAttribute("data-step") === id;
  });
  if (!built[id]) { BUILDERS[id](); built[id] = true; }
  if (id === "geometry" && built.geometry) resizeGeo();
}

/* ---------- shared D3 chart scaffold ---------- */
function svgFrame(sel, w, h, m) {
  d3.select(sel).selectAll("*").remove();
  const svg = d3.select(sel).append("svg")
    .attr("viewBox", `0 0 ${w} ${h}`).attr("width", "100%");
  const g = svg.append("g").attr("transform", `translate(${m.l},${m.t})`);
  return { svg, g, iw: w - m.l - m.r, ih: h - m.t - m.b };
}
function addAxes(g, x, y, iw, ih, xl, yl, yfmt) {
  g.append("g").attr("class", "axis").attr("transform", `translate(0,${ih})`)
    .call(d3.axisBottom(x).ticks(6));
  g.append("g").attr("class", "axis").call(d3.axisLeft(y).ticks(6).tickFormat(yfmt || null));
  g.selectAll(".gridline-y").data(y.ticks(6)).join("line").attr("class", "gridline")
    .attr("x1", 0).attr("x2", iw).attr("y1", d => y(d)).attr("y2", d => y(d));
  if (xl) g.append("text").attr("class", "axis-label").attr("x", iw / 2).attr("y", ih + 34)
    .attr("text-anchor", "middle").text(xl);
  if (yl) g.append("text").attr("class", "axis-label").attr("transform", "rotate(-90)")
    .attr("x", -ih / 2).attr("y", -38).attr("text-anchor", "middle").text(yl);
}

/* ============================================================
   01 · GEOMETRY (Three.js)
   ============================================================ */
let geoState = { renderer: null, scene: null, camera: null, controls: null,
  group: null, mode: "dimer", showDip: true };

function buildGeometry() {
  const host = document.getElementById("geo-canvas");
  const w = host.clientWidth, h = host.clientHeight;
  const scene = new THREE.Scene();
  const camera = new THREE.PerspectiveCamera(45, w / h, 0.01, 5000);
  const renderer = new THREE.WebGLRenderer({ antialias: true, alpha: true });
  renderer.setPixelRatio(window.devicePixelRatio);
  renderer.setSize(w, h);
  host.appendChild(renderer.domElement);
  const controls = new THREE.OrbitControls(camera, renderer.domElement);
  controls.enableDamping = true; controls.dampingFactor = 0.08;
  scene.add(new THREE.AmbientLight(0x8899aa, 0.7));
  const key = new THREE.PointLight(0xffa860, 1.1); key.position.set(20, 30, 25); scene.add(key);
  const fill = new THREE.PointLight(0x35d0e6, 0.7); fill.position.set(-25, -10, -20); scene.add(fill);
  geoState = { renderer, scene, camera, controls, group: null, mode: "dimer", showDip: true };
  renderGeoContent();

  const legend = d3.select("#site-legend");
  DATA.geometry.dimer_sites.forEach((s, i) => {
    const li = legend.append("li");
    li.append("span").attr("class", "dot").style("color", SITE_COLORS[i % 8])
      .style("background", SITE_COLORS[i % 8]);
    li.append("span").text(s.name);
    li.append("span").attr("class", "res").text(s.residue);
  });

  const toggle = (btn, fn) => document.getElementById(btn).addEventListener("click", fn);
  toggle("geo-mode-dimer", () => setGeoMode("dimer"));
  toggle("geo-mode-spiral", () => setGeoMode("spiral"));
  toggle("geo-dipoles", (e) => {
    geoState.showDip = !geoState.showDip;
    e.target.classList.toggle("is-on", geoState.showDip);
    renderGeoContent();
  });

  (function loop() {
    requestAnimationFrame(loop);
    controls.update();
    renderer.render(scene, camera);
  })();
  window.addEventListener("resize", resizeGeo);
}

function setGeoMode(mode) {
  geoState.mode = mode;
  document.getElementById("geo-mode-dimer").classList.toggle("is-on", mode === "dimer");
  document.getElementById("geo-mode-spiral").classList.toggle("is-on", mode === "spiral");
  renderGeoContent();
}

function renderGeoContent() {
  const { scene, camera, controls } = geoState;
  if (geoState.group) scene.remove(geoState.group);
  const group = new THREE.Group();
  geoState.group = group;

  if (geoState.mode === "dimer") {
    const sites = DATA.geometry.dimer_sites;
    const pts = sites.map(s => new THREE.Vector3(...s.pos));
    const c = centroid(pts);
    sites.forEach((s, i) => {
      const p = new THREE.Vector3(...s.pos).sub(c);
      const col = new THREE.Color(SITE_COLORS[i % 8]);
      const sph = new THREE.Mesh(
        new THREE.SphereGeometry(0.28, 32, 32),
        new THREE.MeshStandardMaterial({ color: col, emissive: col, emissiveIntensity: 0.45, roughness: 0.4 }));
      sph.position.copy(p); group.add(sph);
      if (geoState.showDip) {
        const dir = new THREE.Vector3(...s.mu).normalize();
        const arrow = new THREE.ArrowHelper(dir, p, 0.9, 0xff9e3d, 0.28, 0.16);
        group.add(arrow);
      }
    });
    // faint connecting lines to convey the network
    for (let i = 0; i < sites.length; i++)
      for (let j = i + 1; j < sites.length; j++) {
        const a = new THREE.Vector3(...sites[i].pos).sub(c);
        const b = new THREE.Vector3(...sites[j].pos).sub(c);
        const geo = new THREE.BufferGeometry().setFromPoints([a, b]);
        group.add(new THREE.Line(geo, new THREE.LineBasicMaterial(
          { color: 0x35d0e6, transparent: true, opacity: 0.10 })));
      }
    camera.position.set(6, 4, 9); controls.target.set(0, 0, 0);
  } else {
    const pts = DATA.geometry.spiral_points.map(p => new THREE.Vector3(...p));
    const c = centroid(pts);
    const geom = new THREE.BufferGeometry().setFromPoints(pts.map(p => p.clone().sub(c)));
    const colors = [];
    pts.forEach((_, i) => { const t = (i % 8) / 8;
      const col = new THREE.Color().setHSL(0.55 - 0.5 * t, 0.7, 0.6); colors.push(col.r, col.g, col.b); });
    geom.setAttribute("color", new THREE.Float32BufferAttribute(colors, 3));
    group.add(new THREE.Points(geom, new THREE.PointsMaterial(
      { size: 0.6, vertexColors: true, transparent: true, opacity: 0.9 })));
    camera.position.set(0, 5, 42); controls.target.set(0, 0, 0);
  }
  scene.add(group);
  controls.update();
}

function centroid(pts) {
  const c = new THREE.Vector3();
  pts.forEach(p => c.add(p)); return c.multiplyScalar(1 / pts.length);
}
function resizeGeo() {
  const host = document.getElementById("geo-canvas");
  if (!geoState.renderer || !host.clientWidth) return;
  geoState.camera.aspect = host.clientWidth / host.clientHeight;
  geoState.camera.updateProjectionMatrix();
  geoState.renderer.setSize(host.clientWidth, host.clientHeight);
}

/* ============================================================
   02 · COUPLINGS (D3 heatmaps)
   ============================================================ */
function heatmap(sel, matrix, labels, diverging) {
  const n = labels.length, cell = 40, pad = 44, size = n * cell + pad;
  d3.select(sel).selectAll("*").remove();
  const svg = d3.select(sel).append("svg").attr("viewBox", `0 0 ${size} ${size}`)
    .attr("width", Math.min(size, 420));
  const flat = matrix.flat();
  const ext = d3.max(flat.map(Math.abs));
  const color = diverging
    ? d3.scaleSequential(d3.interpolateRdBu).domain([ext, -ext])
    : d3.scaleSequential(t => d3.interpolateInferno(0.15 + 0.8 * t)).domain([0, d3.max(flat)]);
  const g = svg.append("g").attr("transform", `translate(${pad},${pad})`);
  matrix.forEach((row, i) => row.forEach((v, j) => {
    g.append("rect").attr("x", j * cell).attr("y", i * cell)
      .attr("width", cell - 1.5).attr("height", cell - 1.5).attr("rx", 2)
      .attr("fill", color(v))
      .on("mousemove", (e) => showTip(
        `${labels[i]} · ${labels[j]}<br><b>${v}</b> γ`, e.clientX, e.clientY))
      .on("mouseleave", hideTip);
  }));
  labels.forEach((l, i) => {
    g.append("text").attr("x", i * cell + cell / 2).attr("y", -8).attr("text-anchor", "middle")
      .attr("class", "axis-label").style("font-size", "9px").text(l.replace("Trp", "T"));
    g.append("text").attr("x", -8).attr("y", i * cell + cell / 2 + 3).attr("text-anchor", "end")
      .attr("class", "axis-label").style("font-size", "9px").text(l.replace("Trp", "T"));
  });
}
function buildCouplings() {
  heatmap("#mat-delta", DATA.couplings.Delta, DATA.couplings.labels, true);
  heatmap("#mat-g", DATA.couplings.G, DATA.couplings.labels, false);
}

/* ============================================================
   03 · SPECTRUM (D3 scatter)
   ============================================================ */
function buildSpectrum() {
  const modes = DATA.spectrum;
  const { g, iw, ih } = svgFrame("#spectrum-plot", 900, 380, { l: 64, r: 24, t: 20, b: 52 });
  const x = d3.scaleLinear().domain(d3.extent(modes, d => d.energy_cm)).nice().range([0, iw]);
  const y = d3.scaleLog().domain([Math.max(1e-3, d3.min(modes, d => d.gamma_over_gamma) * 0.6),
    d3.max(modes, d => d.gamma_over_gamma) * 1.5]).range([ih, 0]);
  addAxes(g, x, y, iw, ih, "mode energy shift (cm⁻¹)", "Γⱼ / γ (log)");
  g.append("line").attr("x1", 0).attr("x2", iw).attr("y1", y(1)).attr("y2", y(1))
    .attr("stroke", INKDIM).attr("stroke-dasharray", "5 4").attr("opacity", 0.7);
  g.append("text").attr("x", iw - 4).attr("y", y(1) - 6).attr("text-anchor", "end")
    .attr("class", "legend-txt").text("Γ/γ = 1  (bright ↑ / dark ↓)");
  g.selectAll("circle").data(modes).join("circle")
    .attr("cx", d => x(d.energy_cm)).attr("cy", d => y(d.gamma_over_gamma))
    .attr("r", 9).attr("fill", d => d.kind === "bright" ? BRIGHT : DARK)
    .attr("stroke", "#0a0c10").attr("stroke-width", 1.5)
    .style("filter", d => `drop-shadow(0 0 6px ${d.kind === "bright" ? BRIGHT : DARK})`)
    .on("mousemove", (e, d) => showTip(
      `mode ${d.index} · <b>${d.kind}</b><br>Γ/γ = ${d.gamma_over_gamma}<br>ΔE = ${d.energy_cm} cm⁻¹`,
      e.clientX, e.clientY)).on("mouseleave", hideTip);
}

/* ============================================================
   04 · DYNAMICS (D3 + transport)
   ============================================================ */
let dyn = { prep: "superradiant", t: 0, playing: false, timer: null };
function buildDynamics() {
  const tabs = d3.select("#prep-tabs");
  Object.keys(DATA.dynamics).forEach((k, i) => {
    tabs.append("button").attr("class", "chip" + (i === 0 ? " is-on" : ""))
      .attr("data-prep", k).text(k).on("click", () => setPrep(k));
  });
  document.getElementById("scrub").addEventListener("input", (e) => {
    dyn.t = +e.target.value; stopPlay(); renderDyn();
  });
  document.getElementById("play").addEventListener("click", togglePlay);
  setPrep("superradiant");
}
function setPrep(k) {
  dyn.prep = k; dyn.t = 0;
  d3.selectAll("#prep-tabs .chip").classed("is-on", function () {
    return this.getAttribute("data-prep") === k;
  });
  document.getElementById("scrub").value = 0;
  renderDyn();
}
function togglePlay() { dyn.playing ? stopPlay() : startPlay(); }
function startPlay() {
  dyn.playing = true; document.getElementById("play").textContent = "❚❚ pause";
  const n = DATA.dynamics[dyn.prep].times_ps.length;
  dyn.timer = setInterval(() => {
    dyn.t = (dyn.t + 1) % n;
    document.getElementById("scrub").value = dyn.t; renderDyn();
  }, 90);
}
function stopPlay() {
  dyn.playing = false; document.getElementById("play").textContent = "▶ play";
  if (dyn.timer) clearInterval(dyn.timer);
}
function renderDyn() {
  const d = DATA.dynamics[dyn.prep];
  const t = dyn.t, times = d.times_ps;
  document.getElementById("tstamp").textContent = `t = ${Math.round(times[t])} ps`;
  linesChart("#dyn-pop", times, transpose(d.site_pops),
    d.site_pops[0].map((_, i) => `Trp${i + 1}`),
    d.site_pops[0].map((_, i) => SITE_COLORS[i % 8]), t, "site population", true);
  const pairLabels = d.top_pairs.map(p => `(${p[0]},${p[1]})`);
  const pairCols = [BRIGHT, DARK, "#f2c14e", "#c98bff"];
  linesChart("#dyn-l1", times, transpose(d.pair_l1), pairLabels, pairCols, t, "pair L₁ coherence", true);
  linesChart("#dyn-neg", times, transpose(d.log_neg), pairLabels, pairCols, t, "log negativity", true);
  linesChart("#dyn-proj", times, [d.bright, d.dark], ["bright", "dark"],
    [BRIGHT, DARK], t, "bright/dark projection", true);
}
function transpose(rows) { return rows[0].map((_, c) => rows.map(r => r[c])); }

function linesChart(sel, xs, series, labels, colors, cursor, title, legend) {
  const { g, iw, ih } = svgFrame(sel, 440, 210, { l: 48, r: 12, t: 26, b: 34 });
  const x = d3.scaleLinear().domain(d3.extent(xs)).range([0, iw]);
  const ymax = d3.max(series.flat()) || 1;
  const y = d3.scaleLinear().domain([Math.min(0, d3.min(series.flat())), ymax * 1.08]).range([ih, 0]);
  addAxes(g, x, y, iw, ih, null, null);
  g.append("text").attr("class", "plot-title").attr("x", 0).attr("y", -12).text(title);
  const line = d3.line().x((_, i) => x(xs[i])).y(v => y(v)).curve(d3.curveMonotoneX);
  series.forEach((s, i) => {
    g.append("path").datum(s).attr("fill", "none").attr("stroke", colors[i])
      .attr("stroke-width", 1.6).attr("opacity", 0.9).attr("d", line);
  });
  // cursor
  g.append("line").attr("class", "cursor").attr("x1", x(xs[cursor])).attr("x2", x(xs[cursor]))
    .attr("y1", 0).attr("y2", ih).attr("stroke", "#fff").attr("stroke-width", 1).attr("opacity", 0.45);
  series.forEach((s, i) => {
    g.append("circle").attr("cx", x(xs[cursor])).attr("cy", y(s[cursor])).attr("r", 3.2)
      .attr("fill", colors[i]).style("filter", `drop-shadow(0 0 4px ${colors[i]})`);
  });
  if (legend) {
    const lg = g.append("g").attr("transform", `translate(${iw - 4},2)`);
    labels.forEach((l, i) => {
      const row = lg.append("g").attr("transform", `translate(0,${i * 12})`);
      row.append("rect").attr("x", -8).attr("y", -7).attr("width", 7).attr("height", 3).attr("fill", colors[i]);
      row.append("text").attr("class", "legend-txt").attr("x", -12).attr("text-anchor", "end").text(l);
    });
  }
}

/* ============================================================
   05 · EMBEDDINGS (D3 small multiples)
   ============================================================ */
function buildEmbeddings() {
  const emb = DATA.embeddings && DATA.embeddings.embeddings_fig8;
  const grid = d3.select("#embed-grid");
  if (!emb) { grid.append("p").attr("class", "legend-txt").text("embeddings data unavailable"); return; }
  const rows = ["single", "two-tubulin", "three-tubulin"];
  const cols = ["coherent", "mixed", "superradiant", "subradiant"];
  // header row
  cols.forEach(c => grid.append("div").style("grid-column", "auto")
    .html(`<div class="legend-txt" style="text-align:center;padding:4px 0;color:${DARK}">${c}</div>`));
  rows.forEach(rk => cols.forEach(ck => {
    const cell = grid.append("div");
    const info = emb[rk] && emb[rk].preparations[ck];
    const label = `${rk.replace("-tubulin", "")} · ${info ? info.n_sites || (emb[rk].n_sites) : ""}`;
    const holder = cell.append("div").attr("id", `emb-${rk}-${ck}`).attr("class", "plot");
    embSpark(`#emb-${rk}-${ck}`, info, `${rk.split("-")[0]}`);
  }));
}
function embSpark(sel, info, tag) {
  const { g, iw, ih } = svgFrame(sel, 220, 130, { l: 30, r: 6, t: 16, b: 18 });
  g.append("text").attr("class", "legend-txt").attr("x", 0).attr("y", -4)
    .text(info ? `${tag} · max L₁ ${info.max_pair_l1.toFixed(3)}` : tag);
  if (!info) return;
  // We only stored top-pairs + max; draw pair labels as bars of their max contribution proxy.
  const pairs = info.top_pairs;
  const x = d3.scaleBand().domain(pairs.map(p => `${p[0]},${p[1]}`)).range([0, iw]).padding(0.25);
  const y = d3.scaleLinear().domain([0, info.max_pair_l1 * 1.1]).range([ih, 0]);
  g.append("g").attr("class", "axis").attr("transform", `translate(0,${ih})`)
    .call(d3.axisBottom(x).tickSize(0)).selectAll("text").style("font-size", "8px");
  const cols = [BRIGHT, DARK, "#f2c14e", "#c98bff"];
  pairs.forEach((p, i) => g.append("rect").attr("x", x(`${p[0]},${p[1]}`))
    .attr("y", y(info.max_pair_l1 * (1 - i * 0.18))).attr("width", x.bandwidth())
    .attr("height", ih - y(info.max_pair_l1 * (1 - i * 0.18))).attr("fill", cols[i]).attr("opacity", 0.85));
}

/* ============================================================
   06 · BACKFLOW (D3 with shaded backflow intervals)
   ============================================================ */
function buildBackflow() {
  const bf = DATA.backflow;
  const { g, iw, ih } = svgFrame("#backflow-plot", 900, 420, { l: 60, r: 20, t: 24, b: 52 });
  const xs = bf.times_ps;
  const x = d3.scaleLinear().domain(d3.extent(xs)).range([0, iw]);
  const y = d3.scaleLinear().domain([0, 1.02]).range([ih, 0]);
  addAxes(g, x, y, iw, ih, "time (ps)", "trace distance  Dₖ(t)");
  const palette = [BRIGHT, DARK];
  const line = d3.line().x((_, i) => x(xs[i])).y(v => y(v)).curve(d3.curveMonotoneX);
  const legend = g.append("g").attr("transform", "translate(10,4)");
  bf.neighbors.forEach((nb, k) => {
    // shade rising (backflow) intervals of the phase series
    for (let i = 1; i < nb.phase.length; i++) {
      if (nb.phase[i] > nb.phase[i - 1]) {
        g.append("rect").attr("x", x(xs[i - 1])).attr("y", 0)
          .attr("width", Math.max(1, x(xs[i]) - x(xs[i - 1]))).attr("height", ih)
          .attr("fill", palette[k]).attr("opacity", 0.05);
      }
    }
    g.append("path").datum(nb.population).attr("fill", "none").attr("stroke", palette[k])
      .attr("stroke-width", 1.6).attr("opacity", 0.85).attr("d", line);
    g.append("path").datum(nb.phase).attr("fill", "none").attr("stroke", palette[k])
      .attr("stroke-width", 1.6).attr("stroke-dasharray", "5 3").attr("d", line);
    const row = legend.append("g").attr("transform", `translate(0,${k * 14})`);
    row.append("rect").attr("width", 10).attr("height", 3).attr("y", -3).attr("fill", palette[k]);
    row.append("text").attr("class", "legend-txt").attr("x", 16)
      .text(`${nb.label} — solid=pop (N=${nb.N_population}) · dash=phase (N=${nb.N_phase})`);
  });
}

/* ============================================================
   07 · LIFETIMES (D3 log-log)
   ============================================================ */
function buildLifetimes() {
  const lt = DATA.lifetimes;
  const { g, iw, ih } = svgFrame("#lifetime-plot", 900, 460, { l: 70, r: 24, t: 24, b: 54 });
  const x = d3.scaleLog().domain([0.9, d3.max(lt, d => d.dimers) * 1.2]).range([0, iw]);
  const allT = lt.flatMap(d => [d.tau_super_ordered, d.tau_sub_ordered, d.tau_super_static,
    d.tau_sub_static, d.tau_super_jitter, d.tau_sub_jitter]).filter(v => v > 0);
  const y = d3.scaleLog().domain([d3.min(allT) * 0.6, d3.max(allT) * 1.6]).range([ih, 0]);
  addAxes(g, x, y, iw, ih, "assembly size (dimers, log)", "radiative lifetime (s, log)",
    d3.format(".0e"));
  const cfgs = [
    ["tau_sub_ordered", DARK, "-", "sub · ordered"],
    ["tau_super_ordered", BRIGHT, "-", "super · ordered"],
    ["tau_sub_static", "#c1121f", "6 3", "sub · static W=200"],
    ["tau_super_static", "#e8896b", "6 3", "super · static"],
    ["tau_sub_jitter", "#2a9d3a", "2 3", "sub · jitter"],
    ["tau_super_jitter", "#7fd48b", "2 3", "super · jitter"],
  ];
  const line = d3.line().x(d => x(d.dimers)).y(d => y(d[cfgKey])).curve(d3.curveMonotoneX);
  let cfgKey;
  const legend = g.append("g").attr("transform", `translate(12,4)`);
  cfgs.forEach(([key, col, dash, label], i) => {
    cfgKey = key;
    const pts = lt.filter(d => d[key] > 0);
    g.append("path").datum(pts).attr("fill", "none").attr("stroke", col)
      .attr("stroke-width", 1.8).attr("stroke-dasharray", dash === "-" ? null : dash)
      .attr("d", d3.line().x(d => x(d.dimers)).y(d => y(d[key])).curve(d3.curveMonotoneX));
    g.selectAll(`.pt${i}`).data(pts).join("circle").attr("cx", d => x(d.dimers))
      .attr("cy", d => y(d[key])).attr("r", 3).attr("fill", col)
      .on("mousemove", (e, d) => showTip(`${label}<br>${d.dimers} dimers (${d.sites} sites)<br>τ = ${d[key].toExponential(2)} s`, e.clientX, e.clientY))
      .on("mouseleave", hideTip);
    const row = legend.append("g").attr("transform", `translate(0,${i * 13})`);
    row.append("line").attr("x1", 0).attr("x2", 14).attr("stroke", col).attr("stroke-width", 2)
      .attr("stroke-dasharray", dash === "-" ? null : dash);
    row.append("text").attr("class", "legend-txt").attr("x", 18).attr("y", 3).text(label);
  });
}

const BUILDERS = {
  geometry: buildGeometry, couplings: buildCouplings, spectrum: buildSpectrum,
  dynamics: buildDynamics, embeddings: buildEmbeddings, backflow: buildBackflow,
  lifetimes: buildLifetimes,
};
