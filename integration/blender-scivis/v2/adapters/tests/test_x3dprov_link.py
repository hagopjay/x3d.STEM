import importlib.util
from pathlib import Path
import unittest
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('figure_link', ROOT/'x3dprov_link.py')
link = importlib.util.module_from_spec(spec)
spec.loader.exec_module(link)


class ChainGuard(unittest.TestCase):
    def setUp(self):
        self.p = link.load_prov()
        self.xml = '<X3D profile="Interchange" version="4.0"><head/><Scene><Shape><Box size="1 2 3"/></Shape></Scene></X3D>'

    def test_existing_protocol_still_verifies(self):
        stamped = link.append_verified(self.p, self.xml, {'op':'ingest_reference'})
        linked = link.append_verified(self.p, stamped, {'op':'link_existing_render'})
        self.assertEqual(self.p.verify(linked)['status'], 'verified')
        self.assertEqual(self.p.content_hash(self.xml), self.p.content_hash(linked))

    def test_stale_input_cannot_be_laundered_as_next_step(self):
        stamped = self.p.add_step(self.xml, {'op':'generate'})
        changed = stamped.replace('1 2 3', '1 2 4')
        self.assertEqual(self.p.verify(changed)['status'], 'stale')
        # Existing add_step accepts retained stale metadata. The adapter refuses it.
        self.assertEqual(self.p.verify(self.p.add_step(changed, {'op':'validate'}))['status'], 'verified')
        with self.assertRaisesRegex(ValueError, 'stale'):
            link.append_verified(self.p, changed, {'op':'validate'})

    def test_broken_chain_cannot_be_extended(self):
        stamped = self.p.add_step(self.xml, {'op':'generate'})
        broken = stamped.replace('0000000000000000', '1111111111111111', 1)
        with self.assertRaisesRegex(ValueError, 'broken'):
            link.append_verified(self.p, broken, {'op':'render'})

    def test_malformed_xml_cannot_enter_fallback_hash_branch(self):
        with self.assertRaises(Exception):
            link.append_verified(self.p, '<X3D><Scene>', {'op':'generate'})

    def test_entity_inputs_refused(self):
        with self.assertRaisesRegex(ValueError, 'DTD/entity'):
            link.append_verified(self.p, '<!DOCTYPE X3D><X3D/>', {'op':'ingest_reference'})

    def test_reordered_existing_metadata_cannot_hide_a_stale_record(self):
        stamped = self.p.add_step(self.xml, {'op':'generate'})
        root = ET.fromstring(stamped)
        for m in root.findall('./head/meta'):
            if m.get('name','').startswith('x3dprov.step.'):
                name, content = m.get('name'), m.get('content')
                m.attrib.clear(); m.set('content', content); m.set('name', name)
        changed = ET.tostring(root, encoding='unicode').replace('1 2 3', '1 2 4')
        self.assertEqual(self.p.verify(changed)['status'], 'no-record')
        with self.assertRaisesRegex(ValueError, 'Unrecognized provenance serialization'):
            link.append_verified(self.p, changed, {'op':'validate'})

    def test_unknown_provenance_marker_is_not_an_unstamped_scene(self):
        unknown = self.xml.replace('<head/>', '<head><meta name="x3dprov.step.future" content="{}"/></head>')
        with self.assertRaisesRegex(ValueError, 'Unrecognized provenance'):
            link.append_verified(self.p, unknown, {'op':'validate'})

    def test_marker_outside_head_is_refused(self):
        outside = self.xml.replace('<Scene>', '<Scene><meta name="x3dprov.version" content="x3dprov/0.1"/>')
        with self.assertRaisesRegex(ValueError, 'location'):
            link.append_verified(self.p, outside, {'op':'validate'})


if __name__ == '__main__':
    unittest.main()
