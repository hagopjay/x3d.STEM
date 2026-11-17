# Add Research Loom: three witnessed scientific visualization instruments

Researchers need to move a figure between numerical arrays, interactive X3D
and authoring tools without losing track of its units, assumptions or source.
This adds a focused workbench with Flow Loom (ABC trajectories), Tensor Loom
(covariance/PCA and CSV observations) and Resonance Loom (membrane modes).
Nine presets retain raw arrays, 78 saved states and 63 explicit scientific
witnesses. A bank becomes visible only after every candidate and export passes.

The exchange layer writes X3D 4/portable 3.3, VTP/VTI, PLY, OBJ and CSV, and reads
its documented static X3D subset. An owned Blender adapter preserves editable
geometry through a proper Y-up/Z-up rotation and measures actual save/reopen
readback. Three executed Blender5.2.4 scenes, glTF2 transfers and authored CPU
renders are delivered with the ready-to-run distribution. The source patch
retains reproducible recipes and receipts; large computed outputs are ignored.

The UI verifies packet/frame bytes, rejects stale asynchronous scene commits
and labels imported geometry separately from recomputed science. Documentation
includes a field guide, a measured hub matrix, and an assessment of the distinct
roles of x3d.STEM, x3d.demo and x3d.docs.

Validation: normal and optimized Python suites; Node UI adapter controls;
independent scientific references; actual X3D and VTK geometry readback; 78 XSD4
frame checks; three Blender save/reopen mutation controls; three GLB reimports.
See `studies/research-loom/docs/VALIDATION.md` and `evidence/release.json` for exact
counts and identities. Native X_ITE browser pixels remain unverified on this host.

## Apply and open

```sh
git apply --check X3D-STEM-Research-Loom.patch
git apply X3D-STEM-Research-Loom.patch
cd studies/research-loom
python3 -m pip install -r requirements.txt
python3 tools/build.py
python3 serve.py --open
```

Patch base: `09a6321da28ea494b8dc0bae59eaa6936e04d2d8` in
`https://github.com/hagopjay/x3d.STEM`. No upstream commit, push, pull request or
deployment is performed by this delivery.
