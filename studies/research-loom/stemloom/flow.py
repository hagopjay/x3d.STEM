"""A checked, steady ABC velocity field and saved particle trajectories.

The field is an analytic periodic benchmark, not a measured fluid or a CFD
solution.  Its saved trajectories are numerical; their error is measured with
a different integrator.  Tube radii and lighting belong to appearance.
"""
from __future__ import annotations

from functools import lru_cache
from math import pi

import numpy as np
from scipy.integrate import solve_ivp


PRESETS = {
    "default": {"title": "Braids in a steady field", "description": "Balanced ABC coefficients: complicated paths in a velocity field that never changes."},
    "integrable": {"title": "An exact straight-line control", "description": "Set B=C=0: each particle keeps z and has an exactly constant velocity."},
    "anisotropic": {"title": "Change the braid", "description": "Unequal ABC coefficients reorganize the streamlines without changing the divergence identity."},
}

_COEFFICIENTS = {"default": (1., 1., 1.), "integrable": (1., 0., 0.),
                 "anisotropic": (1.4, .7, .9)}
_PALETTE = np.array([[.24, .10, .48], [.14, .38, .67], [.09, .65, .67],
                     [.48, .82, .47], [.98, .81, .27]])
_QUIET = [.12, .23, .31]


def velocity(position, coefficients=(1., 1., 1.)):
    """Vectorized ABC velocity, using right-handed mathematical x,y,z."""
    q = np.asarray(position, dtype=float)
    a, b, c = coefficients
    x, y, z = np.moveaxis(q, -1, 0)
    return np.stack((a*np.sin(z)+c*np.cos(y), b*np.sin(x)+a*np.cos(z),
                     c*np.sin(y)+b*np.cos(x)), axis=-1)


def rk4(seeds, coefficients, duration=6., step=.01):
    """Fixed-step RK4 on unwrapped periodic coordinates; saves every step."""
    steps = int(round(duration/step))
    if steps < 1 or abs(steps*step-duration) > 1e-10:
        raise ValueError("duration must contain a positive integer number of steps")
    state = np.asarray(seeds, dtype=float).copy()
    if state.ndim != 2 or state.shape[1] != 3 or not np.isfinite(state).all():
        raise ValueError("seeds must be a finite N by 3 array")
    result = np.empty((steps+1, len(state), 3))
    result[0] = state
    for j in range(steps):
        k1 = velocity(state, coefficients)
        k2 = velocity(state+step*k1/2, coefficients)
        k3 = velocity(state+step*k2/2, coefficients)
        k4 = velocity(state+step*k3, coefficients)
        state += step*(k1+2*k2+2*k3+k4)/6
        result[j+1] = state
    return np.linspace(0, duration, steps+1), result


def _wrap(q):
    return (np.asarray(q)+pi) % (2*pi)-pi


def split_periodic_polyline(positions):
    """Clip a computed polyline into periodic cells without long wrap jumps.

    Boundary intersections are geometric linear clipping of the saved
    polyline, not newly integrated particle states.  Each returned segment
    stays in [-pi,pi]^3 and retains at least two distinct points.
    """
    points = np.asarray(positions, dtype=float)
    if len(points) < 2:
        return []
    result, current = [], []
    period = 2*pi
    for a, b in zip(points[:-1], points[1:]):
        delta = b-a
        cuts = [0., 1.]
        for axis in range(3):
            if abs(delta[axis]) < 1e-15:
                continue
            low, high = sorted((a[axis], b[axis]))
            first = int(np.floor((low+pi)/period))+1
            last = int(np.floor((high+pi)/period))
            for k in range(first, last+1):
                fraction = (k*period-pi-a[axis])/delta[axis]
                if 1e-12 < fraction < 1-1e-12:
                    cuts.append(float(fraction))
        cuts = sorted(set(cuts))
        for left, right in zip(cuts[:-1], cuts[1:]):
            midpoint = a+(left+right)*delta/2
            cell = np.floor((midpoint+pi)/period)
            start = np.clip(a+left*delta-period*cell, -pi, pi)
            end = np.clip(a+right*delta-period*cell, -pi, pi)
            if np.linalg.norm(end-start) < 1e-13:
                continue
            if current and np.linalg.norm(np.asarray(current[-1])-start) < 1e-10:
                current.append(end.tolist())
            else:
                if len(current) >= 2:
                    result.append(current)
                current = [start.tolist(), end.tolist()]
    if len(current) >= 2:
        result.append(current)
    return result


def _colors(values, upper):
    q = np.clip(np.asarray(values)/upper, 0, 1)*(len(_PALETTE)-1)
    lower = np.minimum(q.astype(int), len(_PALETTE)-2)
    fraction = (q-lower)[..., None]
    return ((1-fraction)*_PALETTE[lower]+fraction*_PALETTE[lower+1]).tolist()


def _witness(name, observed, limit, note=""):
    value = float(observed)
    return {"id": name, "pass": bool(np.isfinite(value) and value <= limit),
            "observed": value, "limit": float(limit), "rule": "at most", "note": note}


def _metric(name, label, value, unit="", note=""):
    return {"id": name, "label": label, "value": value, "unit": unit, "note": note}


def _reference_box():
    lines = []
    for axis in range(3):
        other = [j for j in range(3) if j != axis]
        for i, first in enumerate((-pi, pi)):
            for j, second in enumerate((-pi, pi)):
                a, b = np.zeros(3), np.zeros(3)
                a[axis], b[axis] = -pi, pi
                a[other] = b[other] = [first, second]
                lines.append({"id": f"periodic_box_{axis}_{i}_{j}", "positions": [a.tolist(), b.tolist()],
                              "color": _QUIET[:], "radius": .005, "opacity": .55})
    return lines


def _seeds():
    visual = []
    for height in (-1.9, 0., 1.9):
        for angle in np.linspace(0, 2*pi, 8, endpoint=False):
            visual.append([1.65*np.cos(angle), height, 1.65*np.sin(angle)])
    extra = np.random.default_rng(58271).uniform(-pi, pi, (16, 3))
    return np.vstack((visual, extra))


@lru_cache(maxsize=3)
def _compute(preset):
    coefficients = _COEFFICIENTS[preset]
    seeds = _seeds()
    times, paths = rk4(seeds, coefficients, step=.01)
    _, coarse = rk4(seeds, coefficients, step=.02)
    reference = solve_ivp(lambda t, y: velocity(y.reshape(-1, 3), coefficients).ravel(),
                          (0., 6.), seeds.ravel(), method="DOP853", t_eval=times,
                          rtol=2e-12, atol=2e-13)
    if not reference.success:
        raise RuntimeError("The independent DOP853 trajectory reference failed")
    independent = reference.y.T.reshape(paths.shape)
    fine_error = float(np.max(np.linalg.norm(paths-independent, axis=2)))
    coarse_error = float(np.max(np.linalg.norm(coarse-independent[::2], axis=2)))
    refinement_gap = float(np.max(np.linalg.norm(coarse-paths[::2], axis=2)))
    probes = np.random.default_rng(78452).uniform(-pi, pi, (64, 3))
    h = 1e-5
    derivatives = []
    for axis in range(3):
        offset = np.eye(3)[axis]*h
        derivatives.append((velocity(probes+offset, coefficients)-velocity(probes-offset, coefficients))/(2*h))
    divergence = derivatives[0][:, 0]+derivatives[1][:, 1]+derivatives[2][:, 2]
    curl = np.column_stack((derivatives[1][:, 2]-derivatives[2][:, 1],
                            derivatives[2][:, 0]-derivatives[0][:, 2],
                            derivatives[0][:, 1]-derivatives[1][:, 0]))
    curl_error = float(np.max(np.linalg.norm(curl-velocity(probes, coefficients), axis=1)))
    periodic_error = max(float(np.max(np.abs(velocity(probes+np.eye(3)[axis]*2*pi, coefficients)
                                            -velocity(probes, coefficients)))) for axis in range(3))
    speed_max = float(np.max(np.linalg.norm(velocity(paths, coefficients), axis=2)))
    witnesses = [
        _witness("divergence_finite_difference", np.max(np.abs(divergence)), 1e-9,
                 "Central derivatives at 64 independent probes, h=1e-5. Analytically each same-axis derivative is zero."),
        _witness("curl_equals_velocity", curl_error, 1e-8,
                 "Central-difference curl versus independently evaluated analytic velocity; the ABC field is Beltrami."),
        _witness("periodicity", periodic_error, 1e-13, "Velocity at q+2πe_j versus q for all three axes."),
        _witness("trajectory_DOP853", fine_error, 2e-6,
                 "Maximum Euclidean discrepancy over all 601 times and 40 tracers; RK4 h=.01 versus DOP853 rtol=2e-12."),
        _witness("step_refinement", refinement_gap, 3e-5,
                 "Same starts, RK4 h=.02 versus h=.01 at common times. A diagnostic, not a rigorous global bound."),
    ]
    analytic_error = None
    if preset == "integrable":
        exact = seeds[None, :, :]+times[:, None, None]*velocity(seeds, coefficients)[None, :, :]
        analytic_error = float(np.max(np.linalg.norm(paths-exact, axis=2)))
        witnesses.append(_witness("constant_velocity_exact_solution", analytic_error, 2e-12,
                                  "For A=1,B=C=0, z stays fixed and x,y advance linearly."))
    elif coarse_error > 1e-10:
        ratio = coarse_error/max(fine_error, 1e-16)
        witnesses.append({"id": "fourth_order_refinement", "pass": bool(ratio >= 8.),
                          "observed": ratio, "limit": 8., "rule": "at least",
                          "note": "Error ratio h=.02/.01 against DOP853; expected asymptotic factor is approximately 16, not an imposed identity."})
    return times, paths, seeds, coefficients, speed_max, witnesses, {
        "fine_DOP853_max_error": fine_error, "coarse_DOP853_max_error": coarse_error,
        "coarse_fine_max_gap": refinement_gap, "analytic_control_error": analytic_error,
        "central_difference_curl_error": curl_error,
        "central_difference_max_divergence": float(np.max(np.abs(divergence))),
    }


def build_case(preset="default"):
    """Build one deterministic analytic-field study with nine saved frames."""
    if preset not in PRESETS:
        raise ValueError("Unknown flow preset: "+str(preset))
    times, paths, seeds, coefficients, speed_max, witnesses, diagnostics = _compute(preset)
    frame_indices = np.linspace(0, len(times)-1, 9).astype(int)
    frames, worst_jump, position_count = [], 0., 0
    for index in frame_indices:
        lines = _reference_box()
        for tracer in range(24):
            active_indices = np.unique(np.r_[np.arange(0, index+1, 3), index]).astype(int)
            future_indices = np.unique(np.r_[index, np.arange(index, len(times), 3), len(times)-1]).astype(int)
            for category, indices, opacity, radius in (("active", active_indices, .98, .018),
                                                        ("context", future_indices, .20, .010)):
                for part, segment in enumerate(split_periodic_polyline(paths[indices, tracer])):
                    q = np.asarray(segment)
                    speed = np.linalg.norm(velocity(q, coefficients), axis=1)
                    worst_jump = max(worst_jump, float(np.max(np.abs(np.diff(q, axis=0)))))
                    lines.append({"id": f"{category}_{tracer}_{part}", "positions": segment,
                                  "color": [.12, .64, .73], "colors": _colors(speed, speed_max),
                                  "radius": radius, "opacity": opacity})
        marker_positions = _wrap(paths[index, :24])
        speeds = np.linalg.norm(velocity(marker_positions, coefficients), axis=1)
        particles = [{"id": "saved_tracers", "positions": marker_positions.tolist(),
                      "color": [.70, .92, .95], "colors": _colors(speeds, speed_max),
                      "radius": .060, "opacity": 1.}]
        frame_count = sum(len(row["positions"]) for row in lines)+24
        position_count = max(position_count, frame_count)
        frames.append({"time": float(times[index]), "meshes": [], "lines": lines, "points": particles,
                       "metrics": [
                           _metric("time", "Saved particle time", float(times[index]), "normalized time"),
                           _metric("speed_mean", "Mean speed of shown tracers", float(np.mean(speeds)), "coordinate units / time"),
                           _metric("tracers", "Visible tracked particles", 24),
                           _metric("reference_error", "RK4 / DOP853 maximum discrepancy", diagnostics["fine_DOP853_max_error"], "coordinate units",
                                   "Across 40 tracers and the complete saved integration; not a proof of a uniform error bound."),
                       ]})
    witnesses = [dict(row) for row in witnesses]
    witnesses += [
        _witness("periodic_polyline_max_step", worst_jump, .2,
                 "Maximum component step after geometric periodic clipping; a wrap jump would be about 2π."),
        _witness("geometry_positions_per_frame", position_count, 30000,
                 "Centerline samples, boundary intersections and shown particles; no coordinate quantization."),
    ]
    grid_axis = np.linspace(-pi, pi, 9)
    grid = np.stack(np.meshgrid(grid_axis, grid_axis, grid_axis, indexing="ij"), axis=-1).reshape(-1, 3)
    vectors = velocity(grid, coefficients)
    return {
        "id": "flow-"+("balanced" if preset == "default" else preset), "kind": "flow",
        "title": PRESETS[preset]["title"], "question": "Can an unchanging velocity field carry a particle along a complicated route?",
        "description": "An exact ABC velocity field supplies the instrument; colored fibers are computed particle trajectories, with saved tracers advancing through the same steady field.",
        "scope": "Synthetic, steady, incompressible periodic benchmark. Streamlines and pathlines coincide for this autonomous field. Finite trajectories do not establish chaos, mixing rates, or a Navier–Stokes simulation.",
        "parameters": {"A": coefficients[0], "B": coefficients[1], "C": coefficients[2],
                       "duration": 6., "rk4_step": .01, "reference_rtol": 2e-12,
                       "seed": 58271, "visual_tracers": 24, "reference_tracers": 40},
        "units": {"position": "dimensionless periodic coordinates", "velocity": "coordinate units / normalized time", "time": "normalized time"},
        "axes": "Right-handed x,y,z, Y up; coordinates are centered on the periodic cube [−π,π]³. Opposite faces are identified. Tube radii are authored glyph widths, not physical vortex cores.",
        "sources": [
            {"title": "Dombre et al. · Chaotic streamlines in the ABC flows (1986)",
             "url": "https://doi.org/10.1017/S0022112086002859",
             "note": "Primary study of the steady ABC family; the present finite trajectories are a benchmark visualization, not a fresh chaos measurement."},
            {"title": "ParaView User Guide · Filtering Data / Stream Tracer",
             "url": "https://docs.paraview.org/en/latest/UsersGuide/filteringData.html",
             "note": "A practical comparison hub: seed placement, line integration, step size and polydata representations are part of a streamline's meaning."},
        ],
        "insights": [
            "A velocity field can remain fixed while its particles move. In this steady field, pathlines trace streamlines; that equivalence generally fails for time-dependent fields.",
            "The analytic divergence is zero, so the exact flow is locally volume preserving. The displayed numerical paths have their own finite-step error and are checked separately.",
            "The curl equals the velocity for all three coefficient choices. The tubes show centerlines, not material tubes of a measured radius or a detected vortex-core boundary.",
            "Full computed paths appear faintly as context; bright prefixes and beads mark saved elapsed time. Frame selection does not integrate or invent an intermediate particle state.",
            "Speed colors share one declared case-wide transfer function, from zero to the maximum speed over all computed trajectories. Changing the camera cannot change a measurement.",
            "Periodic boundary crossings are split into geometric polyline pieces. A long line across the box would be a representation error, not sudden particle motion.",
        ],
        "frames": frames,
        "measurements": {**diagnostics, "times": times[::3].tolist(), "seeds": seeds.tolist(),
                         "trajectories_unwrapped": paths[::3].transpose(1, 0, 2).tolist(),
                         "saved_frame_indices_in_full_integrator": frame_indices.tolist(),
                         "color_transfer": {"quantity": "speed", "min": 0., "max": speed_max,
                                            "palette_rgb": _PALETTE.tolist(), "scope": "case-wide maximum over all 40 computed trajectories"},
                         "appearance": {"active_centerline_radius": .018, "context_centerline_radius": .010,
                                        "particle_glyph_radius": .060},
                         "periodic_clipping": "Linear clipping of computed polyline segments at periodic cube faces; not extra integrated states."},
        "datasets": {"velocity_grid": {"shape": [9, 9, 9], "origin": [-pi, -pi, -pi],
                                        "spacing": [pi/4]*3, "positions": grid.tolist(), "velocity": vectors.tolist(),
                                        "association": "point", "ordering": "C order with z fastest; meshgrid indexing=ij",
                                        "units": {"positions": "dimensionless", "velocity": "coordinate units / normalized time"}}},
        "witnesses": witnesses,
    }
