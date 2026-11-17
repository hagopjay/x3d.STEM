# Existing x3dprov figure linkage

This adapter reuses the private x3dprov/0.1 protocol. The vendored module is pinned
to private commit `c1634f5c4f29c4220a092510807a430ce4cbfd2e` plus a one-line
literal-replacement callback repair. Its original SHA, fixed SHA and provenance
are in `vendor/ORIGIN.json`. The repair follows the already archived `xprov` copy;
the original archived kits are unchanged.

```sh
python3 -m pip install lxml
python3 adapters/x3dprov_link.py --study /path/to/x3d.STEM/studies/research-loom --output private/figure-links
python3 -m unittest discover -s adapters/tests
python3 -O -m unittest discover -s adapters/tests
```

The selected cases are the three retained Research Loom hero frames. The adapter
checks source producer files, exact packet/frame bytes, decoded geometry, actual
image bytes and renderer-source identities. It records `link_existing_render`
and explicitly reports `render_reexecuted: false`. Original files are untouched.
Output is a linked X3D document and a sidecar for each case.

There are three distinct identities: file bytes; the original packet frame's
canonical JSON; and the exchange-normalized frame's canonical JSON. The existing
x3dprov XML-content hash is a fourth method. All retain separate field names.
The adapter admits only well-formed owned XML and refuses the protocol's text
fallback branch, stale input and broken chains.

The core patch fixes escaped JSON in `re.sub` replacement text. Five regression
cases cover newlines, Windows paths, replacement-like strings, control escapes
and Unicode/markup. Before the fix, four cases fail; after it all five pass.
The adapter's eight additional controls exercise stale-input refusal, marker
location, reordered XML attributes and protocol compatibility. The owned append
operation only links unchanged scene content; it is not a general transform API.
This remains an unsigned continuity record, not authentication.
