"""Binary mesh frames for the browser: one deflated blob per frame, read by src/meshframe.js.

Layout (little-endian, before deflate):
  positions  uint16 x 3V   quantized over [0, extent] per axis: x = q / 65535 * extent
  normals    int8   x 3V   unit normal * 127
  colors     uint8  x 3V   sRGB-encoded vertex colour
  pad        to a multiple of 4 bytes
  indices    uint32 x 3F
The manifest records V, F, extent, both hashes (compressed and decoded) and the quantization error, so
the page can check the bytes before use and its decoded arrays after.
"""
from __future__ import annotations

import numpy as np

from .core import need


def pack(verts: np.ndarray, normals: np.ndarray, colors_u8: np.ndarray, faces: np.ndarray, extent) -> tuple[bytes, dict]:
    extent = np.asarray(extent, dtype=np.float64)
    V, F = len(verts), len(faces)
    need(V < 2**32 and F > 0, "MESHIO_SIZE", f"{V} {F}")
    need((verts >= 0).all() and (verts <= extent).all(), "MESHIO_EXTENT")
    need(faces.min() >= 0 and faces.max() < V, "MESHIO_INDEX")
    q = np.rint(verts / extent * 65535).astype("<u2")
    nq = np.rint(np.clip(normals, -1, 1) * 127).astype("i1")
    c = np.asarray(colors_u8, dtype="u1")
    need(c.shape == (V, 3), "MESHIO_COLORS")
    head = q.tobytes() + nq.tobytes() + c.tobytes()
    head += b"\0" * (-len(head) % 4)
    raw = head + faces.astype("<u4").tobytes()
    back = q.astype(np.float64) / 65535 * extent
    info = {"vertices": int(V), "triangles": int(F), "extent": extent.tolist(), "layout": "stemkit.meshframe/1",
            "quantization_max_cells": float(np.abs(back - verts).max())}
    return raw, info


def unpack(raw: bytes, info: dict):
    V, F = info["vertices"], info["triangles"]
    extent = np.asarray(info["extent"], dtype=np.float64)
    o = 0
    q = np.frombuffer(raw, "<u2", 3 * V, o).reshape(V, 3); o += 6 * V
    n = np.frombuffer(raw, "i1", 3 * V, o).reshape(V, 3); o += 3 * V
    c = np.frombuffer(raw, "u1", 3 * V, o).reshape(V, 3); o += 3 * V
    o += -o % 4
    f = np.frombuffer(raw, "<u4", 3 * F, o).reshape(F, 3); o += 12 * F
    need(o == len(raw), "MESHIO_LENGTH", f"{o} != {len(raw)}")
    return q.astype(np.float64) / 65535 * extent, n.astype(np.float64) / 127, c, f.astype(np.int64)
