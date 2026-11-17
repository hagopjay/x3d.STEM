# Blender as a measured Research Loom hub

The working target is **Blender 5.2.4 LTS**, executed here in background mode.
The official Linux archive was downloaded from the vendor's release directory
and matched its published SHA-256:

`2fd14c50987426897ba60237ee996edf2b4151f4b1a72a460ca20be58c1d2d86`.

The scientific case remains the authority. Blender supplies authoring,
presentation and offline rendering. A scene made from a saved case does not
turn an analytic example into an experimental measurement, and a geometry edit
does not rerun the solver's scientific witnesses.

## Three routes with different contracts

| Route | Executed version | What the bounded probe established | Boundary |
|---|---|---|---|
| Research Loom owned adapter | Blender 5.2.4 LTS | Selected mesh, sampled line and observation glyph geometry survives import → `.blend` save → reopen → export, with measured coordinates, connectivity and color comparisons | Only owned geometry records and their grouping; arbitrary modifiers, material graphs and animation are outside the contract |
| Official Web3D extension | 2.5.2, commit `a173dfb0d5e8089158d1def9edf0dda33fccea1f` | A 3.3 fixture imports mesh, curve and point-only mesh; its stock export writes a 3.0 header and retains the triangle | In this fixture, line and PointSet exports, vertex colors and scientific metadata are omitted |
| `hagopjay/x3d-blender-io` | Commit `044bea3ae33a991f816de15a307826b6d7f576ec` | Its modern 4.0 route retains the triangle, line, colors, PhysicalMaterial, head provenance and Shape metadata | The fixture's PointSet is omitted and the exporter says the object has no exportable faces |

These are executed **fixture observations**, not general conformance verdicts.
The extension receipts use `status` for successful execution of the import/export
probe and `retention_status` for preservation. Both external routes are `lossy`
for this fixture. The fork's manifest declares 2.6.4 while its exported generator
string says 2.6.1; the commit hash is the unambiguous tested identity.

The official extension advertises X3D 3.3 support and compatibility with Blender
4.2 and newer. This does not make it a general X3D 4 importer. The ecosystem
fork has a separate modern parser/populator/exporter path; it should be assessed
on its own evidence rather than inheriting the stock extension's limitations.
The owned adapter offers a small, explicit scientific contract independent of
which third-party extension is installed.

The three retained demonstrations were all executed on Blender 5.2.4 LTS:

| Case and saved frame | Maximum coordinate error after `.blend` save/reopen | Cycles CPU still, 1280 × 960, 24 samples |
|---|---:|---:|
| Balanced flow, frame 4 | `1.48 × 10⁻⁷` | 51.0 s |
| Correlated tensor, frame 4 | `1.20 × 10⁻⁷` | 89.4 s |
| Degenerate modes, frame 1 | `9.54 × 10⁻⁸` | 60.8 s |

Each transfer also changes one actual Blender vertex with source metadata left
unchanged, verifies that the comparison fails, then restores that vertex. This
control guards against accidentally treating retained metadata as proof of a
geometry round trip. The three PNGs were visually inspected for framing.

## Coordinate and color contracts

Packet coordinates are right-handed Y-up. Blender coordinates are right-handed
Z-up. The adapter uses the proper rotation

| Operation | Mapping |
|---|---|
| Packet → Blender | `(x, y, z) → (x, −z, y)` |
| Blender → packet | `(x, y, z) → (x, z, −y)` |

The rotation has determinant +1 and preserves length, orientation and scale.
There is no automatic normalization to a unit cube or implicit unit change.
Each case retains its declared units and axis explanation.

Mesh vertices and polygon connectivity become Blender mesh data. Sampled
polylines become circular presentation tubes, and observations become grouped
icosphere glyphs. Their radii are authored visual encodings, not measured field
values. Export reads actual mesh coordinates, tube-ring centers and glyph
centers, applies world transforms, and compares them to the source frame.
It does not simply return cached source coordinates. Topology changes that
break grouping and nonuniform glyph scaling are refused.

Scientific colors are declared sRGB display values. The adapter uses the
piecewise sRGB transfer function to store Blender's linear point-color
attributes. A real control caught an avoidable problem: Blender's convenience
`color_srgb` accessor introduced about `3.5×10⁻⁵` round-trip error. Explicit
conversion reduced the measured control color error to about `1.1×10⁻⁸`.
This numerical color check is separate from the rendered image: lights,
transparency, shading and the display transform affect pixel appearance.

The saved `.blend` includes a `ResearchLoom_Source.json` text block and source
identity properties. The round-trip JSON retains scientific measurements and
witnesses as historical provenance, marked as **not recomputed after edits**.
To make a new scientific claim after an edit, regenerate the corresponding data
and rerun its model witnesses.

The text block uses a versioned zlib/base85 envelope, bounded 96-character
chunks, decoded byte count and SHA-256. This is a practical Blender finding:
inserting a 4–6 MB single-line canonical JSON string into a Text block was
extremely slow, even though mesh creation had finished. The chunked encoding
reduced the measured membrane import to about one second while preserving the
complete source packet. Decoding checks framing, byte budget and content hash;
the reader also accepts the earlier plain-JSON owned format.

## Reproduce an owned transfer

Use a built case packet and select a saved frame:

```sh
blender --background --factory-startup --threads 2 --python-exit-code 1 \
  --python tools/blender_bridge.py -- \
  --packet exports/tensor-correlated/8ef744e525ebc928/packet.json --frame 4 \
  --output-blend exports/blender/scientific-tensor.blend \
  --roundtrip exports/blender/tensor-roundtrip.json \
  --receipt evidence/blender-transfer-tensor.json
```

Regeneration may change the content-addressed path; use the location written
by the builder in that case. The
`--python-exit-code 1` switch matters: Blender can otherwise report a Python
exception while its process exits successfully. The script saves the scene,
reopens the file, exports the measured geometry and writes a receipt. It raises
if the comparison fails its declared `3×10⁻⁶` absolute coordinate/color budget.

The pure Python tests check rotation/inverse/handedness, the sRGB transfer,
invalid geometry, and healthy-versus-perturbed coordinate/color/topology twins.
They are not a substitute for the executed Blender receipts.

The transfer tool is a certification-style unchanged round-trip check. To keep
an intentional edit from an already open owned `.blend`, use Blender's Python
console instead of rerunning an import that would replace it:

```python
import sys
sys.path.insert(0, "/absolute/path/to/studies/research-loom")
from stemloom.blender_io import export_case, save_json
save_json("/absolute/path/edited-frame.json", export_case())
```

That JSON is a derived geometry artifact. Its `transfer` record identifies the
source and says the retained scientific measurements are historical. Recompute
the relevant model or data analysis before treating an edit as a new result.

## Reproduce the external extension probes

Clone each source at the tested commit. The probe loads the source package into
a private Blender process; it does not alter global extension preferences.
Enable only one extension route in a process, since both register the same
import/export operator names.

```sh
blender -b --factory-startup -t 2 --python-exit-code 1 \
  --python tools/blender_bridge.py -- \
  --probe-extension /path/to/io_scene_x3d/source --extension-route stock \
  --receipt evidence/blender-stock-extension.json

blender -b --factory-startup -t 2 --python-exit-code 1 \
  --python tools/blender_bridge.py -- \
  --probe-extension /path/to/x3d-blender-io/source --extension-route fork \
  --receipt evidence/blender-ecosystem-fork.json
```

The fixture is authored in the script and its hash is recorded. It combines a
colored triangle, colored line, colored PointSet, scientific unit metadata and
a case identifier. Read primitive counts and preservation fields in addition to
the execution status. A useful next contribution to the fork is an explicit
point-only-mesh → PointSet export control.

## Publication rendering is its own lens

`tools/render_blender.py` renders the same selected packet frame with Cycles on
the CPU. The studio camera, lights, ceramic floor, PBR response and glyph radii
are authored appearance. They live in a separate presentation collection and
are excluded by the owned scientific export. No scientific surface is smoothed
or displaced by the renderer. The renderer's receipt binds the packet, frame,
adapter, rendering script and PNG bytes, names CPU threads, samples and image
dimensions, and states that this is an offline still.

```sh
blender -b --factory-startup -t 2 --python-exit-code 1 \
  --python tools/render_blender.py -- \
  --packet exports/tensor-correlated/8ef744e525ebc928/packet.json --frame 4 \
  --output docs/assets/tensor.png --output-blend exports/blender/tensor.blend \
  --receipt evidence/blender-render-tensor.json --samples 24
```

No browser-identical pixels, real-time frame rate or GPU benchmark is claimed.
Blender 5.3 and later remain compatibility targets until separately executed.

## A measured glTF/GLB continuation

`tools/export_glb.py` uses Blender's bundled glTF 2 exporter on the scientific
collection only. It excludes the studio floor, lights and camera, retains
identity extras and vertex colors, checks GLB header/chunk/buffer framing,
re-imports through the bundled importer, and compares expanded geometry in both
directions with a KD tree. glTF triangulation and normal/color-driven vertex
splits are permitted. This is the rendered mesh/tube/glyph representation;
line centerlines, solver state and arbitrary domain variables remain in the
case packet rather than being inferred from glTF triangles.

```sh
blender -b --factory-startup -t 2 --python-exit-code 1 \
  --python tools/export_glb.py -- \
  --input-blend exports/blender/scientific-tensor.blend \
  --output exports/blender/tensor.glb \
  --receipt evidence/blender-glb-tensor.json
```

Color precision is measured at two different boundaries. The serialized
GLB's FLOAT `COLOR_0` arrays can retain the linear vertex colors. Blender 5.2's
glTF importer allocates `BYTE_COLOR` attributes, so importing the GLB again
quantizes display colors. The receipt records the serialized float-color error
separately from that re-import error, with a bound derived from half an 8-bit
sRGB step. This is a concrete reason to retain raw scientific variables rather
than trying to recover them later from rendered colors.

Use `python3 tools/export_glb.py --self-check` for GLB structural controls without
Blender. The actual hub receipts additionally bind source `.blend`, source case,
Blender version, GLB bytes and the exporter script.

## Primary references

- [Blender 5.2 LTS releases](https://www.blender.org/releases/5-2/)
- [Official release archive and checksum files](https://download.blender.org/release/Blender5.2/)
- [Official Web3D X3D/VRML2 extension](https://extensions.blender.org/add-ons/web3d-x3d-vrml2-format/)
- [Official extension source](https://projects.blender.org/extensions/io_scene_x3d)
- [Ecosystem X3D 4 fork](https://github.com/hagopjay/x3d-blender-io)
- [Blender 5.2 Python API](https://docs.blender.org/api/5.2/)
