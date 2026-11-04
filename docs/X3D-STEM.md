# x3d.STEM: direction, projects and wow factors (v0, 4 Nov 2026)

The beginning of x3d.STEM: science, technology, engineering and maths built as X3D worlds that can be held accountable. Its first delivery is the Scientific Loom Observatory ([REVIEW-scientific.md](REVIEW-scientific.md)). This document proposes where it goes next. **Everything below that is not cited is a proposal (grade S)** until a project builds it and a witness passes; statements about tools are L and flagged where not checked here.

Decided 4 Nov: a new repository `x3d.STEM`; all four audiences, leaning researchers, never excluding K-12; three fidelity tiers from the same verified data.

---

## 1. The idea in one paragraph

Most science visualisation is either beautiful and unaccountable (a render nobody can check) or accountable and austere (a desktop tool only experts open). The Loom already makes 3D worlds that carry their own evidence: a generator, independent witnesses, receipts, and a flywheel that turns every failure into a rule. The Scientific Loom showed that the same discipline holds for real numerical science: a Kerr image whose constraint residual stays below 7×10⁻⁹, a vortex whose Hamiltonian drifts 4×10⁻⁶, gates that rejected beautiful mistakes. **x3d.STEM is that discipline aimed at every science, at every age, at the highest visual fidelity the evidence allows.** Its promise to a viewer: *every frame you see is a measurement, and you can ask how we know.*

What sets it apart (S):
- **From ParaView**: it runs in a browser, tells a story, and carries its receipts; ParaView stays the expert reference (paired review is an open gate).
- **From typical WebGL science demos**: it refuses to show an uncomputed state, names every limit, and fails closed.
- **From classroom simulations**: the K-12 view and the researcher's view are the same verified case, so the child's picture is not a cartoon of the science; it *is* the science, explained differently.

---

## 2. One verified case, four lenses

The answer to "researchers first, but don't exclude elementary": build each study once, as a verified case bank, and present it through **lenses**. A lens changes words, camera, controls and pacing. **It never changes the data, the case or the evidence.**

| Lens | Audience | What it shows | Controls | The "how do we know?" button |
|---|---|---|---|---|
| **Explorer** | K-12, families | One question per scene ("Why do the rings wobble?"), big gestures, sound, a guide | Play, pick a case, one slider that maps to a real parameter | A child-sized receipt: "a computer checked this 960 times; here is what it checked" |
| **Lab** | University | A worked experiment: change a parameter among computed cases, predict, compare to a reference control | Case switch, sections, probes, plots | The witness table with plain-language descriptions of each check |
| **Instrument** | Researchers | Quantitative fields, probes, convergence, raw exports (VTI/VTU), the full evidence ledger | Everything; shift-click probes; ParaView export | The full ledger, receipts, builder hashes, limits |
| **Theatre** | Museums, domes, walls | A self-running cinematic of the measured events, with sound | None, or a single "next" | A wall caption and a QR code to the Instrument lens |

Rules for lenses (S):
1. **Same case hash in every lens.** A lens receipt names the case manifest it shows.
2. **No invented intermediates in any lens.** Theatre's slow motion uses saved states only (the Scientific Loom already enforces this, as its "no invented interpolation" label shows).
3. **Simplify words, not claims.** Explorer may say "the rings bump and bounce apart"; it may not say "they reconnect" unless the topology witness exists (open gate).
4. **Every lens can reach the receipt in one step.**

---

## 3. Three fidelity tiers (decided 4 Nov)

| Tier | Where it renders | What it is for | Honesty rule |
|---|---|---|---|
| **A · Any browser** | The viewer's own GPU through WebGL2 (X_ITE) | Classrooms, laptops, phones, shared links | Adaptive quality; profiles name the renderer; never claim a frame rate measured elsewhere |
| **B · Streamed GPU workstation** | An L4 or G4 cloud workstation running the same page, streamed to the viewer | Live high fidelity for researchers and exhibits on weak clients | The Scientific Loom's own warning holds: *hosting on a GPU does not move rendering*; only a workstation session does. Profile receipts bound to the GPU, viewport and settings; budget per hour on his yes |
| **C · Offline hero** | Path-traced renders (Blender Cycles through x3d-blender-io, or a dedicated volume path tracer) from the same checkpoints | Films, posters, dome masters, papers | The hero frame names the case hash and the renderer; it is never passed off as the interactive view |

One **tier receipt** per pixel source: which tier, which renderer, which case and state. No GPU number has been measured anywhere in the family yet (C: every project's own evidence says software GL only), so Tier B starts with a measurement, not a promise.

---

## 4. Wow factors for high visual fidelity, each with its science-safe rule

| # | Technique | Where it lands | Wow | Science-safe rule |
|---|---|---|---|---|
| W1 | **Progressive convergence when still.** Accumulate jittered ray-march samples while the camera rests; the still frame converges toward reference quality | Tier A/B, all volume studies | A noisy preview that resolves into a crisp, photographic field in a second or two | Accumulate only the *same* state and settings; any change resets (measurement invalidation, failure mode 25). Show the sample count |
| W2 | **Photon rings for Kerr.** Adaptive ray refinement near the critical curve; resolve the n = 1 and n = 2 sub-rings; spectral colour from Doppler and gravitational shift (g) on a blackbody | Kerr 2 (§6) | The thin bright ring hugging the shadow, sharper the closer you look | The analytic critical curve of Kerr is the reference control (L: Bardeen's shadow boundary); ring width must converge under refinement; colour stays tied to g |
| W3 | **Physically based volumes.** Emission–absorption with single scattering in the browser; multiple scattering in Tier C | Vortex, matter, turbulence, plasma | Fields that look like smoke, glass or glowing gas instead of a plastic surface | Transfer functions declared and fixed (law 23); a "surface" view stays labelled as a contour, not the object (S7) |
| W4 | **Event cinematography.** Cameras that frame a *measured* event (closest approach of the rings, onset of the instability, the band edge) | Theatre lens, Tier C films | Shots that feel directed, because they are directed by the data | The shot cites the metric that triggered it; no shot implies an unmeasured event |
| W5 | **Powers-of-ten flights.** Stable multiscale zoom from galaxy to lab to molecule | Cross-study tours | One continuous journey across 20 orders of magnitude | Use the Observatory's stable zoom algebra (−asinh b, failure mode 50); scale bars on screen always |
| W6 | **Sonification.** Hear the data: vortex reconnection emits sound waves in a superfluid; a binary inspiral chirps; Bloch modes ring | Explorer, Theatre | Science you can hear, not only see | Reuse Loomsong's Ear witness: the sound is synthesised from the same case data; onsets match events within a stated tolerance |
| W7 | **Studio light and materials.** GGX studio environment, contact shadows, ambient occlusion from the signed distance field, subsurface for soft matter | All | Gallery-quality stills | Appearance is authored and says so (the Scientific Loom already labels its brass as not molten metal); fix the white clipping on voxel tops and the specular hot spots flagged in the review |
| W8 | **Flow-field language.** Streamlines, pathlines, line-integral convolution, glyph fields | Turbulence, plasma, electromagnetism | The visual vocabulary scientists recognise from ParaView, rendered beautifully | Seeds and integration step declared; integration error witnessed against an analytic flow |
| W9 | **WebXR and domes.** Room-scale walk-inside, hand probes; fisheye masters for planetariums; tiled walls | Theatre, Lab | Standing inside the vortex tangle or under the black hole's sky | Same case and state; the XR camera is witnessed like any camera (arrival epoch, failure mode 48) |
| W10 | **Real next to computed.** Gaussian-splat captures of real apparatus or specimens beside the simulation | Lab, Theatre | "This is the real crystal; this is the model of its vibrations" | The splat names its capture; Pose and Fidelity witnesses from the Loom roadmap apply |
| W11 | **Standard nodes where possible.** X3D's own VolumeRendering component (VolumeData, IsoSurfaceVolumeData) and ParticleSystems before custom shaders | All Tier A scenes | Portable, validator-witnessable scenes that other X3D browsers can open | L, to check: X_ITE's support for the VolumeRendering nodes and their quality against the custom ray marcher. Custom shaders stay behind reconstruction witnesses |

---

## 5. The project catalogue

Each idea pairs a model with **the witness that makes it honest** (a reference control or invariant) and a **wow moment**. Lenses: E = Explorer, L = Lab, I = Instrument, T = Theatre. Size: S/M/L effort. All S (proposals).

### Physics
| Idea | Model / data | Reference control (the honest part) | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Electron Cloud Observatory | Hydrogen-like orbitals; then H₂⁺ and small molecules | Exact hydrogen energies −1/(2n²) hartree; orbital normalisation | Probability clouds coloured by phase, morphing between orbitals | E L I T | S |
| Quantum Double Slit | Linear Schrödinger, split-step Fourier (the GPE engine with the nonlinearity off) | Free Gaussian spreading is analytic | Interference fringes building particle by particle | E L T | S |
| Vortex Reconnection & Sound | GPE at 160³ (the Scientific Loom's `--profile high`) with vortex-line tracking | Particle number, Hamiltonian; topology convergence is the open gate to close | Two rings touch, re-link, and a sound burst radiates; you hear it | L I T | L |
| Ising Crystal | 3D Ising Monte Carlo, phase transition | 2D Onsager critical temperature 2/ln(1+√2) ≈ 2.269 as the control | Domains boiling and freezing as temperature crosses the critical point | E L I | S |
| Light in a Crystal | Maxwell FDTD: dipole antenna, photonic crystal | Far-field dipole pattern; band gap compared with the phononic analogue | Waves bending around a defect; light "trapped" in a gap | L I T | M |
| Turbulence Cathedral | Taylor–Green vortex, spectral Navier–Stokes | Initial analytic decay; published dissipation curve at Re = 1,600 (L) | Vortex tubes (Q-criterion) tangling into a cathedral of filaments | L I T | L |
| Star in a Bottle | Tokamak field lines | Solov'ev analytic equilibrium (L) | Nested magnetic surfaces glowing like a lantern | L I T | M |

### Astronomy and gravity
| Idea | Model / data | Reference control | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Kerr 2: The Photon Ring | The Scientific Loom's geodesic solver, adaptively refined | Analytic Kerr critical curve; ring-width convergence | The sharp photon ring and its sub-rings; spectral colour; a Tier C film | L I T | M |
| Chirp | Binary inspiral, post-Newtonian waveform, sonified | Leading-order (quadrupole) chirp law f(t) | Two black holes spiral in while the room hears the rising chirp | E L T | M |
| Galaxy Collision | N-body with softening | Two-body Kepler orbit; total energy | Tidal tails unfurling (Antennae-like) | E L T | M |
| Real Sky | Solar system from real ephemerides | Published ephemerides as truth (truth gate, licence recorded) | A to-scale flight from the Sun to Neptune | E L | S |

### Chemistry and materials
| Idea | Model / data | Reference control | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Turing Garden | 3D Gray–Scott reaction–diffusion | Turing instability wavelength from linear stability analysis | Spots, stripes and labyrinths growing like coral | E L I T | S |
| Crystals and Brillouin Zones | CIF structures; reciprocal lattices | Symmetry operations and lattice constants checked against the source | Walk through a crystal, then flip to its Brillouin zone and see the phononic paths | L I | S |
| Proteins in Motion | PDB structures; short molecular dynamics | Bond-length and angle statistics; energy drift | A protein breathing, coloured by flexibility | E L I T | M |
| Gyroids to Print | Triply periodic minimal surfaces; link to the matter study's bicontinuous phase | Mean curvature ≈ 0 numerically | The same labyrinth from phase separation, then as a 3D-printable part (3MF) | E L I | S |

### Life and medicine
| Idea | Model / data | Reference control | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Living Heart | Excitable media (Aliev–Panfilov) on an anatomical heart mesh | 1D plane-wave speed; spiral period | Electrical spiral waves rotating across a beating heart | E L I T | M |
| Neuron Forest | Real neuron morphologies + cable equation | Analytic cable length constant | A signal racing down a dendrite tree | E L I | M |
| City Outbreak | SIR on the Data City lineage | Final-size relation of the SIR model | An epidemic lighting up a city, with every number traced to a row | E L I | S |

### Earth
| Idea | Model / data | Reference control | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Seismic Planet | Elastic waves through a layered Earth | Layered travel times (L: a published reference Earth model) | P and S waves crossing the planet; the shadow zone appears | E L I T | L |
| Living Atmosphere | Real reanalysis data | Truth gate on real data, licence recorded | Global winds as glowing streamlines over a night Earth | E L T | M |

### Mathematics
| Idea | Model | Reference control | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Butterfly | Lorenz system | Largest Lyapunov exponent ≈ 0.906 for the classic parameters (L) | Two nearly identical butterflies diverging | E L T | S |
| Knots and Surfaces | Knots, Seifert surfaces; the Armenian knot from the loom renders | Linking number and other invariants computed and checked | A knot's surface unfolding, then the Armenian knot traced | E L | S |
| Hearing Fourier | Fourier series of real musical scores | Parseval's identity | Loomsong's tapestry decomposed into its harmonics, seen and heard | E L T | S |

### Engineering
| Idea | Model / data | Reference control | Wow moment | Lenses | Size |
|---|---|---|---|---|---|
| Metamaterial Building | The phononic FEM inside an IFC building (IFC bridge) | Homogeneous wave speed; IFC truth gates | A building that does not shake when the ground does | L I T | L |
| Robots That Balance | MuJoCo models from X3D/3MF (the MuJoCo playbook) | Energy and contact sanity; a drop test | A robot walking across an X3D world, with its physics witnessed | L I | M |
| Mechanisms | Gear Loom plus torque and contact | Gear Loom's clearance certificate and frame clock | A watch movement, every tooth certified | E L I | M |

---

## 6. Flagship roadmap: the next six, two first

| Order | Build | Why now | Exit criteria (all witnessed, receipts written) | Size |
|---|---|---|---|---|
| **1** | **Kerr 2: The Photon Ring** (pass 1 built 4 Nov in `~/Projects/x3d/x3d.STEM/studies/kerr2`) | Maximum wow, reuses the existing solver, and its honesty test is analytic | Critical curve matches the analytic boundary within a stated tolerance; ring width converges under two refinements; spectral colour bound to g; Tier A view + a Tier C film from the same rays | M |
| **2** | **Turing Garden** (pass 1 built 4 Nov in `~/Projects/x3d/x3d.STEM/studies/turing-garden`: five gardens, 68 witnesses green including exact linear-mode decay and the per-step budget identity, every garden name a measured claim, browser meshes cross-checked against the builder; **not yet**: the Turing wavelength from linear stability, selection across several seeds, the Instrument and Theatre lenses) | Spans K-12 to research, cheap to compute, gorgeous, and reuses the Cahn–Hilliard engine | Turing wavelength matches linear theory; pattern selection reproduced across seeds; all four lenses built on one case bank | S |
| 3 | Electron Cloud Observatory (pass 1 built 4 Nov in `~/Projects/x3d/x3d.STEM/studies/electron-cloud`: ten orbitals 1s to 5g and the Lyman-α superposition, 156 witnesses green against exact hydrogen, browser meshes cross-checked; **not yet**: H₂⁺ and molecules, complex orbitals coloured by phase, the Instrument and Theatre lenses) | Exact references; the chemistry door | Energies within tolerance of −1/(2n²); normalisation; Explorer and Lab lenses | S |
| 4 | Chirp (pass 1 built 4 Nov in `~/Projects/x3d/x3d.STEM/studies/chirp`: three inspirals, 36 witnesses green against Peters and the chirp law, an exact Ear witness with a negative control, picture locked to the audio clock; **not yet**: merger and ringdown, spins, the dome master and a listening test) | The sound-and-sight museum piece; reuses Loomsong's Ear witness | Chirp law reproduced; audio onsets match the waveform; Theatre lens on a dome master | M |
| 5 | Living Heart | Biology, anatomy and spectacle; links to the anatomy work | Plane-wave speed reference; spiral period stable under refinement | M |
| 6 | Vortex Reconnection & Sound | Closes the Scientific Loom's open topology gate; research-grade | Vortex-line topology converges across grids; reconnection claimed only then; acoustic emission measured | L |

Before any of them: **the Scientific Loom pass 2** should absorb the hardening patch (component declarations, fail-closed gates), bind its browser evidence to the candidate, and fix the flagged clipping and hot spots. Every new project starts from `kit/loomkit` and the `x3d-stem-science` profile rather than writing its own gates (S13).

---

## 7. Synergy: how the whole family feeds x3d.STEM

| Family piece | What it gives x3d.STEM |
|---|---|
| **x3d_mcp fork** | The Meaning witness. It already caught the Scientific Loom's undeclared Shaders and Texturing components (C) |
| **x3d.onto** | The rulebook: SCI gates join FACTS and loom_gate; the ontology gives every study a node identity |
| **x3d.ML / x3dprov** | Provenance from solver checkpoint to pixel; PROV-O export makes case banks citable research objects |
| **x3d-blender-io** | Tier C: checkpoints become path-traced films, posters and dome masters |
| **x3d.xray** | The memory lens: a flyable graph of every case, witness and receipt |
| **Gobbler / Linked Observatory** | The semantic bridge: a concept (vorticity, eigenmode) links across studies, as the Observatory linked 103 classes across two worlds |
| **Loomsong** | Sonification and the Ear witness (W6) |
| **Data City / Dynasty Loom** | Truth gates for real data, null semantics, lineage to the row |
| **IFC bridge + Gear Loom** | Engineering studies with certified geometry |
| **MuJoCo playbook** | Robotics and contact physics (Robots That Balance) |
| **Wikidata / Wikipedia maps** | Every study and concept linked to a Wikidata identity, so x3d.STEM grows into a navigable atlas of science |
| **Visualization agenda (X3D-Bench)** | The x3d.STEM witnesses are ground truth for a benchmark of AI-generated scientific 3D: "make a hydrogen 2p orbital scene" scored by its reference control, not by eye |
| **Stumping** | STEM stump prompts whose triggers are physics: an orbital with the wrong node count fails |

---

## 8. A maturity ladder for science projects

| Level | Required | Who it is for |
|---|---|---|
| **STEM-0 · Sketch** | Generator, Grammar, Meaning, Traps; model scope stated | Prototypes; never public |
| **STEM-1 · Checked bank** | `x3d-stem-science/v1`: required reference/invariant/refinement witnesses per kind, display range, publication, builder binding | Shareable demos (the Scientific Loom with its hardening patch is here, C) |
| **STEM-2 · Bound browser** | Browser, reconstruction and frame-coherence witnesses bound to the candidate; all lenses built | Classrooms, museum previews |
| **STEM-3 · Measured fidelity** | Tier B GPU receipts; paired expert review against ParaView; Tier C films with their own receipts | Exhibitions, teaching at scale |
| **STEM-4 · Research grade** | Convergence and topology studies closed; data and code citable (PROV-O, DOI) | Papers, collaborations |

---

## 9. A first layout for the x3d.STEM repository

```
x3d.STEM/
  README.md            the promise, the lenses, the tiers, the ladder
  loom/                profiles (x3d-stem-science), sci gates (from loomkit), the hardening rules
  studies/
    scientific-loom/   pass 1 as delivered, plus pass 2 with the hardening patch
    kerr2/ turing-garden/ ...
  lenses/              shared Explorer / Lab / Instrument / Theatre shells
  tiers/               workstation profile recipes; Tier C render recipes
  bench/               X3D-Bench tasks with reference controls
  docs/                this document, reviews, decisions
```

Large case banks (the Scientific Loom's is about 300 MB) belong in releases or object storage with their hashes in git, not in git history.

---

## 10. Questions to settle as it grows

1. **The first two builds**: Kerr 2 and Turing Garden as proposed, or different priorities?
2. **Tier B budget**: an L4/G4 workstation costs money per hour. Set a cap before the first measured run.
3. **Who reviews?** The paired ParaView review needs a domain expert per study; who?
4. **Licensing**: the Scientific Loom is MIT. Keep MIT for x3d.STEM code, and a separate licence for data?
5. **Which lens first**: researchers (Instrument) or the wow (Theatre) for the next demo?
