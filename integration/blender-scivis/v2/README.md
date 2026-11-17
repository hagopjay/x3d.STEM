# Blender scientific visualization integration v2 (technical subset)

Public-safe, technical parts of a 17 Nov 2026 review of the Blender sci-vis knowledge base.
Everything here was copied unchanged from the review package; nothing was re-executed except the unit tests.

| Folder | What it is | Source of numbers |
|---|---|---|
| `integration/` | Read-only JSON-LD evidence inventory adapter, JSON schema, data model, 13 tests | CPython 3.13.18 (re-run here) |
| `adapters/` | Retrospective figure-link adapter over x3dprov (vendored copy, origin in `vendor/ORIGIN.json`), 8 tests | CPython 3.13.18, needs `lxml` |
| `ontology/` | PROV/SOSA/QUDT/SKOS hooks, SHACL shapes, SPARQL query, graph check | reported by the review |
| `probes/precision/` | Blender 5.2.4 save/reopen precision fixture vs independent binary32 reference | reported: Blender 5.2.4 build cd5dc428cce1 |
| `probes/native53/` | Blender 5.3.0 native 4-splat SH3 import probe and fork round trip | reported: Blender 5.3.0 build 02f0899d78e3 |
| `docs/` | Executed-results table, 21 scoped knowledge corrections, precision figure | reported |

Left out on purpose: the private bridge audit and catalog, kit inventory, raw workflow, corpus-linked evidence map, the atlas and the research-loom inventory example (its locators point at private paths).
`integration/inventory.py import-research-loom` expects a `studies/research-loom` tree that is not in this repo.

```sh
python3 -I -m unittest discover -s integration/tests
python3 -m pip install lxml && python3 -I -m unittest discover -s adapters/tests
```
