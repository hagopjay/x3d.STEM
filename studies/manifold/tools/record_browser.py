"""Bind a browser run (.work/browser-raw.json and .work/frames, from tools/browser_run.js) to the files it ran
against, judge it, and write evidence/browser-<date>.json for tools/check_browser.py and the Loom.

Limits, declared on 6 Nov before the first evidence run, from the exploration of matched frames (four moods:
SSIM 0.909 to 0.958, mean Delta E 1.5 to 2.2, luma within 1 %; the mirrored control 0.53):
  the page's field against the builder's rest heights: 1e-6 (float32 payload)
  fidelity to the original, each mood: SSIM >= 0.90, mean Delta E <= 2.5, luma within 2 %
  controls that must fail: the mirrored original (SSIM <= 0.70); the original 3 time units later
     (SSIM at least 0.02 below the matched pair, mean Delta E above it)
  the saved moment, loaded alone in X_ITE: all seven shaders valid, SSIM >= 0.97 against the live frame
"""
from __future__ import annotations

import datetime
import hashlib
import json
import sys
import zlib
from pathlib import Path

import numpy as np
from PIL import Image, ImageOps

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "tools"))
from fidelity import compare, load    # noqa: E402

h = lambda p: hashlib.sha256((ROOT / p).read_bytes()).hexdigest()
raw = json.loads((ROOT / ".work/browser-raw.json").read_text())
F = ROOT / ".work/frames"
SOURCES = ["index.html", "src/app.js", "src/app.css", "src/original.css", "src/field.js", "src/math-core.js", "src/labels.js", "src/lens.js",
           "scenes/manifold.x3d", "reference/Manifold-of-Emotion.html"]
PROBE = "resilience probe"
ev = {"schema": "manifold.browser/1", "date": datetime.date.today().isoformat(), "browser": "Playwright MCP headless Chromium",
      "user_agent": raw["ua"], "page_sources": {p: h(p) for p in SOURCES}, "case_manifests": {"rest": h("cases/rest/case.json")}}

# health
H = raw["health"]
ev["x3d"] = {"shaders_valid": all(v for _, v in [(s["name"], s["valid"]) for s in H["shaders"]]) and len(H["shaders"]) == 7,
             "blend": H["blend"], "multisampling": H["multisampling"], "lens_hdr": H["lens"]["hdr"], "flows": H["flows"]}
ev["x3d"]["pass"] = ev["x3d"]["shaders_valid"] and H["blend"] == "standard alpha (lightOut)" and H["multisampling"] >= 4 and H["flows"]["traces"] == 30

# the page's field against the builder (cross-implementation: the browser's JS engine against numpy)
case = json.loads((ROOT / "cases/rest/case.json").read_text())
fr = case["frames"][0]
rest = np.frombuffer(zlib.decompress((ROOT / fr["file"]).read_bytes()), "<f4").reshape(513, 513)
d = max(abs(float(rest[j, i]) - v) for i, j, v in raw["parity"])
ev["field_parity"] = {"what": "the page's heightAt at the rest moment against the builder's verified payload, every 16th grid point",
                      "points": len(raw["parity"]), "max_abs": d, "limit": 1e-6, "pass": d <= 1e-6}

p = raw["playback"]
ev["playback"] = {**p, "pass": p["running"][1] > p["running"][0] and p["paused"][0] == p["paused"][1] and p["frames"][1] > p["frames"][0] and p["state"] is False}
rs = raw["resilience"]
ev["callback_resilience"] = {**rs, "what": "the label layer, inside the frame callback's own path, throws once; frames, the field's time and the X3D clock must go on",
                             "pass": rs["thrown"] >= 1 and rs["uncaught"] == 0 and rs["frames_after"] > 0 and rs["time_after"] >= 0.8 * 1.5 * 0.65 and rs["clock_after"] >= 1.3}
ev["ripple"] = {**raw["ripple"], "pass": raw["ripple"]["impulses"] >= 1}

# fidelity to the original
rows, ok = [], True
for m in range(4):
    r = compare(load(F / f"original-{m}.png"), load(F / f"x3d-{m}.png"))
    lum = abs(r["mean_luma"][0] - r["mean_luma"][1]) / r["mean_luma"][0]
    good = r["ssim"] >= 0.90 and r["deltaE_mean"] <= 2.5 and lum <= 0.02
    ok &= good
    rows.append({"mood": raw["original"][m]["mood"], "time": raw["original"][m]["time"], **r, "luma_rel": round(lum, 4), "pass": good,
                 "png_sha256": {"original": hashlib.sha256((F / f"original-{m}.png").read_bytes()).hexdigest(), "x3d": hashlib.sha256((F / f"x3d-{m}.png").read_bytes()).hexdigest()}})
o0 = load(F / "original-0.png")
mirror = compare(o0, np.asarray(ImageOps.mirror(Image.open(F / "original-0.png").convert("RGB")), float) / 255)
later = compare(load(F / "original-0-later.png"), load(F / "x3d-0.png"))
controls = {"mirror": {**mirror, "pass": mirror["ssim"] <= 0.70},
            "later_moment": {**later, "original_time": raw["original_later"], "pass": later["ssim"] <= rows[0]["ssim"] - 0.02 and later["deltaE_mean"] > rows[0]["deltaE_mean"]}}
ev["fidelity"] = {"what": "the original page and this one at the same moment, camera and mood, film grain off, 1280 x 800, interface masked",
                  "moods": rows, "controls_that_must_fail": controls,
                  "pass": ok and all(c["pass"] for c in controls.values())}

# the saved moment, alone
mo = raw["moment"]
ms = compare(load(F / "live-nolens-0.png"), load(F / "moment-0.png"))
ev["saved_moment"] = {"what": "Save X3D's text, loaded alone into X_ITE (createX3DFromString, replaceWorld): no page logic, no lens",
                      "bytes": mo["bytes"], "sha256": hashlib.sha256((ROOT / ".work/moment-0.x3d").read_bytes()).hexdigest(),
                      "shaders": mo["shaders"], "against_live_frame": ms,
                      "pass": all(v for _, v in mo["shaders"]) and ms["ssim"] >= 0.97}

errors = [e for e in raw["errors"] if PROBE not in e]
ev["console_errors"], ev["failed_requests"] = errors, raw["failed"]
ev["scope"] = ("One headless Chromium (software GL) on one machine: correctness, fidelity to the original and portability, not frame rate. "
               "Fidelity is measured against the original running in the same browser; the X3D frame's own improvements (multisampled edges, "
               "the denser mesh, analytic occlusion) count against it here.")
ev["pass"] = all(ev[k]["pass"] for k in ("x3d", "field_parity", "playback", "callback_resilience", "ripple", "fidelity", "saved_moment")) and not errors and not raw["failed"]
out = ROOT / "evidence" / f"browser-{ev['date']}.json"
out.write_text(json.dumps(ev, indent=2) + "\n")

# side-by-side pictures for the debrief (original left, X3D right)
docs = ROOT / "docs/frames"; docs.mkdir(parents=True, exist_ok=True)
for m in range(4):
    a, b = Image.open(F / f"original-{m}.png").convert("RGB"), Image.open(F / f"x3d-{m}.png").convert("RGB")
    s = Image.new("RGB", (a.width * 2, a.height)); s.paste(a, (0, 0)); s.paste(b, (a.width, 0))
    s.resize((s.width // 2, s.height // 2), Image.LANCZOS).save(docs / f"pair-{m}.jpg", quality=86)
for k in ("x3d", "field_parity", "playback", "callback_resilience", "ripple", "fidelity", "saved_moment"):
    print(f"{'ok ' if ev[k]['pass'] else 'RED'} {k}")
for r in rows:
    print(f"    {r['mood']:11s} ssim {r['ssim']}  dE {r['deltaE_mean']}  p95 {r['deltaE_p95']}  luma {r['luma_rel']}")
print(f"    controls: mirror ssim {mirror['ssim']}; later ssim {later['ssim']} dE {later['deltaE_mean']}; saved moment ssim {ms['ssim']}")
print(out.name, "pass" if ev["pass"] else "FAIL", "| console errors:", len(errors), "| failed requests:", len(raw["failed"]))
sys.exit(0 if ev["pass"] else 1)
