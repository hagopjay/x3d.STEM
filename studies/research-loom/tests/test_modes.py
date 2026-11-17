"""Independent reference checks for the exact and discrete membrane studies."""
from __future__ import annotations

import json
from math import pi, sqrt
from pathlib import Path
import sys
import unittest

import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from stemloom.modes import (HEIGHT_SCALE, IN_PLANE_SCALE, PRESETS, angular_frequency,
                           build_case, discrete_eigenvalue, evaluate_field)


class ModeTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {key: build_case(key) for key in PRESETS}

    def test_all_four_boundaries_and_wave_equation(self):
        for case in self.cases.values():
            p = case["parameters"]
            components = [(v["m"], v["n"], v["amplitude"], v["phase"]) for v in p["components"]]
            rng = np.random.default_rng(1986)
            x, z = rng.uniform(0, p["length_x"], 80), rng.uniform(0, p["length_z"], 80)
            for time in (.07, .81, 1.13):
                u, _, _, _, utt, lap = evaluate_field(x, z, time, p["length_x"], p["length_z"], components)
                self.assertLess(np.max(np.abs(utt-lap)), 1e-14)
                for a, b in ((x*0, z), (x*0+p["length_x"], z), (x, z*0), (x, z*0+p["length_z"])):
                    self.assertLess(np.max(np.abs(evaluate_field(a, b, time, p["length_x"], p["length_z"], components)[0])), 1e-15)

    def test_frequencies_against_separation_formula(self):
        for case in self.cases.values():
            p = case["parameters"]
            for mode, frequency in zip(p["components"], case["measurements"]["frequencies"]):
                reference = .5*sqrt((mode["m"]/p["length_x"])**2+(mode["n"]/p["length_z"])**2)
                self.assertAlmostEqual(frequency, reference, places=14)
        self.assertEqual(self.cases["degenerate"]["measurements"]["beat_frequency"], 0)
        self.assertGreater(self.cases["beats"]["measurements"]["beat_frequency"], .01)

    def test_energy_by_independent_modal_orthogonality(self):
        for case in self.cases.values():
            p = case["parameters"]
            expected = p["length_x"]*p["length_z"]/8*sum(
                m["amplitude"]**2*pi*pi*((m["m"]/p["length_x"])**2+(m["n"]/p["length_z"])**2)
                for m in p["components"])
            for measured in case["measurements"]["energy_quadrature"]:
                self.assertAlmostEqual(measured, expected, places=13)
            self.assertLess(case["measurements"]["max_relative_energy_difference"], 1e-12)

    def test_temporal_quadrature_is_a_real_two_mode_solution(self):
        case = self.cases["degenerate"]
        data = case["measurements"]
        period = 1/data["frequencies"][0]
        u0 = np.asarray(data["displacement"][0])
        uq = np.asarray(data["displacement"][2])
        x, z = np.meshgrid(data["x"], data["z"], indexing="xy")
        np.testing.assert_allclose(u0, .021*np.sin(pi*x)*np.sin(2*pi*z), atol=1e-15)
        np.testing.assert_allclose(uq, .021*np.sin(2*pi*x)*np.sin(pi*z), atol=1e-15)
        self.assertAlmostEqual(data["times"][2], period/4)

    def test_finite_difference_convergence_and_assembled_eigenproblem(self):
        for case in self.cases.values():
            data = case["measurements"]
            errors = [r["relative_error"] for r in data["finite_difference_convergence"]]
            self.assertGreater(errors[0], errors[1])
            self.assertGreater(errors[1], errors[2])
            self.assertGreater(data["observed_order"], 1.94)
            self.assertLess(data["observed_order"], 2.06)
            self.assertLess(data["discrete_eigenproblem"]["max_eigenvector_residual"], 1e-8)
            p = case["parameters"]
            direct = discrete_eigenvalue(1, 1, 12, p["length_x"], p["length_z"])
            self.assertAlmostEqual(data["discrete_eigenproblem"]["numeric_eigenvalues"][0], direct, places=9)

    def test_rendered_positions_colors_and_scalar_arrays_match_model(self):
        for case in self.cases.values():
            p, data = case["parameters"], case["measurements"]
            x, z = np.meshgrid(data["x"], data["z"], indexing="xy")
            for frame, raw in zip(case["frames"], data["displacement"]):
                mesh = frame["meshes"][0]
                positions = np.asarray(mesh["positions"])
                u = np.asarray(raw)
                np.testing.assert_allclose(positions[:, 0], IN_PLANE_SCALE*(x.ravel()-p["length_x"]/2))
                np.testing.assert_allclose(positions[:, 1], HEIGHT_SCALE*u.ravel())
                np.testing.assert_allclose(positions[:, 2], IN_PLANE_SCALE*(z.ravel()-p["length_z"]/2))
                np.testing.assert_array_equal(mesh["point_data"]["displacement"]["values"], u.ravel())
                self.assertEqual(len(mesh["colors"]), len(positions))
                self.assertTrue(np.all((np.asarray(mesh["colors"]) >= 0) & (np.asarray(mesh["colors"]) <= 1)))

    def test_beating_envelope_is_local_and_long_time_not_sparse_movie(self):
        data = self.cases["beats"]["measurements"]
        self.assertGreater(data["beat_period"], data["times"][-1]*3)
        self.assertEqual(len(data["probe_envelope"]["time"]), 161)
        self.assertAlmostEqual(data["probe_envelope"]["time"][-1], data["beat_period"])
        self.assertTrue(np.all(np.asarray(data["probe_envelope"]["probe_upper_amplitude"]) >= 0))

    def test_geometry_budgets_finite_witnesses_and_saved_times(self):
        for case in self.cases.values():
            json.dumps(case, allow_nan=False)
            self.assertTrue(all(w["pass"] for w in case["witnesses"]))
            self.assertLessEqual(len(case["frames"]), 12)
            times = np.asarray([f["time"] for f in case["frames"]])
            np.testing.assert_allclose(np.diff(times), np.diff(times)[0], rtol=1e-13)
            for frame in case["frames"]:
                geometry = frame["meshes"]+frame["lines"]+frame["points"]
                self.assertLessEqual(len(geometry), 250)
                self.assertEqual(len(geometry), len({g["id"] for g in geometry}))
                self.assertLessEqual(sum(len(g["positions"]) for g in geometry), 30_000)
                self.assertLessEqual(sum(len(g["faces"]) for g in frame["meshes"]), 10_000)
                for g in geometry:
                    self.assertTrue(np.isfinite(g["positions"]).all())

    def test_fundamental_has_no_interior_nodal_contour(self):
        for frame in self.cases["fundamental"]["frames"]:
            self.assertFalse(any(line["id"].startswith("sampled_zero_contour")
                                 for line in frame["lines"]))

    def test_default_alias_unknown_refusal_and_repeated_build(self):
        self.assertEqual(build_case()["id"], "modes-fundamental")
        with self.assertRaises(ValueError):
            build_case("not-a-mode")
        again = build_case("fundamental")
        self.assertEqual(again["frames"], self.cases["fundamental"]["frames"])


if __name__ == "__main__":
    unittest.main()
