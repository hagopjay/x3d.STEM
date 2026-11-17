# Research Loom

## Three instruments for seeing what equations mean

A complicated trajectory can come from an unchanging field. A beautifully fitted ellipsoid can conceal two populations. A vibrating surface can change its visible pattern without changing either modal frequency. These are useful surprises: each corrects a habit of interpretation that can survive years of working with scientific plots.

Research Loom turns those surprises into inspectable three-dimensional studies. The geometry, numerical measurements, sources and checks travel together in a case packet. X3D provides the interactive view; Blender provides an offline publication view; VTK and Python retain routes back to numerical questions. The common thread is a scientific case whose meaning can be examined before and after transfer.

The examples are synthetic and analytic. They offer controlled instruments for learning, debugging a workflow and planning a visualization of your own data. Their equations are deliberately simpler than a research experiment, so discrepancies between a mathematical statement, a numerical approximation and a visual impression remain visible.

| Start with a question | Open the instrument | Try the counterexample |
|---|---|---|
| Can steady motion look complicated? | [Flow Loom](../web/#flow-balanced) | The integrable field |
| What does “95% ellipsoid” actually mean? | [Tensor Loom](../web/#tensor-correlated) | The two-cluster mixture |
| Can one frequency produce changing shapes? | [Mode Loom](../web/#modes-degenerate) | The slightly rectangular membrane |

## Start locally

From the repository root, enter the study directory and launch the supplied server:

```sh
cd studies/research-loom
python3 serve.py --open
```

The default address is `http://127.0.0.1:8860/web/`. The server also enables the bounded CSV cloud analysis and exported-X3D inspection tools. To regenerate the case bank, use Python with NumPy and SciPy installed, then run `python3 tools/build.py` from this same directory. Rebuilding computes the models and their witnesses before publishing the bank index.

Choose a case, move through its saved states, then open **Evidence ledger**. Read the metric labels and model boundary before interpreting a striking shape. **Export this frame** follows the currently displayed state. The **Exchange** panel also offers a complete JSON packet, a reference-frame bundle and the format-specific projections. Reference-frame downloads can represent a different state from the slider; their label identifies that frame.

Playback selects saved states without interpolation. In Flow and Mode Loom the state coordinate is model time. In Tensor Loom it is a probability threshold: playing the slider does not simulate particles moving. The optional 2D projection draws the same saved positions with averaged face or segment colors. It is an additional lens, with different occlusion and appearance from native X3D.

## 01 · Flow Loom — complexity without a changing field

![Flow Loom publication view: periodic trajectories and saved tracers, colored by speed.](assets/flow.png)

The Arnold–Beltrami–Childress family supplies an exact, steady velocity field:

`u(x,y,z) = (A sin z + C cos y, B sin x + A cos z, C sin y + B cos x)`

The field has zero divergence and its curl equals the field itself. The latter is the Beltrami property. These identities hold for all three supplied coefficient choices. They are mathematical statements about the analytic field, rather than conclusions inferred from the rendered fibers.

**Aha experiment.** Open **Braids in a steady field**. Advance one saved state at a time. Faint paths give context; brighter prefixes and beads show elapsed particle time. Ask what changed: the particle positions changed, while the velocity assigned to each spatial location stayed fixed. A pathline follows one particle through time. A streamline is tangent to the velocity field at one instant. They share integral curves here because the field is steady; that shortcut generally fails in an unsteady flow.

Next choose **An exact straight-line control**. With `A=1, B=C=0`, the `z` coordinate remains fixed and each particle's velocity is constant along its trajectory. The apparent bends at opposite cube faces are periodic identification. Switch back to the balanced coefficients and then the unequal-coefficient case. A modest change in the analytic instrument reorganizes the routes while leaving the divergence and curl identities intact.

The box represents the periodic cube `[−π,π]³`. Opposite faces connect. A particle exiting one side enters the opposite side; a segment drawn straight through the whole box at that instant would be a display error. The exporter clips sampled polyline segments at the faces and starts the corresponding piece on the other side. Those intersection points are linear geometric constructions, not extra integrated particle states.

### What to measure

The metric panel reports saved time, mean speed of the shown particles and the RK4/reference discrepancy. Speed colors use one declared scale across all saved states of a case. Comparing brightness within that case is meaningful; comparing colors between cases requires checking their scale bounds. Tube width and bead size are authored glyph dimensions. Neither denotes a measured vortex radius, mass or concentration.

The main integration is fourth-order Runge–Kutta with step `0.01`. A separate [SciPy DOP853 integration](https://docs.scipy.org/doc/scipy/reference/generated/scipy.integrate.solve_ivp.html), with relative tolerance `2×10⁻¹²`, supplies a trajectory reference over 601 integration times and 40 starting particles. Central differences probe divergence and curl; a coarser RK4 run tests refinement behavior. Agreement between two algorithms helps detect an implementation error, although it does not prove a uniform error bound for all positions or all future times.

Zero analytic divergence means local volume preservation for the exact flow. It does not automatically make a finite-step numerical integrator volume preserving. Likewise, a braided finite trajectory does not establish chaos, a Lyapunov exponent or a mixing rate. The classic [ABC-flow study by Dombre and colleagues](https://doi.org/10.1017/S0022112086002859) motivates the family; this instrument makes a narrower, reproducible visualization claim.

### Carry the question into research

Use this case to test seed placement, periodic seams, coordinate conventions or a proposed streamline color map before applying that workflow to CFD, transport, geophysics or magnetic-field data. The model is a steady benchmark, without a Navier–Stokes time solver, turbulence closure, diffusion or measured boundary conditions.

The packet retains unwrapped sampled trajectories, seeds, diagnostic errors and the color transfer. Its separate `velocity_grid` dataset is a regular `9×9×9` grid of actual velocity vectors. Open `velocity-grid.vti` in a VTK-compatible hub to construct your own seeds and integration settings. Compare those results with the supplied paths, remembering that grid interpolation introduces another approximation. Preserve the packet when exporting a still: a fiber-only mesh cannot reconstruct the underlying velocity field.

## 02 · Tensor Loom — the shape of uncertainty, and its limits

![Tensor Loom publication view: fixed observations, principal axes and a fitted Mahalanobis ellipsoid.](assets/tensor.png)

A cloud has location, orientation and unequal spread. Its sample mean and covariance make those properties geometric. Tensor Loom calculates the unbiased sample covariance using denominator `N−1`, then decomposes it into principal directions and nonnegative eigenvalues. At Mahalanobis radius `r`, ellipsoid semiaxes have lengths `r√λ₁`, `r√λ₂`, `r√λ₃`. Eigenvalues themselves are squared lengths.

**Aha experiment.** Start with **Correlated cloud**, and move from the 50% contour to the 95% contour. The observations stay fixed. Mint points are inside the selected fitted contour; coral points are outside. Compare **Gaussian model probability** with **Observed points enclosed**. One is a reference probability under a model; the other is an actual count in this dataset. They answer different questions and need not agree exactly.

Notice the quiet inner rings. They mark `r=1`, which encloses about **19.9%** of a three-dimensional Gaussian population with known parameters. The familiar one-dimensional “one standard deviation is about 68%” rule does not transfer to a three-dimensional ball. For three dimensions, squared Mahalanobis distance follows a chi-square distribution with three degrees of freedom under the population Gaussian model. The 95% contour therefore uses `r = √χ²₃⁻¹(0.95)`, approximately `2.795`.

This scene fits the mean and covariance to the same finite sample being displayed. Its nominal probabilities are consequently plug-in Gaussian references, without an exact finite-sample coverage guarantee. The ellipsoid describes observation spread. It is not a confidence region for the unknown mean, and the code performs neither a covariance-by-`N` rescaling nor a Hotelling-T² inference.

### The counterexample is part of the instrument

Switch to **A beautiful but incomplete summary**, the mixture case. One smooth global ellipsoid spans two clusters and may place a visually persuasive center in a relatively empty region. The covariance calculation can be correct while a single Gaussian distribution is an inadequate description. Passing an eigendecomposition check cannot establish Gaussianity or discover every population.

Then inspect **No population favorite**. The generating population has no preferred direction, yet a finite sample produces unequal fitted eigenvalues and a displayed basis. Eigenvector sign choices are conventional. Deterministic signs stabilize files; they do not make the estimated directions scientifically unique. Near-equal eigenvalues are a reason to interpret an individual axis cautiously, especially when comparing repeated datasets.

The witnesses check covariance symmetry, reconstruction from the eigenpairs, orthonormal axes, whitening, chi-square inversion and the quadratic form of emitted shell vertices. Those checks connect the drawn surface to the actual calculation. They do not test the experimental sampling design, measurement calibration, independence of observations or distributional adequacy.

### Bring a cloud with a question

The local **Analyze a CSV point cloud** action accepts named `x,y,z` columns with 4–5,000 finite observations. It requires a reasonably conditioned full-rank three-dimensional covariance. A planar cloud is refused rather than padded into a misleading 3D ellipsoid. Imported coordinates retain their supplied numeric scale; you supply their physical interpretation and units.

This is practical for microscopy localization clouds, reconstructed landmarks, repeated sensor estimates or three comparable physical coordinates. For unrelated variables with different units, raw covariance axes can be dominated by unit choice. Decide whether a transformation, correlation analysis or domain-specific metric answers your scientific question before fitting. That decision is outside this geometric instrument.

The packet contains the original observations, sample mean, covariance, principal basis, whitened observations and each point's squared Mahalanobis distance. The VTP projection carries observation-associated principal scores, distance and the selected-contour membership indicator. The shell's positional tint is an appearance aid, without an additional measured variable. Revisit the [NIST multivariate-normal treatment](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc542.htm) and [PCA explanation](https://www.itl.nist.gov/div898/handbook/pmc/section5/pmc551.htm) when choosing how much inference your ellipsoid can support.

## 03 · Mode Loom — symmetry, degeneracy and a moving zero

![Mode Loom publication view: exaggerated transverse displacement, fixed support and sampled zero contours.](assets/modes.png)

A uniform, tension-dominated rectangular membrane with fixed edges has separable mode shapes `sin(mπx/Lx) sin(nπz/Lz)` and frequencies

`fₘₙ = (c/2) √[(m/Lx)² + (n/Lz)²]`.

Here `c=1` in normalized units. The physical domain lies in the X–Z plane and displacement is transverse. The model is an exact solution of the ideal linear wave equation, rather than a plate-bending calculation, shell finite-element model or measured material response.

**Aha experiment.** Begin with the fundamental mode and watch its fixed boundary. Next open **Different shapes, the same frequency**. In a square, modes `(1,2)` and `(2,1)` have equal frequency because swapping their indices leaves the expression unchanged. The case combines them in temporal quadrature. Their instantaneous sum changes shape, and the visible zero contours can move, while the two modal frequencies and modal energies stay fixed. A changing picture alone is insufficient evidence of energy transfer between modes.

Now choose **A small geometric change splits the pair**. One side becomes `1.12` times the other. The exchanged-index pair no longer has equal frequency. The frequency-splitting metric exposes the symmetry breaking directly. At a fixed probe, the two nearby oscillations produce a position-dependent envelope. Its beat period depends on the reciprocal frequency difference; its amplitude also depends on how strongly each spatial mode contributes at that probe.

### Read height, color and time separately

Display coordinates are `(6(x−Lx/2), 55u, 6(z−Lz/2))`. Vertical displacement is multiplied by **55**, while in-plane distances are multiplied by **6**. The resulting height exaggeration relative to lateral length is `55/6`. A tall-looking surface is compatible with a small model displacement. The raw displacement and velocity arrays remain unexaggerated.

Blue through neutral to coral encodes signed displacement on a symmetric scale fixed within the case. Mint curves are zero cuts of sampled triangles. They approximate the instantaneous nodal geometry at the display resolution; they are not a proof of the analytic nodal set. Grid lines and contours receive tiny declared display lifts for legibility. If the whole sheet is zero, it is not misrepresented as one isolated nodal line.

The beat case contains twelve saved states over two mean carrier periods. It does **not** resolve an entire long beat as a movie. A separate 161-sample analytic probe envelope spans a beat period. That envelope describes one retained probe, without claiming a universal envelope for every point on the membrane. Inspect the packet's `probe_envelope` and `beat_period` when studying slow modulation.

### Two errors that should not be confused

The science witnesses check fixed edges, the wave equation and energy using independent spatial quadrature. A separately assembled sparse finite-difference eigenproblem is compared with its closed discrete spectrum. Refinement at 12, 24 and 48 intervals compares the discrete eigenvalue with the continuum reference and checks second-order convergence.

A small algebraic eigenvector residual says the numerical pair solves the assembled discrete system well. It does not say that a coarse grid closely approximates the continuum. This distinction matters across acoustics, structural dynamics, photonics and quantum eigenproblems. The membrane offers an accessible place to rehearse it before confronting a complex solver.

The packet retains physical-grid coordinates, exact sampled displacement and velocity, frequencies, energy measurements and convergence results. VTP stores unexaggerated displacement and velocity as scientific point arrays alongside the exaggerated display geometry. Consult [Daniel Russell's university membrane demonstrations](https://www.acs.psu.edu/drussell/Demos/rect-membrane/rect-mem.html) and [Fitzpatrick's elastic-sheet derivation](https://farside.ph.utexas.edu/teaching/315/Waves/node56.html) for the modal context.

## A scientific case across several hubs

Choose a route according to the question you want to preserve. Geometry interchange, data interchange and solver reconstruction require different contracts.

| Destination | Take this representation | Keep in mind |
|---|---|---|
| Interactive X3D | Current-frame `.x3d` | Static geometry and appearance; the packet retains all states and science |
| Blender publication work | Owned bridge and packet | Coordinates, grouping and colors are measured after save and reopen |
| ParaView / VTK analysis | `.vtp`, plus flow `.vti` | Named arrays and associations survive; display geometry is not automatically a solver mesh |
| Python / notebooks | Complete case JSON | Original observations, unwrapped paths or raw membrane arrays remain available |
| Broad geometry tools | OBJ or PLY | OBJ loses appearance; PLY colors have 8-bit quantization and reduced semantics |
| Spreadsheet inspection | Geometry CSV | Rows are displayed geometry samples, not automatically original observations |

VTK PolyData retains mesh, line and vertex cells plus named scientific arrays. Where a record lacks an array, an explicit `<name>__valid` mask distinguishes missingness from zero. ImageData retains the flow's regular vector lattice with checked x-fast ordering. These choices follow [VTK's XML data model](https://docs.vtk.org/en/latest/vtk_file_formats/vtkxml_file_format.html); they preserve more analytical meaning than a screenshot.

Blender 5.2.4 has three separately measured routes here. The stock 2.5.2 extension imports the mixed 3.3 fixture, but its export writes a 3.0 header and drops the fixture's lines, points, vertex colors and scientific metadata. The tested ecosystem fork's modern 4.0 path retains its mesh, line, colors, PBR material and metadata, while omitting the PointSet. These are bounded fixture observations, without a general verdict on every file the extensions support.

The owned bridge instead targets this study's geometry records. It applies `(x,y,z) → (x,−z,y)` from right-handed Y-up to Blender's right-handed Z-up, with an explicit inverse. It saves and reopens the `.blend`, then reads actual mesh positions, tube centers and glyph centers for comparison. Metadata alone cannot establish a successful transfer. Presentation lights, camera and floor belong to a separate collection. The resulting render is an authored offline still with its own receipt.

Read the [exchange contract](EXCHANGE-CONTRACT.md) and [measured Blender hub guide](BLENDER-HUB.md) for exact supported subsets, losses and commands. Editing a mesh does not recompute the original scientific witnesses. Historical measurements retained with an edited file remain provenance; a new scientific claim requires regeneration and renewed model checks.

## Follow the thread of evidence

The local Loom sequence is deliberately inspectable: a candidate case passes invariants and independent references; written bytes are reopened and hashed into an immutable bank; the selected X3D frame is checked against its recorded identity; a hub reads back actual geometry; each renderer records its own output and scope. A hash identifies bytes. A scientific witness tests a stated relationship. A rendered image communicates a selected view. Each serves a different purpose.

The current bank contains nine cases, 78 saved states and 63 declared scientific witnesses: three flow cases, three clouds and three membranes. These counts describe the authored bank, rather than a certification by an external Loom profile. The executed [build receipt](../evidence/build.json), [verification receipt](../evidence/verification.json) and [Blender contract](BLENDER-HUB.md) identify their instruments and boundaries. Consult the accompanying review evidence for final execution status instead of inferring it from this guide or a hero image.

A useful research session ends with a sharper question: which observed structure follows from the equation, which depends on the numerical method, and which comes from the visual encoding? Keep the packet with the figure, record the selected case and frame, and make those distinctions available to the next person who opens your work.
