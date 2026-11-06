"""Riemannian geometry of the emotional field, written independently of the original page.

The page (src/math-core.js, verbatim from the original) uses two shortcuts that are only valid for a
conformal metric g = lambda^2 (dx^2 + dz^2):
  K = -Laplacian(ln lambda) / lambda^2, and
  geodesics as a unit Euclidean tangent T with dT/ds = grad(ln lambda) - (grad(ln lambda) . T) T.
This module checks both without assuming them (Loom law 25: independent witnesses need independent
assumptions):
  * curvature from Brioschi's formula for a general metric (E, F, G), differentiated symbolically by sympy;
  * geodesics from the full geodesic equation x'' = -Gamma(x', x') with Christoffel symbols of the general
    metric, integrated in its affine parameter by DOP853;
  * two exact references: Clairaut's invariant for a rotationally symmetric source, and the Gauss-Bonnet
    flux identity  integral(K dA_g) = -contour integral(d ln(lambda)/dn ds)  on the drawn square.
The field itself (sources, fold) is the original's arithmetic, ported line by line from src/field.js.
"""
from __future__ import annotations

import math

import numpy as np
import sympy as sp
from scipy.integrate import solve_ivp

PRESETS = [
    dict(name="Reverie", energy=.7, breath=.65, fold=.65, speed=.65, phase=0.0),
    dict(name="Euphoria", energy=1.0, breath=1.05, fold=.9, speed=.85, phase=1.8),
    dict(name="Catharsis", energy=1.25, breath=.9, fold=1.35, speed=.8, phase=3.8),
    dict(name="Stillness", energy=.30, breath=.35, fold=.25, speed=.3, phase=5.5),
]
EXTENT = 11.2          # the drawn square is [-11.2, 11.2]^2 (the original's mesh)


def sources(t: float, mood: int) -> list[dict]:
    """The seven sources of a settled mood at time t (src/field.js updateSources, settled state)."""
    p = PRESETS[mood]
    phase, energy, breath = p["phase"], p["energy"], p["breath"]
    out = []
    for i in range(7):
        a = i * 2.39996 + phase * .17
        rad = .6 if i == 0 else 2.5 + (i % 3) * 1.6
        q = t * (.19 + i * .013) + i * 1.73
        latent = math.sin(q) * math.cos(q * .67 + phase)
        x = math.cos(a) * rad + math.sin(t * .12 + i * 1.5) * (.25 + energy * .6) + math.sin(phase + i) * .5
        z = math.sin(a) * rad + math.cos(t * .10 + i * .9) * (.25 + energy * .6)
        br = 1 + breath * (.27 * math.sin(q * .8) + .17 * math.sin(q * 1.31 + i))
        sx = (1.05 + (i % 3) * .38) * br
        sz = sx * (.72 + .29 * math.sin(q * .37 + i) ** 2)
        amp = (2.8 + (i % 4) * 1.1) * (0.6 + energy * .7) * (1 + breath * .34 * math.sin(q * .91 + 1.))
        angle = a + t * .048 + latent * .3
        out.append(dict(x=x, z=z, amp=amp, sx=sx, sz=sz, angle=angle))
    return out


def fold(x, z, t: float, mood: int):
    """The rotating R^4 fold (display height only), src/field.js foldCPU."""
    qx, qy, qz, qw = x * .25, z * .25, np.sin(x * .19 + t * .13), np.cos(z * .21 - t * .11)
    a = t * .12
    c, s = math.cos(a), math.sin(a)
    xx, ww = c * qx - s * qw, s * qx + c * qw
    c, s = math.cos(a * .73), math.sin(a * .73)
    yy, zz = c * qy - s * qz, s * qy + c * qz
    den = 1.8 - .23 * ww
    vx, vy, vz = xx / den, yy / den, zz / den
    return PRESETS[mood]["fold"] * (.65 * np.sin(vx * 2.6 + vz) * np.cos(vy * 2.2) + .24 * np.sin(vz * 3.7 + vy))


def field(x, z, src):
    """lambda, grad(lambda), Laplacian(lambda) of the conformal factor (vectorised)."""
    x, z = np.asarray(x, float), np.asarray(z, float)
    lam, gx, gz, lap = np.ones_like(x), np.zeros_like(x), np.zeros_like(x), np.zeros_like(x)
    for s in src:
        c, sn = math.cos(s["angle"]), math.sin(s["angle"])
        ix, iz = 1 / s["sx"] ** 2, 1 / s["sz"] ** 2
        axx, axz, azz = c * c * ix + sn * sn * iz, c * sn * (ix - iz), sn * sn * ix + c * c * iz
        dx, dz = x - s["x"], z - s["z"]
        qx, qz = axx * dx + axz * dz, axz * dx + azz * dz
        v = s["amp"] * np.exp(-.5 * (dx * qx + dz * qz))
        lam = lam + v
        gx, gz = gx - v * qx, gz - v * qz
        lap = lap + v * (qx * qx + qz * qz - (ix + iz))
    return lam, gx, gz, lap


def curvature_conformal(x, z, src):
    """The page's formula: K = -(lap/lambda - |grad|^2/lambda^2)/lambda^2."""
    lam, gx, gz, lap = field(x, z, src)
    return -(lap / lam - (gx * gx + gz * gz) / lam ** 2) / lam ** 2


def height(x, z, t: float, mood: int, src=None):
    src = sources(t, mood) if src is None else src
    lam = field(x, z, src)[0]
    return -1.72 * np.log(lam) + fold(x, z, t, mood)


# ---------------------------------------------------------------- symbolic, general-metric references
X, Z = sp.symbols("x z", real=True)


def lambda_symbolic(src):
    lam = sp.Integer(1)
    for s in src:
        c, sn = sp.Float(math.cos(s["angle"]), 30), sp.Float(math.sin(s["angle"]), 30)
        a = c * (X - s["x"]) + sn * (Z - s["z"])
        b = -sn * (X - s["x"]) + c * (Z - s["z"])
        lam += s["amp"] * sp.exp(-sp.Rational(1, 2) * (a ** 2 / s["sx"] ** 2 + b ** 2 / s["sz"] ** 2))
    return lam


def _derivs(expr, names):
    """Symbolic partial derivatives of expr, each compiled separately (with common subexpressions) to numpy."""
    table = {"": expr, "u": sp.diff(expr, X), "v": sp.diff(expr, Z), "uu": sp.diff(expr, X, 2),
             "vv": sp.diff(expr, Z, 2), "uv": sp.diff(expr, X, Z)}
    return {k: sp.lambdify((X, Z), table[k], "numpy", cse=True) for k in names}


def brioschi_numeric(E, F, G, x, z):
    """Brioschi's formula for a general first fundamental form (E, F, G), u = x, v = z, evaluated from
    compiled symbolic derivatives. No conformal shortcut is used: E, F and G enter separately."""
    e = {k: np.broadcast_to(f(x, z), np.shape(x)).astype(float) for k, f in E.items()}
    f_ = {k: np.broadcast_to(f(x, z), np.shape(x)).astype(float) for k, f in F.items()}
    g = {k: np.broadcast_to(f(x, z), np.shape(x)).astype(float) for k, f in G.items()}
    a11 = -e["vv"] / 2 + f_["uv"] - g["uu"] / 2
    m1 = np.stack([np.stack([a11, e["u"] / 2, f_["u"] - e["v"] / 2], -1),
                   np.stack([f_["v"] - g["u"] / 2, e[""], f_[""]], -1),
                   np.stack([g["v"] / 2, f_[""], g[""]], -1)], -2)
    m2 = np.stack([np.stack([np.zeros_like(a11), e["v"] / 2, g["u"] / 2], -1),
                   np.stack([e["v"] / 2, e[""], f_[""]], -1),
                   np.stack([g["u"] / 2, f_[""], g[""]], -1)], -2)
    return (np.linalg.det(m1) - np.linalg.det(m2)) / (e[""] * g[""] - f_[""] ** 2) ** 2


def curvature_general(src):
    lam = lambda_symbolic(src)
    names = ["", "u", "v", "uu", "vv", "uv"]
    E, F, G = _derivs(lam ** 2, names), _derivs(sp.Integer(0) * X, names), _derivs(lam ** 2, names)
    return lambda x, z: brioschi_numeric(E, F, G, x, z)


def christoffel(src):
    """Christoffel symbols from the general formula Gamma^k_ij = 1/2 g^kl (d_i g_jl + d_j g_il - d_l g_ij),
    with the metric components and their first derivatives differentiated symbolically and the inverse metric
    taken numerically. Nothing assumes the metric is conformal. Returns [G^k_ij] in the order k, i, j."""
    lam = lambda_symbolic(src)
    comps = {(0, 0): _derivs(lam ** 2, ["", "u", "v"]), (1, 1): _derivs(lam ** 2, ["", "u", "v"])}

    def gam(x, z):
        g = np.zeros((2, 2)); dg = np.zeros((2, 2, 2))      # dg[l, i, j] = d_l g_ij
        for (i, j), f in comps.items():
            g[i, j] = f[""](x, z); dg[0, i, j] = f["u"](x, z); dg[1, i, j] = f["v"](x, z)
        gi = np.linalg.inv(g)
        out = []
        for k in range(2):
            for i in range(2):
                for j in range(2):
                    out.append(float(sum(gi[k, l] * (dg[i, j, l] + dg[j, i, l] - dg[l, i, j]) for l in range(2)) / 2))
        return out
    return gam


def geodesic_affine(gam, x0, z0, theta, length, n_out=4001, rtol=1e-12, atol=1e-13):
    """The geodesic equation in the metric's affine parameter, from unit Euclidean direction theta.
    Returns the polyline and its Euclidean arc length (the page's parameter), for comparison as curves."""
    def rhs(_, y):
        x, z, u, w, _ = y
        G = gam(x, z)
        du = -(G[0] * u * u + 2 * G[1] * u * w + G[3] * w * w)
        dw = -(G[4] * u * u + 2 * G[5] * u * w + G[7] * w * w)
        return [u, w, du, dw, math.hypot(u, w)]
    span = length * 40
    hit = lambda t, y: y[4] - length
    hit.terminal, hit.direction = True, 1
    sol = solve_ivp(rhs, (0, span), [x0, z0, math.cos(theta), math.sin(theta), 0.0], method="DOP853",
                    rtol=rtol, atol=atol, events=hit, dense_output=True)
    t_end = sol.t_events[0][0] if len(sol.t_events[0]) else sol.t[-1]
    ts = np.linspace(0, t_end, n_out)
    y = sol.sol(ts)
    return y[0], y[1], y[4]


def geodesic_unit_tangent(src, x0, z0, theta, length, n_out=4001, rtol=1e-12, atol=1e-13):
    """The page's formulation (Euclidean arc length, unit tangent), integrated to tolerance: the reference
    the page's fixed-step RK4 is measured against."""
    def rhs(_, y):
        x, z, tx, tz = y
        lam, gx, gz, _ = field(np.array(x), np.array(z), src)
        ax, az = float(gx / lam), float(gz / lam)
        d = ax * tx + az * tz
        return [tx, tz, ax - d * tx, az - d * tz]
    ss = np.linspace(0, length, n_out)
    sol = solve_ivp(rhs, (0, length), [x0, z0, math.cos(theta), math.sin(theta)], method="DOP853",
                    rtol=rtol, atol=atol, t_eval=ss, dense_output=True)
    return sol


def gauss_bonnet_residual(src, n=480):
    """integral over the drawn square of K dA_g (= K lambda^2 dx dz) plus the boundary flux of ln(lambda).
    Zero exactly (divergence theorem on -Laplacian(ln lambda)); Gauss-Legendre on both sides."""
    xg, wg = np.polynomial.legendre.leggauss(n)
    xs, ws = xg * EXTENT, wg * EXTENT
    XX, ZZ = np.meshgrid(xs, xs, indexing="ij")
    lam, gx, gz, lap = field(XX, ZZ, src)
    K = -(lap / lam - (gx * gx + gz * gz) / lam ** 2) / lam ** 2
    area = float(np.einsum("i,j,ij->", ws, ws, K * lam ** 2))
    flux = 0.0
    for side, (px, pz, nx, nz) in enumerate([(EXTENT, xs, 1, 0), (-EXTENT, xs, -1, 0), (xs, EXTENT, 0, 1), (xs, -EXTENT, 0, -1)]):
        px, pz = np.broadcast_to(px, xs.shape), np.broadcast_to(pz, xs.shape)
        l, a, b, _ = field(px, pz, src)
        flux += float(np.sum(ws * (a * nx + b * nz) / l))
    return area, flux, area + flux


def curve_distance(points: np.ndarray, curve: np.ndarray) -> np.ndarray:
    """Distance from each point to a polyline, measured to its segments (not its vertices: a vertex
    distance measures the sampling, which the first formulation check did, 5 Nov)."""
    from scipy.spatial import cKDTree
    _, idx = cKDTree(curve).query(points)
    best = np.full(len(points), np.inf)
    for off in (-1, 0):
        a = np.clip(idx + off, 0, len(curve) - 2)
        A, B = curve[a], curve[a + 1]
        AB = B - A
        t = np.clip(np.einsum("ij,ij->i", points - A, AB) / np.maximum(np.einsum("ij,ij->i", AB, AB), 1e-300), 0, 1)
        d = np.hypot(*(points - (A + t[:, None] * AB)).T)
        best = np.minimum(best, d)
    return best
