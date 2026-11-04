# Kerr 2 · The Photon Ring

The first x3d.STEM flagship. A black hole's photon ring computed from null geodesics, with every pass of light around the hole kept as its own image layer, a ring atlas you can zoom into far below a pixel, colour bound to the frequency shift, and gates that compare the result with exact analytic answers.

## Run

```sh
python3 serve.py --port 8823
```

Open http://localhost:8823 in a current Chromium-based browser. Everything is bundled (X_ITE 16.5.1); no install or internet is needed to view. Do not open `index.html` as a file.

- **Cases** (top): a = 0.99 seen at 84° (near edge-on), a = 0.94 at 68° (the Scientific Loom's case), and a = 0 at 60° (Schwarzschild, the reference).
- **Images of the disk**: n = 0 is the direct image; n = 1, 2, 3 are light that went once, twice, three times further around the hole. "Rings only" hides the direct image.
- **Scroll** to zoom (up to 20,000×), drag to pan, double-click to reset. **Fly into the photon ring** zooms through the sub-rings to where the computed rays end.
- **Unrolled ring** lays the ring out flat: angle across, offset from the critical curve up on a log scale. The sub-rings become evenly spaced stripes; their spacing is the orbit's Lyapunov exponent.
- **Analytic critical curve** overlays Bardeen's exact curve on the computed image.
- **U** hides the interface.

## What is computed, and what is checked

`tools/kerr2.py` integrates null Kerr geodesics in Mino time (u = 1/r, z = cos θ, RK4 step doubling), adapted from the Scientific Loom's solver (MIT; `LICENSE.scientific-loom`). Unlike that solver, a ray continues through the disk plane and records up to four crossings. The disk is optically thin and equatorial; each crossing inside the disk (ISCO to r = 22) emits a blackbody at T(r), seen as a blackbody at g·T(r). Colour comes from CIE 1931 matching functions (analytic fit) into linear sRGB.

Per case (`cases/<name>/case.json`, schema `loom.scientific-case/1`):

| Witness | What it compares | Declared limit |
|---|---|---|
| Unresolved rays | Image and ring atlas | 0 |
| Null constraint residual | Separated radial and polar potentials, every step | ≤ 2×10⁻⁵ |
| **Analytic critical curve** | The shadow edge found by bisection (disk removed) vs Bardeen's spherical-photon-orbit curve, at 72 angles | ≤ 2×10⁻⁴ M |
| **Sub-ring refinement** | Widths of the n = 2, 3 sub-rings, found by bisection, at integration tolerances 10⁻⁹ and 10⁻¹¹, at 24 angles | ≤ 10⁻³ relative |
| **Schwarzschild demagnification** (a = 0 only) | Width ratio w₃/w₂ vs e^(−π) | ≤ 15 % |
| Planckian chromaticity | The colour pipeline's blackbody chromaticities vs Kang et al. 2002 (an independent fit) at 2,000 to 20,000 K | ≤ 0.003 in xy |
| Radiance clipping | RGBM16 encoding | 0 |

The page verifies every texture's sha256 against the manifest before display and keeps red witnesses visible.

## Limits

Optically thin emission with a constant layer weight; no absorption, scattering, polarization or GRMHD. The 6,500 K peak temperature is a display choice (real disks are X-ray hot); colour is bound to g, the scale is not. Crossings beyond n = 3 are not traced. The atlas is sampled; the display interpolates between samples. Observer at r = 200 with an impact-parameter screen. Frame rates here are from software rendering only.

## Rebuild

```sh
python3 tools/kerr2.py           # about 20 minutes on 8 cores; needs numpy, numba, Pillow
python3 tools/scene.py
python3 tools/film.py --case extreme
```
