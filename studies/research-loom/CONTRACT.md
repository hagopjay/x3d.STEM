# Research Loom case packet, version 1

All authored model modules expose `build_case(preset="default") -> dict` and
`PRESETS` (mapping id to title/description). Root builder invokes each case.
Only deterministic NumPy/SciPy generators run in Python; browser selects saved
cases and frames. No frontend solver or arbitrary expression evaluation.

Case fields: `id` (safe slug), `kind` (`flow`, `tensor`, `modes`), `title`,
`question`, `description`, `scope`, `parameters` (JSON), `units` (mapping),
`axes` (explanation string), `sources` ([{title,url,note}]), `insights` (strings),
`frames`, `measurements` (JSON-safe raw numeric arrays/results), `witnesses`.
Optional `datasets` contains raw scientific arrays with clear semantics.

Each frame: `time` (finite float), `meshes`, `lines`, `points`, `metrics`.
Each geometry collection can be empty. IDs unique per frame across collections.

- Mesh: `{id, positions:[[x,y,z],...], faces:[[i,j,k],...], color:[r,g,b],
  colors:[[r,g,b],...] (optional per vertex), opacity:0..1}`. Faces triangles or
  quads, no -1 separators. No node transforms; positions in case coordinates.
- Line: `{id, positions:[[x,y,z],...], color:[r,g,b], colors:[[r,g,b],...]
  (optional), radius:positive (optional default .012), opacity:0..1}`.
  It is a centerline; authored tube/glyph radius is appearance, not a field.
- Points: `{id, positions:[[x,y,z],...], color:[r,g,b], colors:[[r,g,b],...]
  (optional), radius:positive (optional default .035), opacity:0..1}`.
- Metric: `{id,label,value,unit,note}`; value can be finite number or short string.
- Optional geometry `point_data`: `{name:{values:[scalar or vector per position],
  components:1|3,units:string}}` retains unexaggerated scientific attributes.
  Missing attributes in a merged hub export require a declared availability mask.
- Witness: `{id,pass:bool,observed:finite_number,limit:finite_number,rule:
  "at most"|"at least",note}`. Use explicit comparisons, not Python `assert`.
  All builder publication gates raise on failure and re-read written bytes.

Coordinate convention: right-handed Y-up for every packet. Model-specific
axes explain how scientific coordinates map to this view. Blender uses
`(x,y,z)_X3D -> (x,-z,y)_Blender`, a proper +90° X rotation. Exact inverse
is `(x,z,-y)`. No position quantization or implicit unit normalization.

Budgets: <=12 frames per case; <=30,000 total positions per frame; <=10,000
faces per frame; <=250 individual geometry records per frame. Prefer 7–9
frames and 3 presets per model. Data is synthetic or analytic unless explicitly
attributed otherwise. No imported clinical or human-subject dataset.

The common package owns scene validation, X3D emission/import of the declared
subset, portable X3D 3.3 projection, VTK PolyData, OBJ/PLY/CSV and Blender paths.
Exported geometry carries case/frame/content identity; raw variables and units
remain in packet data. A mesh round trip does not recover a solver or all domain
semantics from another hub. Every supported subset and every loss is declared.
