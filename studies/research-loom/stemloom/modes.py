"""Exact rectangular-membrane modes, with independent discrete witnesses.

The coloured sheet is a magnified displacement graph, not a finite-element
simulation or a time-resolved experimental movie. All saved states are computed
from the declared linear wave equation. Appearance never changes that model.
"""
from __future__ import annotations

from math import pi, sqrt

import numpy as np
from scipy.sparse import diags, kronsum
from scipy.sparse.linalg import eigsh


PRESETS = {
    "fundamental": {"title": "One whole membrane breathes",
                    "description": "The fundamental mode has no interior nodal line."},
    "degenerate": {"title": "Different shapes, the same frequency",
                   "description": "Two square-membrane modes in temporal quadrature share one frequency."},
    "beats": {"title": "A small geometric change splits the pair",
              "description": "A rectangular perturbation separates the two frequencies; the long envelope is retained as data."},
}

IN_PLANE_SCALE = 6.0
HEIGHT_SCALE = 55.0
GRID_INTERVALS = 40
COOL = np.array([.13, .43, .90])
MID = np.array([.57, .76, .81])
WARM = np.array([.97, .31, .23])
QUIET = [.11, .23, .33]
COPPER = [.91, .58, .28]
MINT = [.28, .96, .76]


def _need(condition, message):
    if not condition:
        raise ValueError(message)


def _witness(key, value, limit, note, rule="at most"):
    value, limit = float(value), float(limit)
    _need(np.isfinite(value) and np.isfinite(limit), "Nonfinite membrane witness")
    passed = value <= limit if rule == "at most" else value >= limit
    return {"id": key, "pass": bool(passed), "observed": value,
            "limit": limit, "rule": rule, "note": note}


def _metric(key, label, value, unit="", note=""):
    return {"id": key, "label": label, "value": value, "unit": unit, "note": note}


def _configuration(preset):
    if preset == "default":
        preset = "fundamental"
    _need(preset in PRESETS, "Unknown membrane preset: " + str(preset))
    if preset == "fundamental":
        return preset, 1., 1., [(1, 1, .025, 0.)]
    if preset == "degenerate":
        return preset, 1., 1., [(1, 2, .021, 0.), (2, 1, .021, -pi/2)]
    return preset, 1., 1.12, [(1, 2, .021, 0.), (2, 1, .021, 0.)]


def angular_frequency(m, n, lx, lz, speed=1.):
    return speed*pi*sqrt((m/lx)**2+(n/lz)**2)


def evaluate_field(x, z, time, lx, lz, components, speed=1.):
    """Return u, u_t, u_x, u_z, u_tt and Laplacian in physical model units."""
    x, z = np.broadcast_arrays(np.asarray(x, dtype=float), np.asarray(z, dtype=float))
    arrays = [np.zeros_like(x) for _ in range(6)]
    for m, n, amplitude, phase in components:
        kx, kz = m*pi/lx, n*pi/lz
        omega = angular_frequency(m, n, lx, lz, speed)
        sx, sz = np.sin(kx*x), np.sin(kz*z)
        temporal = np.cos(omega*time+phase)
        shape = sx*sz
        u = amplitude*shape*temporal
        arrays[0] += u
        arrays[1] += -amplitude*omega*shape*np.sin(omega*time+phase)
        arrays[2] += amplitude*kx*np.cos(kx*x)*sz*temporal
        arrays[3] += amplitude*kz*sx*np.cos(kz*z)*temporal
        arrays[4] += -omega*omega*u
        arrays[5] += -(kx*kx+kz*kz)*u
    return tuple(arrays)


def discrete_eigenvalue(m, n, intervals, lx, lz):
    """Exact eigenvalue of the five-point Dirichlet difference operator."""
    return (4/(lx/intervals)**2*np.sin(m*pi/(2*intervals))**2
            + 4/(lz/intervals)**2*np.sin(n*pi/(2*intervals))**2)


def _discrete_witness(lx, lz):
    intervals = 12
    q = intervals-1
    one = np.ones(q)
    tx = diags([-one[:-1], 2*one, -one[:-1]], [-1, 0, 1])/(lx/intervals)**2
    tz = diags([-one[:-1], 2*one, -one[:-1]], [-1, 0, 1])/(lz/intervals)**2
    operator = kronsum(tx, tz, format="csr")
    # A retained starting vector makes this instrument deterministic. Signs or
    # rotations within a repeated eigenspace are never treated as identities.
    start = np.linspace(.75, 1.25, q*q)
    values, vectors = eigsh(operator, k=6, which="SM", tol=1e-12, v0=start)
    order = np.argsort(values)
    values, vectors = values[order], vectors[:, order]
    reference = np.sort([discrete_eigenvalue(m, n, intervals, lx, lz)
                         for m in range(1, 6) for n in range(1, 6)])[:6]
    difference = float(np.max(np.abs(values-reference)))
    residual = float(np.max(np.linalg.norm(operator@vectors-vectors*values, axis=0)))
    return {"intervals": intervals, "numeric_eigenvalues": values.tolist(),
            "discrete_reference": reference.tolist(),
            "max_eigenvalue_difference": difference, "max_eigenvector_residual": residual}


def _colour(values, bound):
    t = np.clip(np.asarray(values)/bound, -1, 1).ravel()
    return np.where((t < 0)[:, None],
                    MID[None, :]+(-t[:, None])*(COOL-MID)[None, :],
                    MID[None, :]+t[:, None]*(WARM-MID)[None, :]).tolist()


def _positions(x, z, displacement, lx, lz):
    return np.stack([IN_PLANE_SCALE*(x-lx/2), HEIGHT_SCALE*displacement,
                     IN_PLANE_SCALE*(z-lz/2)], axis=-1).reshape(-1, 3)


def _zero_contours(x, z, field, faces, lx, lz):
    """Stitch zero cuts of the displayed triangles; not an analytic nodal solver."""
    flat = field.ravel()
    if np.max(np.abs(flat)) < 1e-12:
        return []  # The whole sheet is flat; representing it as a line is wrong.
    if np.min(flat) > -1e-13 or np.max(flat) < 1e-13:
        return []  # No interior sign-changing node; omit boundary triangulation cuts.
    coords = np.stack([x.ravel(), z.ravel()], axis=-1)
    adjacency, positions = {}, {}
    tolerance = 1e-13
    for face in faces:
        cuts = []
        for a, b in zip(face, face[1:]+face[:1]):
            va, vb = flat[a], flat[b]
            # A zero edge need not be unique between triangles. Skip it: outer
            # boundary zeros already have a separate frame, while interior
            # nodal segments are supplied by adjacent nonzero triangles.
            if abs(va) < tolerance and abs(vb) < tolerance:
                continue
            if va*vb < 0 or abs(va) < tolerance or abs(vb) < tolerance:
                t = 0. if abs(va) < tolerance else 1. if abs(vb) < tolerance else va/(va-vb)
                point = coords[a]+t*(coords[b]-coords[a])
                key = tuple(round(float(v), 10) for v in point)
                if key not in cuts:
                    cuts.append(key)
        if len(cuts) == 2 and cuts[0] != cuts[1]:
            a, b = cuts
            # Fixed-edge zeros already belong to the copper support. Keep the
            # contour overlay for interior nodal structure instead of painting
            # a duplicate mint perimeter over that reference frame.
            if any(abs(a[axis]-edge) < 1e-9 and abs(b[axis]-edge) < 1e-9
                   for axis, edge in ((0, 0.), (0, lx), (1, 0.), (1, lz))):
                continue
            adjacency.setdefault(a, set()).add(b)
            adjacency.setdefault(b, set()).add(a)
            positions[a], positions[b] = a, b
    lines = []
    unused = {tuple(sorted((a, b))) for a in adjacency for b in adjacency[a]}
    while unused:
        endpoints = [a for a in adjacency if sum(tuple(sorted((a, b))) in unused
                                                 for b in adjacency[a]) == 1]
        start = min(endpoints) if endpoints else min(unused)[0]
        path, current = [start], start
        while True:
            choices = [b for b in adjacency[current] if tuple(sorted((current, b))) in unused]
            if not choices:
                break
            nxt = min(choices)
            unused.remove(tuple(sorted((current, nxt))))
            path.append(nxt)
            current = nxt
            if current == start:
                break
        if len(path) > 1:
            # Lifting by 0.018 is explicitly display styling, not displacement.
            lines.append([[IN_PLANE_SCALE*(q[0]-lx/2), .018,
                           IN_PLANE_SCALE*(q[1]-lz/2)] for q in path])
    return lines


def build_case(preset="default"):
    preset, lx, lz, components = _configuration(preset)
    frequencies = [angular_frequency(m, n, lx, lz)/(2*pi) for m, n, _, _ in components]
    omegas = [2*pi*f for f in frequencies]
    mean_period = 2*pi/float(np.mean(omegas))
    times = np.linspace(0, mean_period*(2 if preset == "beats" else 1),
                        12 if preset == "beats" else 9)
    grid = GRID_INTERVALS+1
    xs, zs = np.linspace(0, lx, grid), np.linspace(0, lz, grid)
    x, z = np.meshgrid(xs, zs, indexing="xy")
    faces = []
    for j in range(grid-1):
        for i in range(grid-1):
            k = j*grid+i
            faces.extend([[k, k+1, k+grid+1], [k, k+grid+1, k+grid]])
    amplitude_bound = sum(c[2] for c in components)
    exact_energy = lx*lz/8*sum(amplitude**2*angular_frequency(m, n, lx, lz)**2
                             for m, n, amplitude, _ in components)
    energy_x, energy_z = np.meshgrid(np.linspace(0, lx, 129), np.linspace(0, lz, 129), indexing="xy")
    frames, fields, velocities, energies = [], [], [], []
    maximum_boundary = maximum_pde = 0.
    for frame_index, time in enumerate(times):
        u, ut, _, _, utt, lap = evaluate_field(x, z, time, lx, lz, components)
        maximum_boundary = max(maximum_boundary, float(np.max(np.abs(np.r_[u[0], u[-1], u[:, 0], u[:, -1]]))))
        maximum_pde = max(maximum_pde, float(np.max(np.abs(utt-lap))))
        _, vt, ux, uz, _, _ = evaluate_field(energy_x, energy_z, time, lx, lz, components)
        density = .5*(vt*vt+ux*ux+uz*uz)
        energy = float(np.trapezoid(np.trapezoid(density, dx=lx/128, axis=1), dx=lz/128))
        energies.append(energy)
        fields.append(u.tolist())
        velocities.append(ut.tolist())
        mesh = {"id": "membrane", "positions": _positions(x, z, u, lx, lz).tolist(),
                "faces": faces, "color": MID.tolist(), "colors": _colour(u, amplitude_bound),
                "opacity": .98,
                "point_data": {"displacement": {"values": u.ravel().tolist(), "components": 1,
                                                  "units": "normalized length"},
                               "velocity": {"values": ut.ravel().tolist(), "components": 1,
                                            "units": "normalized length / normalized time"}}}
        lines = [{"id": "fixed_support", "positions": [[-3*lx, 0, -3*lz], [3*lx, 0, -3*lz],
                  [3*lx, 0, 3*lz], [-3*lx, 0, 3*lz], [-3*lx, 0, -3*lz]],
                  "color": COPPER, "radius": .035, "opacity": 1.}]
        for axis in range(2):
            for j in range(0, grid, 5):
                sample = u[j, :] if axis == 0 else u[:, j]
                xx, zz = (xs, np.full(grid, zs[j])) if axis == 0 else (np.full(grid, xs[j]), zs)
                positions = _positions(xx, zz, sample, lx, lz)
                positions[:, 1] += .012
                lines.append({"id": f"surface_grid_{axis}_{j}", "positions": positions.tolist(),
                              "color": QUIET, "radius": .007, "opacity": .48})
        contour_paths = _zero_contours(x, z, u, faces, lx, lz)
        for j, path in enumerate(contour_paths):
            lines.append({"id": f"sampled_zero_contour_{j}", "positions": path,
                          "color": MINT, "radius": .013, "opacity": .88})
        probe_x, probe_z = .37*lx, .61*lz
        probe_u, probe_v, *_ = evaluate_field(probe_x, probe_z, time, lx, lz, components)
        probe = [6*(probe_x-lx/2), HEIGHT_SCALE*float(probe_u), 6*(probe_z-lz/2)]
        lines.append({"id": "sensor_displacement", "positions": [[probe[0], 0, probe[2]], probe],
                      "color": COPPER, "radius": .014, "opacity": 1.})
        metrics = [_metric("probe", "Probe displacement", float(probe_u), "model length",
                           "Raw displacement, before the vertical display magnification."),
                   _metric("frequency", "First component frequency", frequencies[0], "1/model time"),
                   _metric("energy", "Relative energy/reference difference", abs(energy-exact_energy)/exact_energy,
                           "", "Independent 129×129 spatial quadrature of kinetic plus elastic energy."),
                   _metric("time", "Saved physical-model time", float(time), "model time")]
        if len(frequencies) == 2:
            split = abs(frequencies[0]-frequencies[1])
            metrics.append(_metric("splitting", "Component frequency splitting", split, "1/model time",
                                   "Zero means degeneracy, not a silent field."))
        frames.append({"time": float(time), "meshes": [mesh], "lines": lines,
                       "points": [{"id": "sensor", "positions": [probe], "color": COPPER,
                                   "radius": .065, "opacity": 1.}], "metrics": metrics})

    convergence = []
    first_m, first_n, *_ = components[0]
    reference_lambda = angular_frequency(first_m, first_n, lx, lz)**2
    for intervals in (12, 24, 48):
        approximation = float(discrete_eigenvalue(first_m, first_n, intervals, lx, lz))
        convergence.append({"intervals": intervals, "lambda_fd": approximation,
                            "lambda_reference": reference_lambda,
                            "relative_error": abs(approximation-reference_lambda)/reference_lambda})
    order = float(np.log2(convergence[-2]["relative_error"]/convergence[-1]["relative_error"]))
    discrete = _discrete_witness(lx, lz)
    maximum_energy = float(np.max(np.abs(np.asarray(energies)-exact_energy))/exact_energy)
    witnesses = [_witness("fixed_boundary", maximum_boundary, 1e-14,
                          "Analytic sine factors obey all four fixed-edge conditions."),
                 _witness("wave_equation", maximum_pde, 2e-14,
                          "Analytic u_tt and spatial Laplacian independently assembled per mode."),
                 _witness("energy_quadrature", maximum_energy, 1e-11,
                          "Spatial trapezoid energy agrees with the modal orthogonality reference."),
                 _witness("fd_second_order", abs(order-2), .06,
                          "Observed refinement order of the five-point eigenvalue against the continuum frequency."),
                 _witness("sparse_eigenvalue", discrete["max_eigenvalue_difference"], 2e-9,
                          "SciPy sparse eigenvalues agree with the separate closed discrete formula."),
                 _witness("sparse_eigen_residual", discrete["max_eigenvector_residual"], 1e-8,
                          "Residual of the actual assembled finite-difference matrix/eigenvector pair.")]
    _need(all(w["pass"] for w in witnesses), "Membrane science gate rejected a reference check")
    beat_frequency = abs(frequencies[0]-frequencies[1]) if len(frequencies) == 2 else 0.
    envelope = None
    if beat_frequency > 1e-12:
        envelope_times = np.linspace(0, 1/beat_frequency, 161)
        # This is the envelope only at the retained probe for this equal-phase
        # two-frequency case. A membrane does not have one universal envelope.
        probe_modes = [amplitude*np.sin(m*pi*.37)*np.sin(n*pi*.61)
                       for m, n, amplitude, _ in components]
        a, b = probe_modes
        envelope = {"time": envelope_times.tolist(),
                    "probe_upper_amplitude": np.sqrt(np.maximum(0, a*a+b*b+2*a*b*np.cos(2*pi*beat_frequency*envelope_times))).tolist(),
                    "meaning": "Exact analytic-signal magnitude at the fixed probe; not a globally uniform membrane envelope."}
    return {"id": "modes-"+preset, "kind": "modes", "title": PRESETS[preset]["title"],
            "question": "Can different spatial patterns share a frequency, and what breaks that degeneracy?",
            "description": PRESETS[preset]["description"],
            "scope": "Synthetic exact solution of the ideal, uniform, tension-dominated linear membrane equation; not a shell/plate FEM, measured material, nonlinear large-deflection model or resolved film.",
            "parameters": {"preset": preset, "length_x": lx, "length_z": lz, "wave_speed": 1.,
                           "components": [{"m": m, "n": n, "amplitude": amplitude, "phase": phase}
                                          for m, n, amplitude, phase in components],
                           "in_plane_display_scale": IN_PLANE_SCALE, "vertical_display_scale": HEIGHT_SCALE,
                           "mesh_intervals": GRID_INTERVALS, "color_displacement_bound": amplitude_bound},
            "units": {"length": "normalized length", "time": "normalized length / wave speed",
                      "displacement": "normalized length", "frequency": "inverse normalized time"},
            "axes": "Right-handed Y-up display: (6(x−Lx/2), 55u, 6(z−Lz/2)). Height is magnified 55/6 relative to in-plane lengths. Grid lines are lifted by 0.012 and interior sampled zero contours by 0.018 display units for legibility; raw scalar arrays are unshifted.",
            "sources": [{"title": "Daniel A. Russell, Penn State · Rectangular membrane modes",
                         "url": "https://www.acs.psu.edu/drussell/Demos/rect-membrane/rect-mem.html",
                         "note": "Mode shapes, frequencies and degeneracy; equations are implemented with original geometry and wording, not copied animations."},
                        {"title": "Richard Fitzpatrick, UT Austin · Oscillation of an elastic sheet",
                         "url": "https://farside.ph.utexas.edu/teaching/315/Waves/node56.html",
                         "note": "Separation of the two-dimensional linear wave equation and fixed-boundary eigenfunctions."},
                        {"title": "SciPy · eigsh",
                         "url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.sparse.linalg.eigsh.html",
                         "note": "Independent numerical eigenproblem for the assembled symmetric finite-difference operator."}],
            "insights": ["The membrane oscillates transversely in display Y. Its physical domain is the X–Z plane; the conspicuous height is a declared magnification, not a claim of large physical deflection.",
                         "A colour represents signed displacement on a fixed symmetric scale within the case. Mint contours are zero cuts of sampled triangles, not a proof of an analytic nodal set. If the whole field is zero, it is not drawn as a single nodal line.",
                         "The square permits distinct (1,2) and (2,1) shapes at the same frequency. Temporal quadrature can move the instantaneous zero pattern while the two modal energies stay fixed.",
                         "Changing one side length splits that pair. The beat period depends on the frequency difference and the local envelope also depends on the probe position.",
                         "Playback selects saved exact checkpoints. The near-degenerate case covers only two mean-carrier periods; its separately retained long envelope is not a time-resolved movie of the whole beat.",
                         "A finite-difference eigenvalue approaches the continuum reference at second order. A small algebraic eigensolver residual and a small continuum discretization error measure different things."],
            "frames": frames,
            "measurements": {"grid_shape": [grid, grid], "x": xs.tolist(), "z": zs.tolist(),
                             "times": times.tolist(), "displacement": fields, "velocity": velocities,
                             "frequencies": frequencies, "angular_frequencies": omegas,
                             "energy_reference": exact_energy, "energy_quadrature": energies,
                             "max_relative_energy_difference": maximum_energy,
                             "finite_difference_convergence": convergence, "observed_order": order,
                             "discrete_eigenproblem": discrete,
                             "probe": {"x": .37*lx, "z": .61*lz},
                             "beat_frequency": beat_frequency,
                             "beat_period": 1/beat_frequency if beat_frequency > 1e-12 else None,
                             "probe_envelope": envelope,
                             "color": {"quantity": "signed displacement", "minimum": -amplitude_bound,
                                       "maximum": amplitude_bound, "zero_color": MID.tolist()}},
            "datasets": {"membrane": {"layout": "rectilinear x,z grid; arrays indexed [time][z][x]",
                                       "coordinates": {"x": xs.tolist(), "z": zs.tolist()},
                                       "time": times.tolist(), "displacement": fields, "velocity": velocities,
                                       "units": {"displacement": "normalized length",
                                                 "velocity": "normalized length / normalized time"}}},
            "witnesses": witnesses}
