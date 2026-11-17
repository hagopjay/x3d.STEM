# Private scientific visualization evidence inventory adapter

This small Python adapter answers: **Which unchanged records support this
narrowly scoped claim?** It indexes original receipts and files without
executing a producer, rewriting a source grade, restamping an X3D scene, or
introducing a competing provenance protocol.

`x3dprov` remains the inspected scene-carried provenance mechanism. Research
Loom receipts remain the records of their executed model, transfer and render
checks. The new JSON-LD file is a private interchange inventory over those
records. `prov:wasDerivedFrom` expresses lineage; it never supplies transitive
claim support.

## Run

Runtime dependencies are Python's standard library. The code uses features
available in Python 3.12 and 3.13+; the delivered tests record the actual
interpreter used. No renderer, model API, network access or paid service is
called by this adapter.

From this directory, substitute your local paths:

```sh
python3 inventory.py import-research-loom \
  --study /path/to/x3d.STEM/studies/research-loom \
  --output examples/research-loom-inventory.jsonld \
  --bridge-map examples/bridge_map.json

python3 inventory.py verify examples/research-loom-inventory.jsonld \
  --root stem_repo=/path/to/x3d.STEM \
  --output examples/current-bindings.json

python3 inventory.py support examples/research-loom-inventory.jsonld \
  urn:x3d-scivis:claim:blender-geometry-tensor \
  --inspection examples/current-bindings.json
```

The import requires the complete, current Research Loom distribution, including
its bank and Blender artifacts. It fails if a referenced file is absent or
disagrees with the source receipt's declared SHA or length. It reads large
scientific assets to hash them; it does not copy them into the inventory.

The delivered example additionally indexes the historical attachment and new
private probes/figure links. Regenerate it with:

```sh
python3 inventory.py import-research-loom \
  --study /path/to/x3d.STEM/studies/research-loom \
  --historical-notes /path/to/attached-notes \
  --private-workspace /path/to/blender-scivis-integration \
  --output examples/research-loom-inventory.jsonld \
  --bridge-map examples/bridge_map.json

python3 inventory.py verify examples/research-loom-inventory.jsonld \
  --root stem_repo=/path/to/x3d.STEM \
  --root review_inputs=/path/to/attached-notes \
  --root private_workspace=/path/to/blender-scivis-integration \
  --output examples/current-bindings.json
```

`--historical-notes` accepts an explicit Markdown file, or a directory containing
`FLYWHEEL-SYNERGY-v1 (2).md` or the archive's `FLYWHEEL-SYNERGY-v1.md`.
The optional private workspace contains the exact
receipt paths emitted by this integration pass; it is not a general kit
discovery mechanism. Roots are supplied explicitly at verification time, so the
artifact locators do not embed machine-specific absolute source paths. Original
receipt measurements and captured logs can still retain historical paths.
Every locator
must stay inside its supplied root after resolving symlinks.

The support command returns exit code **0** for recorded support within scope,
**2** for unsupported, and **1** for an invalid inventory/inspection. The
inspection records its time. A support query refers to those checked bytes at
that time; rerun `verify` when files or source change. An inspection from a
different inventory, even one with the same entity identifiers, is refused.

## Keep four axes separate

| Axis | Values | Meaning |
|---|---|---|
| Recorded evidence state | reported / inspected / executed / reproduced | How the source observation was obtained |
| Recorded outcome | pass / fail / partial / unknown | What that observation concluded |
| Current binding result | artifact bindings / producer bindings, separately checked | Whether exact referenced bytes still match |
| Applicability | explicit subjects, facets and structured scope terms | Which narrow claims can use the observation |

Reading a successful Blender receipt is an inspection of an **executed**
record; it is not a new Blender execution. Hashing a PNG does not establish
pixel parity. A passing schema check does not establish physical validity.
An unchanged historical document can remain `reported` even if it calls its
own old result “Confirmed.” No original source grade is promoted or erased.

The inventory includes deliberate unsupported claims for native browser
visibility, scientific correctness after geometry edits, and current historical
corpus counts. Their purpose is to demonstrate the boundary. The same evidence
that supports a selected-frame geometry claim must leave those claims unsupported.

## Entities and ontology hooks

The ten entity kinds are `Claim`, `EvidenceRecord`, `Artifact`, `ToolBuild`,
`ValidationRun`, `Bridge`, `Transformation`, `Loss`, `Dataset` and
`CoordinateFrame`. Their shape is described in `inventory.schema.json`; runtime
checks additionally resolve references, reject duplicate identities and facet
wildcards, enforce explicit hash methods, and reject future/unexecuted
execution promotions.

JSON-LD uses a pinned local context and vocabulary. PROV-O supplies the lineage
hook. SOSA, QUDT and SKOS prefixes are available for the owning ontology's
alignment, without pretending that free-text unit labels already identify a
registered QUDT unit. `scope_terms` provide machine-comparable constraints
such as `saved-frame:4` and `owned-geometry-subset`; the prose `scope` retains
the human meaning. See `DATA-MODEL.md` for worked distinctions.

The `bridge_map.json` file aligns B01–B27 by **method overlap**, not historical
completion. For example, a new four-splat Blender5.3 layout probe is relevant to
B01/B13, but does not rerun the old size ladder or establish rendered pixels.

## Hash identities are not interchangeable

| Identity | Explicit method | Use |
|---|---|---|
| Retained file | `sha256-file-bytes` | Receipt, packet, scene, PNG, `.blend`, GLB or source identity |
| Inventory/inspection join | `sha256-json-sortkeys-utf8-compact-no-nonfinite` | Bind a support query to the inspected inventory |
| Research Loom internal report hash | Same canonicalization with `report_sha256` omitted | Preserve the report's own embedded identity as a separate field |
| Existing x3dprov content hash | The method and branch stated by its figure-link receipt | Scene content after that protocol's stripping/canonicalization rules |

These hashes identify different things, even when all use SHA-256. The adapter
does not recompute x3dprov content with a simplified replacement algorithm. Its
figure-link records retain the owning adapter's exact method label, branch,
source hash and linked scene bytes. Neither the original protocol nor these
unsigned inventories authenticate a publisher against an adversary.

## Verify the adapter

```sh
python3 -m unittest discover -s tests -v
python3 -O -m unittest discover -s tests -q
```

The controls mutate receipt bytes and producer source independently; reject
geometry→pixels/science and frame→arbitrary-frame overreach; preserve a
reported historical grade; reject future or unrun execution, duplicate IDs,
dangling references, facet wildcards, hash-method confusion and symlink escape.
Runtime refusal uses explicit exceptions, so Python optimization cannot remove
the gates. These tests exercise this adapter; they do not rerun all original
scientific pipelines.

The next practical convergence exercise is in `ONE-ORACLE.md`. Keeping one
fixture's meaning intact across several existing tools is more informative
than adding another global score.
