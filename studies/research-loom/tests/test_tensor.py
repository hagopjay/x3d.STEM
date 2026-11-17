"""Independent checks of covariance geometry, probability semantics and imports."""
import json
from math import erf, exp, pi, sqrt
import unittest

import numpy as np
from scipy.spatial.distance import mahalanobis
from scipy.stats import chi2

from stemloom.tensor import LEVELS, PRESETS, build_case, build_from_points


class TensorTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.cases = {key: build_case(key) for key in PRESETS}

    def test_sample_moments_against_independent_numpy_covariance(self):
        for case in self.cases.values():
            data = np.asarray(case['measurements']['observations'])
            mean = np.asarray(case['measurements']['sample_mean'])
            covariance = np.asarray(case['measurements']['sample_covariance'])
            np.testing.assert_allclose(mean, np.mean(data, axis=0), atol=1e-14)
            np.testing.assert_allclose(covariance, np.cov(data, rowvar=False, ddof=1), atol=2e-15)
            inverse = np.linalg.inv(covariance)
            values = [mahalanobis(point, mean, inverse)**2 for point in data]
            np.testing.assert_allclose(values, case['measurements']['mahalanobis_squared'], atol=4e-13)

    def test_one_sigma_is_not_68_percent_in_three_dimensions(self):
        # Closed chi-square_3 CDF at one, independent of scipy.stats.chi2.cdf.
        reference = erf(1/sqrt(2))-sqrt(2/pi)*exp(-.5)
        self.assertAlmostEqual(reference, .19874804309879915, places=14)
        for case in self.cases.values():
            self.assertAlmostEqual(case['measurements']['one_radius_gaussian_probability'], reference, places=14)
            self.assertIn('not a confidence ellipsoid', case['scope'])

    def test_frames_are_thresholds_and_never_move_observations(self):
        for case in self.cases.values():
            data = case['measurements']['observations']
            previous = 0
            for level, frame in zip(LEVELS, case['frames']):
                self.assertEqual(frame['time'], level)
                self.assertEqual(frame['points'][0]['positions'], data)
                count = next(m['value'] for m in frame['metrics'] if m['id'] == 'count')
                self.assertGreaterEqual(count, previous)
                previous = count
                fields = frame['points'][0]['point_data']
                q = np.asarray(fields['mahalanobis_squared']['values'])
                flag = np.asarray(fields['inside_selected_ellipsoid']['values'])
                np.testing.assert_array_equal(flag, q <= chi2.ppf(level, 3))
                self.assertEqual(fields['principal_scores']['components'], 3)
                self.assertEqual(np.asarray(fields['principal_scores']['values']).shape, (360, 3))

    def test_every_emitted_surface_vertex_has_declared_quadratic_radius(self):
        for case in self.cases.values():
            mean = np.asarray(case['measurements']['sample_mean'])
            inverse = np.linalg.inv(case['measurements']['sample_covariance'])
            for level, frame in zip(LEVELS, case['frames']):
                delta = np.asarray(frame['meshes'][0]['positions'])-mean
                squared = np.einsum('ij,jk,ik->i', delta, inverse, delta)
                np.testing.assert_allclose(squared, chi2.ppf(level, 3), rtol=3e-13, atol=5e-13)
                self.assertLessEqual(len(delta), 500)
                self.assertLessEqual(len(frame['meshes'][0]['faces']), 1000)

    def test_witnesses_json_and_repeatability(self):
        for key, case in self.cases.items():
            self.assertTrue(all(w['pass'] for w in case['witnesses']))
            first = json.dumps(case, sort_keys=True, allow_nan=False)
            self.assertEqual(first, json.dumps(build_case(key), sort_keys=True, allow_nan=False))
        self.assertEqual(build_case()['id'], 'tensor-correlated')
        with self.assertRaises(ValueError):
            build_case('arbitrary')

    def test_population_reference_and_mixture_are_distinct(self):
        spherical = self.cases['spherical']['measurements']
        np.testing.assert_allclose(spherical['population_reference']['covariance'], .64*np.eye(3))
        # Finite-sample preferred axes are not misrepresented as population axes.
        self.assertGreater(np.ptp(spherical['eigenvalues']), .01)
        mixture = self.cases['mixture']
        self.assertEqual(mixture['parameters']['assumption'], 'non-Gaussian mixture')
        self.assertIn('comparison model only', mixture['scope'])
        self.assertEqual(set(mixture['measurements']['group_labels']), {0, 1})
        for case in self.cases.values():
            self.assertGreater(case['measurements']['population_reference']['affine_determinant'], 0)

    def test_import_refuses_bad_shape_types_nonfinite_and_rank(self):
        bad = [[], [[0, 1, 2]], np.ones((4, 2)), np.ones((4, 3)),
               np.zeros((5001, 3)), np.ones((4, 3), dtype=bool),
               np.array([['1', '2', '3']]*4), np.ones((4, 3), dtype=complex),
               [[0, 0, 0], [1, 0, 0], [0, 1, 0], [1, 1, 0]],
               [[0, 0, 0], [1, 0, 0], [0, 1, 0], [0, 0, float('nan')]]]
        for points in bad:
            with self.subTest(shape=np.asarray(points).shape), self.assertRaises(ValueError):
                build_from_points(points)

    def test_import_has_content_identity_and_no_gaussian_claim(self):
        points = [[0, 0, 0], [2, 0, 0], [0, 3, 0], [0, 0, 4], [1, 1, 1]]
        case = build_from_points(points, 'Five laboratory observations')
        self.assertEqual(case['measurements']['observations'], points)
        self.assertTrue(case['id'].startswith('tensor-import-'))
        self.assertEqual(case['parameters']['assumption'], 'unclassified imported observations')
        self.assertIn('not asserted Gaussian', case['scope'])
        self.assertNotEqual(case['id'], build_from_points(np.asarray(points)*2)['id'])
        with self.assertRaises(ValueError):
            build_from_points(points, label='')


if __name__ == '__main__':
    unittest.main()
