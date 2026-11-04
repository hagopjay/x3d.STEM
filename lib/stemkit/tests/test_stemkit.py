"""stemkit tests: exact geometric references and negative controls. Run normally and under -O:

  python3 -E -s -m unittest discover -s lib/stemkit/tests -t lib
  python3 -O -E -s -m unittest discover -s lib/stemkit/tests -t lib
"""
from __future__ import annotations

import unittest

import numpy as np

from stemkit import docs, mesh, meshio
from stemkit.core import Rejected, witness


def grid(n):
    return np.stack(np.meshgrid(*(np.arange(n, dtype=float),) * 3, indexing="ij"), axis=-1)


def sphere(n=34, R=10.0):
    x = grid(n) - (n - 1) / 2
    return R - np.linalg.norm(x, axis=-1), R


def torus(n=40, R=11.0, r=4.0):
    x = grid(n) - (n - 1) / 2
    q = np.hypot(x[..., 0], x[..., 1]) - R
    return r - np.hypot(q, x[..., 2]), R, r


def euler(verts, faces):
    e = np.concatenate([faces[:, [0, 1]], faces[:, [1, 2]], faces[:, [2, 0]]])
    e.sort(axis=1)
    return len(verts) - len(np.unique(e, axis=0)) + len(faces)


class SurfaceNets(unittest.TestCase):
    # Characterization bounds on a unit grid (measured 4 Nov: sphere R = 10 volume -0.97 %, area -0.58 %;
    # torus R = 11, r = 4 volume -1.99 %). Both deficits are expected: the trilinear interpolant of a convex
    # distance field lies inside the true surface, and a polyhedron with vertices on a convex surface is
    # inscribed in it (mean gap H * sum(l^2) / 24 per triangle). A sign or scale error is far outside them.
    def test_sphere_against_exact_geometry(self):
        f, R = sphere()
        v, t = mesh.surface_nets(f, 0.0)
        c = mesh.checks(f, 0.0, v, t, np.random.default_rng(1))
        self.assertEqual(c["boundary_edges"], 0)
        self.assertEqual(euler(v, t), 2)
        self.assertLess(abs(c["volume"] / (4 / 3 * np.pi * R**3) - 1), 0.015)
        self.assertLess(abs(c["area"] / (4 * np.pi * R**2) - 1), 0.015)
        self.assertLess(c["volume_rel_diff"], 0.01)
        self.assertLess(c["iso_distance_p95"], 0.01)
        H = mesh.mean_curvature(f, v)
        self.assertLess(abs(np.median(H) * R - 1), 0.03)
        nrm = mesh.vertex_normals(f, v)
        centre = (np.array(f.shape) - 1) / 2
        self.assertTrue((np.einsum("ij,ij->i", nrm, v - centre) > 0).all(), "normals must point outward")

    def test_torus_volume_and_genus(self):
        f, R, r = torus()
        v, t = mesh.surface_nets(f, 0.0)
        c = mesh.checks(f, 0.0, v, t, np.random.default_rng(2))
        self.assertEqual(c["boundary_edges"], 0)
        self.assertEqual(euler(v, t), 0)
        self.assertLess(abs(c["volume"] / (2 * np.pi**2 * R * r**2) - 1), 0.03)

    def test_projection_converges_on_a_step(self):
        # a sharp seed: v = 0.25 inside a cube, 0.005 outside (the Turing Garden's t = 0)
        f = np.full((24, 24, 24), 0.005)
        f[8:16, 8:16, 8:16] = 0.25
        v, t = mesh.surface_nets(f, 0.2)
        c = mesh.checks(f, 0.2, v, t, np.random.default_rng(6))
        self.assertEqual(c["boundary_edges"], 0)
        self.assertLess(c["iso_distance_p95"], 1e-6)

    def test_trilinear_gradient_matches_finite_differences(self):
        rng = np.random.default_rng(8)
        f = rng.random((6, 6, 6))
        p = rng.random((50, 3)) * 4.8 + 0.1
        h = 1e-6
        fd = np.stack([(mesh.trilinear(f, p + h * e) - mesh.trilinear(f, p - h * e)) / (2 * h) for e in np.eye(3)], axis=1)
        self.assertLess(np.abs(mesh.trilinear_grad(f, p) - fd).max(), 1e-6)

    def test_open_surface_is_rejected_and_padding_closes_it(self):
        f, _ = sphere(n=20, R=12.0)          # the sphere is cut by the box
        with self.assertRaises(Rejected) as e:
            mesh.surface_nets(f, 0.0)
        self.assertEqual(e.exception.code, "MESH_OPEN_AT_BOUNDARY")
        v, t = mesh.surface_nets(mesh.pad_field(f, -1.0), 0.0)
        self.assertEqual(mesh.checks(mesh.pad_field(f, -1.0), 0.0, v, t, np.random.default_rng(3))["boundary_edges"], 0)

    def test_negative_control_reversed_faces_fail_the_volume_witness(self):
        f, _ = sphere()
        v, t = mesh.surface_nets(f, 0.0)
        c = mesh.checks(f, 0.0, v, t[:, ::-1], np.random.default_rng(4))
        self.assertLess(c["volume"], 0)
        self.assertFalse(witness("volume", c["volume_rel_diff"], 0.02)["pass"])

    def test_negative_control_open_mesh_is_seen(self):
        f, _ = sphere()
        v, t = mesh.surface_nets(f, 0.0)
        self.assertGreater(mesh.checks(f, 0.0, v, t[1:], np.random.default_rng(5))["boundary_edges"], 0)


class MeshIO(unittest.TestCase):
    def test_roundtrip(self):
        f, _ = sphere()
        v, t = mesh.surface_nets(f, 0.0)
        n = mesh.vertex_normals(f, v)
        col = np.full((len(v), 3), 200, "u1")
        ext = np.array(f.shape, float) - 1
        raw, info = meshio.pack(v, n, col, t, ext)
        v2, n2, c2, t2 = meshio.unpack(raw, info)
        self.assertTrue(np.array_equal(t2, t))
        self.assertTrue(np.array_equal(c2, col))
        self.assertLessEqual(np.abs(v2 - v).max(), ext.max() / 65535 / 2 + 1e-12)
        self.assertAlmostEqual(info["quantization_max_cells"], float(np.abs(v2 - v).max()))
        self.assertLess(np.abs(n2 - n).max(), 1 / 127 + 1e-9)

    def test_truncated_blob_is_rejected(self):
        f, _ = sphere()
        v, t = mesh.surface_nets(f, 0.0)
        raw, info = meshio.pack(v, mesh.vertex_normals(f, v), np.zeros((len(v), 3), "u1"), t, np.array(f.shape, float) - 1)
        with self.assertRaises((Rejected, ValueError)):
            meshio.unpack(raw[:-4], info)


class Docs(unittest.TestCase):
    def test_escapes_html(self):
        out = docs.render("# T <b>\n\nA <script>x</script> and `<i>` **bold**", "t")
        self.assertNotIn("<script>x", out)
        self.assertIn("&lt;script&gt;", out)
        self.assertIn("<code>&lt;i&gt;</code>", out)
        self.assertIn("<strong>bold</strong>", out)

    def test_table_and_list(self):
        out = docs.render("| a | b |\n|---|---|\n| 1 | 2 |\n\n1. one\n2. two", "t")
        self.assertIn("<td>1</td>", out)
        self.assertIn("<ol><li>one</li><li>two</li></ol>", out)


class NoStdlibShadowing(unittest.TestCase):
    def test_no_tool_or_module_named_like_the_standard_library(self):
        # A study's tools/ directory is sys.path[0] for every script in it: tools/numbers.py once hid the
        # stdlib 'numbers' module and NumPy failed to import (Kerr 2, 4 Nov).
        import sys
        from pathlib import Path
        repo = Path(__file__).resolve().parents[3]
        files = list(repo.glob("studies/*/tools/*.py")) + list(repo.glob("lib/stemkit/*.py"))
        self.assertTrue(files)
        bad = [str(f.relative_to(repo)) for f in files if f.stem in sys.stdlib_module_names]
        self.assertEqual(bad, [])


class SharedJavaScript(unittest.TestCase):
    # Studies serve only their own folder, so they carry copies of lib/stemkit/js; a copy that drifts from
    # the library would mesh differently from the Python reference. Pinned copies are listed with a reason.
    PINNED = {"studies/turing-garden/src/nets.js": "accepted 4 Nov before the library copy existed; migrate in its next pass"}

    def test_study_copies_match_the_library(self):
        from pathlib import Path
        repo = Path(__file__).resolve().parents[3]
        lib = (repo / "lib/stemkit/js/nets.js").read_bytes()
        copies = [p for p in repo.glob("studies/*/src/nets.js") if str(p.relative_to(repo)) not in self.PINNED]
        self.assertTrue(copies)
        self.assertEqual([str(p.relative_to(repo)) for p in copies if p.read_bytes() != lib], [])


class FailClosed(unittest.TestCase):
    def test_witness_is_not_an_assert(self):
        self.assertFalse(witness("x", 2.0, 1.0)["pass"])
        with self.assertRaises(Rejected):
            witness("x", float("nan"), 1.0)


if __name__ == "__main__":
    unittest.main()
