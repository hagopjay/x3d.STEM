"""stemkit core: fail-closed publication for x3d.STEM studies (Loom laws 18 and 24).

Every gate raises (`need`), so `python -O` cannot turn a red case green; every payload is written
atomically and reopened before its hash is recorded; every case manifest is loom.scientific-case/1 and
names the builder that produced it, so the Loom's science gate (loomkit.sci) can check it.
"""
from __future__ import annotations

import hashlib
import io
import json
import os
import platform
import zlib
from pathlib import Path

import numpy as np

CASE_SCHEMA = "loom.scientific-case/1"


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


def witness(id: str, observed: float, limit: float, rule: str = "at most", note: str = "") -> dict:
    observed, limit = float(observed), float(limit)
    need(np.isfinite(observed) and np.isfinite(limit), "WITNESS_NONFINITE", id)
    need(rule in ("at most", "at least"), "WITNESS_RULE", rule)
    ok = observed <= limit if rule == "at most" else observed >= limit
    w = {"id": id, "pass": bool(ok), "observed": observed, "limit": limit, "rule": rule}
    if note:
        w["note"] = note
    return w


class Study:
    """One study folder: root/cases/<name>/case.json plus payloads, built by root/<builder>."""

    def __init__(self, root: Path, kind: str, builder: str):
        self.root, self.kind, self.builder = Path(root), kind, builder
        need((self.root / builder).is_file(), "BUILDER_MISSING", builder)

    def rel(self, path: Path) -> str:
        return Path(path).resolve().relative_to(self.root.resolve()).as_posix()

    def publish_png(self, array_u8: np.ndarray, path: Path) -> dict:
        """Write a PNG atomically, then reopen it: a published payload must decode (law 24)."""
        from PIL import Image
        buf = io.BytesIO()
        Image.fromarray(array_u8).save(buf, format="PNG", optimize=False)
        atomic_bytes(path, buf.getvalue())
        data = path.read_bytes()
        need(data[-8:-4] == b"IEND", "PUBLICATION_UNDECODABLE", str(path))
        back = np.asarray(Image.open(io.BytesIO(data)))
        need(back.shape == array_u8.shape and np.array_equal(back, array_u8), "PUBLICATION_ROUNDTRIP", str(path))
        return {"file": self.rel(path), "sha256": sha(data), "bytes": len(data)}

    def publish_deflate(self, raw: bytes, path: Path, **extra) -> dict:
        """zlib-deflate a binary payload (the browser inflates it with DecompressionStream('deflate')),
        write it atomically, reopen and inflate it, and record both hashes: the browser checks the
        compressed bytes before use and the decoded bytes after."""
        atomic_bytes(path, zlib.compress(raw, 9))
        data = path.read_bytes()
        need(zlib.decompress(data) == raw, "PUBLICATION_ROUNDTRIP", str(path))
        return {"file": self.rel(path), "sha256": sha(data), "bytes": len(data),
                "decoded_sha256": sha(raw), "decoded_bytes": len(raw), **extra}

    def save_case(self, name: str, meta: dict, frames: list, metrics: list, witnesses: list) -> Path:
        out = self.root / "cases" / name
        case = {"schema": CASE_SCHEMA, "id": f"{self.kind}/{name}", "kind": self.kind, "name": name, **meta,
                "frames": frames, "metrics": metrics, "witnesses": witnesses,
                "builder_sha256": sha((self.root / self.builder).read_bytes()),
                "runtime": {"python": platform.python_version(), "numpy": np.__version__}}
        write_json(out / "case.json", case)
        return out / "case.json"
