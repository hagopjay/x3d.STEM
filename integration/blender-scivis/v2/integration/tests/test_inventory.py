import copy
from datetime import datetime, timezone
from pathlib import Path
import tempfile
import unittest
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import inventory as inv


class InventoryControls(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(); self.root = Path(self.temp.name)
        (self.root/'receipt.json').write_bytes(b'{"status":"pass"}\n')
        (self.root/'tool.py').write_bytes(b'print("oracle")\n')
        builder = inv.Builder(self.root)
        self.receipt = builder.artifact(self.root/'receipt.json', role='receipt')
        self.source = builder.artifact(self.root/'tool.py', role='producer')
        subject = builder.add('Dataset', 'fixture', 'Fixture', 'One asymmetric static fixture.')
        tool = builder.add('ToolBuild', 'oracle', 'Oracle source', 'One local comparison.', source_artifacts=[self.source])
        self.run = builder.add('ValidationRun', 'original', 'Recorded comparison', 'Selected geometry only.',
                               execution='recorded', outcome='pass', ended_at='2020-01-01T00:00:00+00:00',
                               tool=tool, artifacts=[self.receipt])
        self.evidence = builder.add('EvidenceRecord', 'geometry', 'Recorded geometry result', 'Selected geometry only.',
                                    evidence_state='executed', outcome='pass', observed_at='2020-01-01T00:00:00+00:00',
                                    run=self.run, subjects=[subject], facets=['geometry.coordinates'],
                                    scope_terms=['fixture','frame:1'], artifacts=[self.receipt], source_bindings=[self.source])
        self.claim = builder.add('Claim', 'geometry', 'Coordinates survive', 'Selected geometry only.',
                                 subjects=[subject], facets=['geometry.coordinates'], scope_terms=['fixture','frame:1'],
                                 required_state='executed', evidence=[self.evidence])
        self.graph = {'schema':inv.SCHEMA, '@context':inv.CONTEXT, '@graph':list(builder.nodes.values())}

    def tearDown(self):
        self.temp.cleanup()

    def node(self, ident):
        return next(r for r in self.graph['@graph'] if r['@id'] == ident)

    def inspect(self):
        return inv.verify(self.graph, {'stem_repo': self.root})

    def test_unchanged_record_supports_only_recorded_geometry(self):
        report = self.inspect()
        self.assertEqual(report['status'], 'pass')
        self.assertFalse(report['evidence'][0]['fresh_execution'])
        self.assertEqual(inv.support(self.graph,self.claim,report)['status'], 'supported_within_declared_scope')

    def test_receipt_byte_drift_blocks_support_without_rewriting_history(self):
        (self.root/'receipt.json').write_bytes(b'{"status":"fail"}\n')
        result = self.inspect()
        self.assertEqual(result['status'], 'fail')
        self.assertEqual(result['evidence'][0]['recorded_state'], 'executed')
        self.assertEqual(inv.support(self.graph,self.claim,result)['status'], 'unsupported')

    def test_producer_drift_is_separate_from_receipt_binding(self):
        (self.root/'tool.py').write_bytes(b'print("changed")\n')
        report = self.inspect(); evidence = report['evidence'][0]
        self.assertEqual(evidence['artifact_bindings'], 'pass')
        self.assertEqual(evidence['producer_bindings'], 'unverified')
        self.assertEqual(inv.support(self.graph,self.claim,report)['status'], 'unsupported')

    def test_geometry_cannot_certify_pixels_or_science(self):
        for facet in ['appearance.pixel_parity', 'science.model', 'science.after_geometry_edit']:
            self.node(self.claim)['facets'] = [facet]
            result = inv.support(self.graph,self.claim,self.inspect())
            self.assertEqual(result['status'], 'unsupported')
            self.assertEqual(result['missing_facets'], [facet])

    def test_frame_scope_does_not_generalize(self):
        self.node(self.claim)['scope_terms'] = ['fixture', 'frame:99']
        result = inv.support(self.graph,self.claim,self.inspect())
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(result['evidence_rejected'][0]['reason'], 'different_scope')

    def test_future_or_unrun_execution_cannot_promote(self):
        self.node(self.evidence)['observed_at'] = '2999-01-01T00:00:00+00:00'
        with self.assertRaisesRegex(inv.Rejected, 'FUTURE_EXECUTION'): inv.validate(self.graph)
        self.node(self.evidence)['observed_at'] = '2020-01-01T00:00:00+00:00'
        self.node(self.run)['execution'] = 'not_run'
        with self.assertRaisesRegex(inv.Rejected, 'UNRUN_EVIDENCE'): inv.validate(self.graph)

    def test_same_run_cannot_be_called_reproduced(self):
        self.node(self.evidence)['evidence_state'] = 'reproduced'
        self.node(self.evidence)['reproduces'] = self.evidence
        with self.assertRaisesRegex(inv.Rejected, 'INDEPENDENT_REPEAT'): inv.validate(self.graph)

    def test_reproduction_must_match_the_original_frame_scope(self):
        run = copy.deepcopy(self.node(self.run)); run['@id'] = 'urn:test:repeat-run'
        repeat = copy.deepcopy(self.node(self.evidence))
        repeat.update({'@id':'urn:test:repeat-evidence', 'run':run['@id'],
                       'evidence_state':'reproduced', 'reproduces':self.evidence})
        self.graph['@graph'].extend([run, repeat])
        inv.validate(self.graph)
        repeat['scope_terms'] = ['fixture', 'frame:99']
        with self.assertRaisesRegex(inv.Rejected, 'REPRODUCTION_SCOPE_DIFFERS'):
            inv.validate(self.graph)

    def test_historical_confirmed_label_remains_reported(self):
        e = self.node(self.evidence)
        e.update(evidence_state='reported', outcome='pass', source_grade='Confirmed')
        result = inv.support(self.graph,self.claim,self.inspect())
        self.assertEqual(result['status'], 'unsupported')
        self.assertEqual(e['evidence_state'], 'reported')
        self.assertEqual(e['source_grade'], 'Confirmed')

    def test_lossy_execution_pass_does_not_become_lossless(self):
        e = self.node(self.evidence)
        e.update(facets=['software.import_export_execution'], measurements={'status':'pass','retention_status':'lossy'})
        self.node(self.claim)['facets'] = ['geometry.lossless_transfer']
        self.assertEqual(inv.support(self.graph,self.claim,self.inspect())['status'], 'unsupported')

    def test_old_inspection_cannot_certify_changed_inventory(self):
        report = self.inspect()
        self.node(self.claim)['title'] = 'Changed after inspection'
        with self.assertRaisesRegex(inv.Rejected, 'DIFFERENT_INVENTORY'):
            inv.support(self.graph,self.claim,report)

    def test_duplicate_identity_wildcard_dangling_reference_and_hash_method_refused(self):
        mutations = [lambda g:g['@graph'].append(copy.deepcopy(g['@graph'][0])),
                     lambda g:next(r for r in g['@graph'] if r['@id']==self.evidence).update(facets=['geometry.*']),
                     lambda g:next(r for r in g['@graph'] if r['@id']==self.claim).update(evidence=['urn:missing']),
                     lambda g:next(r for r in g['@graph'] if r['@id']==self.receipt).update(hash_method='xml-c14n')]
        for mutate in mutations:
            graph = copy.deepcopy(self.graph); mutate(graph)
            with self.assertRaises(inv.Rejected): inv.validate(graph)

    def test_local_roots_cannot_escape_through_symlink(self):
        with tempfile.TemporaryDirectory() as other:
            target = Path(other)/'remote';target.write_bytes((self.root/'receipt.json').read_bytes())
            (self.root/'receipt.json').unlink();(self.root/'receipt.json').symlink_to(target)
            self.assertEqual(self.inspect()['status'], 'fail')


if __name__ == '__main__':
    unittest.main()
