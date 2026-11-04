"""Kerr 2 publication helpers. Fail-closed by construction (Loom laws 18 and 24):
every gate raises, nothing relies on `assert`, and every published image is reopened after writing.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
from pathlib import Path

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


class Rejected(Exception):
    def __init__(self, code: str, detail: str = ""):
        self.code, self.detail = code, detail
        super().__init__(f"{code}: {detail}" if detail else code)


def need(condition, code: str, detail: str = "") -> None:
    if not condition:
        raise Rejected(code, detail)


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def atomic_bytes(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_name("." + path.name + ".tmp")
    with tmp.open("wb") as f:
        f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp, path)


def write_json(path: Path, data) -> None:
    atomic_bytes(path, (json.dumps(data, indent=2, allow_nan=False) + "\n").encode())


def publish_png(array_u8: np.ndarray, path: Path) -> dict:
    """Write a PNG atomically, then reopen it: a published payload must decode (law 24)."""
    buf = io.BytesIO()
    Image.fromarray(array_u8).save(buf, format="PNG", optimize=False)
    atomic_bytes(path, buf.getvalue())
    data = path.read_bytes()
    need(data[-8:-4] == b"IEND", "PUBLICATION_UNDECODABLE", str(path))
    back = np.asarray(Image.open(io.BytesIO(data)))
    need(back.shape == array_u8.shape and np.array_equal(back, array_u8), "PUBLICATION_ROUNDTRIP", str(path))
    return {"file": path.relative_to(ROOT).as_posix(), "sha256": sha(data), "bytes": len(data)}


def rgbm(rgb: np.ndarray, path: Path, scale: float = 16.0) -> dict:
    """Linear HDR RGB -> RGBM8 (multiplier 16), counting clipped values instead of hiding them."""
    need(np.isfinite(rgb).all(), "NONFINITE_RADIANCE", str(path))
    m = np.ceil(np.clip(np.max(rgb, axis=-1) / scale, 1 / 255, 1) * 255) / 255
    out = np.concatenate([np.clip(rgb / (m[..., None] * scale), 0, 1), m[..., None]], -1)
    f = publish_png(np.rint(out * 255).astype("uint8"), path)
    f.update({"encoding": "linear RGBM; multiplier 16", "time": 0, "clipped_values": int(np.count_nonzero(rgb > scale))})
    return f


def witness(id: str, observed: float, limit: float, rule: str = "at most") -> dict:
    observed, limit = float(observed), float(limit)
    need(np.isfinite(observed) and np.isfinite(limit), "WITNESS_NONFINITE", id)
    ok = observed <= limit if rule == "at most" else observed >= limit
    return {"id": id, "pass": bool(ok), "observed": observed, "limit": limit, "rule": rule}


def save_case(name: str, meta: dict, frames: list, metrics: list, witnesses: list) -> Path:
    out = ROOT / "cases" / name
    case = {"schema": "loom.scientific-case/1", "id": "kerr2/" + name, "kind": "kerr2", "name": name, **meta,
            "frames": frames, "metrics": metrics, "witnesses": witnesses,
            "builder_sha256": sha((ROOT / "tools/kerr2.py").read_bytes()),
            "runtime": {"python": platform.python_version(), "numpy": np.__version__}}
    write_json(out / "case.json", case)
    return out / "case.json"
