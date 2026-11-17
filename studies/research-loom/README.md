# Research Loom · three scientific instruments

Three practical, visually directed scientific studies share one measured route
from Python arrays to X3D, Blender 5.2+, VTK/ParaView, and common geometry/data
formats. Each case retains raw variables, units, source identities, saved states
and explicit numerical witnesses. Data is analytic or synthetic; appearance is
authored. The interactive view and the offline studio renders use the same case.

| Instrument | Useful question | Research transfer |
|---|---|---|
| Flow Loom | Can a steady field produce complicated particle routes? | Check integration, seeds, speed colors and periodic seams before interpreting CFD or field-line data. |
| Tensor Loom | What does a 95% ellipsoid mean, and what can it conceal? | Import an x,y,z CSV cloud; study covariance, PCA, Mahalanobis distance and the Gaussian assumption. |
| Resonance Loom | Can one frequency produce changing shapes? | Separate continuum modes, discrete eigenproblem accuracy, nodal geometry and display magnification. |

The distribution includes **nine cases, 78 saved states and 63 declared
scientific witnesses**. Playback selects saved states; it does not run an
unseen frontend solver or invent intermediate scientific states.

## Open the ready-to-run distribution

From the focused ZIP's root, run:

```sh
python3 run_research_loom.py --open
```

On Windows, use `python run_research_loom.py --open`. On WSL/Linux the command
above starts a loopback server at **http://127.0.0.1:8860/web/**. Browser playback
of the included bank uses Python's standard library and bundled X_ITE. No npm,
API key or Blender installation is needed to explore it.

The source repository keeps the hashes and build recipe; computed payloads and
renders are regenerated. From a source checkout:

```sh
cd studies/research-loom
python3 -m pip install -r requirements.txt
python3 tools/build.py
python3 serve.py --open
```

The local scientific imports require the NumPy/SciPy dependencies. Static
hosting can serve the prebuilt `web/`, `docs/`, `exports/` and `evidence/` paths;
CSV analysis and bounded X3D inspection use the accompanying local server.

## Start with an experiment

1. Open **Flow Loom**, compare the integrable case with the balanced ABC field,
   and follow a tracer through the periodic box faces. The full paths provide
   computed context; the active prefix gives elapsed particle time.
2. Open **Tensor Loom**, choose the 95% threshold, then compare the Gaussian
   cloud with the two-cluster mixture. A fitted contour is not a confidence
   region for the mean or a coverage guarantee for an arbitrary distribution.
3. Open **Resonance Loom**, compare equal-frequency square-membrane modes with
   the slightly rectangular case. Raw displacement is retained separately from
   the explicitly magnified display surface.

Read the [illustrated research guide](docs/Field-Guide.html), its
[text edition](docs/RESEARCH-GUIDE.md), the [exchange contract](docs/EXCHANGE-CONTRACT.md)
and the [measured Blender hub guide](docs/BLENDER-HUB.md).

## Carry your data into the instrument

**Analyze a CSV point cloud** accepts named x,y,z columns, 4–5,000 finite rows,
and a full-rank three-dimensional covariance. The browser downloads a complete
packet after analysis. Repeated imports are bound to exact input/packet identities;
editing producer source requires restarting the server.

```sh
python3 tools/hub.py import-csv cloud.csv imported.json --units micrometres --label "Particle observations"
python3 tools/hub.py export imported.json imported.x3d --format x3d4 --frame 4
python3 tools/hub.py export imported.json imported.vtp --format vtp --frame 4
```

The unit option labels existing numeric coordinates; it does not rescale them.
Imported-X3D inspection reads the documented static subset's actual nodes.
It reconstructs geometry and reports retained provenance; it does not recover a
solver or re-certify scientific claims after edits.

## Hub paths and actual limits

- X3D 4 and portable X3D 3.3 carry scene geometry and provenance. The bounded
  reader compares actual coordinates, topology, colors and appearance.
- VTP carries geometry plus named scientific arrays and validity masks. VTI
  retains the raw ABC velocity grid. The membrane's display geometry is magnified;
  its displacement and velocity arrays remain in model units.
- PLY retains geometry and 8-bit colors with a measured quantization bound. OBJ
  and coordinate CSV are explicit projections, not full scientific packets.
- The owned Blender bridge uses a proper Y-up→Z-up rotation, actual editable
  geometry, explicit color transfer and measured save/reopen/readback. Studio
  lights, floor and camera live outside the scientific collection.
- The stock Blender extension and modern ecosystem fork are separately executed
  compatibility routes. Successful execution does not imply lossless retention.

Actual Blender version, source hashes, comparisons and render settings are in
`evidence/blender-*.json`. The vendor Blender executable is not bundled.

## Reproduce the checks

The focused ZIP includes the computed bank and Blender artifacts required by
the complete release check. A source-only patch requires `tools/build.py` and
the three transfer/render/GLB commands in the Blender hub guide before that
complete check can pass. To run just the source-level scientific and exchange
suite after installing dependencies, use `python3 -m unittest discover -s tests`.

```sh
python3 tools/check.py
```

This runs model, hub and HTTP tests normally and under Python `-O`, the shared
stemkit controls, a UI ordering harness, actual VTK readers, and pinned X3D 4
schema/semantic checks. Scientific gates use explicit rejection, so optimization
cannot disable them. The published bank is exposed only after every candidate
and export succeeds. Imported geometry is explicitly separated from fresh
scientific certification.

Native X_ITE browser pixels remain unverified on this host because browser
socket operations are blocked. Blender Cycles CPU stills have separate real
render receipts; they are not represented as browser screenshots or GPU tests.

See [foldback findings](docs/FOLDBACK.md) for practical lessons and the root
repository assessment for the roles of x3d.STEM, x3d.demo and x3d.docs.
