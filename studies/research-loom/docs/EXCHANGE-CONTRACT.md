# Research Loom exchange contract

The canonical artifact is a case packet containing saved frame geometry,
scientific arrays, units, sources and witnesses. A rendered scene is one view of
that packet. The adapters deliberately distinguish geometry interchange from
scientific-data interchange and from an editable simulation checkpoint.

## Implemented routes

| Route | Preserved | Declared boundary |
|---|---|---|
| Packet → X3D 4.0 | World-coordinate meshes, triangle/quad topology, polylines, points, RGB, vertex RGB, opacity, IDs, case/frame hashes, coordinate/units metadata | Static frame; no browser controls, solver, animation system or raw scientific array reconstruction |
| Packet → X3D 3.3 | The same bounded standard-node subset | Portable geometry projection for consumers such as Blender's stock X3D extension; a consumer's preservation of metadata/colors must still be measured |
| Owned X3D → frame | Actual parsed coordinate/color/index values, geometry IDs, appearance opacity and authored glyph/centerline radii | Only the writer's declared static subset; no arbitrary X3D world import |
| Packet → VTK `.vtp` | Float64 positions, polygon connectivity, polyline cells, vertex cells, RGBA8, record/local indices, metadata, optional scientific point arrays | Display geometry is not automatically a volume or a solver mesh; missing scientific attributes carry an explicit validity mask |
| Regular vector grid → VTK `.vti` | Uniform origin/spacing, complete regular grid, Float64 vector velocity/speed, units metadata | Point-associated regular grids only, maximum 250,000 points; supplied coordinates establish x-fast VTK ordering |
| Packet → OBJ | Vertices, polygon faces, polyline and point elements | No material colors, opacity, glyph radii, units schema or scientific arrays; provenance appears only in comments |
| Packet → ASCII PLY | Float64 vertex text, RGB/alpha quantized to 8-bit, face connectivity, optional edge elements | Group/polyline identities, glyph radii, units schema and scientific arrays are lost; consumers may ignore the optional edge element |
| Packet → geometry CSV | Every displayed sample's group, ID, local index, XYZ and RGB | This is a long-form geometry table, not automatically the original observations or vector grid; use the separate raw-data exports for analysis |

Writers validate before serializing. They do not mutate the incoming packet.
Coordinates are expressed with seventeen significant decimal digits, retaining
binary64 values in text round trips. X3D `Coordinate` remains a single-precision
rendering field: exact text is distinct from a renderer's in-memory/pixel
precision. There is no implicit centering, unit rescaling or axis swap in these
writers. Scientific coordinates use the packet's declared right-handed Y-up
convention; the Blender adapter owns its separate proper rotation.

## Owned X3D subset

The writer uses Interchange-profile `IndexedFaceSet`, `IndexedLineSet`,
`PointSet`, `Coordinate`, `Color`, `Material`, grouping, lights, viewpoint and
metadata. There are no external textures, scripts, URLs, node imports or
transforms. Shape DEF names derive from source IDs; a sanitization collision
fails rather than silently merging objects. The scientific geometry has no
unrecorded floor, pedestal or camera-facing helper embedded in it. All saved
frames of a case share one bounds-derived viewpoint, so selecting a frame does
not change the viewing scale.

`from_x3d(text)` reads coordinate and index fields. It does not restore a hidden
copy of vertices from metadata. Editing a valid coordinate therefore changes
the imported geometry, while editing an index out of bounds refuses the import.
The returned frame includes metadata with both the declared provenance and a
fresh geometry identity diagnostic. Opacity is normalized through X3D
transparency (1−opacity) for that diagnostic, avoiding false edits from harmless
binary64 complement roundoff. A declared hash is not authentication.
Camera, lights, specular highlights and emissive appearance are not imported as
scientific variables. Scientific `point_data` arrays stay in the case packet
and VTK export; the X3D subset does not claim to recover them.

The reader refuses DTD/entity declarations, unsupported elements, unsupported
attributes, references, scripts, `Inline`, `Transform`, per-face color indexing,
line topologies beyond one ordered polyline per record, nonfinite values,
invalid RGB, malformed faces and excess budgets. It accepts at most 32 MiB,
30,000 coordinates, 10,000 triangle/quad faces and 250 geometry records, with an
XML depth limit. Both 3.3 and 4.0 documents must identify this adapter. It is not
a general replacement for a full X3D parser, a browser, or Blender's extension.

## Scientific point arrays and missingness

A geometry record can carry:

```json
{"point_data":{"displacement":{"components":1,"units":"m","values":[0.1,0.2,0.3]}}}
```

Each array must have one finite scalar or three-vector per position. VTK exports
combine same-named arrays only when components and units agree. Records lacking
an array receive zero-filled values **and** `<name>__valid = 0`; present values
receive a mask of one. A missing value therefore cannot silently become a
measured zero. Array units and mask meaning are retained as UTF-8 metadata.
ColorRGBA, geometry_record, geometry_kind and local_index are reserved names.

The VTI writer checks every supplied coordinate against the declared regular
lattice and maps its velocity to `i + nx*(j + ny*k)`. Duplicate, missing or off-grid
locations fail. This explicitly handles an input generator whose flattening
order differs from VTK's x-fast convention.

## Evidence and interpretation

`tests/test_exchange.py` checks actual edited X3D geometry, both X3D versions,
unsafe/unsupported XML controls, malformed coordinates/colors/indices, OBJ/PLY
connectivity, geometry CSV, and the installed VTK readers. The VTP test checks
cell types, colors, a scientific array and missingness. The VTI test deliberately
provides z-fast input, then asks `vtkXMLImageDataReader` for vectors at actual
XYZ locations. Those are executed reader checks, not a claim that ParaView's
interactive UI was run. A pinned X3D 4.0 XSD/semantic check also accepts the
mixed mesh/line/point fixture.

Primary references:

- [VTK XML file formats](https://docs.vtk.org/en/latest/vtk_file_formats/vtkxml_file_format.html): PolyData cells, ImageData extents/origin/spacing and point association.
- [X3D specifications](https://www.web3d.org/specifications): standard geometry and metadata are distinguished from application-level semantics.
- [Blender Web3D extension](https://extensions.blender.org/add-ons/web3d-x3d-vrml2-format/): the stock extension advertises X3D 3.3; its operator/runtime evidence is tracked separately from this adapter.
