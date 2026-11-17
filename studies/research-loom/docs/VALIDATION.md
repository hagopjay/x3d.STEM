# Executed validation and its scope

The release check finished at **2026-11-17T19:54:31.067264+00:00** with status **PASS**
and no source changes during execution. The machine-readable record is
[`evidence/release.json`](../evidence/release.json). Its source hashes identify
the checked implementation; this report does not certify later edits.

| Instrument | Result |
|---|---|
| `-m unittest discover -s tests -q` | PASS · 59 tests |
| `-O -m unittest discover -s tests -q` | PASS · 59 tests |
| `tests/scene.test.cjs` | PASS |
| `-E -s -m unittest discover -s lib/stemkit/tests -t lib -q` | PASS · 14 tests |
| `-O -E -s -m unittest discover -s lib/stemkit/tests -t lib -q` | PASS · 14 tests |
| `tools/verify.py` | PASS |
| `tools/validate_x3d.py` | PASS |

The bank contains **nine cases, 78 saved frames and 63 declared scientific
witnesses**. Independent readback checks actual X3D coordinates, topology and
appearance. VTK's real readers check exported geometry, point arrays, field
data and missing-value masks. A separate pinned X3D instrument checks all 78
X3D 4 frames against XSD 4.0 and its recorded semantic vocabulary. This is not
a claim that portable 3.3 files were checked against a 3.3 schema.

## Blender execution

Blender **5.2.4 LTS** actually imported, saved, reopened and read back each of
the three selected scientific scenes. A deliberate vertex edit with retained
metadata was detected for each. All three glTF2 exports were reimported; their
receipts distinguish exact serialized FLOAT colors from Blender's quantized
BYTE_COLOR reimport. All three 1280×960 PNGs are actual Cycles CPU stills,
rendered with 24 samples. Their packet, selected frame, tool and image identities
are recorded separately. See [the measured hub report](BLENDER-HUB.md).

The release runner binds the three transfer, three render and three GLB
receipts to the current bank and delivered artifacts. It rechecks retained
round-trip geometry. It does not reinstall or execute Blender on every run.
The supplied commands reproduce those more expensive operations.

## Practical limits

- Data are analytic or synthetic. The CSV importer creates a fresh covariance
  case from supplied numeric observations; it does not establish their provenance
  or Gaussian distribution.
- Geometry imported through X3D or edited in Blender carries historical scientific
  measurements. Those measurements are explicitly not recomputed by an editor.
- The bounded X3D reader supports the documented static exchange subset. It is
  not a general X3D parser, animation engine or material-graph translator.
- Native X_ITE browser rendering remains unverified on this host because browser
  socket operations are blocked. Node tests cover actual UI adapter functions,
  state ordering and projection geometry. The Blender stills supply independent
  offline rendering evidence, without a browser pixel or GPU-performance claim.

## Reproduce

```sh
cd studies/research-loom
python3 -m pip install -r requirements.txt
python3 tools/check.py
```

For a source-only patch, build the bank with `python3 tools/build.py`, then
regenerate the three transfers, renders and GLBs using the Blender hub guide
before invoking the complete release check. The source-level tests can run
without those rendered artifacts. The focused ZIP already contains the exact
computed bank, export snapshots and images referred to by its manifests.
The official Blender executable is not bundled.
