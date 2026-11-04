"""Reconstruction witness: a browser frame vs the offline renderer at the same view.

Inputs: a PNG capture of the X3D canvas and the exact view the page reported when it was captured
(zoom, pan, layer mask, samples, exposure, canvas size). The offline renderer (tools/film.py) resamples
the same verified payloads with the same mapping, so a mismatch means the GPU path differs: texture
orientation (the Scientific Loom's double Y flip), channel decoding or sampling.

Declared before the first run: luminance correlation >= 0.98 and mean absolute difference <= 4/255.
Negative control: the same capture flipped vertically must FAIL the correlation threshold; if it does
not, the witness cannot see an orientation error and its pass means nothing.

  python3 tools/reconstruct.py --case extreme --capture cap.png --view view.json
"""
from __future__ import annotations

import argparse
import json

import numpy as np
from PIL import Image

from common import ROOT, need, sha, write_json, witness
import film


def luminance(rgb8: np.ndarray) -> np.ndarray:
    a = rgb8[..., :3].astype(np.float64) / 255.0
    return a @ np.array([0.2126, 0.7152, 0.0722])


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a, b = a.ravel() - a.mean(), b.ravel() - b.mean()
    den = np.sqrt((a * a).sum() * (b * b).sum())
    return float((a * b).sum() / den) if den > 0 else 0.0


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", required=True)
    p.add_argument("--capture", required=True)
    p.add_argument("--view", required=True)
    a = p.parse_args()
    view = json.loads(open(a.view).read())
    # The page reports the view it drew (kerr2View()); a capture of another view or case measures nothing.
    need(view.get("case") == a.case, "CAPTURE_CASE", f"page drew {view.get('case')!r}, witness asked for {a.case!r}")
    need(view.get("view") == 0, "CAPTURE_VIEW_MODE", f"page drew view {view.get('view')!r}; the offline renderer draws the sky (0)")
    need(view.get("loading") is False, "CAPTURE_WHILE_LOADING", a.capture)
    cap = np.asarray(Image.open(a.capture).convert("RGB"))
    H, W = cap.shape[:2]
    need([W, H] == [round(v) for v in view["canvas_px"]], "CAPTURE_SIZE", f"{[W, H]} vs {view['canvas_px']}")
    d = film.load_case(a.case)
    ss = {1: 1, 4: 2, 16: 4}[view["samples"]]
    ref = film.render(d, view["zoom"], (view["panX"], view["panY"]), (W, H), view["mask"], ss, view["exposure"])
    la, lb = luminance(cap), luminance(ref)
    c = corr(la, lb)
    mad = float(np.mean(np.abs(cap.astype(float) - ref.astype(float))))
    flipped = corr(la[::-1], lb)
    Image.fromarray(ref).save(ROOT / f"evidence/reconstruction-{a.case}-offline.png")
    # A dark or flat frame correlates with almost anything: the view must carry signal for the comparison to count.
    tests = [witness("signal: offline luminance standard deviation", float(lb.std()), 0.02, "at least"),
             witness("luminance correlation, browser vs offline", c, 0.98, "at least"),
             witness("mean absolute difference (8-bit units)", mad, 4.0),
             witness("negative control: vertically flipped capture correlation stays below 0.98", flipped, 0.98 - 1e-12)]
    write_json(ROOT / f"evidence/reconstruction-{a.case}.json", {
        "schema": "kerr2.reconstruction/1", "case": a.case,
        "case_manifest_sha256": sha((ROOT / "cases" / a.case / "case.json").read_bytes()),
        "view": view, "capture_sha256": sha(open(a.capture, "rb").read()),
        "offline_sha256": sha((ROOT / f"evidence/reconstruction-{a.case}-offline.png").read_bytes()),
        "witnesses": tests, "pass": all(t["pass"] for t in tests),
        "scope": "One view per case. Shares the mapping's assumptions with the shader (law 25): it detects GPU-path errors (orientation, decoding, sampling), not mistakes in the mapping itself."})
    print(json.dumps({"case": a.case, "signal_std": float(lb.std()), "corr": c, "mad": mad, "flipped_corr": flipped, "pass": all(t["pass"] for t in tests)}))


if __name__ == "__main__":
    main()
