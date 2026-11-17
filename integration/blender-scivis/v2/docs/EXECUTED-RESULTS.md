# Executed results and acceptance boundaries

Private integration pass · 17 November 2026.

| Instrument | Executed result | Scope |
|---|---|---|
| Archive audit | 439 files, 4,583,862 bytes; all Git blobs and attachment identities checked | Original archived source, not missing external assets |
| Inventory regression suite | 13 tests pass normally and with `-O`, on Python 3.12 and actual Python 3.13 | Scope, evidence state, identity drift, references, reproduction frames and root containment |
| Figure-link regression suite | 8 tests pass normally and with `-O` | Existing protocol compatibility and refusal of stale, hidden, misplaced or malformed records |
| Core escape regression suite | 5 tests pass normally and with `-O`; four failed before the callback repair | JSON string preservation through provenance metadata insertion |
| Existing ingestion tests | 15 passed; 2 skipped because their external real-data directories are absent | Existing local fixture behavior after the core repair |
| Live inventory | 238 file bindings pass; 23 claim queries yield 16 scoped positives and 7 intended unsupported results | Current referenced bytes and declared support, without new Blender execution |
| RDF metadata | 7,812 data triples; 68 shape triples; 286 query rows; malformed-SHA control rejected | Local JSON-LD, Turtle, SHACL and SPARQL metadata structure |
| Atlas logic | Actual embedded script passes inventory/filter/tab/unique-ID controls | Node DOM adapter; native browser pixels not checked |
| Precision control | Actual Blender 5.2.4 save/reopen, independent binary32 reference and mutation controls | Two synthetic coordinate-storage cases |
| Native splat control | Actual Blender 5.3.0, four SH3 splats, 20 independently checked XML arrays, fork and save/reopen readback | Small structural/data fixture, not rendered image fidelity |
| Native transform control | Center positions approximately retained; covariance difference 0.22836776 fixture units² | Deliberately reproduced preservation loss, not a passing preservation claim |
| Existing figure linkage | All three Research Loom scenes linked to their retained image and receipt bytes | Retrospective `link_existing_render`; no new render |

There are **26 new targeted software test cases** across inventory, adapter and
core suites. Running them under multiple interpreters or optimization settings
does not make them additional unique cases. The pre-existing ingestion suite is
reported separately, including its two unavailable-data tests.

Machine-readable receipts:

- `private/integration-release.json`
- `integration/examples/current-bindings.json`
- `integration/examples/claim-query-controls.json`
- `private/ontology-validation.json`
- `private/probes/precision-control.json`
- `private/native53/results/native53-result.json`
- `private/native53/results/x3d-validation.json`
- `private/figure-links/*-figure-link.json`

The release checker runs software and metadata inspections. It does not silently
execute archived scripts, old model experiments, Blender or a native browser.
The separate Blender receipts identify the actual executions made in this pass.
Hash identity is not publisher authentication; SHACL validity is not scientific
truth; a source-level match is not a universal extension-conformance result.

## Reproduce the aggregate software/metadata check

With the original Research Loom distribution and private repository checkout:

```sh
python3 -m pip install -r requirements-review.txt
python3 verify_review.py \
  --study /path/to/x3d.STEM/studies/research-loom \
  --private-repo /path/to/x3d.ml
python3 ontology/check_graph.py
```

Pass `--python313 /path/to/python3.13` to repeat the stdlib inventory suite in
that interpreter. The individual Blender commands are in the probe reports.
Rebuilding scientific data, changing tools or editing a bound file requires a
new inspection and, where relevant, a new producer run.
