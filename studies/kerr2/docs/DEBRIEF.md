# Kerr 2 · The Photon Ring: debrief, pass 1 (4 Nov 2026)

The first x3d.STEM flagship, built with the X3D Loom. Grades: **C** = a named tool ran and showed it; **L** = read or reasoned; **S** = suspected or a visual judgement.

## 1. What changed from the Scientific Loom's Kerr Observatory

| Scientific Loom (pass 1) | Kerr 2 (pass 1) |
|---|---|
| Ray stops at the first disk crossing: the direct image only | Rays pass through an optically thin disk; up to four crossings recorded, so the n = 0, 1, 2, 3 images are separate layers |
| One ray per pixel; the debrief says sub-pixel critical-curve structure is not resolved | A polar ring atlas samples 2,048 angles × 1,024 log-spaced offsets from the analytic critical curve, 10⁻⁶ M to 1.5 M |
| Authored colour ramp times g⁴ | Blackbody at g·T(r) through the official CIE 1931 table; colour is bound to g |
| Reference control: Schwarzschild capture at b² = 27 for nine impact parameters | Reference controls: the bisected shadow edge against Bardeen's analytic critical curve at 72 angles for every spin; Schwarzschild sub-ring demagnification against e^−π |
| Viewer: one precomputed image, magnified | Viewer: sky, unrolled ring, per-layer toggles, analytic curve overlay, zoom to 20,000×, a guided flight into the ring |

The integrator itself (separated Kerr equations in Mino time, u = 1/r, z = cos θ, RK4 step doubling) is the Scientific Loom's, adapted under its MIT licence.

## 2. Witness results

Every case is green on the final build. That covers unresolved rays, the separated null constraint, the analytic critical curve, sub-ring width change under refinement, the e^−π demagnification (Schwarzschild), Planckian chromaticity against Kang et al. and CIE Illuminant A, and clipping. The browser frame matches the offline render of the same verified payloads for all three cases (correlation above 0.99999), each with a signal floor and a flipped negative control that fails as it should. Every number is in [NUMBERS](NUMBERS.html), generated from the manifests and evidence by `tools/witness_tables.py`.

## 3. What failed, and what it taught

1. **The colour gate failed on the first run (C).** The analytic CIE colour-matching fit (Wyman, Sloan & Shirley 2013) is least accurate in the red: chromaticity 0.0036 from Kang et al.'s independent Planckian-locus fit at 2,000 K, over the 0.003 limit declared before the run. Against the exact CIE Illuminant A the fit was off by 0.0016, Kang by 0.0005, so the weaker instrument was mine. The fix was the official table (DOI 10.25039/CIE.DS.xvudnb9b, CC BY-SA 4.0, md5 and sha256 matching the CIE's published checksums), not a wider threshold. Afterwards: 0.00047 against Kang, 4×10⁻⁵ against Illuminant A. The first run's case file is kept in `evidence/history/`.
2. **Sub-rings can touch the critical curve (L, then C).** At high spin the ISCO moves close to the hole (2.02 M at a = 0.94), so on part of the ring the spherical photon orbit's radius exceeds the disk's inner edge. There the n-th crossing never falls inside the edge, and the sub-ring runs right up to the curve. The edge finder first rejected these angles (`SUBRING_BRACKET`); it now records the inner edge as the curve itself.
3. **The n = 1 image is not yet a thin ring for inclined observers (C).** At the top of an inclined view the n = 1 crossing stays inside the disk for offsets beyond 3 M (the lensed far side). The refinement and demagnification gates therefore use n = 2 and n = 3, the true thin sub-rings; n = 1 widths that leave the search window are counted, not guessed.
4. **The builder could not import its own module (C).** `python -I` drops the script directory from `sys.path`: the same mistake recorded once already (Loom failure mode 43). Builders now launch with `-E -s`.
5. **The browser tested a stale stylesheet (C)**, because the copied server sent no cache policy; and a CSS `display` rule overrode the `hidden` attribute, so a loading veil dimmed every frame. Both fixed (`Cache-Control: no-cache`; `[hidden]{display:none}`).

6. **The refinement gate went red on both Kerr cases (C): 1.37 relative width change, limit 10⁻³.** At three angles the edge finder, at tolerance 10⁻⁹, placed the n = 2 inner edge beyond the outer edge. There the spherical photon orbit's radius (3.1 to 3.8 M) lies outside the disk's inner edge (2.02 M), so the ring truly abuts the curve and no inner edge exists; the finder had latched onto a noisy transition. Fix: decide from Bardeen's exact r_ph(ψ) whether an inner edge exists, search only below the outer edge, and reject any edge order violation. Worst change afterwards: 3.4×10⁻⁶ (Kerr), 5.1×10⁻⁶ (extreme), limit unchanged.
7. **Nine rays came back unresolved (C)**, all near the spin axis, all at the 40,000-step cap with 0 or 1 crossings. The error control included φ, whose rate has a 1/(1 − z²) factor at the pole; φ never feeds back into the trajectory and Kerr 2 does not use it, so it no longer sets the step.

8. **An asymptotic intuition was wrong for small n (L, then C).** The edge finder first assumed the n-th crossing radius tends to the photon orbit r_ph as the offset shrinks. That holds as n grows, but the critical ray spirals onto the photon orbit from outside, so its first crossings lie well above r_ph: at ψ = 2.749 in the a = 0.99 case r_ph = 1.27 M is inside the disk edge (1.45 M) while the n = 1 crossing stays outside it, and the n = 1 ring reaches the curve. The build aborted (`SUBRING_BRACKET`) instead of guessing; the finder now uses r_ph only as a sufficient condition and lets the sampled crossings decide, and the manifest counts every such angle.

9. **The browser "disagreed" with the offline renderer, and the browser was right (C).** The first reconstruction of the extreme case gave correlation −0.015 and looked like a GPU sampling error. The page had been left in its unrolled-ring mode by an earlier test, and a hash navigation kept that state, so the witness compared the unrolled atlas against the sky. Now the page reports the view it drew (`kerr2View()`), deep links set the whole view (`#extreme/v=0/z=2/x=2.3549/y=2.5/m=15/s=16/e=1.2`), and the witness rejects a capture whose case, mode or loading state differs from what the offline renderer draws (Loom failure mode 64).
10. **The witness's own controls rejected two weak views (C).** The ring-top view of the extreme case is nearly black (luminance standard deviation 0.009 under a 0.02 floor declared before measuring), and a centred edge-on view is almost mirror-symmetric, so the vertically flipped capture still correlated 0.981 and the negative control could not fail. Both views were replaced, not the thresholds (failure modes 65, 66).

## 4. Limits (also in every case manifest)

Optically thin equatorial emission with a constant layer weight; no absorption, scattering, polarization or GRMHD. The 6,500 K peak temperature is a display choice; real accretion disks are far hotter, so colour is bound to g and the scale is not. Crossings beyond n = 3 are not traced. The ring atlas is sampled and the display interpolates between samples. Observer at r = 200 with an impact-parameter screen. Float32 in the browser limits useful zoom to about 2×10⁴ (a pixel of about 10⁻⁶ M near the ring). All browser observations are from software rendering; no GPU frame rate is claimed.

## 5. Next pass

- Kerr's sub-ring ratio varies around the ring because the Lyapunov exponent does; add the analytic Kerr Lyapunov exponent as the reference for spinning cases.
- A Theatre-lens film at dome resolution (Tier C), and a measured GPU run (Tier B) on the user's decision.
- Optional optically thick mode (first crossing only) for comparison with the Scientific Loom's image.
- Polarization and a physically motivated emissivity (Novikov–Thorne) as a declared model change.

## 6. Numbers

See [NUMBERS](NUMBERS.html) (generated; not retyped here, so it cannot drift from the manifests).
