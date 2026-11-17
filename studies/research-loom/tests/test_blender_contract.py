"""Pure transfer-contract controls; actual Blender execution has separate receipts."""
import copy
import math
import unittest

from stemloom.blender_io import (compare_frames, from_blender, to_blender,
                                validate_frame, srgb_to_linear, linear_to_srgb,
                                encode_source, decode_source, canonical)


def specimen():
    return {"time": .25, "metrics": [], "meshes": [
        {"id": "triangle", "positions": [[0, 0, 0], [1.2, -.4, .2], [.3, 1.1, .5]],
         "faces": [[0, 1, 2]], "colors": [[1, 0, 0], [0, 1, 0], [0, 0, 1]], "opacity": .6}],
        "lines": [{"id": "path", "positions": [[-.3, 0, 1], [.1, .4, .7], [.6, .7, .9]],
                   "color": [.2, .7, .9], "radius": .023}],
        "points": [{"id": "observations", "positions": [[.25, -.2, .9], [.2, .3, -.1]],
                    "colors": [[.7, .3, .2], [.1, .4, .8]], "radius": .04}]}


class BlenderContract(unittest.TestCase):
    def test_source_storage_is_chunked_bound_and_recovers_actual_packet(self):
        packet = {'frames': [specimen()], 'id': 'sample', 'long': list(range(5000))}
        encoded = encode_source(packet)
        self.assertLess(max(map(len, encoded.splitlines())), 110)
        self.assertEqual(decode_source(encoded), packet)
        self.assertEqual(decode_source(canonical(packet)), packet)
        changed = encoded.replace('"decoded_bytes": ', '"decoded_bytes": 1', 1)
        with self.assertRaises(ValueError): decode_source(changed)

    def test_explicit_srgb_transfer_has_a_tight_inverse(self):
        for value in (0, .001, .04045, .1, .5, 1):
            self.assertAlmostEqual(linear_to_srgb(srgb_to_linear(value)), value, places=7)

    def test_rotation_inverse_and_handedness(self):
        for p in ([1, 2, 3], [-.1234, 14.5, -4], [0, 0, 0]):
            self.assertEqual(from_blender(to_blender(p)), list(p))
            self.assertAlmostEqual(sum(x*x for x in p), sum(x*x for x in to_blender(p)))
        x, y, z = [to_blender(p) for p in ([1,0,0], [0,1,0], [0,0,1])]
        cross = [x[1]*y[2]-x[2]*y[1], x[2]*y[0]-x[0]*y[2], x[0]*y[1]-x[1]*y[0]]
        self.assertEqual(cross, z)

    def test_contract_and_unchanged_twin(self):
        frame = specimen(); self.assertIs(validate_frame(frame), frame)
        result = compare_frames(frame, copy.deepcopy(frame))
        self.assertEqual(result['status'], 'pass')
        self.assertEqual(result['scientific_positions'], 8)

    def test_perturbed_coordinate_color_topology_and_record_are_caught(self):
        frame = specimen()
        variants = []
        other = copy.deepcopy(frame); other['meshes'][0]['positions'][1][0] += .001; variants.append(other)
        other = copy.deepcopy(frame); other['meshes'][0]['colors'][0][0] = .8; variants.append(other)
        other = copy.deepcopy(frame); other['meshes'][0]['faces'] = [[0,2,1]]; variants.append(other)
        other = copy.deepcopy(frame); other['lines'][0]['id'] = 'different'; variants.append(other)
        for changed in variants:
            self.assertEqual(compare_frames(frame, changed)['status'], 'fail')
        self.assertEqual(compare_frames(frame, copy.deepcopy(frame))['status'], 'pass')

    def test_nonfinite_and_bad_geometry_refuse(self):
        for value in (math.nan, math.inf, True):
            other = specimen(); other['points'][0]['positions'][0][0] = value
            with self.assertRaises(ValueError): validate_frame(other)
        for mutation in ('index', 'duplicate', 'color', 'radius'):
            other = specimen()
            if mutation == 'index': other['meshes'][0]['faces'] = [[0,1,8]]
            elif mutation == 'duplicate': other['lines'][0]['id'] = 'triangle'
            elif mutation == 'color': other['points'][0]['colors'][0][1] = -1
            elif mutation == 'radius': other['lines'][0]['radius'] = 0
            with self.assertRaises(ValueError): validate_frame(other)


if __name__ == '__main__':
    unittest.main()
