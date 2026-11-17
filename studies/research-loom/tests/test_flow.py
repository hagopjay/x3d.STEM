"""Independent controls for the analytic flow and its displayed periodic paths."""
import json
from math import pi
from pathlib import Path
import sys
import unittest

import numpy as np

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stemloom.flow import PRESETS, build_case, rk4, split_periodic_polyline, velocity


class FieldIdentityTests(unittest.TestCase):
    def test_velocity_matches_scalar_formula_and_periodicity(self):
        q = np.array([[.4, -.7, 1.1], [-2., 2.7, -.5]])
        coefficients = (1.4, .7, .9)
        a, b, c = coefficients
        expected = np.array([[a*np.sin(z)+c*np.cos(y), b*np.sin(x)+a*np.cos(z),
                              c*np.sin(y)+b*np.cos(x)] for x, y, z in q])
        np.testing.assert_allclose(velocity(q, coefficients), expected, atol=1e-15)
        for axis in np.eye(3):
            np.testing.assert_allclose(velocity(q+2*pi*axis, coefficients), expected, atol=3e-15)

    def test_integrable_control_retains_z_and_constant_velocity(self):
        seeds = np.array([[.4, -.7, 1.1], [-2., 2.7, -.5], [0., 0., 0.]])
        times, paths = rk4(seeds, (1, 0, 0), duration=2., step=.02)
        expected = seeds+times[:, None, None]*np.array([[np.sin(z), np.cos(z), 0.] for _, _, z in seeds])[None]
        np.testing.assert_allclose(paths, expected, atol=2e-14)

    def test_numerical_curl_matches_field_and_divergence_vanishes(self):
        q = np.random.default_rng(32).uniform(-2, 2, (30, 3))
        h = 2e-5
        derivatives = [(velocity(q+h*axis)-velocity(q-h*axis))/(2*h) for axis in np.eye(3)]
        div = sum(derivatives[j][:, j] for j in range(3))
        curl = np.column_stack([derivatives[1][:, 2]-derivatives[2][:, 1],
                                derivatives[2][:, 0]-derivatives[0][:, 2],
                                derivatives[0][:, 1]-derivatives[1][:, 0]])
        np.testing.assert_allclose(div, 0, atol=1e-12)
        np.testing.assert_allclose(curl, velocity(q), atol=2e-9)

    def test_rk4_refinement_agrees_with_a_separate_small_step_reference(self):
        seeds = np.array([[.4, -.7, 1.1], [-2., 2.7, -.5]])
        _, coarse = rk4(seeds, (1.4, .7, .9), duration=2, step=.08)
        _, fine = rk4(seeds, (1.4, .7, .9), duration=2, step=.04)
        _, reference = rk4(seeds, (1.4, .7, .9), duration=2, step=.005)
        coarse_error = np.linalg.norm(coarse[-1]-reference[-1])
        fine_error = np.linalg.norm(fine[-1]-reference[-1])
        self.assertGreater(coarse_error/fine_error, 12)
        self.assertLess(coarse_error/fine_error, 20)


class PeriodicGeometryTests(unittest.TestCase):
    def test_single_face_crossing_is_split_at_the_boundary(self):
        parts = split_periodic_polyline([[pi-.1, 0, 0], [pi+.1, .2, 0]])
        self.assertEqual(len(parts), 2)
        np.testing.assert_allclose(parts[0], [[pi-.1, 0, 0], [pi, .1, 0]], atol=1e-14)
        np.testing.assert_allclose(parts[1], [[-pi, .1, 0], [-pi+.1, .2, 0]], atol=1e-14)

    def test_multiple_and_negative_crossings_preserve_total_polyline_length(self):
        points = np.array([[pi-.2, -pi+.1, 0.], [pi+.3, -pi-.4, .7],
                           [4*pi+.1, -3*pi-.2, -pi-.2]])
        parts = split_periodic_polyline(points)
        expected = sum(np.linalg.norm(b-a) for a, b in zip(points[:-1], points[1:]))
        observed = sum(np.linalg.norm(b-a) for part in parts for a, b in zip(np.asarray(part)[:-1], np.asarray(part)[1:]))
        self.assertAlmostEqual(observed, expected, places=12)
        self.assertTrue(all(np.max(np.abs(part)) <= pi+1e-12 for part in map(np.asarray, parts)))

    def test_all_cases_are_finite_within_geometry_budgets_and_own_green_witnesses(self):
        for preset in PRESETS:
            with self.subTest(preset=preset):
                case = build_case(preset)
                json.dumps(case, allow_nan=False)
                self.assertEqual(len(case['frames']), 9)
                self.assertTrue(all(w['pass'] for w in case['witnesses']), case['witnesses'])
                for frame in case['frames']:
                    records = frame['meshes']+frame['lines']+frame['points']
                    self.assertLessEqual(len(records), 250)
                    self.assertLessEqual(sum(len(r['positions']) for r in records), 30000)
                    self.assertEqual(len(records), len({r['id'] for r in records}))
                    for row in records:
                        positions = np.asarray(row['positions'])
                        self.assertTrue(np.isfinite(positions).all())
                        self.assertLessEqual(np.max(np.abs(positions)), pi+1e-12)
                        if 'colors' in row:
                            colors = np.asarray(row['colors'])
                            self.assertEqual(colors.shape, positions.shape)
                            self.assertTrue(((colors >= 0) & (colors <= 1)).all())
                        if row in frame['lines'] and not row['id'].startswith('periodic_box'):
                            self.assertLess(np.max(np.abs(np.diff(positions, axis=0))), .2)

    def test_saved_particles_are_wrapped_actual_integrator_states(self):
        case = build_case('default')
        paths = np.asarray(case['measurements']['trajectories_unwrapped'])
        for frame in case['frames']:
            index = round(frame['time']/.03)
            expected = (paths[:24, index]+pi) % (2*pi)-pi
            np.testing.assert_allclose(frame['points'][0]['positions'], expected, atol=1e-13)

    def test_velocity_grid_is_an_attributed_point_dataset(self):
        case = build_case('anisotropic')
        field = case['datasets']['velocity_grid']
        self.assertEqual(field['shape'], [9, 9, 9])
        expected = velocity(field['positions'], (1.4, .7, .9))
        np.testing.assert_allclose(field['velocity'], expected, atol=1e-15)

    def test_unknown_case_refuses(self):
        with self.assertRaises(ValueError):
            build_case('unknown')


if __name__ == '__main__':
    unittest.main()
