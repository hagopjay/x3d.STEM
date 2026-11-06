"""Manifold of Emotion builder: witnesses for the Riemannian structure, and the data the X3D scene embeds.

  python3 -E -s tools/manifold.py          # about a minute

The field is the original page's (reference/Manifold-of-Emotion.html): g = lambda^2 (dx^2 + dz^2) on the
plane, lambda = 1 + seven rotated anisotropic Gaussians that breathe and drift with time. The page computes
curvature and geodesics with conformal shortcuts (src/math-core.js, verbatim); tools/geometry.py checks them
with general-metric formulas, and tools/parity.mjs runs the page's own JavaScript under Node.

Limits declared before the first build, from the exploration on 6 Nov (t = 3.7, four settled moods):
  sources and heights, Python against the page's JS: <= 1.8e-15     -> limit 1e-12
  curvature, page formula against Brioschi (general metric): 4.1e-15 relative -> 1e-12
  Gauss-Bonnet flux identity on the drawn square: residual <= 2.8e-13 (integral K dA up to 1.94) -> 1e-10
  geodesic formulation (unit tangent) against the affine geodesic equation: <= 9.6e-9 at 200 001 samples
     (the first check measured the sampling: 9.7e-3 at 6 001 vertex samples) -> 1e-7
  page RK4 against the reference: order 3.98 to 4.00; error at the original's step 0.13: <= 2.15e-3;
     at this page's step 0.065: <= 1.37e-4 -> limit 2e-4 at the page's step, order within 0.1 of 4
  Clairaut invariant along the reference, one round source: drift <= 1.8e-11 -> 1e-9
The baked rest heights (the X3D file's ElevationGrid, 4 decimals) are checked when the scene is written.
"""
from __future__ import annotations

import json
import math
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "tools"))
sys.path.insert(0, str(ROOT.parents[1] / "lib"))

import numpy as np                                                   # noqa: E402

import geometry as G                                                 # noqa: E402
from stemkit.core import Study, need, sha, witness, write_json      # noqa: E402

TIMES = (3.7, 41.3, 177.9)          # the original's start, and two later moments of the drifting field
PAGE_STEP, PAGE_COUNT = .065, 400   # this page: half the original's step, same length (26 units)
REST = dict(time=3.7, mood=0, grid=513)
DEPENDENCIES = ["tools/geometry.py", "tools/parity.mjs", "src/math-core.js", "src/field.js"]


def node_parity(t: float, grid: int = 161) -> dict:
    r = subprocess.run(["node", str(ROOT / "tools/parity.mjs"), repr(t), str(grid)], capture_output=True, text=True, check=True)
    return json.loads(r.stdout)


def pts(a) -> np.ndarray:
    return np.asarray(a, float).reshape(-1, 2)


def lcg_seeds(n: int = 900) -> np.ndarray:
    """The original's particle seeds: randSeed = 74631, an LCG (1664525, 1013904223) mod 2^32."""
    seed, out = 74631, np.zeros((n, 4))
    def rnd():
        nonlocal seed
        seed = (seed * 1664525 + 1013904223) % 2 ** 32
        return seed / 4294967296
    for i in range(n):
        out[i] = [(rnd() * 2 - 1) * 11, (rnd() * 2 - 1) * 11, rnd(), rnd()]
    return out


def induced_vs_metric(t: float, mood: int) -> float:
    """Display honesty, reported: the drawn surface (height -1.72 ln lambda + fold) has its own metric
    I + grad h grad h^T. How far does its geodesic stray from g's, from the same start and direction?"""
    import sympy as sp
    src = G.sources(t, mood)
    lam = G.lambda_symbolic(src)
    p = G.PRESETS[mood]
    x, z = G.X, G.Z
    qx, qy, qz, qw = x * .25, z * .25, sp.sin(x * .19 + t * .13), sp.cos(z * .21 - t * .11)
    a = t * .12
    c, s = math.cos(a), math.sin(a)
    xx, ww = c * qx - s * qw, s * qx + c * qw
    c, s = math.cos(a * .73), math.sin(a * .73)
    yy, zz = c * qy - s * qz, s * qy + c * qz
    den = 1.8 - .23 * ww
    vx, vy, vz = xx / den, yy / den, zz / den
    h = -1.72 * sp.log(lam) + p["fold"] * (.65 * sp.sin(vx * 2.6 + vz) * sp.cos(vy * 2.2) + .24 * sp.sin(vz * 3.7 + vy))
    hx, hz = sp.diff(h, x), sp.diff(h, z)
    comps = {(0, 0): G._derivs(1 + hx ** 2, ["", "u", "v"]), (0, 1): G._derivs(hx * hz, ["", "u", "v"]),
             (1, 1): G._derivs(1 + hz ** 2, ["", "u", "v"])}

    def gam(px, pz):
        g, dg = np.zeros((2, 2)), np.zeros((2, 2, 2))
        for (i, j), f in comps.items():
            for (ii, jj) in {(i, j), (j, i)}:
                g[ii, jj] = f[""](px, pz); dg[0, ii, jj] = f["u"](px, pz); dg[1, ii, jj] = f["v"](px, pz)
        gi = np.linalg.inv(g)
        return [float(sum(gi[k, l] * (dg[i, j, l] + dg[j, i, l] - dg[l, i, j]) for l in range(2)) / 2)
                for k in range(2) for i in range(2) for j in range(2)]
    worst = 0.0
    for z0 in (-6.0, -2.0, 2.0, 6.0):
        L = 20.0
        ref = G.geodesic_unit_tangent(src, -10.5, z0, 0.0, L, n_out=2001)
        ax, az, _ = G.geodesic_affine(gam, -10.5, z0, 0.0, L, n_out=20001)
        worst = max(worst, float(np.max(G.curve_distance(np.c_[ref.y[0], ref.y[1]][:1900], np.c_[ax, az]))))
    return worst


def main() -> None:
    st = Study(ROOT, "manifold", "tools/manifold.py")
    W, M = [], []
    par_src = par_h = par_k = 0.0
    k_rel = gb_res = 0.0
    gb_total = []
    form = 0.0
    rk_err_page = rk_err_orig = 0.0
    orders = []
    for t in TIMES:
        P = node_parity(t)
        N, E = P["grid"], P["extent"]
        xs = (np.arange(N) / (N - 1) * 2 - 1) * E
        XX, ZZ = np.meshgrid(xs, xs, indexing="xy")
        for Md in P["moods"]:
            m = Md["mood"]
            src = G.sources(t, m)
            par_src = max(par_src, max(abs(a[k] - b[k]) for a, b in zip(src, Md["sources"]) for k in a))
            par_h = max(par_h, float(np.max(np.abs(G.height(XX, ZZ, t, m, src) - np.array(Md["heights"]).reshape(N, N)))))
            par_k = max(par_k, max(abs(k["K"] - float(G.curvature_conformal(np.array(k["x"]), np.array(k["z"]), src))) for k in Md["K"]))
            rng = np.random.default_rng(int(t * 100) + m)
            px, pz = rng.uniform(-E, E, 3000), rng.uniform(-E, E, 3000)
            Kc, Kb = G.curvature_conformal(px, pz, src), G.curvature_general(src)(px, pz)
            k_rel = max(k_rel, float(np.max(np.abs(Kc - Kb)) / np.max(np.abs(Kc))))
            area, flux, res = G.gauss_bonnet_residual(src, 240)
            gb_res = max(gb_res, abs(res)); gb_total.append(area)
            if t == TIMES[0]:
                gam = G.christoffel(src)
                for tr in Md["traces"][::3]:
                    p_h = pts(tr["h"])
                    if len(p_h) < 3:
                        continue
                    L = 0.13 * (len(p_h) - 1)
                    ref = G.geodesic_unit_tangent(src, -10.5, tr["z"], tr["theta"], L, n_out=len(p_h))
                    ax, az, _ = G.geodesic_affine(gam, -10.5, tr["z"], tr["theta"], L * 0.999, n_out=200001)
                    form = max(form, float(np.max(G.curve_distance(np.c_[ref.y[0], ref.y[1]][: int(len(p_h) * 0.995)], np.c_[ax, az]))))
                    e = {}
                    for k, step in (("h", .13), ("h2", .065), ("h4", .0325)):
                        p = pts(tr[k]); s_ = np.arange(len(p)) * step
                        keep = s_ <= L + 1e-12            # never compare where the reference is extrapolated
                        r = ref.sol(s_[keep])
                        e[k] = float(np.max(np.hypot(p[keep, 0] - r[0], p[keep, 1] - r[1])))
                    rk_err_orig, rk_err_page = max(rk_err_orig, e["h"]), max(rk_err_page, e["h2"])
                    if e["h4"] > 1e-9:                    # an order needs errors above the reference's rounding
                        orders += [math.log2(e["h"] / e["h2"]), math.log2(e["h2"] / e["h4"])]
                # Clairaut: one round source; the reference keeps lambda r sin(psi) to rounding
                if m == 0:
                    iso = Md["iso"]
                    clair = 0.0
                    for tr in Md["isoTraces"]:
                        ref = G.geodesic_unit_tangent(iso, -10, tr["b"], 0.0, 20.0, n_out=2001)
                        x, z, tx, tz = ref.y
                        lam = 1 + iso[0]["amp"] * np.exp(-.5 * (x * x + z * z) / iso[0]["sx"] ** 2)
                        clair = max(clair, float(np.ptp(lam * (x * tz - z * tx))))
    W += [witness("sources_match_page_js", par_src, 1e-12, note="the seven sources, Python against the page's JS under Node, 3 times x 4 moods"),
          witness("heights_match_page_js", par_h, 1e-12, note="-1.72 ln(lambda) + fold on a 161^2 grid"),
          witness("curvature_matches_page_js", par_k, 1e-12),
          witness("curvature_general_metric", k_rel, 1e-12, note="page's conformal K against Brioschi's general formula (sympy), relative to max |K|"),
          witness("gauss_bonnet_flux_identity", gb_res, 1e-10, note="integral of K dA_g plus the boundary flux of ln(lambda) on the drawn square"),
          witness("geodesic_formulation", form, 1e-7, note="page's unit-tangent ODE against the affine geodesic equation with general Christoffel symbols, as curves"),
          witness("geodesic_rk4_error_page_step", rk_err_page, 2e-4, note=f"page step {PAGE_STEP}; the original's step 0.13 gives {rk_err_orig:.2e}"),
          witness("geodesic_rk4_order", max(abs(o - 4) for o in orders), 0.1, note=f"observed orders {min(orders):.3f} to {max(orders):.3f} over {len(orders)} trace pairs"),
          witness("clairaut_reference", clair, 1e-9, note="lambda r sin(psi) along the reference for one round source")]
    M += [{"id": "integral_K_dA_drawn_square", "value": [round(v, 6) for v in gb_total], "note": "total curvature of the drawn square; not zero because the field does not vanish at its edge"},
          {"id": "geodesic_error_original_step", "value": rk_err_orig}]

    # display honesty (reported, not gated: it describes the picture, not a defect)
    sep = induced_vs_metric(3.7, 0)
    M.append({"id": "drawn_surface_geodesic_separation", "value": round(sep, 3),
              "note": "the paths are geodesics of g; the drawn surface's own geodesics from the same starts stray this far within 20 units"})

    # particle seeds: the original's LCG, ported; parity against the page's arithmetic is exact by construction
    seeds = lcg_seeds()
    js = subprocess.run(["node", "-e", "let s=74631;const r=()=>{s=(Math.imul(s,1664525)+1013904223)>>>0;return s/4294967296};const o=[];for(let i=0;i<900;i++)o.push((r()*2-1)*11,(r()*2-1)*11,r(),r());console.log(JSON.stringify(o))"],
                        capture_output=True, text=True, check=True)
    W.append(witness("particle_seeds_match_page_js", float(np.max(np.abs(np.array(json.loads(js.stdout)).reshape(-1, 4) - seeds))), 0.0))

    # rest heights for the scene's ElevationGrid: what any X3D browser shows if it runs no shader
    n = REST["grid"]
    xs = (np.arange(n) / (n - 1) * 2 - 1) * G.EXTENT
    XX, ZZ = np.meshgrid(xs, xs, indexing="xy")
    rest = G.height(XX, ZZ, REST["time"], REST["mood"]).astype(np.float64)
    frames = [st.publish_deflate(rest.astype("<f4").tobytes(), ROOT / "cases/rest/heights.f32", shape=[n, n], dtype="<f4",
                                 time=REST["time"], quantization_max=5e-5,
                                 note="rest heights, Reverie at t = 3.7, x then z, row j = z index; the scene writes them to 4 decimals (5e-5)")]
    write_json(ROOT / "cases/rest/particles.json", {"seeds": seeds.round(7).tolist()})
    meta = {"title": "Manifold of Emotion: the field, its curvature and its geodesics",
            "equation": "g = lambda^2 (dx^2 + dz^2), lambda = 1 + sum_i a_i exp(-1/2 d^T A_i d); K = -Laplacian(ln lambda)/lambda^2; geodesics dT/ds = grad ln lambda - (grad ln lambda . T) T",
            "domain": {"shape": [n, n], "units": "the original page's scene units; the drawn square is [-11.2, 11.2]^2", "extent": G.EXTENT},
            "parameters": {"moods": [p["name"] for p in G.PRESETS], "times": list(TIMES), "page_step": PAGE_STEP, "page_count": PAGE_COUNT,
                           "traces": 30, "rest": REST},
            "limits": ["An artistic model: the sources, their breathing and the four moods are authored (label Authored), not measurements of anyone's emotions.",
                       "Geodesics are traced in snapshots of a metric that changes with time (a frozen field), not as spacetime geodesics.",
                       "The drawn height -1.72 ln(lambda) + fold + ripples is a picture of the metric, not an isometric embedding: its own geodesics stray up to the reported separation from those of g.",
                       "Curvature, Gauss-Bonnet and geodesics are checked on the drawn square only, at three times in four settled moods.",
                       "Limits were declared in tools/manifold.py's docstring before the first build."],
            "rest": REST,
            "dependencies": {d: sha((ROOT / d).read_bytes()) for d in DEPENDENCIES},
            "particles_sha256": sha((ROOT / "cases/rest/particles.json").read_bytes())}
    path = st.save_case("rest", meta, frames, M, W)
    bad = [w["id"] for w in W if not w["pass"]]
    for w in W:
        print(f"{'ok ' if w['pass'] else 'RED'} {w['id']:34s} {w['observed']:.3e}  (limit {w['limit']:.0e})")
    for m_ in M:
        print("    ", m_["id"], m_["value"])
    need(not bad, "WITNESS_RED", ", ".join(bad))
    print("case:", path.relative_to(ROOT))


if __name__ == "__main__":
    main()
