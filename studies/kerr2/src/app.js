/* Kerr 2 · The Photon Ring. Shows computed rays only; every texture is verified against its case
   manifest (sha256) before the shader may use it, and red witnesses stay visible. */
"use strict";
const CASES = [
  { id: "extreme", label: "a = 0.99 · 84°", line: "A near-extremal black hole seen almost edge-on. The ring is flattened on the side where the disk's light travels with the spin." },
  { id: "kerr", label: "a = 0.94 · 68°", line: "The Scientific Loom's rapid Kerr case, now with every pass of light kept." },
  { id: "schwarzschild", label: "a = 0 · 60°", line: "No spin: the ring is a circle of radius √27 M, and each sub-ring is e^−π ≈ 1/23 the width of the last." },
];
const $ = (id) => document.getElementById(id);
const state = { id: null, geom: null, rho: null, view: 0, mask: 15, samples: 4, curve: 0, exposure: 1.2,
  zoom: 1, panX: 0, panY: 0, epoch: 0, fly: null, aspect: 1.6, res: [1600, 1000] };
let B, scene, shader;

const sha = async (buf) => Array.from(new Uint8Array(await crypto.subtle.digest("SHA-256", buf)), (v) => v.toString(16).padStart(2, "0")).join("");

function el(tag, text, cls) { const e = document.createElement(tag); if (text !== undefined) e.textContent = text; if (cls) e.className = cls; return e; }

async function verifiedTexture(frame, nearest, repeatS) {
  const res = await fetch(frame.file, { cache: "no-store" });
  if (!res.ok) throw Error("missing payload " + frame.file);
  const bytes = await res.arrayBuffer();
  if (bytes.byteLength !== frame.bytes || (await sha(bytes)) !== frame.sha256) throw Error("payload does not match its manifest: " + frame.file);
  const tex = scene.createNode("ImageTexture"), props = scene.createNode("TextureProperties");
  props.generateMipMaps = false;
  props.minificationFilter = nearest ? "NEAREST_PIXEL" : "AVG_PIXEL";
  props.magnificationFilter = nearest ? "NEAREST_PIXEL" : "AVG_PIXEL";
  props.boundaryModeS = repeatS ? "REPEAT" : "CLAMP_TO_EDGE";
  props.boundaryModeT = "CLAMP_TO_EDGE";
  tex.textureProperties = props;
  tex.colorSpaceConversion = false;          // these PNGs are data (RGBM radiance, 24-bit radii), not sRGB pictures
  tex.repeatS = !!repeatS; tex.repeatT = false;
  const url = URL.createObjectURL(new Blob([bytes], { type: "image/png" }));
  tex.url = [url];
  try { await tex.getValue().requestImmediateLoad(); } finally { URL.revokeObjectURL(url); }
  return { tex, bytes };
}

async function decodeCurve(bytes) {
  const bmp = await createImageBitmap(new Blob([bytes], { type: "image/png" }), { colorSpaceConversion: "none", premultiplyAlpha: "none" });
  const c = new OffscreenCanvas(bmp.width, 1), g = c.getContext("2d");
  g.drawImage(bmp, 0, 0);
  const d = g.getImageData(0, 0, bmp.width, 1).data, rho = new Float64Array(bmp.width);
  for (let k = 0; k < bmp.width; k++) rho[k] = ((d[4 * k] * 256 + d[4 * k + 1]) * 256 + d[4 * k + 2]) / 16777215 * 16;
  return rho;
}

function rhoC(psi) {
  const n = state.rho.length, k = psi / (2 * Math.PI) * n - 0.5, k0 = Math.floor(k), f = k - k0;
  const a = state.rho[((k0 % n) + n) % n], b = state.rho[(((k0 + 1) % n) + n) % n];
  return a + (b - a) * f;
}

function ledger(c) {
  const tb = $("witnesses").tBodies[0]; tb.replaceChildren();
  for (const w of c.witnesses) {
    const tr = el("tr");
    tr.append(el("td", w.pass ? "✓" : "✗", w.pass ? "ok" : "bad"), el("td", w.id), el("td", fmt(w.observed), "num"), el("td", (w.rule === "at most" ? "≤ " : "≥ ") + fmt(w.limit), "num"));
    tb.append(tr);
  }
  $("limits").textContent = "Limits: " + c.limits.join(" ");
  $("provenance").textContent = `Case ${c.id} · builder sha256 ${c.builder_sha256.slice(0, 12)}… · ${c.frames.length} payloads verified by sha256 in this browser before display.`;
  const red = c.witnesses.filter((w) => !w.pass);
  $("banner").hidden = red.length === 0;
  $("banner").textContent = red.length ? `Not admitted: ${red.length} witness${red.length > 1 ? "es" : ""} red (${red.map((w) => w.id.split(",")[0]).join("; ")}). Shown for review; the colour fix is listed in the ledger.` : "";
}

function fmt(x) { if (x === 0) return "0"; const a = Math.abs(x); return a >= 1e4 || a < 1e-3 ? x.toExponential(2) : (+x.toPrecision(4)).toString(); }

async function load(id) {
  const epoch = ++state.epoch;
  $("loading").hidden = false; $("loading").textContent = "Verifying computed rays…";
  for (const b of $("cases").children) b.classList.toggle("on", b.dataset.id === id);
  const meta = CASES.find((c) => c.id === id);
  const [c, g] = await Promise.all([fetch(`cases/${id}/case.json`).then((r) => r.json()), fetch(`cases/${id}/geometry.json`).then((r) => r.json())]);
  if (c.schema !== "loom.scientific-case/1") throw Error("unexpected case schema");
  const byName = Object.fromEntries(c.frames.map((f) => [f.file.split("/").pop().replace(".png", ""), f]));
  const names = ["image-n0", "image-n1", "image-n2", "image-n3", "ring-n0", "ring-n1", "ring-n2", "ring-n3", "curve"];
  const loaded = [];
  for (const n of names) {
    if (!byName[n]) throw Error("manifest lacks " + n);
    loaded.push(await verifiedTexture(byName[n], n === "curve", n.startsWith("ring")));
    if (epoch !== state.epoch) return;
  }
  const rho = await decodeCurve(loaded[8].bytes);
  ["img0", "img1", "img2", "img3", "ring0", "ring1", "ring2", "ring3", "curve"].forEach((f, i) => { shader[f] = loaded[i].tex; });
  Object.assign(state, { id, geom: g, rho, zoom: 1, panX: 0, panY: 0, fly: null });
  shader.centerAlpha = g.center_alpha; shader.npsi = g.npsi; shader.ndelta = g.ndelta; shader.deltaMin = g.delta_min; shader.deltaMax = g.delta_max;
  shader.span = g.span; shader.imageAspect = g.width / g.height;
  $("title").textContent = c.title; $("subtitle").textContent = meta.line;
  ledger(c); push(); $("loading").hidden = true;
}

function push() {
  if (!shader) return;
  const cv = $("canvas"), w = cv.clientWidth, h = cv.clientHeight;
  shader.aspect = w / Math.max(h, 1); shader.resolution = new X3D.SFVec2f(w * devicePixelRatio, h * devicePixelRatio);
  shader.zoom = state.zoom; shader.panX = state.panX; shader.panY = state.panY; shader.exposure = state.exposure;
  shader.viewMode = state.view; shader.layerMask = state.mask; shader.samples = state.samples; shader.showCurve = state.curve;
  const vh = state.geom ? state.geom.span / (state.geom.width / state.geom.height) / state.zoom : 22.5;
  const target = vh / 5, p10 = Math.pow(10, Math.floor(Math.log10(target))), nice = [1, 2, 5].map((m) => m * p10).filter((v) => v <= target).pop() || p10;
  $("scale").querySelector("i").style.width = (nice / vh * h) + "px";
  $("scaleLabel").textContent = state.view === 1 ? "unrolled: angle across · offset up (log scale)" : `${fmt(nice)} GM/c² · zoom ×${fmt(state.zoom)}`;
}

function screenToAB(x, y) {
  const cv = $("canvas"), w = cv.clientWidth, h = cv.clientHeight, vh = state.geom.span / (state.geom.width / state.geom.height) / state.zoom;
  return [state.panX + (x / w - 0.5) * vh * w / h, state.panY + (0.5 - y / h) * vh];
}

function readout(x, y) {
  if (!state.geom || state.view === 1) return;
  const [a, b] = screenToAB(x, y), ra = a - state.geom.center_alpha, psi = (Math.atan2(b, ra) + 2 * Math.PI) % (2 * Math.PI);
  const d = Math.hypot(ra, b) - rhoC(psi);
  $("readout").textContent = `α ${a.toFixed(5)}  β ${b.toFixed(5)} GM/c² · ${Math.abs(d) < 1e-6 ? "within 1e-6 M of" : (d > 0 ? "outside" : "inside")} the critical curve by ${fmt(Math.abs(d))} M`;
}

function wire() {
  for (const c of CASES) { const b = el("button", c.label); b.dataset.id = c.id; b.onclick = () => load(c.id).catch(fail); $("cases").append(b); }
  for (const b of $("views").children) b.onclick = () => { state.view = +b.dataset.view; [...$("views").children].forEach((x) => x.classList.toggle("on", x === b)); push(); };
  for (const b of $("layers").children) b.onclick = () => { state.mask ^= +b.dataset.bit; b.classList.toggle("on", !!(state.mask & +b.dataset.bit)); push(); };
  const setMask = (m) => { state.mask = m; for (const b of $("layers").children) b.classList.toggle("on", !!(m & +b.dataset.bit)); push(); };
  $("ringsOnly").onclick = () => setMask(14); $("allLayers").onclick = () => setMask(15);
  $("curve").onchange = (e) => { state.curve = e.target.checked ? 1 : 0; push(); };
  $("exposure").oninput = (e) => { state.exposure = +e.target.value; $("expVal").textContent = state.exposure.toFixed(2); push(); };
  for (const b of $("quality").children) b.onclick = () => { state.samples = +b.dataset.s; [...$("quality").children].forEach((x) => x.classList.toggle("on", x === b)); push(); };
  $("reset").onclick = () => { state.fly = null; Object.assign(state, { zoom: 1, panX: 0, panY: 0 }); push(); };
  $("fly").onclick = fly;
  const cv = $("canvas");
  cv.addEventListener("wheel", (e) => {
    if (!state.geom || state.view === 1) return; e.preventDefault(); state.fly = null;
    const [a, b] = screenToAB(e.offsetX, e.offsetY), z0 = state.zoom, z1 = Math.min(2e4, Math.max(0.5, z0 * Math.exp(-e.deltaY * 0.0015)));
    state.panX = a - (a - state.panX) * z0 / z1; state.panY = b - (b - state.panY) * z0 / z1; state.zoom = z1; push(); readout(e.offsetX, e.offsetY);
  }, { passive: false });
  let drag = null;
  cv.addEventListener("pointerdown", (e) => { drag = { x: e.clientX, y: e.clientY, px: state.panX, py: state.panY }; state.fly = null; cv.setPointerCapture(e.pointerId); });
  cv.addEventListener("pointermove", (e) => {
    readout(e.offsetX, e.offsetY);
    if (!drag || !state.geom || state.view === 1) return;
    const vh = state.geom.span / (state.geom.width / state.geom.height) / state.zoom, h = cv.clientHeight;
    state.panX = drag.px - (e.clientX - drag.x) / h * vh; state.panY = drag.py + (e.clientY - drag.y) / h * vh; push();
  });
  cv.addEventListener("pointerup", () => { drag = null; });
  cv.addEventListener("dblclick", () => $("reset").onclick());
  addEventListener("resize", push);
  addEventListener("keydown", (e) => { if (e.key === "u" || e.key === "U") document.body.classList.toggle("hide"), setTimeout(push, 50); if (e.key === "Escape") state.fly = null; });
}

// Where each flight dives in: the Doppler-beamed side for the spinning cases, the ring top for Schwarzschild.
// Same table as FLY_PSI in tools/film.py, so the page and the Tier C film take the same path.
const FLY_PSI = { extreme: Math.PI, kerr: Math.PI, schwarzschild: Math.PI / 2 };

// A continuous zoom toward the ring: log-linear in zoom, the target held at the screen centre.
function fly() {
  if (!state.geom) return;
  const psi = FLY_PSI[state.id] ?? Math.PI / 2, rc = rhoC(psi), d = 2e-3;
  const tx = state.geom.center_alpha + (rc + d) * Math.cos(psi), ty = (rc + d) * Math.sin(psi);
  const start = performance.now(), dur = 16000, z0 = 1, z1 = 1.2e4, p0 = [state.panX, state.panY];
  state.fly = { start };
  const tick = (t) => {
    if (!state.fly || state.fly.start !== start) return;
    const u = Math.min(1, (t - start) / dur), e = u * u * (3 - 2 * u);
    state.zoom = z0 * Math.pow(z1 / z0, e);
    const k = Math.min(1, u / 0.35), s = k * k * (3 - 2 * k);
    state.panX = p0[0] + (tx - p0[0]) * s; state.panY = p0[1] + (ty - p0[1]) * s; push();
    if (u < 1) requestAnimationFrame(tick);
  };
  requestAnimationFrame(tick);
}

function fail(e) { console.error(e); $("loading").hidden = false; $("loading").textContent = "This case could not be shown: " + e.message; }

// Deep links name a whole view, so a frame can be reproduced and shared:
//   #extreme/v=0/z=6/x=2.3549/y=5.4772/m=15/s=16/e=1.2/c=0
// v view (0 sky, 1 unrolled) · z zoom · x, y pan in GM/c² · m layer mask · s samples · e exposure · c curve overlay.
// A key left out keeps its current value; out-of-range values are clamped, and kerr2View() reports what was used.
const HASH_KEYS = { v: "view", z: "zoom", x: "panX", y: "panY", m: "mask", s: "samples", e: "exposure", c: "curve" };

function parseHash() {
  const [id, ...pairs] = decodeURIComponent(location.hash.slice(1)).split("/");
  const view = {};
  for (const p of pairs) { const [k, v] = p.split("="); if (HASH_KEYS[k] && v !== "" && Number.isFinite(+v)) view[HASH_KEYS[k]] = +v; }
  return { id: CASES.some((c) => c.id === id) ? id : null, view };
}

function applyView(v) {
  const clamp = (x, lo, hi) => Math.min(hi, Math.max(lo, x));
  if ("view" in v) state.view = v.view === 1 ? 1 : 0;
  if ("zoom" in v) state.zoom = clamp(v.zoom, 0.5, 2e4);
  if ("panX" in v) state.panX = v.panX;
  if ("panY" in v) state.panY = v.panY;
  if ("mask" in v) state.mask = clamp(Math.round(v.mask), 0, 15);
  if ("samples" in v) state.samples = v.samples >= 16 ? 16 : v.samples >= 4 ? 4 : 1;
  if ("exposure" in v) state.exposure = clamp(v.exposure, +$("exposure").min, +$("exposure").max);
  if ("curve" in v) state.curve = v.curve ? 1 : 0;
  if (Object.keys(v).length) state.fly = null;
  // Keep every control in step with the state, so what the panel shows is what the shader draws.
  [...$("views").children].forEach((b) => b.classList.toggle("on", +b.dataset.view === state.view));
  [...$("layers").children].forEach((b) => b.classList.toggle("on", !!(state.mask & +b.dataset.bit)));
  [...$("quality").children].forEach((b) => b.classList.toggle("on", +b.dataset.s === state.samples));
  $("curve").checked = !!state.curve; $("exposure").value = state.exposure; $("expVal").textContent = state.exposure.toFixed(2);
  push();
}

async function route() {
  const { id, view } = parseHash();
  if (id ? id !== state.id : !state.id) await load(id || "extreme");
  applyView(view);
}

// Read-only report of the view the page is drawing; capture witnesses record this, not what they asked for.
window.kerr2View = () => {
  const host = $("canvas"), cv = host.shadowRoot?.querySelector("canvas");
  const px = cv ? [cv.width, cv.height] : [Math.round(host.clientWidth * devicePixelRatio), Math.round(host.clientHeight * devicePixelRatio)];
  return { case: state.id, view: state.view, zoom: state.zoom, panX: state.panX, panY: state.panY, mask: state.mask,
    samples: state.samples, exposure: state.exposure, curve: state.curve, canvas_px: px,
    dpr: devicePixelRatio, loading: !$("loading").hidden };
};

// A world load gets a time budget: X_ITE's replaceWorld can leave its promise pending if an internal wait
// rejects (X_ITE teardown F01; Loom failure mode 89), and a page must say so rather than hang.
function loadWorld(url, ms = 30000) {
  return Promise.race([B.loadURL(new X3D.MFString(url)),
    new Promise((_, reject) => setTimeout(() => reject(Error(`the X3D scene did not load within ${ms / 1000} s: ${url}`)), ms))]);
}

async function main() {
  wire();
  B = X3D.getBrowser("#canvas");
  await loadWorld("scenes/kerr2.x3d");
  scene = B.currentScene; shader = scene.getNamedNode("RingShader");
  // A hash-only navigation does not reload the page: route it, so the page never shows stale data. Wired only
  // once the scene is ready (Loom failure mode 78); a hash that changed while loading is routed afterwards.
  addEventListener("hashchange", () => route().catch(fail));
  await route();
  if (parseHash().id && parseHash().id !== state.id) await route();
}
main().catch(fail);
