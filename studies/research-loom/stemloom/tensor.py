"""Tensor Loom: covariance geometry with explicit distribution assumptions.

The saved frames change a Mahalanobis threshold, not the observations.  The
chi-square probability label is a Gaussian-model probability.  In particular,
it is neither a confidence interval for a fitted mean nor a coverage guarantee
for the deliberately non-Gaussian mixture example.
"""
from __future__ import annotations

import hashlib
from math import pi

import numpy as np
from scipy.stats import chi2

PRESETS = {
    "correlated": {"title": "Correlated cloud", "description": "An anisotropic Gaussian turns covariance into three unequal principal axes."},
    "spherical": {"title": "No population favorite", "description": "An isotropic Gaussian has no preferred population directions; a finite sample still does."},
    "mixture": {"title": "A beautiful but incomplete summary", "description": "Two clusters share one global covariance ellipsoid; Gaussian coverage is not a valid distribution claim."},
}
LEVELS = (.50, .68, .80, .90, .95, .975, .99)
MINT = [.26, .94, .78]
CORAL = [1., .39, .48]
AMBER = [1., .71, .27]
VIOLET = [.66, .53, 1.]
CYAN = [.29, .78, 1.]
QUIET = [.15, .27, .37]
SOURCE_URLS = [
    {"title": "NIST/SEMATECH · The Multivariate Normal Distribution", "url": "https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc542.htm", "note": "Mean, covariance, and the quadratic form defining multivariate Gaussian density."},
    {"title": "Penn State STAT 505 · The Multivariate Normal Distribution", "url": "https://online.stat.psu.edu/stat505/Lesson04", "note": "Study multivariate normal geometry and probability regions; keep population contours separate from inference about a mean."},
    {"title": "SciPy · chi2 distribution", "url": "https://docs.scipy.org/doc/scipy/reference/generated/scipy.stats.chi2.html", "note": "The three-degree-of-freedom inverse CDF selects a Mahalanobis-radius probability contour under a Gaussian model."},
]


def _metric(key, label, value, unit="", note=""):
    return {"id": key, "label": label, "value": value, "unit": unit, "note": note}


def _witness(key, observed, limit, note=""):
    value, bound = float(observed), float(limit)
    if not np.isfinite(value) or not np.isfinite(bound):
        raise ValueError("Nonfinite tensor witness: " + key)
    return {"id": key, "pass": bool(value <= bound), "observed": value,
            "limit": bound, "rule": "at most", "note": note}


def _validated_points(points):
    """Refuse malformed, nonnumeric, nonfinite, huge, or degenerate observations."""
    try:
        raw = np.asarray(points)
    except (TypeError, ValueError) as error:
        raise ValueError("Observations must be a rectangular numeric N×3 array.") from error
    if raw.ndim != 2 or raw.shape[1:] != (3,) or not 4 <= len(raw) <= 5000:
        raise ValueError("Observations require 4..5000 rows and exactly three columns.")
    if raw.dtype.kind not in "iuf":
        raise ValueError("Observations must contain real numbers, not strings, objects, booleans or complex values.")
    data = np.asarray(raw, dtype=np.float64)
    if not np.isfinite(data).all():
        raise ValueError("Every observation coordinate must be finite.")
    with np.errstate(over="ignore", invalid="ignore"):
        mean = data.mean(axis=0)
        centered = data-mean
        covariance = centered.T @ centered/(len(data)-1)
    if not np.isfinite(covariance).all() or not np.isfinite(mean).all():
        raise ValueError("Observation magnitudes exceed the finite covariance budget.")
    eigenvalues, eigenvectors = np.linalg.eigh(covariance)
    if eigenvalues[-1] <= 0 or eigenvalues[0] <= eigenvalues[-1]*1e-10:
        raise ValueError("A full-rank, reasonably conditioned three-dimensional covariance is required.")
    # Fix signs and handedness for reproducible glyphs, without implying that
    # eigenvector signs or repeated-eigenvalue bases have statistical meaning.
    order = np.argsort(eigenvalues)[::-1]
    eigenvalues, eigenvectors = eigenvalues[order], eigenvectors[:, order]
    for column in range(3):
        index = int(np.argmax(np.abs(eigenvectors[:, column])))
        if eigenvectors[index, column] < 0:
            eigenvectors[:, column] *= -1
    if np.linalg.det(eigenvectors) < 0:
        eigenvectors[:, -1] *= -1
    return data, mean, centered, covariance, eigenvalues, eigenvectors


def _sphere_mesh(nlat=16, nlon=32):
    """A nondegenerate indexed unit sphere: two poles and latitude rings."""
    points = [[0., 1., 0.]]
    for j in range(1, nlat):
        latitude = pi*j/nlat
        for i in range(nlon):
            azimuth = 2*pi*i/nlon
            points.append([np.sin(latitude)*np.cos(azimuth), np.cos(latitude),
                           np.sin(latitude)*np.sin(azimuth)])
    south = len(points)
    points.append([0., -1., 0.])
    faces = []
    for i in range(nlon):
        ni = (i+1) % nlon
        # Winding points outward in this Y-up sphere parameterization.
        faces.append([0, 1+ni, 1+i])
        for j in range(nlat-2):
            a, b = 1+j*nlon+i, 1+j*nlon+ni
            c, d = a+nlon, b+nlon
            faces.extend([[a, b, d], [a, d, c]])
        a, b = 1+(nlat-2)*nlon+i, 1+(nlat-2)*nlon+ni
        faces.append([a, b, south])
    return np.asarray(points, dtype=float), faces


def _line(identity, positions, color, radius=.012, opacity=1.):
    return {"id": identity, "positions": np.asarray(positions, dtype=float).tolist(),
            "color": list(color), "radius": radius, "opacity": opacity}


def _build(points, label, identity, *, preset, assumption, population=None, groups=None):
    data, mean, centered, covariance, eigenvalues, basis = _validated_points(points)
    n = len(data)
    scaled_basis = basis @ np.diag(np.sqrt(eigenvalues))
    whitened = centered @ basis / np.sqrt(eigenvalues)
    squared_distances = np.einsum("ij,ij->i", whitened, whitened)
    sphere, faces = _sphere_mesh()
    inverse = np.linalg.inv(covariance)
    reconstruction = basis @ np.diag(eigenvalues) @ basis.T
    whitened_covariance = whitened.T @ whitened/(n-1)
    radii = np.sqrt(chi2.ppf(np.asarray(LEVELS), 3))
    shell_residual = 0.
    frames = []
    reference_radius = 1.
    for level, radius in zip(LEVELS, radii):
        positions = mean+sphere @ scaled_basis.T*radius
        delta = positions-mean
        q = np.einsum("ij,jk,ik->i", delta, inverse, delta)
        shell_residual = max(shell_residual, float(np.max(np.abs(q/radius**2-1))))
        inside = squared_distances <= radius**2
        colors = np.where(inside[:, None], np.asarray(MINT), np.asarray(CORAL))
        # Surface color is a restrained positional tint, not a second field.
        tint = np.clip((sphere[:, 1]+1)/2, 0, 1)
        surface_colors = ((1-tint[:, None])*np.array([.15, .44, .63])+
                          tint[:, None]*np.array([.38, .91, .79]))
        meshes = [{"id": "probability-ellipsoid", "positions": positions.tolist(),
                   "faces": faces, "color": MINT[:], "colors": surface_colors.tolist(),
                   "opacity": .19}]
        lines = []
        for j, color in enumerate((AMBER, CYAN, VIOLET)):
            direction = basis[:, j]*np.sqrt(eigenvalues[j])*radius
            lines.append(_line(f"principal-axis-{j+1}", [mean-direction, mean+direction], color, .018))
        # One-standard-deviation-radius wire rings are fixed while the outer
        # probability contour grows. In 3D this encloses only ~19.9% for N3.
        angles = np.linspace(0, 2*pi, 97)
        for j in range(3):
            ring = np.zeros((len(angles), 3))
            ring[:, j] = np.cos(angles)
            ring[:, (j+1) % 3] = np.sin(angles)
            lines.append(_line(f"unit-mahalanobis-ring-{j}",
                               mean+reference_radius*ring @ scaled_basis.T,
                               QUIET, .008, .9))
        # Outer meridians communicate surface geometry even with low opacity.
        for j in range(6):
            longitude = 2*pi*j/6
            meridian = np.c_[np.sin(angles)*np.cos(longitude), np.cos(angles),
                             np.sin(angles)*np.sin(longitude)]
            lines.append(_line(f"outer-meridian-{j}", mean+radius*meridian @ scaled_basis.T,
                               [.31, .65, .69], .005, .56))
        empirical = float(inside.mean())
        frames.append({
            # This is a threshold coordinate, explicitly not physical time.
            "time": float(level), "meshes": meshes, "lines": lines,
            "points": [{"id": "observations", "positions": data.tolist(), "color": MINT[:],
                        "colors": colors.tolist(), "radius": .037, "opacity": .93,
                        "point_data": {
                            "mahalanobis_squared": {"values": squared_distances.tolist(), "components": 1, "units": "dimensionless"},
                            "inside_selected_ellipsoid": {"values": inside.astype(int).tolist(), "components": 1, "units": "boolean indicator"},
                            "principal_scores": {"values": (centered @ basis).tolist(), "components": 3, "units": "input length units"},
                        }},
                       {"id": "sample-mean", "positions": [mean.tolist()], "color": AMBER[:],
                        "radius": .075, "opacity": 1.}],
            "metrics": [
                _metric("nominal", "Gaussian model probability", 100*level, "%", "A model probability, not guaranteed finite-sample coverage."),
                _metric("radius", "Mahalanobis radius", float(radius), "", "sqrt(chi-square quantile), three degrees of freedom."),
                _metric("empirical", "Observed points enclosed", 100*empirical, "%", "Computed from this fixed dataset using fitted mean/covariance."),
                _metric("count", "Observations enclosed", int(inside.sum()), f"of {n}"),
                _metric("condition", "Covariance eigenvalue ratio", float(eigenvalues[0]/eigenvalues[-1]), "×", "The shape condition number; not an uncertainty probability."),
            ]})
    scale = max(float(np.linalg.norm(covariance)), np.finfo(float).tiny)
    witnesses = [
        _witness("covariance-symmetry", np.max(np.abs(covariance-covariance.T))/scale, 1e-13),
        _witness("eigen-reconstruction", np.linalg.norm(reconstruction-covariance)/scale, 2e-12),
        _witness("orthonormal-principal-basis", np.max(np.abs(basis.T @ basis-np.eye(3))), 2e-12),
        _witness("whitened-sample-covariance", np.max(np.abs(whitened_covariance-np.eye(3))), 2e-10,
                 "An algebraic check of this fitted data, not evidence that its law is Gaussian."),
        _witness("chi-square-quantile-roundtrip", np.max(np.abs(chi2.cdf(radii*radii, 3)-LEVELS)), 5e-14),
        _witness("emitted-ellipsoid-quadratic-form", shell_residual, 2e-9,
                 "Recomputes the covariance quadratic form on every exported shell vertex."),
    ]
    if population is not None:
        determinant = float(population["affine_determinant"])
        witnesses.append({"id": "generating-affine-determinant", "pass": determinant >= 0,
                          "observed": determinant, "limit": 0., "rule": "at least",
                          "note": "The authored generating affine map preserves handedness; covariance geometry alone cannot detect a reflected sample."})
    coverage = float(chi2.cdf(1., 3))
    gaussian_scope = ("Gaussian probability labels are justified for the stated synthetic population law; fitted contours remain plug-in estimates."
                      if assumption == "gaussian" else
                      "The Gaussian reference is a comparison model only. The dataset is not asserted Gaussian; nominal probabilities are not valid coverage guarantees.")
    return {
        "id": identity, "kind": "tensor", "title": label,
        "question": "What can an ellipsoid tell you about a cloud—and what can it hide?",
        "description": "A fixed cloud of observations, its unbiased sample covariance, and three principal directions. Saved frames grow an exact Mahalanobis contour; no observation is moved or interpolated.",
        "scope": "Covariance/PCA geometry and a fitted Gaussian reference region for observations. This is not a confidence ellipsoid for the unknown mean, a prediction-region calibration, or a Gaussianity test. "+gaussian_scope,
        "parameters": {"preset": preset, "observations": n, "threshold_probabilities": list(LEVELS),
                       "covariance_ddof": 1, "assumption": assumption, "seed": 41023 if preset != "imported" else None},
        "units": {"position": "arbitrary input length units", "covariance": "squared input length units", "frame_coordinate": "nominal Gaussian probability, not time"},
        "axes": "Right-handed Cartesian XYZ in input units; Y is up in the scene. No coordinates are rescaled. Gold/cyan/violet show PC1/PC2/PC3. The saved-frame control changes a probability threshold, not physical time.",
        "legend": [{"label": "Inside the selected ellipsoid", "color": MINT[:]},
                   {"label": "Outside the selected ellipsoid", "color": CORAL[:]},
                   {"label": "PC1 / sample mean", "color": AMBER[:]},
                   {"label": "PC2", "color": CYAN[:]}, {"label": "PC3", "color": VIOLET[:]}],
        "sources": [dict(row) for row in SOURCE_URLS],
        "insights": [
            "An eigenvector is a direction of sample spread; its sign is conventional. The ellipsoid semiaxes are r√λ, not the covariance eigenvalues themselves.",
            f"A Mahalanobis radius of one encloses {100*coverage:.3f}% of a three-dimensional Gaussian population with known parameters, not the familiar one-dimensional 68%. The quiet inner rings have that fixed radius.",
            "The outer contour uses r²=χ²₃⁻¹(p). The plotted sample mean and covariance are estimated from these observations, so its nominal p is a plug-in Gaussian reference rather than an exact finite-sample coverage claim.",
            "An ellipsoid for observations is different from a confidence region for a mean. No division of covariance by sample size or Hotelling-T² inference is performed here.",
            "In the isotropic population there is no preferred basis. A finite sample still has unequal fitted eigenvalues; deterministic eigenvector signs make files reproducible, not statistically unique.",
            "The mixture deliberately puts two clusters inside one smooth global summary. A good covariance reconstruction does not prove a Gaussian law or reveal every cluster.",
        ],
        "frames": frames,
        "measurements": {"columns": ["x", "y", "z"], "observations": data.tolist(),
                         "sample_mean": mean.tolist(), "sample_covariance": covariance.tolist(),
                         "eigenvalues": eigenvalues.tolist(), "principal_basis_columns": basis.tolist(),
                         "mahalanobis_squared": squared_distances.tolist(),
                         "whitened_observations": whitened.tolist(),
                         "one_radius_gaussian_probability": coverage,
                         "threshold_probabilities": list(LEVELS), "threshold_radii": radii.tolist(),
                         "distribution_assumption": assumption, "population_reference": population,
                         "group_labels": None if groups is None else np.asarray(groups, dtype=int).tolist()},
        "datasets": {"observations": {"columns": ["x", "y", "z"], "units": "arbitrary input length units", "values": data.tolist(),
                                     "description": "Unmoved source observations; the fitted covariance uses denominator N−1."}},
        "witnesses": witnesses,
    }


def build_case(preset="default"):
    """Build one deterministic synthetic cloud and seven probability contours."""
    if preset == "default":
        preset = "correlated"
    if preset not in PRESETS:
        raise ValueError("Unknown tensor preset: " + str(preset))
    generator = np.random.default_rng(41023)
    white = generator.standard_normal((360, 3))
    if preset == "correlated":
        affine = np.array([[1.25, 0., 0.], [.82, .72, 0.], [.3, -.23, .4]])
        center = np.array([.15, -.1, .2])
        data = center+white @ affine.T
        population = {"kind": "Gaussian", "mean": center.tolist(), "covariance": (affine @ affine.T).tolist(),
                      "affine_determinant": float(np.linalg.det(affine))}
        assumption, groups = "gaussian", None
    elif preset == "spherical":
        data = white*.8
        population = {"kind": "Gaussian", "mean": [0., 0., 0.], "covariance": (.64*np.eye(3)).tolist(),
                      "affine_determinant": .8**3}
        assumption, groups = "gaussian", None
    else:
        groups = np.repeat([0, 1], 180)
        offset = np.array([1.65, .4, -.35])
        affine = np.array([[.32, 0., 0.], [.12, .48, 0.], [-.05, .1, .31]])
        data = white @ affine.T+(2*groups-1)[:, None]*offset
        population = {"kind": "equal-weight two-Gaussian mixture", "mean": [0., 0., 0.],
                      "component_means": [(-offset).tolist(), offset.tolist()],
                      "component_covariance": (affine @ affine.T).tolist(),
                      "covariance": (affine @ affine.T+np.outer(offset, offset)).tolist(),
                      "affine_determinant": float(np.linalg.det(affine))}
        assumption = "non-Gaussian mixture"
    return _build(data, "Tensor Loom · "+PRESETS[preset]["title"], "tensor-"+preset,
                  preset=preset, assumption=assumption, population=population, groups=groups)


def build_from_points(points, label="Imported observations"):
    """Fit an explicitly unclassified CSV/array cloud, without claiming Gaussianity."""
    if not isinstance(label, str) or not label.strip() or len(label) > 120:
        raise ValueError("Imported dataset label must contain 1..120 characters.")
    data, *_ = _validated_points(points)
    identity = "tensor-import-"+hashlib.sha256(data.astype("<f8").tobytes()).hexdigest()[:12]
    return _build(data, label.strip(), identity, preset="imported", assumption="unclassified imported observations")
