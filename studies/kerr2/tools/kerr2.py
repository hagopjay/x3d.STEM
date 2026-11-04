"""Kerr 2 · The Photon Ring. Null geodesics through an optically thin equatorial disk, every crossing kept.

The integrator (separated Kerr equations in Mino time, u = 1/r, z = cos theta, RK4 step doubling) is
adapted from the Scientific Loom's tools/kerr.py (MIT, see LICENSE.scientific-loom). What changes:
- the ray does not stop at the first disk crossing: it records radius, frequency shift g and phi of up
  to NREC equatorial crossings, so the n = 0, 1, 2, 3 images (the photon sub-rings) are separate layers;
- a polar "ring atlas" samples rays at angle psi around the analytic critical curve and at a
  log-spaced offset delta from it (1e-6 to 1.5 M), so the ring can be zoomed far below a pixel;
- witnesses compare the computed shadow edge with Bardeen's analytic critical curve, measure sub-ring
  widths by bisection at two integration tolerances, and (Schwarzschild) compare the sub-ring
  demagnification with e^-pi.
G = M = c = 1. Backward rays from an observer at r0 = 200 with conserved (lambda, q) set by the screen
point (alpha, beta), exactly as the source solver.
"""
from __future__ import annotations

import argparse
import json
import time

import numpy as np
from numba import njit, prange, set_num_threads

from common import ROOT, need, rgbm, save_case, witness, write_json
import color

set_num_threads(8)
NREC = 4                 # crossings recorded per ray (n = 0..3)
REC = 6 + 3 * NREC       # status, errmax, iterations, crossings, r_end, z_end, then (r, g, phi) per crossing
SPAN = 36.0              # screen width in GM/c^2, as the Scientific Loom
R0 = 200.0


@njit(cache=True)
def rhs(s, a, lam, q):
    u, w, z, v, phi = s
    C = q + (lam - a) ** 2
    A = 2 * (a * a - a * lam) - C
    return np.array([w, A * u + 3 * C * u * u - 2 * a * a * q * u ** 3, v, (a * a - q - lam * lam) * z - 2 * a * a * z ** 3,
                     lam / max(1 - z * z, 1e-13) - a + a * (1 + (a * a - a * lam) * u * u) / (1 - 2 * u + a * a * u * u)])


@njit(cache=True)
def step(s, h, a, lam, q):
    k1 = rhs(s, a, lam, q)
    k2 = rhs(s + h * k1 / 2, a, lam, q)
    k3 = rhs(s + h * k2 / 2, a, lam, q)
    k4 = rhs(s + h * k3, a, lam, q)
    return s + h * (k1 + 2 * k2 + 2 * k3 + k4) / 6


@njit(cache=True)
def gshift(r, a, lam):
    """Frequency shift for a prograde circular Keplerian emitter at radius r (r outside the photon orbit)."""
    d = r ** 3 - 3 * r * r + 2 * a * r ** 1.5
    if d <= 0:
        return 0.0
    omega = 1 / (r ** 1.5 + a)
    ut = (r ** 1.5 + a) / np.sqrt(d)
    return 1 / (ut * (1 - omega * lam))


@njit(cache=True)
def trace(alpha, beta, a, inc, rin, rout, tol, stop_after):
    """Status: 0 captured, 2 escaped, 3 unresolved, 4 stopped after `stop_after` crossings."""
    out = np.zeros(REC)
    lam = -alpha * np.sin(inc)
    q = beta * beta + (alpha * alpha - a * a) * np.cos(inc) ** 2
    P = R0 * R0 + a * a - a * lam
    R = P * P - (R0 * R0 - 2 * R0 + a * a) * (q + (lam - a) ** 2)
    if R < 0:
        out[0] = 3.0
        return out
    s = np.array([1 / R0, np.sqrt(R) / R0 ** 2, np.cos(inc), -np.sin(inc) * beta, 0.0])
    rp = 1 + np.sqrt(1 - a * a)
    h = .02 / np.sqrt(1 + abs(q) + lam * lam)
    errmax = 0.0
    n = 0
    for it in range(40000):
        u, w, z, v, phi = s
        r = 1 / max(u, 1e-12)
        if r < rp + .002:
            out[0] = 0.0; out[1] = errmax; out[2] = it; out[3] = n; out[4] = r; out[5] = z
            return out
        if u < 1 / R0 and w < 0:
            out[0] = 2.0; out[1] = errmax; out[2] = it; out[3] = n; out[4] = r; out[5] = z
            return out
        h = min(h, .05 / np.sqrt(1 + abs(q) + lam * lam), .1 * abs((1 / rp - u) / max(abs(w), 1e-12)))
        one = step(s, h, a, lam, q)
        half = step(s, h / 2, a, lam, q)
        two = step(half, h / 2, a, lam, q)
        # phi is a passive quadrature (it never feeds back and Kerr 2 does not use it for emission), so it is
        # left out of the error norm: near the spin axis its 1/(1-z^2) rate collapsed the step and 9 rays ran
        # out of steps unresolved in the first full run (C, 4 Nov).
        scales = np.array([1., max(abs(w), 1.), 1., max(abs(v), 1.)])
        error = np.max(np.abs(two[:4] - one[:4]) / scales) / 15
        if not np.isfinite(error) or error > tol:
            h *= .5
            if h < 1e-14:
                out[0] = 3.0; out[1] = errmax; out[2] = it; out[3] = n
                return out
            continue
        if s[2] * two[2] < 0:
            lo = 0.0
            hi = h
            for _ in range(30):
                mid = (lo + hi) / 2
                hit = step(s, mid, a, lam, q)
                if hit[2] * s[2] > 0:
                    lo = mid
                else:
                    hi = mid
            hit = step(s, (lo + hi) / 2, a, lam, q)
            rr = 1 / hit[0]
            if n < NREC:
                out[6 + 3 * n] = rr
                out[7 + 3 * n] = gshift(rr, a, lam) if (rr >= rin and rr <= rout) else 0.0
                out[8 + 3 * n] = hit[4]
            n += 1
            if n >= stop_after:
                out[0] = 4.0; out[1] = errmax; out[2] = it; out[3] = n; out[4] = rr; out[5] = 0.0
                return out
        s = two
        u, w, z, v, phi = s
        C = q + (lam - a) ** 2
        A = 2 * (a * a - a * lam) - C
        er = abs(w * w - (1 + A * u * u + 2 * C * u ** 3 - a * a * q * u ** 4)) / (1 + abs(A) * u * u + 2 * abs(C * u ** 3) + a * a * abs(q) * u ** 4)
        ez = abs(v * v - (q + (a * a - q - lam * lam) * z * z - a * a * z ** 4)) / (1 + abs(q) + lam * lam + a * a)
        errmax = max(errmax, er, ez)
        if error < tol / 32:
            h *= 1.5
    out[0] = 3.0; out[1] = errmax; out[2] = 40000; out[3] = n
    return out


@njit(parallel=True, cache=True)
def bank(w, h, a, inc, rin, rout, tol):
    out = np.zeros((h, w, REC), np.float32)
    for j in prange(h):
        for i in range(w):
            out[j, i] = trace(((i + .5) / w - .5) * SPAN, (.5 - (j + .5) / h) * SPAN * h / w, a, inc, rin, rout, tol, NREC)
    return out


@njit(parallel=True, cache=True)
def atlas(cx, psi, rho, delta, a, inc, rin, rout, tol):
    out = np.zeros((len(delta), len(psi), REC), np.float32)
    for k in prange(len(psi)):
        c, s_ = np.cos(psi[k]), np.sin(psi[k])
        for j in range(len(delta)):
            rr = rho[k] + delta[j]
            out[j, k] = trace(cx + rr * c, rr * s_, a, inc, rin, rout, tol, NREC)
    return out


# ---------------------------------------------------------------- analytic critical curve (Bardeen 1973)
def critical_curve(a: float, inc: float, n: int = 400000):
    """Screen points (alpha, beta) of the critical curve: images of spherical photon orbits.
    lambda = (r^2(3-r) - a^2(r+1)) / (a(r-1)),  q = r^3(4a^2 - r(r-3)^2) / (a^2 (r-1)^2),
    alpha = -lambda / sin(inc),  beta = +-sqrt(q + a^2 cos^2 inc - lambda^2 cot^2 inc).  a = 0: circle sqrt(27)."""
    if a < 1e-12:
        t = np.linspace(0, 2 * np.pi, n, endpoint=False)
        return np.sqrt(27) * np.cos(t), np.sqrt(27) * np.sin(t), np.full(n, 3.0)
    r1 = 2 * (1 + np.cos(2 / 3 * np.arccos(-a)))
    r2 = 2 * (1 + np.cos(2 / 3 * np.arccos(a)))
    r = np.linspace(r1, r2, n)
    lam = (r * r * (3 - r) - a * a * (r + 1)) / (a * (r - 1))
    q = r ** 3 * (4 * a * a - r * (r - 3) ** 2) / (a * a * (r - 1) ** 2)
    b2 = q + a * a * np.cos(inc) ** 2 - lam ** 2 / np.tan(inc) ** 2
    ok = b2 >= 0
    al = -lam[ok] / np.sin(inc)
    be = np.sqrt(b2[ok])
    rr = r[ok]
    return np.concatenate([al, al[::-1]]), np.concatenate([be, -be[::-1]]), np.concatenate([rr, rr[::-1]])


def polar_curve(a: float, inc: float, npsi: int):
    """rho_c(psi) about the centre of the curve's alpha extent; requires a star-shaped curve."""
    al, be, rr = critical_curve(a, inc)
    cx = 0.5 * (al.min() + al.max())
    ang = np.mod(np.arctan2(be, al - cx), 2 * np.pi)
    rad = np.hypot(al - cx, be)
    order = np.argsort(ang)
    ang, rad, rr = ang[order], rad[order], rr[order]
    need(np.all(np.diff(ang) >= 0), "CURVE_NOT_STAR_SHAPED")
    psi = (np.arange(npsi) + 0.5) * 2 * np.pi / npsi
    rho = np.interp(psi, ang, rad, period=2 * np.pi)
    POLAR_CACHE[(a, inc)] = (ang, rr)
    return cx, psi, rho, (al, be)


POLAR_CACHE: dict = {}
ABUTTING: list = []


def photon_orbit_radius(a, inc, psi):
    """Radius of the spherical photon orbit whose image is the critical-curve point at angle psi (exact)."""
    ang, rr = POLAR_CACHE[(a, inc)]
    return float(np.interp(psi, ang, rr, period=2 * np.pi))


# ---------------------------------------------------------------- bisection witnesses
def capture_edge(cx, psi, rho_c, a, inc, tol=1e-10, half=0.5, iters=60):
    """delta at which a disk-free ray switches from captured to escaped, along direction psi."""
    lo, hi = -half, half
    c, s_ = np.cos(psi), np.sin(psi)
    def status(d):
        return trace(cx + (rho_c + d) * c, (rho_c + d) * s_, a, inc, 1e9, 1e10, tol, 10 ** 6)[0]
    need(status(lo) == 0 and status(hi) == 2, "EDGE_BRACKET", f"psi={psi}")
    unresolved = 0
    for _ in range(iters):
        mid = 0.5 * (lo + hi)
        st = status(mid)
        if st == 0:
            lo = mid
        elif st == 2:
            hi = mid
        else:
            unresolved += 1
            break
    return 0.5 * (lo + hi), hi - lo, unresolved


def crossing_radius(cx, psi, rho_c, d, a, inc, n, tol):
    """Radius of the n-th (0-based) equatorial crossing; +inf if the ray escapes or is captured first."""
    t = trace(cx + (rho_c + d) * np.cos(psi), (rho_c + d) * np.sin(psi), a, inc, 1e9, 1e10, tol, n + 1)
    return float(t[6 + 3 * n]) if (t[0] == 4 and n < NREC) else np.inf


def subring_edges(cx, psi, rho_c, a, inc, n, rin, rout, tol, iters=55):
    """Outside the curve, the n-th crossing radius falls from +inf toward the photon-orbit radius r_ph(psi)
    as delta -> 0+. Sub-ring n is the delta-interval where rin <= r_n <= rout; returns (delta_in, delta_out).
    The outer edge is found first. If r_ph(psi) >= rin (exact, from Bardeen's parametrisation) the ring
    reaches the curve (delta_in = 0); if r_ph < rin an inner edge exists only when the critical ray's n-th
    crossing also falls inside rin, which the sampled crossing radii decide. When it exists it is searched
    strictly below the outer edge, taking the last transition there: the first version took the first
    noisy dip and could return delta_in > delta_out where r_ph is close to rin (C, 4 Nov)."""
    grid = np.geomspace(1e-9, 12.0, 480)
    vals = np.array([crossing_radius(cx, psi, rho_c, d, a, inc, n, tol) for d in grid])

    def bisect(lo, hi, target):
        for _ in range(iters):
            mid = np.sqrt(lo * hi)
            if crossing_radius(cx, psi, rho_c, mid, a, inc, n, tol) > target:
                hi = mid
            else:
                lo = mid
        return np.sqrt(lo * hi)

    above = vals > rout
    idx = np.nonzero(above[1:] & ~above[:-1])[0]
    if len(idx) == 0 and n == 1:
        return np.nan, np.nan   # inclined views: the n = 1 image can extend past the search window (counted)
    need(len(idx) >= 1, "SUBRING_BRACKET", f"n={n} psi={psi:.3f} target=rout")
    d_out = bisect(grid[idx[0]], grid[idx[0] + 1], rout)
    if photon_orbit_radius(a, inc, psi) >= rin:
        return 0.0, d_out
    below = np.nonzero((grid < d_out) & (vals <= rin))[0]
    if len(below) == 0:
        # The critical ray spirals onto the photon orbit from outside, so its n-th crossing lies above r_ph and
        # only approaches it as n grows. For small n that crossing can sit outside rin even when r_ph < rin:
        # the sub-ring then reaches the curve. Recorded as delta_in = 0 and counted by the caller.
        ABUTTING.append((n, float(psi)))
        return 0.0, d_out
    need(below[-1] + 1 < len(grid), "SUBRING_BRACKET", f"n={n} psi={psi:.3f} target=rin")
    d_in = bisect(grid[below[-1]], min(grid[below[-1] + 1], d_out), rin)
    need(0 <= d_in < d_out, "SUBRING_ORDER", f"n={n} psi={psi:.3f}")
    return d_in, d_out


def isco(a):
    z1 = 1 + (1 - a * a) ** (1 / 3) * ((1 + a) ** (1 / 3) + (1 - a) ** (1 / 3))
    z2 = np.sqrt(3 * a * a + z1 * z1)
    return 3 + z2 - np.sqrt((3 - z1) * (3 + z1 + 2 * z2))


# ---------------------------------------------------------------- emission and colour
T_PEAK = 6500.0     # display temperature scale (K): an authored choice; real disks are X-ray hot
TAU = 0.25          # optically thin layer weight per crossing; no absorption between crossings


def layer_rgb(rec: np.ndarray, rin: float, table) -> tuple[list, int]:
    """Per-layer linear sRGB from recorded crossings: each crossing in the disk emits a blackbody at T(r),
    observed as a blackbody at g T(r). Normalised so a g = 1 crossing at the hottest radius has Y = 1."""
    norm = 1.0 / color.blackbody_xyz([T_PEAK])[0, 1]
    rr = np.linspace(rin, 60, 20000)
    flux = (rin / rr) ** 3 * (1 - np.sqrt(rin / rr))
    fmax = flux.max()
    layers, negatives = [], 0
    for n in range(NREC):
        r = rec[..., 6 + 3 * n].astype(float)
        g = rec[..., 7 + 3 * n].astype(float)
        hit = g > 0
        T = np.zeros_like(r)
        F = np.where(hit, (rin / np.maximum(r, rin)) ** 3 * (1 - np.sqrt(rin / np.maximum(r, rin))), 0)
        T[hit] = T_PEAK * (F[hit] / fmax) ** 0.25
        rgb, neg = table(np.where(hit, g * T, 0.0))
        negatives += neg
        layers.append(rgb * TAU * norm * hit[..., None])
    return layers, negatives


CASES = {
    "schwarzschild": (0.0, 60.0),
    "kerr": (0.94, 68.0),
    "extreme": (0.99, 84.0),
}


def build(name, w, h, npsi, ndelta, tol=1e-9):
    a, deg = CASES[name]
    inc = np.deg2rad(deg)
    rin, rout = isco(a), 22.0
    out = ROOT / "cases" / name
    out.mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    rays = bank(w, h, a, inc, rin, rout, tol)
    t_bank = time.time() - t0
    cx, psi, rho, (al, be) = polar_curve(a, inc, npsi)
    half = ndelta // 2
    mag = np.geomspace(1e-6, 1.5, half)
    delta = np.concatenate([-mag[::-1], mag])
    t1 = time.time()
    ring = atlas(cx, psi, rho, delta, a, inc, rin, rout, tol)
    t_atlas = time.time() - t1
    table = color.Table()
    frames = []
    clipped = 0
    negatives_total = 0
    for label, rec in (("image", rays), ("ring", ring)):
        layers, negatives = layer_rgb(rec, rin, table)
        negatives_total += negatives
        for n, rgb in enumerate(layers):
            f = rgbm(rgb, out / f"{label}-n{n}.png")
            f.update({"layer": n, "kind": label})
            clipped += f["clipped_values"]
            frames.append(f)
    # rho_c(psi) at 24-bit precision for the shader (range 0..16 M): R,G,B = high, mid, low bytes.
    code = np.rint(np.clip(rho / 16.0, 0, 1) * (2 ** 24 - 1)).astype(np.uint32)
    curve_png = np.zeros((1, npsi, 4), np.uint8)
    curve_png[0, :, 0] = code >> 16
    curve_png[0, :, 1] = (code >> 8) & 255
    curve_png[0, :, 2] = code & 255
    curve_png[0, :, 3] = 255
    from common import publish_png
    cf = publish_png(curve_png, out / "curve.png")
    cf.update({"kind": "curve", "encoding": "rho_c(psi)/16 M as 24-bit RGB, psi = (k+0.5) 2pi/npsi", "time": 0, "clipped_values": 0})
    frames.append(cf)
    rays.tofile(out / "image.f32")
    status = rays[..., 0]
    meta = {"center_alpha": float(cx), "npsi": npsi, "ndelta": ndelta, "delta_min": 1e-6, "delta_max": 1.5,
            "delta_layout": "first half: -1.5..-1e-6 (geometric, mirrored); second half: +1e-6..+1.5 (geometric)",
            "span": SPAN, "width": w, "height": h, "rin": rin, "rout": rout}
    write_json(out / "geometry.json", meta)
    return {"a": a, "deg": deg, "inc": inc, "rin": rin, "rout": rout, "rays": rays, "ring": ring, "cx": cx, "psi": psi, "rho": rho,
            "frames": frames, "clipped": clipped, "negatives": negatives_total, "t_bank": t_bank, "t_atlas": t_atlas, "out": out,
            "status": status, "meta": meta}


def witnesses_for(name, b, n_edge=72, n_ring=24):
    a, inc, cx, rin, rout = b["a"], b["inc"], b["cx"], b["rin"], b["rout"]
    rays, ring = b["rays"], b["ring"]
    tests = []
    st = np.concatenate([rays[..., 0].ravel(), ring[..., 0].ravel()])
    tests.append(witness("unresolved rays", np.count_nonzero(st == 3), 0))
    res = max(float(rays[..., 1].max()), float(ring[..., 1].max()))
    tests.append(witness("separated null constraint normalized residual", res, 2e-5))
    # Analytic critical curve vs the bisected capture edge (disk disabled).
    psis = (np.arange(n_edge) + 0.5) * 2 * np.pi / n_edge
    rho_e = np.interp(psis, b["psi"], b["rho"], period=2 * np.pi)
    devs, unres = [], 0
    for p, rc in zip(psis, rho_e):
        d, width, u = capture_edge(cx, p, rc, a, inc)
        unres += u
        devs.append(abs(d) + width / 2)
    tests.append(witness("analytic critical curve max deviation of the bisected shadow edge (M)", max(devs), 2e-4))
    # Sub-ring widths at two integration tolerances.
    psir = (np.arange(n_ring) + 0.5) * 2 * np.pi / n_ring
    rho_r = np.interp(psir, b["psi"], b["rho"], period=2 * np.pi)
    widths = {9: {1: [], 2: [], 3: []}, 11: {1: [], 2: [], 3: []}}
    for e, tol in ((9, 1e-9), (11, 1e-11)):
        for p, rc in zip(psir, rho_r):
            for n in (1, 2, 3):
                di, do = subring_edges(cx, p, rc, a, inc, n, rin, rout, tol)
                widths[e][n].append(do - di)
    rel = max(abs(x - y) / y for n in (2, 3) for x, y in zip(widths[9][n], widths[11][n]))
    tests.append(witness("sub-ring width change between integration tolerances 1e-9 and 1e-11 (n = 2, 3; relative)", rel, 1e-3))
    n1_unbounded = int(np.count_nonzero(~np.isfinite(widths[11][1])))
    below_floor = sorted(set(ABUTTING)); ABUTTING.clear()
    ratios = {f"w{n + 1}/w{n}": [float(y / x) for x, y in zip(widths[11][n], widths[11][n + 1]) if np.isfinite(x)] for n in (1, 2)}
    if a == 0.0:
        r23 = np.array(ratios["w3/w2"])
        tests.append(witness("Schwarzschild sub-ring demagnification w3/w2 vs e^-pi, max relative error", float(np.max(np.abs(r23 / np.exp(-np.pi) - 1))), 0.15))
    err, xy = color.chromaticity_witness()
    tests.append(witness("Planckian chromaticity vs Kang et al. 2002, max xy distance (2000 to 20000 K)", err, 0.003))
    tests.append(witness("Illuminant A (2856 K blackbody) chromaticity vs the CIE published value, xy distance", color.illuminant_a_witness(), 2e-4))
    tests.append(witness("radiance encoding clipping", b["clipped"], 0))
    metrics = [{"time": 0, "a": a, "inclination_degrees": b["deg"], "isco": rin, "disk_rays_n0": int(np.count_nonzero(rays[..., 7] > 0)),
                "captured_pixels": int(np.count_nonzero(rays[..., 0] == 0)), "crossing_cap_pixels": int(np.count_nonzero(rays[..., 0] == 4)),
                "max_constraint": res, "edge_unresolved_bisections": unres, "edge_deviation_median": float(np.median(devs)),
                "subring_width_median": {str(n): float(np.nanmedian(widths[11][n])) for n in (1, 2, 3)},
                "n1_unbounded_angles": n1_unbounded, "subrings_reaching_curve_although_rph_below_rin": [[n, round(p, 4)] for n, p in below_floor], "subring_widths_tol1e-11": {str(n): [float(x) for x in widths[11][n]] for n in (1, 2, 3)},
                "subring_ratio_median": {k: float(np.median(v)) for k, v in ratios.items()}, "e_minus_pi": float(np.exp(-np.pi)),
                "out_of_gamut_values_clamped": b["negatives"], "planck_xy": xy,
                "build_seconds": {"image": b["t_bank"], "ring_atlas": b["t_atlas"]}}]
    return tests, metrics


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--width", type=int, default=1600)
    p.add_argument("--height", type=int, default=1000)
    p.add_argument("--npsi", type=int, default=2048)
    p.add_argument("--ndelta", type=int, default=1024)
    p.add_argument("--cases", nargs="*", default=list(CASES))
    a = p.parse_args()
    for name in a.cases:
        b = build(name, a.width, a.height, a.npsi, a.ndelta)
        tests, metrics = witnesses_for(name, b)
        title = {"schwarzschild": "Schwarzschild reference ring", "kerr": "Rapid Kerr ring (a = 0.94, 68°)", "extreme": "Near-extremal edge-on ring (a = 0.99, 84°)"}[name]
        save_case(name, {"title": title,
            "equation": "null Kerr geodesics in Mino time (u = 1/r, z = cos theta); optically thin equatorial disk, every crossing kept",
            "domain": {"shape": [a.width, a.height], "units": "G=M=c=1; screen impact coordinates in GM/c^2", "boundary": "observer at r = 200; disk rin = ISCO to rout = 22"},
            "parameters": {"spin": b["a"], "inclination_degrees": b["deg"], "isco": b["rin"], "outer_disk": b["rout"], "observer_r": R0, "screen_width": SPAN,
                           "tolerance": 1e-9, "crossings_recorded": NREC, "display_temperature_K": T_PEAK, "layer_weight": TAU},
            "display": {"color": "blackbody at g T(r) through the CIE 1931 2-degree table, linear sRGB (D65 primaries), RGBM16", "cie_table": {"file": "sources/CIE_xyz_1931_2deg.csv", "sha256": color.CIE_SHA256, "doi": "10.25039/CIE.DS.xvudnb9b", "licence": "CC BY-SA 4.0"}, "geometry": "geometry.json", "probe": "image.f32"},
            "limits": ["Optically thin equatorial emission with a constant layer weight; no absorption, scattering, polarization or GRMHD.",
                       "Display temperature scale is authored (6,500 K peak); real accretion disks are far hotter; colour is bound to g, the scale is not.",
                       "Crossings beyond n = 3 are not traced (their contribution is below e^-4pi of n = 0).",
                       "The ring atlas is sampled; display interpolation between samples is not a computed ray.",
                       "Observer at finite r = 200 with impact-parameter screen, as in the Scientific Loom."]},
            b["frames"], metrics, tests)
        print(name, [(t["id"][:40], t["pass"], round(t["observed"], 8)) for t in tests], metrics[0]["build_seconds"], flush=True)


if __name__ == "__main__":
    main()
