# Knowledge base v1.2: corrections and evidence facets

Private additive review · 17 November 2026. The supplied v1 and v1.1 files remain unchanged.

The strongest change is to make every assertion name its subject and scope. A current product release, a supported format, an executed import and a scientifically faithful round trip are different claims. Preserve the historical grading while recording these additional facets.

| ID | Topic | Assessment |
|---|---|---|
| K01 | runtime freshness | stale |
| K02 | native splat attribute order | incorrect component order |
| K03 | native support versus interchange | overbroad if inferred |
| K04 | splat byte arithmetic | incomplete storage accounting |
| K05 | precision | wrong quantity |
| K06 | scientific color | overbroad |
| K07 | data textures | needs semantic distinction |
| K08 | X3D attribute carrier | too absolute |
| K09 | molecular semantics | requires a core/application distinction |
| K10 | analysis ownership | useful policy stated as a false absolute |
| K11 | splat versus mesh | heuristic not a theorem |
| K12 | current extension routes | incorrect aggregation of separate routes |
| K13 | compression | depends on the storage profile and corpus |
| K14 | glTF splat standard | status strengthened; exact historical date unverified |
| K15 | molecular confidence | requires a provenance condition |
| K16 | render measurement | overbroad |
| K17 | float tolerance | universal absolute bound unjustified |
| K18 | OpenUSD freshness | supported at the documentation level |
| K19 | geospatial standards reuse | existing standard hook |
| K20 | evidence grading | one grade mixes independent evidence axes |
| K21 | outcome/licensing claims | park for targeted review |

## K01 · runtime freshness

Blender 5.3.0 was released on 10 November 2026. Blender 5.2.4 is the current 5.2 LTS patch on that date. Keep the 5.2 LTS and 5.3 native-splat lanes separately pinned.

**Evidence:** `primary_documentation_checked`. [S01](https://www.blender.org/releases/5-3/), [S02](https://www.blender.org/releases/5-2/)

**Next action:** Replace the historical future-release task with a stable 5.3 CI/probe task. Do not infer PyPI wheel availability from the executable release.

**Ontology hooks:** `SoftwareBuild`, `hasVersion`, `retrievedAt`.

## K02 · native splat attribute order

Blender stores raw SH degree-zero coefficients in radiance:base.xyz, followed by activated opacity in w. The new four-splat native 5.3 test reproduces this mapping and all 15 higher-degree RGB coefficient slots.

**Evidence:** `primary_documentation_and_executed_native53_control`. [S03](https://developer.blender.org/docs/release_notes/5.3/rendering/)

**Next action:** Keep asymmetric known-answer splats. Treat SH basis, channel order, opacity activation and scale activation as separate declared mappings.

**Ontology hooks:** `AttributeSemantic`, `componentOrder`, `activation`.

Local evidence: `native53/results/native53-result.json`.

## K03 · native support versus interchange

Native import and rendering are available in Blender 5.3; the official notes state that native export is absent. The new structural test reproduces native PLY import, a fork X3D 4.1 round trip and a loss of covariance under Apply Transform.

**Evidence:** `primary_documentation_and_executed_native53_control`. [S03](https://developer.blender.org/docs/release_notes/5.3/rendering/)

**Next action:** Keep native import, fork export, rendering and transform preservation as separate capabilities. This four-splat structural test does not complete the B01 renderer or scale ladder.

**Ontology hooks:** `ImportRoute`, `ExportRoute`, `KnownLimitation`.

Local evidence: `native53/results/native53-result.json`.

## K04 · splat byte arithmetic

SH degree 3 uses 59 model scalars, or 236 bytes at float32. The common reference PLY adds three normal scalars, yielding 62 float32 properties and 248 bytes per vertex, before the header.

**Evidence:** `derived_from_primary_code`. [S05](https://github.com/graphdeco-inria/gaussian-splatting/blob/main/scene/gaussian_model.py)

**Next action:** Name the property list, scalar width, endianness and header separately. Preserve the 68/104/164/248-byte table only for this declared layout.

**Ontology hooks:** `StorageLayout`, `propertyCount`, `payloadBytes`.

## K05 · precision

This distinction concerns significant precision, not exponent range. Reopened Blender 5.2.4 mesh coordinates matched float32 quantization in two metric coordinate controls. Local-origin storage substantially reduced the measured errors.

**Evidence:** `executed_bounded_control`. [S06](https://docs.python.org/3.13/tutorial/floatingpoint.html), [S07](https://numpy.org/doc/stable/reference/arrays.scalars.html)

**Next action:** Retain 64-bit source coordinates and reversible origin/units metadata. Budget absolute error at the actual coordinate magnitude.

**Ontology hooks:** `CoordinateFrame`, `origin`, `unit`, `maxAbsoluteError`.

Local evidence: `probes/precision-control.json`.

## K06 · scientific color

Standard avoids an additional creative view transform, but display conversion, material lighting, exposure and alpha still affect pixels. X_ITE exposes colorSpace, displayColorSpace and toneMapping controls.

**Evidence:** `primary_documentation_checked`. [S08](https://docs.blender.org/manual/en/4.5/render/color_management.html), [S09](https://create3000.github.io/x_ite/)

**Next action:** Pin both color pipelines. Use unlit known-color charts for quantitative comparison and retain beauty renders as a separate view.

**Ontology hooks:** `ColorEncoding`, `DisplayTransform`, `Exposure`, `LightingCondition`.

## K07 · data textures

Tag numeric data maps as Non-Color. An already encoded display colormap is color data and needs its declared encoding rather than automatic Non-Color tagging.

**Evidence:** `primary_documentation_and_inference`. [S08](https://docs.blender.org/manual/en/4.5/render/color_management.html)

**Next action:** Record scalar units and the transfer function separately from RGB encodings. The second sentence is an interpretation of the documented color pipeline.

**Ontology hooks:** `ScalarField`, `TransferFunction`, `ColorEncoding`.

## K08 · X3D attribute carrier

X3D has named FloatVertexAttribute and matrix vertex attributes for shaders, plus typed Metadata. These carriers do not automatically provide scientific meaning or an equivalent of a Geometry Nodes graph.

**Evidence:** `primary_specification_checked`. [S10](https://www.web3d.org/specifications/X3Dv4/ISO-IEC19775-1v4-IS/Part01/components/shaders.html)

**Next action:** Define attributes with a name, data association, component count, units, missing-value mask and display mapping. Check the supported runtime profile.

**Ontology hooks:** `AttributeSemantic`, `DataAssociation`, `Unit`, `Missingness`.

## K09 · molecular semantics

The core is not a molecular analysis ontology, but Web3D already supplies CML-to-X3D molecular prototype examples. Preserve domain identities through PROTO/Metadata and a molecular sidecar.

**Evidence:** `primary_project_examples_checked`. [S11](https://www.web3d.org/x3d/content/examples/Basic/ChemistryMarkupLanguage/)

**Next action:** Reuse the established chemical mapping direction before proposing new Atom/Bond core nodes. Retain source PDB, mmCIF or CML identifiers.

**Ontology hooks:** `MolecularEntity`, `Residue`, `Bond`, `wasDerivedFrom`.

## K10 · analysis ownership

Treat independently checked scientific arrays as authoritative. Blender Python and Geometry Nodes can perform analysis; those computations still need units, validation and reproducible reference checks.

**Evidence:** `architectural_recommendation`.

**Next action:** Separate numerical authority from presentation authority by contract rather than by application name.

**Ontology hooks:** `ScientificComputation`, `PresentationTransform`, `AuthorityScope`.

## K11 · splat versus mesh

A radiance field is not automatically a validated surface, and a mesh is not automatically a measurement. Analytical suitability depends on acquisition, reconstruction, calibration and uncertainty.

**Evidence:** `architectural_recommendation`.

**Next action:** Grade each representation against its intended task and retain its reconstruction assumptions.

**Ontology hooks:** `Representation`, `MeasurementProcess`, `UncertaintyModel`, `FitForPurpose`.

## K12 · current extension routes

The official extension advertises X3D 3.3. Current local Blender 5.2.4 fixtures test stock commit a173dfb and fork commit 044bea3 separately. Both execute, while their recorded preservation losses differ.

**Evidence:** `primary_documentation_and_existing_executed_receipts`. [S04](https://extensions.blender.org/add-ons/web3d-x3d-vrml2-format/)

**Next action:** Use the current bounded loss tables. Do not transfer one route's capabilities or losses to another route.

**Ontology hooks:** `CapabilityObservation`, `Route`, `LossEvent`, `SoftwareBuild`.

Local evidence: `../../x3d.STEM/studies/research-loom/evidence/blender-stock-extension.json`, `../../x3d.STEM/studies/research-loom/evidence/blender-ecosystem-fork.json`.

## K13 · compression

PLY property types and the writer determine precision. SPZ documents quantization. Compression ratios and fidelity must be measured for the exact codec settings and corpus.

**Evidence:** `primary_documentation_and_inference`. [S13](https://github.com/nianticlabs/spz/blob/main/README.md)

**Next action:** Report decoded position, scale, angular and SH errors alongside bytes. A ZSTD container does not imply lossless model storage.

**Ontology hooks:** `CodecProfile`, `Quantization`, `ErrorBudget`, `Corpus`.

## K14 · glTF splat standard

The current Khronos primary README marks the base extension Complete/Ratified. This does not verify the 3 September date or ratify every dependent compression extension.

**Evidence:** `primary_specification_checked`. [S12](https://github.com/KhronosGroup/glTF/blob/main/extensions/2.0/Khronos/KHR_gaussian_splatting/README.md)

**Next action:** Pin a committed specification revision. Test quaternion order, linear/log scale and opacity activation on each route.

**Ontology hooks:** `SpecificationRevision`, `ExtensionStatus`, `Activation`, `QuaternionConvention`.

## K15 · molecular confidence

AlphaFold downloads store pLDDT in B-factor fields. Do not reinterpret arbitrary experimental PDB B-factors as pLDDT. Local confidence does not establish correct relative chain placement.

**Evidence:** `primary_documentation_checked`. [S14](https://alphafold.ebi.ac.uk/faq)

**Next action:** Require producer and field-semantic metadata. Test the confidence-band boundary values explicitly.

**Ontology hooks:** `ConfidenceScore`, `Producer`, `FieldSemantic`, `Threshold`.

## K16 · render measurement

AOVs are numeric outputs of a rendering process. Scientific measurement requires defined units, conventions, calibration and validation against the claimed quantity.

**Evidence:** `architectural_recommendation`.

**Next action:** Record the camera, depth convention, color encoding, sample count/seed, masks and display mapping. Keep raw buffers with the figure.

**Ontology hooks:** `RenderActivity`, `MeasurementClaim`, `Calibration`, `CameraModel`.

## K17 · float tolerance

Use quantity-specific absolute and relative tolerances. Compare quaternion rotations modulo q/−q, covariance under basis changes, and SH after the declared basis and rotation mapping.

**Evidence:** `derived_numeric_recommendation`. [S06](https://docs.python.org/3.13/tutorial/floatingpoint.html), [S07](https://numpy.org/doc/stable/reference/arrays.scalars.html)

**Next action:** Attach units and a tolerance rationale to each witness. Distinguish serialization quantization from display error.

**Ontology hooks:** `Tolerance`, `EquivalenceRelation`, `Unit`, `ScientificWitness`.

## K18 · OpenUSD freshness

AOUSD's 26.03 announcement identifies the ParticleField schema family, including UsdVolParticleField3DGaussianSplat. Schema availability does not prove any particular Blender import/export path.

**Evidence:** `primary_project_documentation_checked`. [S15](https://aousd.org/blog/openusd-v26-03/)

**Next action:** Preserve this positive interoperability link, but require an executed fixture before claiming adapter capability.

**Ontology hooks:** `SchemaType`, `AdapterCapability`, `CapabilityObservation`.

## K19 · geospatial standards reuse

X3D's Geospatial design already uses GeoCoordinate double-precision coordinates and local origins. The new Blender probe supplies bounded storage measurements for the authoring hub.

**Evidence:** `primary_specification_and_executed_control`. [S16](https://www.web3d.org/specifications/X3Dv4Draft/ISO-IEC19775-1v4-IS.proof/Part01/components/geospatial.html)

**Next action:** Map the original CRS and local frame to established standards where applicable. Never infer a CRS from coordinate magnitude.

**Ontology hooks:** `GeoCoordinate`, `CoordinateReferenceSystem`, `LocalOrigin`.

Local evidence: `probes/precision-control.json`.

## K20 · evidence grading

Record claim type, source quality, executed scope, artifact identity, falsification controls and freshness separately. A release fact can be primary-checked without a renderer; schema validity cannot confirm domain truth.

**Evidence:** `methodology_recommendation`.

**Next action:** Keep the historical grades unchanged. Add structured evidence facets rather than silently upgrading every claim after one new test.

**Ontology hooks:** `Claim`, `EvidenceActivity`, `ArtifactIdentity`, `Freshness`, `Scope`.

## K21 · outcome/licensing claims

Retain these historical claims as dated research notes. They are not refreshed by this technical review and must not be promoted as current medical, legal or commercial guidance.

**Evidence:** `not_revalidated`.

**Next action:** Create separate source-specific review tasks when the corresponding molecular or licensed-asset workflow is selected.

**Ontology hooks:** `HistoricalClaim`, `ReviewTask`, `LicensePassport`, `ValidityInterval`.

## Reproduced precision control

Blender 5.2.4 LTS, build `cd5dc428cce1`, saved and reopened real mesh data. Readback matched an independent binary32 packing reference. Source coordinates and a decimal origin remained in the saved source text. Deliberate actual-vertex changes were detected with the source metadata left unchanged.

| Synthetic metric frame | Direct global maximum error | Restored local-origin maximum error |
|---|---:|---:|
| ecef_like | 0.2345 m | 1.89058483e-06 m |
| utm_like | 0.1543211 m | 1.89064303e-06 m |

Restoration happens in Python binary64 outside Blender world transforms. Translating an object back to a large float32 world position can reintroduce the loss. This is a bounded storage result, not a GPU, X3D or general geospatial-accuracy certification.

## Reference PLY size arithmetic

The formula below is independently derived from the reference writer's declared property list. Header bytes are extra. PLY writers with different types or omitted normals have different sizes.

| Maximum SH degree | Model scalars | Model float32 bytes | Reference PLY bytes including normals |
|---:|---:|---:|---:|
| 0 | 14 | 56 | 68 |
| 1 | 23 | 92 | 104 |
| 2 | 38 | 152 | 164 |
| 3 | 59 | 236 | 248 |

## Retrieval boundaries

All online sources were checked on 17 November 2026. Some official pages refused a direct fetch while their primary-domain search excerpts remained available; the JSON source register records that distinction. Current `main` documents are observations, not reproducible commit pins. Exact historical release dates and all addon/version claims not expressly corrected above remain unverified. No new medical-outcome or license guidance is inferred.

The official stock extension, the ecosystem fork, the owned scientific adapter and Blender's native splat importer are separate routes. Preserve their independent source pins and fixtures; combining their feature lists into one virtual application would overstate what any one executable path can do.

## Executed native Blender 5.3 update

The [seven-answer native report](native53/NATIVE53-RESULTS.md) records the new four-splat SH3 test, independent X3D scalar checks, fork save/import behavior and the Apply Transform covariance failure. Its receipts and reproducible probe are in `native53/results/`. This is structural and attribute evidence; it does not complete the B01 renderer or scale ladder.
