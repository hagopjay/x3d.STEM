"""Publication gates and actual-geometry controls independent of model presets."""
import copy
import importlib.util
from pathlib import Path
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
spec = importlib.util.spec_from_file_location('research_loom_verify', ROOT/'tools/verify.py')
instrument = importlib.util.module_from_spec(spec)
spec.loader.exec_module(instrument)
from stemloom.core import canonical, validate_case, verify_packet
from stemloom.exchange import from_x3d, to_x3d, to_vtp, to_obj, to_ply, points_csv


class PipelineTests(unittest.TestCase):
    def test_digest_and_science_gates_reject_under_optimization(self):
        report = instrument.negative_controls()
        self.assertEqual(report['count'], 5)
        self.assertGreater(report['asymmetric_signed_volume'], 0)
        self.assertEqual(report['asymmetric_signed_volume'], report['rotated_signed_volume'])

    def test_healthy_packet_and_actual_geometry_round_trip(self):
        case = instrument.fixture()
        raw = validate_case(case)
        result = verify_packet(raw, instrument.sha(raw))
        self.assertEqual(result['id'], case['id'])
        for version in ('3.3','4.0'):
            decoded = from_x3d(to_x3d(case, version=version))
            self.assertEqual(instrument.geometry_difference(case['frames'][0], decoded), 0)
            self.assertTrue(decoded['metadata']['geometry_matches_declared_hash'])

    def test_visual_coordinate_displacement_cannot_hide_in_metadata(self):
        expected = instrument.fixture()['frames'][0]
        changed = copy.deepcopy(expected)
        changed['meshes'][0]['positions'][3][2] += .1
        with self.assertRaisesRegex(ArithmeticError, 'Actual geometry difference'):
            instrument.geometry_difference(expected, changed)

    def test_scientific_witness_cannot_be_forged_by_boolean(self):
        case = instrument.fixture()
        case['witnesses'][0]['observed'] = 1
        with self.assertRaisesRegex(Exception, 'WITNESS_INCONSISTENT'):
            validate_case(case)

    @unittest.skipUnless(importlib.util.find_spec('vtk'), 'Optional actual VTK reader unavailable')
    def test_vtk_reader_and_text_hubs_decode_the_asymmetric_fixture(self):
        import vtk
        case = instrument.fixture()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory)
            for name, writer in [('geometry.vtp', to_vtp), ('geometry.obj', to_obj),
                                 ('geometry.ply', to_ply), ('coordinates.csv', points_csv)]:
                (path/name).write_text(writer(case))
            report = instrument.vtk_check(path/'geometry.vtp', case['frames'][0], vtk, case)
            self.assertEqual(report['points'], 7)
            self.assertEqual(report['max_position_difference'], 0)
            self.assertEqual(report['scientific_arrays'], ['temperature'])
            self.assertEqual(instrument.text_hub_checks(path, case['frames'][0])['polygons'], 4)


if __name__ == '__main__':
    unittest.main()
