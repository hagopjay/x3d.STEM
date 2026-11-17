# Research Loom: STEM analysis, scientific visualization and hub interoperability

Assessment date: 17 November 2026. This report reads public source snapshots and
names each observation's scope. It separates repository capability, recorded
historical results, proposed integration and measurements made in this pass.

The useful next step for x3d.STEM is a compact research workbench: three
scientific cases with portable geometry, original numerical arrays, and
independent checks. The existing Loom work already supplies valuable publishing
and evidence machinery. The main architectural improvement is to make the
boundary between scientific data and visual representation explicit at every
hub transfer.

## 1. The repositories have different jobs

| Repository and inspected snapshot | Observed role | Recommended responsibility for this work |
|---|---|---|
| `hagopjay/x3d.STEM@09a6321da28ea494b8dc0bae59eaa6936e04d2d8` | Study generators, case manifests, payloads, scientific witnesses, browser reconstructions and a shared `stemkit` | Own the numerical cases, canonical data, scientific checks, interchange fixtures and source binding |
| `hagopjay/x3d.demo@94e9b2649d7603877aa5e368a650f402d4955a6e` | A versioned discovery shelf; `docs/versions/vN/` freezes front-page snapshots and `docs/demos/<name>/vN/` preserves demo versions | Add a discoverable card after the live destination is verified; retain prior versions and the site's numbering policy |
| `hagopjay/x3d.docs@5ee6469f51d9cbaa01f366bd4f8b1ab92c4f2228` | AST teardowns, X3D concept chapters, named instruments, claim grades, drills and generated registers | Document reusable contracts, failure modes, worked transfer exercises and measured limits |

The supplied plural name `x3d.demos` was not resolved. The existing STEM README
links the singular public repository `x3d.demo`, which is the repository read
here. The docs README currently names `https://hagsmac.github.io/x3d.docs/` as its
site. A repository name alone does not establish a new deployment URL.

The baseline repository inspection examined `README.md`, `docs/X3D-STEM.md`,
the shared library and tests, representative builders, a browser consumer,
manifests/debriefs, and historical browser evidence. It did not rebuild all
expensive flagship solvers, retest every hosted page or establish a fresh GPU
benchmark. Related repositories were inspected through Git trees and selected
files; their source was not modified. Subsequent experiments for the new
Research Loom study did execute the stock Blender extension, the
x3d-blender-io fork and the owned transfer/rendering routes. Their measured
scope and preservation limits are recorded in the [Blender hub
guide](../studies/research-loom/docs/BLENDER-HUB.md) and the final
[release receipt](../studies/research-loom/evidence/release.json).

## 2. What is already strong, and exactly where it stops

| Evidence | Status in this assessment | Practical consequence |
|---|---|---|
| `lib/stemkit/core.py:28` uses explicit `need()` / `Rejected`, rather than `assert`, for runtime refusals | Observed in source; the shared suite was freshly run normally and with `-O` | Reuse this pattern so optimization cannot silently remove checks |
| `core.py:37` atomically replaces payload files; PNG and deflate publishers reopen and compare decoded content | Observed in source | Preserve publication round trips and both compressed/decoded hashes when introducing a new payload type |
| `core.py:51` rejects nonfinite witness values and unsupported comparison rules | Observed in source | A malformed diagnostic cannot become a successful comparison |
| `mesh.py` checks fields, constructs surface nets, projects vertices and measures geometric properties | Observed in source; sphere/torus/step and bad-geometry controls ran in the shared suite | Reuse when a scalar-field isosurface is scientifically appropriate; do not turn every visualization into an isosurface |
| `meshio.py:19` packs positions, normals, colors and triangle indices, reporting quantization error | Observed in source; encode/decode test ran | Keep the original float arrays for analysis; the quantized mesh is a declared display representation |
| `tests/test_stemkit.py:159` keeps copied JavaScript meshers equal to the shared version | Observed; tested | This is a useful dependency-drift control when studies must serve self-contained folders |
| `studies/living-heart/src/app.js:15` checks compressed and decoded payload length/hash | Observed in source | Reuse identity checks before a scene becomes the accepted current state |
| Living Heart and Electron Cloud browser receipts bind page-source and case-manifest hashes and record reconstruction/playback checks | Recorded historical evidence, read here | These are scoped observations of those candidates, not certification of new files or new hardware |
| `docs/X3D-STEM.md` describes four lenses, three fidelity tiers and a maturity ladder | Explicit design direction, partly implemented by individual studies | Keep the direction; let current receipts determine each new study's maturity |

Fresh shared-library commands in this pass:

```bash
python3 -E -s -m unittest discover -s lib/stemkit/tests -t lib
python3 -O -E -s -m unittest discover -s lib/stemkit/tests -t lib
```

Both runs passed **14 tests**. These are shared-library tests, not a rerun of
every physics solver or a browser-rendering claim.

### Publication validity and scientific eligibility are separate gates

One boundary deserves a concrete repair in future shared infrastructure.
`Study.save_case()` at `core.py:94` records the supplied witnesses without
requiring them all to pass. Living Heart's `finish()` saves the case and its
`main()` writes the case index before collecting red witnesses and exiting
with status 1 (`tools/heart.py:319` and `:345`). Its viewer then displays a red
banner and ledger (`src/app.js:137`) rather than refusing the scientific case.

That is useful for inspecting failed research, but it is narrower than a
universal “only green cases can be published” guarantee. A robust distinction
is an inspectable **candidate** versus an eligible **published case bank**.
Keep red candidates and their explanations; update the public index only after
the configured scientific and transport gates pass. A failed candidate should
not replace the last accepted case. This recommendation follows from the code
paths just named; no new gate result is claimed here.

The design document also references `REVIEW-scientific.md`, `loomkit.sci` and a
shared `x3d-stem-science` acceptance profile. Those implementations are not in
the inspected STEM tree. Treat them as external dependencies or planned
integration until their exact source, version and invocation are supplied.

## 3. Three cases with broad research value

The selected cases complement the existing specialist flagships. Each uses a
clean mathematical reference, a useful visual vocabulary, and a data format a
researcher can reuse. Actual new-case results belong to the new study's own
receipts, not to this baseline assessment.

| Case | Researchers who can use its method | Visual construction | Independent questions to check |
|---|---|---|---|
| **Flow Loom: ABC vector field** | Fluid dynamics, transport, dynamical systems, field integration, scientific software | Speed-colored paths, active trajectory prefixes and saved tracer positions in a periodic domain | Does numerical curl match velocity? Is divergence zero? Do RK4 paths refine against a separate integrator? Are periodic cuts drawn without spurious crossing segments? |
| **Tensor Loom: covariance and PCA** | Imaging, ecology, experimental physics, materials, multivariate measurement | A measured/synthetic point cloud, principal axes, covariance ellipsoids and projection diagnostics | Do eigenpairs reconstruct covariance? Are eigenvector signs handled without implying uniqueness? Does a purported probability region have the required Gaussian and parameter assumptions? |
| **Resonance Loom: membrane modes** | Acoustics, mechanics, imaging, modal analysis and numerical PDEs | A diverging-color displacement surface, zero-displacement nodal lines and a spectrum | Do fixed edges remain zero? Do discrete eigenvalues converge to the analytic frequencies? Are displacement and color linked to the same stored state? |

### Flow: a beautiful curve does not establish chaos

For the standard dimensionless ABC field,

\[
u=(A\sin z+C\cos y,\;B\sin x+A\cos z,\;C\sin y+B\cos x),
\]

direct differentiation gives `div u = 0` and `curl u = u`. These identities are
strong controls for field sampling and coordinate transforms. They do not
measure a Lyapunov exponent or prove that every displayed path is chaotic.
The original ABC-flow study is Dombre and colleagues, *Journal of Fluid
Mechanics* 167 (1986), DOI
[10.1017/S0022112086002859](https://doi.org/10.1017/S0022112086002859).

A steady field makes streamlines and particle pathlines share integral curves,
though their parameterization may differ. An imported time-dependent field
does not inherit that equivalence. Record seeds, integration interval,
tolerances, periodic domain and the reason a path terminates. A tube radius is
an authored glyph size unless a physical cross-section has been calculated.

### Tensor: state which ellipsoid is being drawn

A covariance ellipsoid is useful across disciplines because its directions
show correlation and its axes show directional spread. For known Gaussian
mean and positive-definite covariance, a region
`(x−μ)ᵀΣ⁻¹(x−μ) ≤ χ²₃(p)` has probability `p`. A fitted covariance contour is
not automatically an exact finite-sample confidence region for the unknown
mean. Sample-based prediction and mean-confidence regions require their own
statistical construction.

The [NIST multivariate-normal definition](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc542.htm),
[NIST principal-component properties](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc551.htm)
and [Penn State STAT 505, multivariate normal distribution](https://online.stat.psu.edu/stat505/Lesson04)
are appropriate study companions. Retain the raw points, fitting convention,
centering/scaling choice and rank. A spherical covariance has no unique
principal directions; repeated eigenvalues should be compared through invariant
subspaces or reconstruction, not a particular vector sign.

### Resonance: a membrane is a model with explicit boundaries

For an ideal uniform membrane fixed on a rectangle, the modes are
`sin(mπx/Lx) sin(nπy/Ly)` and
`ωmn = cπ√((m/Lx)²+(n/Ly)²)`. A square's `(m,n)` and `(n,m)` modes can be
degenerate. Their superpositions can change the nodal picture while retaining
the same frequency. The [Penn State acoustics demonstration](https://www.acs.psu.edu/drussell/Demos/rect-membrane/rect-mem.html)
and [University of Texas wave notes](https://farside.ph.utexas.edu/teaching/315/Waves/node56.html)
give authored university treatments of this model.

This is a tension-dominated, small-displacement membrane model. A thick bending
plate, a free boundary, anisotropic material or a nonlinear large-amplitude
response needs a different operator and references. Height exaggeration and
slow playback should be declared display transforms. At a zero-displacement
instant the membrane can still have kinetic energy.

## 4. One scientific object, several hub representations

Keep numerical arrays and scientific metadata as the canonical object.
Renderers receive derived geometry and appearance. This prevents a successful
mesh transfer from being mistaken for preservation of the underlying field,
uncertainty model or simulation procedure.

| Hub | Useful import/export route | What should survive | What must be separately preserved or checked |
|---|---|---|---|
| Python / NumPy / SciPy | Arrays, explicit JSON metadata and CSV for bounded tabular exchange | Values, units, coordinate order, indices, sample time, masks and stable IDs | Dtype, missing-value policy, row association, precision and provenance |
| X3D / X_ITE | Standard mesh, line and point nodes plus scene metadata; optional behavior nodes | Inspectable scene graph, geometry, colors, viewpoints, authored interaction when supported | Original numerical fields, solver configuration, transfer function and consumer node coverage |
| Blender 5.2+ | Scoped X3D import/export or explicit data-to-geometry bridge; `.blend` for publication scenes | Geometry and identity within the tested subset; selected colors/materials and cameras when measured | Scientific arrays, units, glyph meaning, alpha/color-space mapping, unsupported nodes and event semantics |
| VTK / ParaView | VTP for point/line/surface data; VTI for regular image grids; save scientific arrays with point/cell associations | Typed geometry and arrays, component counts, origin/spacing for grids | Array association, coordinate ordering, time series and field metadata need round-trip checks |
| napari | Points/vectors/surfaces and image arrays; CSV or Python adapter with explicit axis mapping | Sample coordinates, features and transforms within the layer model | napari's axis order, `scale`, `translate`, `units` and physical calibration |
| Matplotlib / notebooks | Consume arrays directly for reference plots and publication figures | Plotted data and explicit projection/normalization | A figure backend is not a native X3D scene exporter; return to arrays or the common scene representation |
| glTF / GLB or USD | Secondary appearance/asset transport when a destination requires it | Selected mesh/material/animation features | Per-tool extension coverage, scientific arrays, identity, units and round-trip loss; measure before promoting |

The [VTK XML specification](https://docs.vtk.org/en/latest/vtk_file_formats/vtkxml_file_format.html)
distinguishes structured ImageData (`.vti`) from polygonal PolyData (`.vtp`) and
defines point/cell data associations. The [ParaView saving guide](https://docs.paraview.org/en/latest/UsersGuide/savingResults.html)
separates saving datasets from exporting a rendered scene and lists X3D among
scene exports. Exporting a scene is therefore a useful visual bridge; it does
not by itself reconstruct the filter pipeline or prove that all source arrays
remain available.

The [napari Points guide](https://napari.org/stable/howtos/layers/points.html)
and [unit-aware rendering guide](https://napari.org/0.8.0/guides/units.html)
make scale and transforms first-class concerns. Use an explicit axis table
rather than guessing that a three-column array has the same order in every
tool. [Matplotlib's documented backends](https://matplotlib.org/stable/users/explain/figure/backends.html)
support screen and figure-file outputs; a custom X3D writer should be described
as project code rather than an assumed Matplotlib feature.

## 5. Blender: three routes, three distinct evidence claims

The [official Web3D X3D/VRML2 extension](https://extensions.blender.org/add-ons/web3d-x3d-vrml2-format/)
advertises X3D 3.3 support. Its [version history](https://extensions.blender.org/add-ons/web3d-x3d-vrml2-format/versions/)
lists extension 2.5.2 and compatibility with Blender 4.2 LTS and newer. That
advertised range is a reason to test Blender 5.2; it is not a measured result
for a particular scientific scene or a claim of X3D 4 feature parity.

The ecosystem also has `hagopjay/x3d-blender-io`. The inspected docs teardown,
`x3d.docs@5ee6469:docs/x3d-blender-io/MASTERCLASS.md`, reads that fork at
`e071a61` and identifies an IR-based X3D 4 export path plus legacy import paths.
It explicitly states that the add-on was not executed in Blender for that
analysis. Its AST node inventory is evidence of source coverage, not a
feature-by-feature round-trip result.

| Route | Proper use | Required evidence before a compatibility claim |
|---|---|---|
| Official extension, X3D 3.3 subset | Broadly available baseline for supported mesh/line/point scenes | Exact Blender and extension version; imported/exported fixture counts, bounds, topology, colors and axis checks |
| x3d-blender-io fork, X3D 4 path | Candidate for richer materials, metadata and scene features | Exact fork commit, chosen import/export path, option values and per-feature tests; AST presence alone is insufficient |
| Research Loom's scoped adapter | Predictable transfer of this study's declared geometry/data subset | Clear supported-node/field list, refusal of unsupported input, numerical round trip and renderer receipt |

Use the same small fixture suite across all three routes. Include an asymmetric
chiral shape, colored indexed mesh, open polyline, point cloud, transparent
surface, camera, non-default scale, and a deliberately unsupported node. A
“loaded without exception” check is only the first row of the suite.

### Coordinate and unit contract

X3D establishes a right-handed Cartesian system with +Y up; see the
[standard's coordinate section](https://www.web3d.org/documents/specifications/19775-1/V4.0/Part01/concepts.html).
A useful explicit mapping to Blender's Z-up coordinates is
`(x,y,z) → (x,−z,y)`, with inverse `(x,y,z) → (x,z,−y)`. This is a proper
rotation with determinant +1; simply swapping two axes would reverse
handedness. A unit conversion is a separate scale factor and must not be
silently folded into an unexplained transform.

Test point coordinates, pairwise distances, oriented volume, transformed
normals and the inverse mapping. For arbitrary nonuniform transforms, normals
need the inverse-transpose rule. Do not compare an authored thick tube mesh to
the source polyline as if both were the same scientific geometry: compare its
retained centerline, and declare the radius as a display choice.

For materials, test which colors the destination actually uses and record the
color-space assumption. For time, state whether a transfer preserves discrete
checkpoints, bakes keyframes, approximates an interpolator or exports one static
state. Simulation regeneration from an edited Blender mesh is a separate
inverse problem and should not be implied by a geometry round trip.

## 6. The Loom technique applied to transfer and publication

| Gate | Question it answers | A useful bad control |
|---|---|---|
| Source binding | Are these receipts attached to the exact model, importer, exporter and case bytes? | Change a producer file or payload after the receipt is made |
| Scientific reference | Does the model meet its declared analytic/reference comparison? | Alter a sign, unit or eigenvalue |
| Refinement | Is the numerical result stable under the stated discretization change? | Increase integration step enough to violate its bound |
| Geometry reconstruction | Do emitted positions, indices and arrays match the accepted model? | Drop a triangle, reorder points without associated arrays, or change handedness |
| Transport round trip | Did a destination preserve the properties the adapter promises? | Suppress a point-data array or change axis scale |
| Display mapping | Are colors, glyph sizes, clipping and normalization traceable? | Independently rescale one field or color a different frame |
| Frame coherence | Do label, measurements, visible geometry and downloaded export name the same state? | Finish an obsolete asynchronous load after a newer one |
| Public eligibility | Can only accepted candidates replace the published index? | Attempt to publish a case containing a red or missing mandatory witness |
| Render receipt | Which software, device, camera and representation produced the image? | Reuse a receipt for another camera, source or renderer |

This makes beauty an inspectable product of the same accepted scientific case.
An offline Cycles image may use authored lighting and smooth glyphs while the
scientific coordinates remain bound to their source. Its caption should name
the render route and distinguish appearance from physical emissivity,
temperature or probability density. XSD validity checks vocabulary and
structure; it is one gate rather than a proof of scientific correctness or
cross-renderer fidelity. Web3D's [schema resources](https://www.web3d.org/specifications/)
and [X3D architecture](https://www.web3d.org/documents/specifications/19775-1/V4.0/Part01/concepts.html)
are the governing references for that distinction.

## 7. Foldback into the family

**Into x3d.STEM:** keep the three cases and interchange code together under one
research study. Reuse `stemkit` publication where its assumptions fit, retain
raw arrays alongside sampled geometry, and expose the evidence ledger from
every lens. Promote the candidate/publication distinction into shared code
after its behavior is exercised by negative controls.

**Into x3d.demo:** offer an unnumbered Research Loom entry with a verified live
URL, source link, preview provenance and concise scope. Its README and changelog
preserve old versions and reserve front-page numbering for the shelf's owner.
Do not copy a historical browser result onto a new version or claim a new live
deployment from a local bundle.

**Into x3d.docs:** turn successful transfer measurements into a compact chapter
with exact tool versions, a feature-loss matrix and drills that deliberately
break handedness, array association and frame identity. Reuse
`docs/learn/AUTHORING.md`'s distinction between measured, reasoned and suspected
claims. The source chapters' numerical and AST claims remain dated to their
own source snapshots until rerun.

## 8. Three bounded next iterations

| Iteration | Deliverable | Exit condition |
|---|---|---|
| **1. Portable research cases** | The three checked cases, a single coordinate/data contract, CSV and VTK routes, X3D scenes and a Blender subset path | Independent scientific comparisons pass; exported arrays and geometry round-trip under declared tolerances; unsupported content is refused or recorded |
| **2. Measured hub matrix** | The same fixtures through stock Blender, the fork, ParaView and napari, plus one domain-expert comparison per case | Versioned receipts distinguish preserved, transformed, omitted and untested features; scene and data round trips are reported separately |
| **3. Researcher-owned datasets** | A documented importer for each chosen case family, a reproducible notebook and a publication scene recipe | A researcher can replace the synthetic data, preserve units/IDs/masks, reproduce the numerical checks and regenerate a citable figure without editing scene internals |

Broader formats, remote GPU streaming and larger case banks can follow those
measured seams. The priority is a researcher being able to answer a question,
inspect the calculation and carry the same scientific object into another hub
without losing its meaning.
