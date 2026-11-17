# Data model and inference boundaries

The inventory is an adapter over existing evidence. It has no universal
“Confirmed” field and no ranking that collapses scientific validity, software
execution and image quality into one number.

| Entity | Necessary role | Suggested ontology alignment | Boundary |
|---|---|---|---|
| Claim | A statement with named subjects, facets and scope terms | A claim/proposition entity in the owning ontology; lineage may use PROV-O | A title is not evidence |
| EvidenceRecord | A recorded observation with method state and outcome | PROV-O entity; qualify measurement-style observations with SOSA where appropriate | A recorded pass is not a fresh execution |
| Artifact | Exact retained bytes and a relative source-root locator | PROV-O entity | A byte hash is not publisher authentication |
| ToolBuild | Version, source artifacts and recorded runtime details | PROV-O entity for the build; connect an executing software agent separately | A build is not automatically an agent |
| ValidationRun | A recorded or absent execution | PROV-O activity | `not_run` cannot support an executed claim |
| Bridge | Historical B01–B27 integration identifier | SKOS concept for catalog alignment | Method overlap does not complete a bridge |
| Transformation | An explicit coordinate/encoding operation | PROV-O activity when an actual operation is recorded | A matrix declaration alone does not establish its execution |
| Loss | A measured or declared loss with an explicit scope | SOSA observation for measured quantities; otherwise a loss assertion | Semantic loss and numeric error need different descriptions |
| Dataset | Numeric/model observations behind a representation | Dataset entity in the owning ontology | Display coordinates may have been magnified |
| CoordinateFrame | Handedness, axes and unit policy | A domain coordinate reference entity; QUDT unit links when identified | Axis conversion, origin shift and rescaling are different operations |

These are proposed hooks, not blanket OWL equivalences. The owning ontology
can add stronger class axioms after checking the representation's intended
domains and ranges. In particular, globally mapping every `artifacts` field
to `prov:used` would infer that receipt entities are activities. This adapter
uses `scivis:boundArtifact` and leaves activity-specific PROV qualification to
the owning ontology.

## Worked geometry query

The tensor transfer record has subject `tensor-correlated`, facets
`geometry.coordinates`, `geometry.topology`, `geometry.color_attributes`, and
scope terms selecting the authored case, saved frame4 and owned geometry
subset. A claim requiring those same terms can cite it after current artifact
and producer binding inspection passes.

The record cannot support any of these different statements:

- a different membrane or imported CSV case survived;
- every frame survived Blender editing;
- a modifier graph or material graph survived;
- X_ITE and Cycles produced equal pixels;
- the source observations are Gaussian;
- an edited geometry file still satisfies the original physical model.

They fail by different subject, different scope, or missing facet. Lineage
through `prov:wasDerivedFrom` does not change that result.

## Three color observations

The owned `.blend` transfer measures scientific color attributes through an
explicit sRGB/linear conversion. The GLB receipt separately measures serialized
FLOAT colors and Blender's BYTE_COLOR reimport quantization. The authored PNG
then adds illumination, transparency, shading and a display transform. These
are three different observation levels. Exact color attributes can coexist
with quite different rendered pixels.

## Current binding and original execution

The bank source map includes `../../lib/stemkit/core.py`; the release source map
alone does not. Import reads both maps and resolves their references within
the repository root. Evidence has separately checked `artifacts` and
`source_bindings`, so an unchanged receipt with an edited producer source
does not silently describe the new code.

An inspection snapshots hashes at a time. It neither freezes the filesystem
nor prevents files changing afterwards. Support output records the inspection
time, and the inventory digest prevents accidentally applying one inventory's
inspection to another inventory. Before a consequential new statement, inspect
the current files again and rerun whichever domain instrument its facet needs.

## Historical counts and present denominators

The flywheel source uses corpus counts with several denominators and explicitly
records disagreements. The imported text fragments are `reported` and retain
that uncertainty. Reading and hashing that document establishes that the
fragments are present, not that the old corpus exists now or has the same
membership. A fresh corpus count needs an explicit manifest, included/excluded
rules, a census command, and a retained result from that command.

## Privacy follows the evidence

Every imported node is private. This graph is unsuitable for direct publication
because its source locators and historical assertions expose private project
structure. A future public projection should enumerate approved fields and
artifacts, remove private locators and assertions, then validate the projected
graph separately. Removing a title or replacing a private repository name alone
would not sanitize nested `measurements` or recorded command output.
