# x3d.STEM

Science, technology, engineering and maths as X3D worlds that carry their own evidence. Every frame is a measurement, and every study can answer "how do we know?".

x3d.STEM is built with the X3D Loom: generators instead of hand-edited files, independent witnesses (including exact analytic references), acceptance profiles that fail closed, receipts, and a flywheel that turns each failure into a rule. Its direction, audiences, fidelity tiers and project catalogue are in [docs/X3D-STEM.md](docs/X3D-STEM.md).

## Studies

| Study | What it shows | State |
|---|---|---|
| [Kerr 2 · The Photon Ring](studies/kerr2/) | A black hole's photon ring with every pass of light kept as its own layer, zoomable 20,000× into the sub-rings, colour bound to the frequency shift, checked against Bardeen's analytic critical curve and the e^−π sub-ring law | Flagship 1, pass 1 |
| [Turing Garden](studies/turing-garden/) | Five 3D reaction–diffusion gardens (spots, Swiss cheese, coral, sheets, chaos) grown from three seeds; the browser meshes each verified field, checks its mesh against the builder's, and plays the growth through X3D's own TimeSensor route | Flagship 2, pass 1 |
| [Electron Cloud Observatory](studies/electron-cloud/) | Hydrogen solved numerically and held to the exact answers: ten orbitals from 1s to 5g coloured by the sign of the wave, and Lyman-α, a superposition whose charge swings through the nucleus at the frequency of hydrogen's 121.5 nm line | Flagship 3, pass 1 |
| [Chirp](studies/chirp/) | Two black holes spiral together and you hear them: the orbit integrated with radiation reaction and held to Peters' laws and the chirp law, the wave pattern spreading across the orbital plane, and the strain played at its real pitch (or three octaves up), picture locked to the sound | Flagship 4, pass 1 |
| Scientific Loom Observatory, pass 1 | Quantum vortices, Kerr lensing, phase separation, phononic modes (the first delivery; reviewed in the Loom's REVIEW-scientific.md) | Lives outside this repo for now |

## Shared library

[`lib/stemkit`](lib/stemkit/): fail-closed publication (atomic writes that reopen what they wrote, deflated binary frames with both hashes), surface nets with the measurements that check them (tested against an exact sphere, torus and step), the browser port of the mesher (`lib/stemkit/js/nets.js`, copied into studies and kept identical by a test), binary mesh frames, and Markdown debriefs to HTML with witness tables generated from the manifests.

```bash
python3 -E -s -m unittest discover -s lib/stemkit/tests -t lib      # and again with -O
```

## Payloads

Case payloads (PNGs, fields, films) are not committed: about 330 MB for Kerr 2, 43 MB for the Turing Garden, 7 MB for the Electron Cloud and 4 MB for Chirp. Each study's builder regenerates them, and the committed manifests carry their sha256, so a rebuilt payload either matches or the Loom's science gate rejects it.

## Principles

- **One verified case, four lenses** (Explorer, Lab, Instrument, Theatre): lenses change words and camera, never data.
- **Three fidelity tiers** from the same verified case: any browser, a streamed GPU workstation, offline hero renders.
- **No uncomputed state is shown.** Controls select computed cases; playback commits computed frames; the display interpolates only between computed samples, and says so.
- **Exact references first.** Each study names the analytic or published result its solver must reproduce.

## Status

Local repository; no remote yet (to be `hagopjay/x3d.STEM`). Nothing here has been measured on a real GPU.
