"""Tier C film: a zoom into the photon ring, rendered offline from the same verified PNG payloads the
browser shows, then encoded with ffmpeg. No new rays are traced; every frame is a resampling of
computed rays (image layers + ring atlas), with the same mapping as shaders/kerr2.frag.

This second implementation of the display mapping also serves the reconstruction witness: a browser
frame and the film renderer's frame at the same view must agree (they share the mapping's
assumptions, so this catches GPU/texture-orientation errors, not mistakes in the mapping itself).

  python3 tools/film.py --case extreme --seconds 16 --fps 30 --size 1280x720
"""
from __future__ import annotations

import argparse
import json
import subprocess
from pathlib import Path

import numpy as np
from PIL import Image

from common import ROOT, need, sha, write_json


def load_rgbm(path: Path) -> np.ndarray:
    """Encoded RGBM as floats in [0, 1]. Filtering happens on encoded values and decoding after, exactly
    as the GPU's bilinear filter does in the browser, so film and browser use the same sampling semantics."""
    return np.asarray(Image.open(path)).astype(np.float32) / 255.0


def decode(rgba: np.ndarray) -> np.ndarray:
    return rgba[..., :3] * rgba[..., 3:4] * 16.0


def load_case(name: str) -> dict:
    case = json.loads((ROOT / "cases" / name / "case.json").read_text())
    for f in case["frames"]:
        p = ROOT / f["file"]
        need(p.is_file() and sha(p.read_bytes()) == f["sha256"], "PAYLOAD_HASH", f["file"])
    g = json.loads((ROOT / "cases" / name / "geometry.json").read_text())
    by = {Path(f["file"]).stem: ROOT / f["file"] for f in case["frames"]}
    img = [load_rgbm(by[f"image-n{n}"]) for n in range(4)]
    ring = [load_rgbm(by[f"ring-n{n}"]) for n in range(4)]
    c = np.asarray(Image.open(by["curve"])).astype(np.int64)[0]
    rho = ((c[:, 0] * 256 + c[:, 1]) * 256 + c[:, 2]) / (2 ** 24 - 1) * 16.0
    return {"case": case, "geom": g, "img": img, "ring": ring, "rho": rho}


def bilinear(tex: np.ndarray, x: np.ndarray, y: np.ndarray, wrap_x: bool) -> np.ndarray:
    """Sample tex[row, col] at continuous texel coordinates (x = col, y = row, texel centres at +0.5)."""
    h, w, _ = tex.shape
    x = x - 0.5
    y = np.clip(y - 0.5, 0, h - 1)
    x0 = np.floor(x).astype(np.int64)
    y0 = np.floor(y).astype(np.int64)
    fx = (x - x0)[..., None]
    fy = (y - y0)[..., None]
    y1 = np.minimum(y0 + 1, h - 1)
    if wrap_x:
        x0m, x1m = x0 % w, (x0 + 1) % w
    else:
        x0m, x1m = np.clip(x0, 0, w - 1), np.clip(x0 + 1, 0, w - 1)
    return ((tex[y0, x0m] * (1 - fx) + tex[y0, x1m] * fx) * (1 - fy) + (tex[y1, x0m] * (1 - fx) + tex[y1, x1m] * fx) * fy)


def render(d: dict, zoom: float, pan: tuple, size: tuple, mask: int = 15, ss: int = 2, exposure: float = 1.2) -> np.ndarray:
    """ss x ss sub-samples per pixel on the same regular grid as the shader (samples = ss*ss)."""
    g, rho = d["geom"], d["rho"]
    W, H = size
    span, imgasp = g["span"], g["width"] / g["height"]
    vh = span / imgasp / zoom
    acc = np.zeros((H, W, 3), np.float32)
    for sy in range(ss):
        for sx in range(ss):
            u = (np.arange(W) + (sx + 0.5) / ss) / W - 0.5
            v = 0.5 - (np.arange(H) + (sy + 0.5) / ss) / H
            al = pan[0] + u[None, :] * vh * W / H + 0 * v[:, None]
            be = pan[1] + v[:, None] * vh + 0 * u[None, :]
            rx, ry = al - g["center_alpha"], be
            psi = np.mod(np.arctan2(ry, rx), 2 * np.pi)
            k = psi / (2 * np.pi) * g["npsi"] - 0.5
            k0 = np.floor(k).astype(np.int64)
            f = k - k0
            rc = rho[k0 % g["npsi"]] * (1 - f) + rho[(k0 + 1) % g["npsi"]] * f
            dd = np.hypot(rx, ry) - rc
            half = g["ndelta"] / 2
            m = np.clip(np.abs(dd), g["delta_min"], g["delta_max"])
            kk = np.log(m / g["delta_min"]) / np.log(g["delta_max"] / g["delta_min"]) * (half - 1)
            row = np.where(dd > 0, half + kk, half - 1 - kk) + 0.5
            col = psi / (2 * np.pi) * g["npsi"]
            in_ring = np.abs(dd) <= g["delta_max"]
            ix = (al / span + 0.5) * g["width"]
            iy = (1 - (be / (span / imgasp) + 0.5)) * g["height"]
            inside = (ix >= 0) & (ix <= g["width"]) & (iy >= 0) & (iy <= g["height"])
            c = np.zeros((H, W, 3), np.float32)
            for n in range(4):
                if mask & (1 << n):
                    c += np.where(in_ring[..., None], decode(bilinear(d["ring"][n], col, row, True)),
                                  np.where(inside[..., None], decode(bilinear(d["img"][n], ix, iy, False)), 0))
            acc += c
    c = acc / (ss * ss) * exposure
    c = np.clip((c * (2.51 * c + 0.03)) / (c * (2.43 * c + 0.59) + 0.14), 0, 1)
    return (np.power(c, 1 / 2.2) * 255 + 0.5).astype(np.uint8)


# Where each flight dives in: the Doppler-beamed side for the spinning cases, the ring top for Schwarzschild.
# Same table as FLY_PSI in src/app.js.
FLY_PSI = {"extreme": np.pi, "kerr": np.pi, "schwarzschild": np.pi / 2}


def flight(d: dict, t: float, psi: float, z1: float = 1.2e4):
    """Same path as the page's 'Fly into the photon ring' (src/app.js)."""
    g = d["geom"]
    n = g["npsi"]
    k = psi / (2 * np.pi) * n - 0.5
    k0 = int(np.floor(k))
    rc = d["rho"][k0 % n] * (1 - (k - k0)) + d["rho"][(k0 + 1) % n] * (k - k0)
    tx, ty = g["center_alpha"] + (rc + 2e-3) * np.cos(psi), (rc + 2e-3) * np.sin(psi)
    e = t * t * (3 - 2 * t)
    zoom = z1 ** e
    s = min(1, t / 0.35)
    s = s * s * (3 - 2 * s)
    return zoom, (tx * s, ty * s)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--case", default="extreme")
    p.add_argument("--seconds", type=float, default=16)
    p.add_argument("--fps", type=int, default=30)
    p.add_argument("--size", default="1280x720")
    p.add_argument("--still", default="", help="render one frame at zoom,panX,panY to this PNG path and stop")
    a = p.parse_args()
    W, H = map(int, a.size.split("x"))
    d = load_case(a.case)
    out = ROOT / "film"
    out.mkdir(exist_ok=True)
    if a.still:
        z, px, py = map(float, a.still.split(":")[0].split(","))
        Image.fromarray(render(d, z, (px, py), (W, H))).save(a.still.split(":")[1])
        return
    frames = int(a.seconds * a.fps)
    tmp = out / f".frames-{a.case}"
    tmp.mkdir(exist_ok=True)
    for i in range(frames):
        z, pan = flight(d, i / max(frames - 1, 1), FLY_PSI[a.case])
        Image.fromarray(render(d, z, pan, (W, H))).save(tmp / f"{i:05d}.png")
    mp4 = out / f"photon-ring-{a.case}.mp4"
    subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(a.fps), "-i", str(tmp / "%05d.png"),
                    "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "16", "-movflags", "+faststart", str(mp4)], check=True)
    for f in tmp.glob("*.png"):
        f.unlink()
    tmp.rmdir()
    write_json(out / f"photon-ring-{a.case}.json", {"schema": "kerr2.film/1", "case": d["case"]["id"],
               "case_manifest_sha256": sha((ROOT / "cases" / a.case / "case.json").read_bytes()),
               "film": mp4.name, "sha256": sha(mp4.read_bytes()), "bytes": mp4.stat().st_size, "frames": frames, "fps": a.fps,
               "size": [W, H], "supersampling": "2x2 per pixel", "target_psi": FLY_PSI[a.case], "zoom_end": 1.2e4, "exposure": 1.2, "renderer": "tools/film.py (numpy resampling of the verified PNG payloads)",
               "scope": "Tier C film from computed rays only; no new rays traced, no interpolation in time beyond camera motion."})
    print("film", mp4, frames, "frames")


if __name__ == "__main__":
    main()
