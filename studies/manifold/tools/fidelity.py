"""Fidelity of the X3D frame against the original page's frame at the same moment (Loom pattern G: an
independent renderer must reproduce the picture). Both frames are captured by tools/record_browser.py with
film grain off, at one time, camera, mood and pixel ratio; the interface chrome is masked out.

  python3 -I tools/fidelity.py ORIGINAL.png X3D.png [--json]

Measures, on the scene region: SSIM of luminance (Gaussian window 1.5 px), Pearson correlation of luminance,
mean absolute difference of the 8-bit RGB values, and the mean and p95 colour difference (CIE76 Delta E in
Lab, D65). Controls that must score worse are computed by record_browser.py (mirror, another moment).
"""
from __future__ import annotations

import json
import sys

import numpy as np
from PIL import Image
from scipy.ndimage import gaussian_filter

# Chrome rectangles at 1280 x 800 (x0, y0, x1, y1): masthead, intro, dock and footer.
CHROME = [(0, 0, 1280, 92), (0, 520, 330, 700), (0, 700, 1280, 800)]


def load(path):
    return np.asarray(Image.open(path).convert("RGB"), dtype=np.float64) / 255.0


def mask_for(shape):
    h, w = shape[:2]
    m = np.ones((h, w), bool)
    sx, sy = w / 1280, h / 800
    for x0, y0, x1, y1 in CHROME:
        m[int(y0 * sy):int(y1 * sy), int(x0 * sx):int(x1 * sx)] = False
    return m


def srgb_to_lab(rgb):
    c = np.where(rgb <= 0.04045, rgb / 12.92, ((rgb + 0.055) / 1.055) ** 2.4)
    M = np.array([[0.4124564, 0.3575761, 0.1804375], [0.2126729, 0.7151522, 0.0721750], [0.0193339, 0.1191920, 0.9503041]])
    xyz = c @ M.T / np.array([0.95047, 1.0, 1.08883])
    f = np.where(xyz > (6 / 29) ** 3, np.cbrt(xyz), xyz / (3 * (6 / 29) ** 2) + 4 / 29)
    return np.stack([116 * f[..., 1] - 16, 500 * (f[..., 0] - f[..., 1]), 200 * (f[..., 1] - f[..., 2])], -1)


def ssim(a, b, m, sigma=1.5):
    C1, C2 = 0.01 ** 2, 0.03 ** 2
    mu_a, mu_b = gaussian_filter(a, sigma), gaussian_filter(b, sigma)
    saa = gaussian_filter(a * a, sigma) - mu_a ** 2
    sbb = gaussian_filter(b * b, sigma) - mu_b ** 2
    sab = gaussian_filter(a * b, sigma) - mu_a * mu_b
    s = ((2 * mu_a * mu_b + C1) * (2 * sab + C2)) / ((mu_a ** 2 + mu_b ** 2 + C1) * (saa + sbb + C2))
    return float(s[m].mean())


def compare(a, b):
    m = mask_for(a.shape)
    la, lb = a @ [0.2126, 0.7152, 0.0722], b @ [0.2126, 0.7152, 0.0722]
    de = np.linalg.norm(srgb_to_lab(a) - srgb_to_lab(b), axis=-1)[m]
    return {"ssim": round(ssim(la, lb, m), 4), "corr": round(float(np.corrcoef(la[m], lb[m])[0, 1]), 4),
            "mad8": round(float(np.abs(a - b)[m].mean() * 255), 2), "deltaE_mean": round(float(de.mean()), 2),
            "deltaE_p95": round(float(np.percentile(de, 95)), 2), "mean_luma": [round(float(la[m].mean()), 4), round(float(lb[m].mean()), 4)]}


if __name__ == "__main__":
    r = compare(load(sys.argv[1]), load(sys.argv[2]))
    print(json.dumps(r) if "--json" in sys.argv else "  ".join(f"{k} {v}" for k, v in r.items()))
