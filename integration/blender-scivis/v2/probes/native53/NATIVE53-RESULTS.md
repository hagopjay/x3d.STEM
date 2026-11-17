# Native Blender 5.3: seven splat questions, measured

Private research result · 17 November 2026.

The recovered seven-question probe is now an executed, bounded structural test.
Four asymmetric splats with all SH coefficients through degree 3 import into an
actual Blender 5.3.0 native Gaussian-splat PointCloud. The current ecosystem
fork exports them to X3D 4.1 and imports them back with identical native
attribute values. A separate XML comparison checks the declared scientific
mapping rather than trusting the fork's own parser. Applying an object transform
does **not** preserve the splats' world covariance in the tested control.

This supplies a concrete B13 result. It does not complete the B01 size ladder,
renderer parity experiment or large-corpus round-trip programme.

## Executed identities

| Item | Identity |
|---|---|
| Blender | 5.3.0, release build `02f0899d78e3`, 10 November 2026 |
| Official Linux archive | `blender-5.3.0-linux-x64.tar.xz`, 406,944,100 bytes |
| Archive SHA-256 | `dacb8264197a3f7fda6001285a5a506fc97ee943881261c2c3bd63c882f22e05` |
| Checksum comparison | Matches the vendor's downloaded `blender-5.3.0.sha256` |
| Ecosystem fork | `hagopjay/x3d-blender-io@044bea3ae33a991f816de15a307826b6d7f576ec`; clean worktree |
| Fixture | Four splats, maximum SH degree 3, binary little-endian reference PLY |
| Payload | 62 float32 properties × 4 splats = 992 bytes; header counted separately |
| Coordinate units | Arbitrary fixture units; these are structural controls rather than physical observations |
| Validator | `hagopjay/x3d_mcp@b5c9956917714747fe1d034c729612e99b0f09c9`, XSD 4.1 and semantic vocabulary 4.1 |

The runtime download receipt, probe source hash, fork source hashes, PLY, X3D
and `.blend` hashes are retained in the JSON receipts. The vendor runtime and
400 MB archive should remain outside the portable evidence bundle.

## Answers from actual imported attributes

The expected values derive from the written PLY property list and exactly
serialized float32 inputs. The tested fork is not used as the import oracle.

| Question | Observed answer | Maximum absolute difference |
|---|---|---:|
| Q1: Is `radiance:base.xyz` raw DC or reconstructed RGB? | Raw SH DC coefficients. The reconstructed-RGB hypothesis fails distinctly. | DC: `0`; RGB hypothesis: `1.9358104` |
| Q2: Is `radiance:base.w` activated opacity? | Matches the sigmoid of the PLY opacity logit. | `4.9436317 × 10⁻⁸` |
| Q3: Is `scale` linear? | Matches `exp(scale_i)` from the PLY log-scale fields. | `1.4238989 × 10⁻⁸` |
| Q4: What is the quaternion ordering? | Normalized `(w,x,y,z)` in Blender's native attribute. | `4.7503028 × 10⁻⁸` |
| Q5: How are higher SH slots ordered? | All 15 `radiance:sh_i` RGB triples match channel-major PLY `f_rest` unpacking, with `i = degree² − 1 + coefficient`. | `0` across every tested slot |
| Q6: What happens to the PLY coordinates? | The default importer leaves these raw positions unchanged, with an identity object matrix; world positions match the source. | Raw and world positions: `0` |
| Q7: Is a color-space label exposed? | No dedicated encoding label was found by the inspected PointCloud RNA/custom-property checks. `color_attributes` exists as a collection. | Descriptive inspection; no color-fidelity conclusion |

Q6 reports numeric behavior for this import operation. It does not establish
the physical meaning of an arbitrary PLY's axes. Keep the source up/forward
convention explicit. Q7 is bounded introspection, not proof that every internal
Blender color mechanism lacks metadata.

## Fork transfer and independent checks

The probe selects only the original native object and uses matching identity-axis
export/import settings. Its independent XML reader checks **20 arrays**:
positions, scales, orientations, opacities, the DC term and all 15 higher SH
coefficient triples. This catches a mapping error even if a fork importer and
exporter accidentally agree with each other.

| Check | Result |
|---|---|
| Independent expected values versus actual XML scalars | Maximum error `7.7977882 × 10⁻⁸` |
| Native attributes before export versus after fork import | Maximum error `0` |
| Native attributes across `.blend` save/reopen | Maximum error `0` for all three retained PointCloud objects |
| Deliberately changed actual native position, source retained | Detected |
| XSD 4.1 validation of the actual fork output | Pass |
| Semantic diagnostics | Three informational messages; no errors |
| Deliberately invalid XML attribute | Rejected by the pinned validator |

The informational diagnostics concern unused DEF names and the absence of an
authored Viewpoint. The XML artifact is a structural transfer fixture, without
an authored publication camera. No native X_ITE rendering was executed here.

## Apply Transform: a demonstrated limitation

The control copies the native object, applies translation `(1,2,3)`, Euler
rotation `(0.2,−0.3,0.4)` radians and scale `(1.5,0.75,2)`, then calls the actual
Blender Apply Transform operator.

Before and after the operation, world covariance is reconstructed from the
actual scale/quaternion attributes and object matrix:

\[
\Sigma_{world}=M R\,\mathrm{diag}(s_x^2,s_y^2,s_z^2)R^T M^T.
\]

World positions change by at most `4.7683716 × 10⁻⁷` fixture units, while world
covariance changes by as much as **`0.22836776` fixture units²**. Position
preservation alone would therefore miss the shape change. The report records
both raw attribute snapshots and both covariance arrays.

Keep object transforms explicit until a route proves preservation of the full
Gaussian, including directional SH behavior. This probe does not implement a
general affine covariance decomposition or Wigner-D SH rotation.

## Reproduce

From this directory, with a Blender 5.3 executable and the named fork checkout:

```sh
/path/to/blender --background --factory-startup --threads 2 --python-exit-code 1 \
  --python probe_native53.py -- --output results \
  --addon-root /path/to/x3d-blender-io
```

The XML validator adapter defaults to the existing pinned Research Loom
validator in this workspace. An explicit path supports another checkout:

```sh
python3 validate_native_x3d.py --study-root /path/to/x3d.STEM/studies/research-loom
```

Do not silently substitute a different validator and retain the old receipt.

## Remaining scope

No renderer parity, beauty render, SPZ/glTF/USD native import, memory scaling,
large point count or GPU performance claim is established. Native export absence
is a documented Blender limitation, not a conclusion drawn from trying every
export operator. The four-splat mapping result should become a small CI canary;
the larger B01/B06/B16/B26 experiments remain separate tasks.

Primary sources checked on 17 November 2026:

- [Blender 5.3 release](https://www.blender.org/releases/5-3/)
- [Blender 5.3 rendering and native splat limitations](https://developer.blender.org/docs/release_notes/5.3/rendering/)
- [Official runtime directory](https://download.blender.org/release/Blender5.3/)
- [Official SHA-256 list](https://download.blender.org/release/Blender5.3/blender-5.3.0.sha256)
- [Reference 3DGS PLY writer](https://github.com/graphdeco-inria/gaussian-splatting/blob/main/scene/gaussian_model.py)
