"""Isosurfaces for x3d.STEM: naive surface nets, plus the measurements that check them.

Surface nets place one vertex per active cell at the mean of its edge crossings, so the vertex is NOT
exactly on the isosurface: its distance from it is a real quantity a witness can bound (marching cubes
puts vertices exactly on the linear interpolant, which would make that witness a tautology).

Conventions: the field is indexed f[x, y, z] on unit spacing; vertex coordinates are in cells; faces are
oriented so normals point from the high side (f > iso) to the low side. Pad the field with a value below
iso (``pad=``) and every surface closes at the box walls: the mesh has no boundary edges.
"""
from __future__ import annotations

import numpy as np

from .core import need

# The 12 edges of a unit cell as (corner a, corner b); corner c = (cx, cy, cz) with index cx + 2 cy + 4 cz.
_CORNERS = np.array([(x, y, z) for z in (0, 1) for y in (0, 1) for x in (0, 1)])
_EDGES = [(a, b) for a in range(8) for b in range(a + 1, 8) if np.abs(_CORNERS[a] - _CORNERS[b]).sum() == 1]


def pad_field(f: np.ndarray, value: float) -> np.ndarray:
    return np.pad(f, 1, mode="constant", constant_values=value)


def surface_nets(f: np.ndarray, iso: float, project: int = 3):
    """Return (verts float64 (V, 3), faces int64 (F, 3)); coordinates are in the indexing of f.

    `project` Newton steps move each vertex along the field gradient toward f = iso (plain surface nets
    shrink convex shapes: 1.1 % of a radius-10 sphere's volume, 2.2 % of a torus with a 4-cell tube)."""
    f = np.asarray(f, dtype=np.float64)
    need(f.ndim == 3 and min(f.shape) >= 2, "MESH_FIELD_SHAPE", str(f.shape))
    need(np.isfinite(f).all(), "MESH_FIELD_NONFINITE")
    nx, ny, nz = f.shape
    c = np.stack([f[cx:nx - 1 + cx, cy:ny - 1 + cy, cz:nz - 1 + cz] for cx, cy, cz in _CORNERS], axis=-1)
    above = c > iso
    active = above.any(-1) & ~above.all(-1)
    acc = np.zeros(active.shape + (3,))
    cnt = np.zeros(active.shape)
    for a, b in _EDGES:
        fa, fb = c[..., a], c[..., b]
        cross = (fa > iso) != (fb > iso)
        t = np.where(cross, (iso - fa) / np.where(cross, fb - fa, 1.0), 0.0)
        p = _CORNERS[a] + t[..., None] * (_CORNERS[b] - _CORNERS[a])
        acc += np.where(cross[..., None], p, 0.0)
        cnt += cross
    idx = np.full(active.shape, -1, dtype=np.int64)
    cells = np.argwhere(active)
    idx[active] = np.arange(len(cells))
    verts = cells + acc[active] / cnt[active][:, None]
    if project:
        verts = project_to_iso(f, verts, iso, project)

    quads = []
    # A grid edge along `axis` from point p to p + e_axis with a sign change is surrounded by four cells;
    # listed counter-clockwise about +axis, the quad's normal is +axis, which is outward when f(p) > iso.
    for axis in range(3):
        u, w = (axis + 1) % 3, (axis + 2) % 3
        sl0 = [slice(None)] * 3
        sl1 = [slice(None)] * 3
        sl0[axis], sl1[axis] = slice(0, -1), slice(1, None)
        e0, e1 = f[tuple(sl0)] > iso, f[tuple(sl1)] > iso
        edges = np.argwhere(e0 != e1)
        # the four cells need index u-1 >= 0 and w-1 >= 0 and u, w within the cell grid
        keep = (edges[:, u] >= 1) & (edges[:, w] >= 1) & (edges[:, u] <= f.shape[u] - 2) & (edges[:, w] <= f.shape[w] - 2)
        need(keep.all(), "MESH_OPEN_AT_BOUNDARY", "pad the field below iso to close the surface")
        ring = []
        for du, dw in ((-1, -1), (0, -1), (0, 0), (-1, 0)):
            cc = edges.copy()
            cc[:, u] += du
            cc[:, w] += dw
            ring.append(idx[cc[:, 0], cc[:, 1], cc[:, 2]])
        q = np.stack(ring, axis=1)
        need((q >= 0).all(), "MESH_DANGLING_QUAD", f"axis {axis}")
        flip = ~e0[tuple(edges.T)]          # f(p) <= iso: the high side is at +axis, so reverse
        q[flip] = q[flip][:, ::-1]
        quads.append(q)
    q = np.concatenate(quads)
    # split each quad along its shorter diagonal
    d02 = np.linalg.norm(verts[q[:, 0]] - verts[q[:, 2]], axis=1)
    d13 = np.linalg.norm(verts[q[:, 1]] - verts[q[:, 3]], axis=1)
    a = d02 <= d13
    t1 = np.where(a[:, None], q[:, [0, 1, 2]], q[:, [0, 1, 3]])
    t2 = np.where(a[:, None], q[:, [0, 2, 3]], q[:, [1, 2, 3]])
    return verts, np.concatenate([t1, t2])


def trilinear(f: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Sample f at points p (N, 3) by trilinear interpolation; points must lie inside the grid."""
    p = np.asarray(p, dtype=np.float64)
    hi = np.array(f.shape) - 1
    need(((p >= 0) & (p <= hi)).all(), "TRILINEAR_OUTSIDE")
    i0 = np.minimum(np.floor(p).astype(np.int64), hi - 1)
    t = p - i0
    out = np.zeros(len(p))
    for cx, cy, cz in _CORNERS:
        wgt = (t[:, 0] if cx else 1 - t[:, 0]) * (t[:, 1] if cy else 1 - t[:, 1]) * (t[:, 2] if cz else 1 - t[:, 2])
        out += wgt * f[i0[:, 0] + cx, i0[:, 1] + cy, i0[:, 2] + cz]
    return out


def trilinear_grad(f: np.ndarray, p: np.ndarray) -> np.ndarray:
    """Exact gradient of the trilinear interpolant at p (N, 3): the derivative of the function Newton is
    solving, so projection converges quadratically even at a step (a central-difference gradient spans two
    cells and left vertices 0.3 cells off the surface of a sharp seed, Turing Garden first build, 4 Nov)."""
    p = np.asarray(p, dtype=np.float64)
    hi = np.array(f.shape) - 1
    need(((p >= 0) & (p <= hi)).all(), "TRILINEAR_OUTSIDE")
    i0 = np.minimum(np.floor(p).astype(np.int64), hi - 1)
    t = p - i0
    out = np.zeros((len(p), 3))
    for cx, cy, cz in _CORNERS:
        fv = f[i0[:, 0] + cx, i0[:, 1] + cy, i0[:, 2] + cz]
        wx, wy, wz = (t[:, 0] if cx else 1 - t[:, 0]), (t[:, 1] if cy else 1 - t[:, 1]), (t[:, 2] if cz else 1 - t[:, 2])
        out[:, 0] += (1 if cx else -1) * wy * wz * fv
        out[:, 1] += (1 if cy else -1) * wx * wz * fv
        out[:, 2] += (1 if cz else -1) * wx * wy * fv
    return out


def project_to_iso(f: np.ndarray, verts: np.ndarray, iso: float, steps: int) -> np.ndarray:
    """Newton steps p <- p - (f(p) - iso) g / |g|^2 on the trilinear interpolant with its exact gradient;
    each move is capped at half a cell so a vertex cannot jump to another sheet."""
    hi = np.array(f.shape) - 1.0
    p = verts.copy()
    for _ in range(steps):
        gv = trilinear_grad(f, p)
        g2 = np.einsum("ij,ij->i", gv, gv)
        step = ((trilinear(f, p) - iso) / np.where(g2 > 1e-24, g2, np.inf))[:, None] * gv
        ln = np.linalg.norm(step, axis=1)
        step *= np.minimum(1.0, 0.5 / np.maximum(ln, 1e-300))[:, None]
        p = np.clip(p - step, 0.0, hi)
    return p


def gradient(f: np.ndarray) -> np.ndarray:
    return np.stack(np.gradient(np.asarray(f, dtype=np.float64)), axis=-1)


def vertex_normals(f: np.ndarray, verts: np.ndarray) -> np.ndarray:
    """Unit normals from the field gradient, pointing from high to low."""
    g = gradient(f)
    n = -np.stack([trilinear(g[..., i], verts) for i in range(3)], axis=1)
    ln = np.linalg.norm(n, axis=1)
    need((ln > 0).all(), "MESH_ZERO_GRADIENT")
    return n / ln[:, None]


def mean_curvature(f: np.ndarray, verts: np.ndarray) -> np.ndarray:
    """H = -1/2 div(grad f / |grad f|) sampled at the vertices; positive where the high region is convex
    (a sphere of radius R around a maximum has H = 1/R)."""
    g = gradient(f)
    mag = np.linalg.norm(g, axis=-1)
    mag = np.where(mag > 1e-12, mag, 1e-12)
    div = sum(np.gradient(g[..., i] / mag, axis=i) for i in range(3))
    return trilinear(-0.5 * div, verts)


def edge_use(faces: np.ndarray) -> np.ndarray:
    """How many faces use each undirected edge."""
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e.sort(axis=1)
    _, counts = np.unique(e, axis=0, return_counts=True)
    return counts


def checks(f: np.ndarray, iso: float, verts: np.ndarray, faces: np.ndarray, rng: np.random.Generator,
           samples: int = 400_000) -> dict:
    """Measurements a mesh witness can bound, each from an independent route where possible."""
    use = edge_use(faces)
    tri = verts[faces]
    cross = np.cross(tri[:, 1] - tri[:, 0], tri[:, 2] - tri[:, 0])
    area = 0.5 * np.linalg.norm(cross, axis=1)
    signed_volume = float(np.einsum("ij,ij->i", tri[:, 0], np.cross(tri[:, 1], tri[:, 2])).sum() / 6)
    # Independent volume: Monte Carlo over the box, counting points where the trilinear field exceeds iso.
    hi = np.array(f.shape) - 1.0
    pts = rng.random((samples, 3)) * hi
    frac = float(np.mean(trilinear(f, pts) > iso))
    mc_volume = frac * float(np.prod(hi))
    mc_se = float(np.sqrt(frac * (1 - frac) / samples) * np.prod(hi))
    # Distance of each vertex from the isosurface, to first order |f(p) - iso| / |grad f(p)|, in cells.
    gv = np.linalg.norm(trilinear_grad(f, verts), axis=1)
    dist = np.abs(trilinear(f, verts) - iso) / np.maximum(gv, 1e-12)
    return {
        "vertices": int(len(verts)), "triangles": int(len(faces)),
        "boundary_edges": int(np.count_nonzero(use % 2 == 1)),
        "nonmanifold_edges": int(np.count_nonzero(use > 2)),
        "degenerate_triangles": int(np.count_nonzero(area < 1e-12)),
        "area": float(area.sum()), "volume": signed_volume,
        "mc_volume": mc_volume, "mc_volume_se": mc_se,
        "volume_rel_diff": abs(signed_volume - mc_volume) / max(mc_volume, 1e-12),
        "iso_distance_p95": float(np.percentile(dist, 95)), "iso_distance_max": float(dist.max()),
    }
