#!/usr/bin/env python3
"""Private, read-only evidence inventory adapter; never executes a producer.

Original receipts remain authoritative records. This overlay identifies bytes,
links their scopes and answers narrow support queries; it is not x3dprov, a new
provenance protocol, signature system, scientific validator or scalar score.
"""
from __future__ import annotations

import argparse
from collections import Counter
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path, PurePosixPath
import re
import sys

SCHEMA = 'scivis.evidence-spine/1'
STATES = {'reported': 0, 'inspected': 1, 'executed': 2, 'reproduced': 3}
OUTCOMES = {'pass', 'fail', 'partial', 'unknown'}
CONFIDENTIALITY = {'private', 'restricted', 'public'}
TYPES = {'Claim', 'EvidenceRecord', 'Artifact', 'ToolBuild', 'ValidationRun',
         'Bridge', 'Transformation', 'Loss', 'Dataset', 'CoordinateFrame'}
HASH_METHOD = 'sha256-file-bytes'
CANONICAL_METHOD = 'sha256-json-sortkeys-utf8-compact-no-nonfinite'
CONTEXT = {
    '@vocab': 'urn:x3d-scivis:inventory:',
    'scivis': 'urn:x3d-scivis:inventory:',
    'prov': 'http://www.w3.org/ns/prov#',
    'sosa': 'http://www.w3.org/ns/sosa/',
    'qudt': 'http://qudt.org/schema/qudt/',
    'skos': 'http://www.w3.org/2004/02/skos/core#',
    'dcterms': 'http://purl.org/dc/terms/',
    'title': 'dcterms:title', 'scope': 'dcterms:description',
    'based_on': {'@id': 'prov:wasDerivedFrom', '@type': '@id', '@container': '@set'},
    'subjects': {'@id': 'scivis:subject', '@type': '@id', '@container': '@set'},
    'artifacts': {'@id': 'scivis:boundArtifact', '@type': '@id', '@container': '@set'},
    'source_artifacts': {'@id': 'scivis:toolSourceArtifact', '@type': '@id', '@container': '@set'},
    'source_bindings': {'@id': 'scivis:sourceBinding', '@type': '@id', '@container': '@set'},
    'run': {'@id': 'scivis:validationRun', '@type': '@id'},
    'tool': {'@id': 'scivis:toolBuild', '@type': '@id'},
    'bridge': {'@id': 'scivis:relatesToBridge', '@type': '@id', '@container': '@set'},
    'evidence': {'@id': 'scivis:candidateEvidence', '@type': '@id', '@container': '@set'},
    'coordinate_frame': {'@id': 'scivis:coordinateFrame', '@type': '@id'},
    'input_frame': {'@id': 'scivis:inputFrame', '@type': '@id'},
    'output_frame': {'@id': 'scivis:outputFrame', '@type': '@id'},
    'packet': {'@id': 'scivis:packetArtifact', '@type': '@id'},
    'reproduces': {'@id': 'scivis:reproducesEvidence', '@type': '@id'},
    'facets': 'scivis:facet', 'outcome': 'scivis:outcome',
    'evidence_state': 'scivis:evidenceState', 'hash_method': 'scivis:hashMethod',
    'sha256': 'scivis:sha256', 'confidentiality': 'scivis:confidentiality',
}


class Rejected(ValueError):
    pass


def need(ok, message):
    if not ok:
        raise Rejected(message)


def digest(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':'),
                      allow_nan=False).encode('utf-8')


def read_json(path):
    def pairs(rows):
        out = {}
        for k, v in rows:
            need(k not in out, 'DUPLICATE_JSON_KEY: ' + k)
            out[k] = v
        return out
    def invalid(value):
        raise Rejected('NONFINITE_JSON: ' + value)
    return json.loads(Path(path).read_text(encoding='utf-8'), object_pairs_hook=pairs,
                      parse_constant=invalid)


def write_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    raw = json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + '\n'
    temporary = path.with_name(path.name + '.tmp')
    temporary.write_text(raw, encoding='utf-8'); temporary.replace(path)


def moment(value):
    need(isinstance(value, str), 'TIMESTAMP_REQUIRED')
    try:
        dt = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as error:
        raise Rejected('INVALID_TIMESTAMP') from error
    need(dt.tzinfo is not None, 'TIMEZONE_REQUIRED')
    return dt.astimezone(timezone.utc)


def entity_type(row):
    value = row.get('@type', '')
    return value.removeprefix('scivis:') if isinstance(value, str) else ''


def validate(graph, now=None):
    """Fail-closed semantic checks; the accompanying JSON Schema adds structure."""
    need(graph.get('schema') == SCHEMA, 'SCHEMA_MISMATCH')
    need(graph.get('@context') == CONTEXT, 'PINNED_LOCAL_CONTEXT_REQUIRED')
    need(isinstance(graph.get('@graph'), list), 'GRAPH_ARRAY_REQUIRED')
    current = now or datetime.now(timezone.utc)
    nodes = {}
    for row in graph['@graph']:
        need(isinstance(row, dict), 'ENTITY_OBJECT_REQUIRED')
        ident = row.get('@id'); kind = entity_type(row)
        need(isinstance(ident, str) and ident.startswith('urn:') and ident not in nodes,
             'UNIQUE_URN_REQUIRED')
        need(kind in TYPES, 'UNSUPPORTED_ENTITY_TYPE: ' + kind)
        need(isinstance(row.get('title'), str) and bool(row['title']), 'TITLE_REQUIRED')
        need(row.get('confidentiality') in CONFIDENTIALITY, 'CONFIDENTIALITY_REQUIRED')
        need(isinstance(row.get('scope'), str) and bool(row['scope']), 'SCOPE_REQUIRED')
        nodes[ident] = row
        if kind == 'Artifact':
            loc = row.get('locator', {}); path = PurePosixPath(loc.get('path', '/'))
            need(isinstance(loc.get('root'), str) and bool(loc['root']), 'ROOT_LABEL_REQUIRED')
            need(not path.is_absolute() and '..' not in path.parts and path.parts,
                 'UNSAFE_ARTIFACT_LOCATOR')
            need(row.get('hash_method') == HASH_METHOD, 'EXPLICIT_HASH_METHOD_REQUIRED')
            need(bool(re.fullmatch('[0-9a-f]{64}', str(row.get('sha256', '')))), 'SHA256_REQUIRED')
            need(type(row.get('bytes')) is int and row['bytes'] >= 0, 'BYTE_COUNT_REQUIRED')
        if kind in ('Claim', 'EvidenceRecord'):
            need(isinstance(row.get('facets'), list) and row['facets'] and
                 all(isinstance(x, str) and re.fullmatch(r'[a-z][a-z0-9_-]*(?:\.[a-z][a-z0-9_-]*)+', x)
                     for x in row['facets']), 'FACETS_REQUIRED_NO_WILDCARDS')
            need(isinstance(row.get('subjects'), list) and row['subjects'], 'SUBJECTS_REQUIRED')
            need(isinstance(row.get('scope_terms'), list) and row['scope_terms'] and
                 all(isinstance(x, str) and x for x in row['scope_terms']), 'STRUCTURED_SCOPE_REQUIRED')
        if kind == 'Claim':
            need(row.get('required_state') in STATES, 'REQUIRED_STATE_INVALID')
        if kind == 'EvidenceRecord':
            state = row.get('evidence_state')
            need(state in STATES, 'EVIDENCE_STATE_INVALID')
            need(row.get('outcome') in OUTCOMES, 'OUTCOME_INVALID')
            if state in ('executed', 'reproduced'):
                need(moment(row.get('observed_at')) <= current, 'FUTURE_EXECUTION_CANNOT_SUPPORT')
                need(row.get('run') and row.get('artifacts'), 'EXECUTION_BINDING_REQUIRED')
            if state == 'reproduced':
                need(row.get('reproduces') and row.get('reproduces') != row['@id'],
                     'INDEPENDENT_REPEAT_REFERENCE_REQUIRED')
        if kind == 'ValidationRun':
            need(row.get('outcome') in OUTCOMES, 'RUN_OUTCOME_INVALID')
            need(row.get('execution') in ('recorded', 'not_run'), 'RUN_EXECUTION_INVALID')
            if row['execution'] == 'recorded':
                need(moment(row.get('ended_at')) <= current, 'FUTURE_RUN_CANNOT_SUPPORT')
                need(row.get('tool') and row.get('artifacts'), 'RUN_BINDING_REQUIRED')
    reference_lists = ('subjects', 'artifacts', 'source_bindings', 'based_on', 'evidence', 'bridge', 'source_artifacts')
    reference_one = ('run', 'tool', 'coordinate_frame', 'reproduces', 'packet', 'input_frame', 'output_frame')
    for row in nodes.values():
        for key in reference_lists:
            for ref in row.get(key, []):
                need(ref in nodes, 'DANGLING_REFERENCE: ' + str(ref))
        for key in reference_one:
            if row.get(key): need(row[key] in nodes, 'DANGLING_REFERENCE: ' + str(row[key]))
        if entity_type(row) == 'EvidenceRecord' and row['evidence_state'] in ('executed', 'reproduced'):
            run = nodes[row['run']]
            need(entity_type(run) == 'ValidationRun' and run['execution'] == 'recorded',
                 'UNRUN_EVIDENCE_CANNOT_PROMOTE')
            need(run['outcome'] == row['outcome'], 'RUN_OUTCOME_DISAGREES')
            need(set(row.get('artifacts', [])) <= set(run.get('artifacts', [])),
                 'EVIDENCE_NOT_BOUND_TO_RUN_ARTIFACTS')
            if row['evidence_state'] == 'reproduced':
                original = nodes[row['reproduces']]
                need(entity_type(original) == 'EvidenceRecord' and original.get('run') != row['run'],
                     'SAME_RUN_IS_NOT_REPRODUCTION')
                need(original.get('evidence_state') in ('executed', 'reproduced') and
                     set(row['subjects']) == set(original['subjects']) and
                     set(row['facets']) <= set(original['facets']) and
                     set(row['scope_terms']) == set(original['scope_terms']), 'REPRODUCTION_SCOPE_DIFFERS')
    return nodes


def verify(graph, roots):
    """Rehash bytes and producer sources, without running Blender or any validator."""
    nodes = validate(graph); rows = []; statuses = {}
    for node in nodes.values():
        if entity_type(node) != 'Artifact': continue
        loc = node['locator']; result = {'artifact': node['@id'], 'role': node.get('role', 'unspecified')}
        try:
            need(loc['root'] in roots, 'SOURCE_ROOT_NOT_PROVIDED')
            root = Path(roots[loc['root']]).resolve()
            path = (root / loc['path']).resolve()
            need(path.is_relative_to(root), 'RESOLVED_PATH_ESCAPES_ROOT')
            raw = path.read_bytes()
            need(len(raw) == node['bytes'] and digest(raw) == node['sha256'], 'ARTIFACT_BYTES_CHANGED')
            result.update(status='pass')
        except (OSError, Rejected) as error:
            result.update(status='fail', reason=str(error))
        rows.append(result); statuses[node['@id']] = result['status']
    evidence = []
    for node in nodes.values():
        if entity_type(node) != 'EvidenceRecord': continue
        artifacts = node.get('artifacts', []); sources = node.get('source_bindings', [])
        evidence.append({'evidence': node['@id'], 'recorded_state': node['evidence_state'],
                         'outcome': node['outcome'],
                         'artifact_bindings': 'pass' if artifacts and all(statuses.get(a) == 'pass' for a in artifacts) else 'unverified',
                         'producer_bindings': 'pass' if sources and all(statuses.get(a) == 'pass' for a in sources) else 'unverified',
                         'fresh_execution': False})
    return {'schema': 'scivis.binding-inspection/1', 'checked_at': datetime.now(timezone.utc).isoformat(),
            'inventory_digest': {'hash_method': CANONICAL_METHOD, 'value': digest(canonical(graph))},
            'status': 'pass' if all(r['status'] == 'pass' for r in rows) else 'fail',
            'scope': 'Exact local bytes and separately labelled producer bindings. No producer, renderer or validator was rerun.',
            'artifact_count': len(rows), 'artifacts': rows, 'evidence': evidence}


def support(graph, claim_id, inspection):
    """Facet coverage query, not a project grade or promotion of source assertions."""
    nodes = validate(graph); need(claim_id in nodes, 'CLAIM_NOT_FOUND')
    need(inspection.get('schema') == 'scivis.binding-inspection/1', 'INSPECTION_SCHEMA_REQUIRED')
    need(moment(inspection.get('checked_at')) <= datetime.now(timezone.utc), 'FUTURE_INSPECTION_CANNOT_SUPPORT')
    need(inspection.get('inventory_digest') == {'hash_method': CANONICAL_METHOD, 'value': digest(canonical(graph))},
         'INSPECTION_IS_FOR_DIFFERENT_INVENTORY')
    claim = nodes[claim_id]; need(entity_type(claim) == 'Claim', 'CLAIM_TYPE_REQUIRED')
    checked = {r['evidence']: r for r in inspection.get('evidence', [])}
    covered = set(); used = []; rejected = []
    for ref in claim.get('evidence', []):
        row = nodes[ref]; reason = None
        if entity_type(row) != 'EvidenceRecord': reason = 'not_evidence'
        elif not set(claim['subjects']) <= set(row['subjects']): reason = 'different_subject'
        elif not set(claim['scope_terms']) <= set(row['scope_terms']): reason = 'different_scope'
        elif row['outcome'] != 'pass': reason = 'nonpassing_outcome'
        elif STATES[row['evidence_state']] < STATES[claim['required_state']]: reason = 'insufficient_recorded_state'
        elif checked.get(ref, {}).get('artifact_bindings') != 'pass': reason = 'artifact_binding_unverified'
        elif row['evidence_state'] in ('executed', 'reproduced') and checked.get(ref, {}).get('producer_bindings') != 'pass': reason = 'producer_binding_unverified'
        if reason: rejected.append({'evidence': ref, 'reason': reason}); continue
        overlap = set(claim['facets']) & set(row['facets'])
        if overlap: covered.update(overlap); used.append(ref)
        else: rejected.append({'evidence': ref, 'reason': 'unrelated_facet'})
    missing = sorted(set(claim['facets']) - covered)
    return {'claim': claim_id, 'status': 'supported_within_declared_scope' if not missing else 'unsupported',
            'covered_facets': sorted(covered), 'missing_facets': missing, 'evidence_used': used,
            'evidence_rejected': rejected, 'scope': claim['scope'], 'binding_inspected_at':inspection['checked_at'],
            'fresh_execution':False,
            'grade_policy': 'No Confirmed/Likely/Suspected grade is rewritten; no support beyond the named subjects and facets.'}


class Builder:
    def __init__(self, repo):
        self.repo = Path(repo).resolve(); self.nodes = {}; self.files = {}

    def add(self, kind, key, title, scope, **values):
        ident = 'urn:x3d-scivis:' + kind.lower() + ':' + key
        row = {'@id': ident, '@type': 'scivis:' + kind, 'title': title, 'scope': scope,
               'confidentiality': 'private', **values}
        need(ident not in self.nodes, 'DUPLICATE_ENTITY: ' + ident)
        self.nodes[ident] = row
        return ident

    def artifact(self, path, expected=None, role='source', size=None, root_label='stem_repo', root_path=None):
        path = Path(path).resolve(); root = Path(root_path).resolve() if root_path else self.repo
        need(path.is_relative_to(root), 'IMPORT_PATH_ESCAPES_ROOT')
        rel = path.relative_to(root).as_posix(); key = root_label + ':' + rel; raw = path.read_bytes(); measured = digest(raw)
        if expected: need(measured == expected, 'IMPORTED_BINDING_MISMATCH: ' + rel)
        if size is not None: need(len(raw) == size, 'IMPORTED_SIZE_MISMATCH: ' + rel)
        if key in self.files:
            return self.files[key]
        ident = self.add('Artifact', digest(key.encode())[:20], path.name,
                         'Exact retained file bytes; no authentication or scientific correctness follows from a hash.',
                         locator={'root': root_label, 'path': rel}, sha256=measured, bytes=len(raw),
                         hash_method=HASH_METHOD, role=role)
        self.files[key] = ident
        return ident


def import_research_loom(study, historical_notes=None, private_workspace=None):
    study = Path(study).resolve(); repo = study.parents[1]; b = Builder(repo)
    bank = read_json(study/'web/bank/index.json'); release = read_json(study/'evidence/release.json')
    need(bank.get('schema') == 'stemloom.bank/1' and release.get('status') == 'pass', 'EXPECTED_RELEASE_REQUIRED')
    bank_artifact = b.artifact(study/'web/bank/index.json', role='inventory')
    release_artifact = b.artifact(study/'evidence/release.json', role='receipt')
    producer = [b.artifact(study/name, expected, role='producer') for name, expected in bank['source_sha256'].items()]
    release_sources = [b.artifact(study/name, expected, role='producer') for name, expected in release['source_sha256'].items()]
    all_sources = sorted(set(producer + release_sources))
    frame = b.add('CoordinateFrame', 'research-loom-y-up', 'Research Loom right-handed Y-up',
                  'Unscaled display coordinates. Per-case unit labels and display magnification remain with the original packet.',
                  handedness='right', up_axis='+Y', unit_policy='per-dataset')
    blender_frame = b.add('CoordinateFrame', 'blender-z-up', 'Blender right-handed Z-up',
                          'Owned adapter proper rotation; unit scale is preserved.', handedness='right', up_axis='+Z')
    b.add('Transformation', 'y-up-to-z-up', 'Owned adapter coordinate rotation',
          'Proper rotation, no normalization or implicit rescaling. Scientific display magnification is an earlier transformation.',
          matrix=[[1,0,0],[0,0,-1],[0,1,0]], determinant=1,
          input_frame=frame, output_frame=blender_frame, based_on=producer)
    links = {1: [], 4: [], 6: [], 9: [], 10: [], 12: [], 26: [], 27: []}
    bridges = {}
    for i in range(1, 28):
        bridges[i] = b.add('Bridge', f'B{i:02d}', f'Historical bridge B{i:02d}',
                            'Identifier alignment only. Original bridge grades and completion claims are not imported as new measurements.',
                            historical_identifier=f'B{i:02d}', adoption='inventory-alignment-only')
    tool = b.add('ToolBuild', 'research-loom-check', 'Research Loom recorded release runner',
                 'Recorded runner and live source identities; importing this receipt does not execute it.',
                 version=release['schema'], source_artifacts=release_sources,
                 runtime={'python': release['python']})
    run = b.add('ValidationRun', 'research-loom-release', 'Recorded Research Loom release checks',
                release['scope'], execution='recorded', outcome='pass', tool=tool,
                ended_at=release['finished_utc'], artifacts=[release_artifact, bank_artifact],
                recorded_commands=release['commands'])
    evidence = b.add('EvidenceRecord', 'research-loom-release', 'Recorded release execution',
                     release['scope'], evidence_state='executed', outcome='pass',
                     observed_at=release['finished_utc'], run=run,
                     subjects=[run], facets=['software.regression_suite'], scope_terms=['research-loom-release', 'recorded-command-suite'],
                     artifacts=[release_artifact, bank_artifact], source_bindings=all_sources,
                     based_on=[release_artifact])
    b.add('Claim', 'release-suite', 'The recorded scoped regression suite passed',
          release['scope'], facets=['software.regression_suite'], subjects=[run],
          scope_terms=['research-loom-release', 'recorded-command-suite'],
          required_state='executed', evidence=[evidence], based_on=[release_artifact])
    datasets = {}; exports = {}
    for row in bank['cases']:
        packet_path = study/'web/bank'/row['packet']
        packet_artifact = b.artifact(packet_path, row['sha256'], 'scientific-packet', row['bytes'])
        packet = read_json(packet_path)
        dataset = b.add('Dataset', row['id'], row['title'], row['scope'], coordinate_frame=frame,
                        units=packet['units'], axes=packet['axes'], packet=packet_artifact,
                        based_on=[packet_artifact], declared_witness_count=len(packet['witnesses']),
                        saved_states=len(packet['frames']), synthetic=True)
        datasets[row['id']] = dataset
        exports[row['id']] = [packet_artifact]
        for item in list(row['exports'].values()) + row['frame_exports']:
            artifact = b.artifact(study/item['file'], item['sha256'], 'export', item['bytes'])
            exports[row['id']].append(artifact)
    verification_path = study/'evidence/verification.json'; vr = read_json(verification_path)
    verification_artifact = b.artifact(verification_path, role='receipt')
    b.nodes[verification_artifact]['embedded_hashes'] = [{
        'field': 'report_sha256', 'value': vr['report_sha256'],
        'hash_method': CANONICAL_METHOD+'-excluding-report_sha256',
        'relationship_to_file_sha256': 'different-identity-not-interchangeable'}]
    verify_tool = b.add('ToolBuild', 'research-loom-verify', 'Independent local readback instrument',
                       vr['scope'], source_artifacts=[b.artifact(study/'tools/verify.py', vr['instrument_sha256'], 'producer')],
                       runtime=vr['runtime'], version=vr['schema'])
    for row in vr['cases']:
        key = row['id']; subject = datasets[key]
        artifacts = sorted(set([verification_artifact, bank_artifact] + exports[key]))
        run = b.add('ValidationRun', 'readback-'+key, 'Recorded independent readback: '+key,
                    vr['scope'], execution='recorded', outcome=row['status'], tool=verify_tool,
                    ended_at=vr['finished_utc'], artifacts=artifacts)
        e = b.add('EvidenceRecord', 'readback-'+key, 'Recorded model and transfer checks: '+key,
                  vr['scope'], evidence_state='executed', outcome=row['status'],
                  observed_at=vr['finished_utc'], run=run, subjects=[subject],
                  scope_terms=['published-case:'+key, 'selected-hub-snapshot', 'sampled-model-checks'],
                  facets=['science.sampled_invariants', 'geometry.x3d_readback', 'data.vtk_readback'],
                  artifacts=artifacts, source_bindings=all_sources,
                  measurements=row, based_on=[verification_artifact], bridge=[bridges[10], bridges[12]])
        links[10].append(e); links[12].append(e)
        b.add('Claim', 'readback-'+key, 'Selected local scientific and transfer checks pass: '+key,
              vr['scope'], subjects=[subject], facets=['science.sampled_invariants', 'geometry.x3d_readback', 'data.vtk_readback'],
              scope_terms=['published-case:'+key, 'selected-hub-snapshot', 'sampled-model-checks'],
              required_state='executed', evidence=[e])
        b.add('Loss', 'text-hubs-'+key, 'Declared projections into OBJ, PLY and CSV',
              row['text_hubs']['losses'], subjects=[subject], based_on=[verification_artifact],
              loss_kind='semantic-projection', epistemic_status='recorded-observation')
    xp = study/'evidence/x3d-validation.json'; xr = read_json(xp)
    need(xr.get('status') == 'pass' and all(x.get('status') == 'pass' for x in xr['files']), 'XSD_RECEIPT_NOT_PASSING')
    xa = b.artifact(xp, role='receipt')
    x_sources = [b.artifact(study/'tools/validate_x3d.py', xr['instrument']['adapter_sha256'], 'producer')]
    x_sources += [b.artifact(study/'vendor/x3d_mcp'/name, expected, 'validator-source')
                  for name, expected in xr['instrument']['files_sha256'].items()]
    x_artifacts = [xa] + [b.artifact(study/row['path'], row['candidate_sha256'], 'export', row['bytes']) for row in xr['files']]
    xt = b.add('ToolBuild', 'pinned-x3d-validator', 'Pinned X3D validator and adapter',
               'Actual direct local calls recorded; XML schema and semantic vocabulary versions remain separate.',
               version=xr['instrument']['commit'], source_artifacts=x_sources,
               repository=xr['instrument']['repository'], xsd_version=xr['instrument']['xsd_version'],
               semantic_vocabulary_version=xr['instrument']['semantic_vocabulary_version'])
    xrun = b.add('ValidationRun', 'x3d-frames', 'Recorded 78-frame X3D4 validation',
                 '; '.join(xr['limitations']), execution='recorded', outcome='pass', tool=xt,
                 ended_at=xr['created_utc'], artifacts=x_artifacts)
    xe = b.add('EvidenceRecord', 'x3d-frames', 'Recorded schema and implemented semantic checks',
               'XSD4.0 and recorded vocabulary4.1 only. Does not establish visible rendering, mapping fidelity or physical validity.',
               evidence_state='executed', outcome='pass', observed_at=xr['created_utc'], run=xrun,
               subjects=list(datasets.values()), scope_terms=['78-authored-x3d4-frame-documents'],
               facets=['syntax.xsd4', 'syntax.semantic_vocabulary4-1'], artifacts=x_artifacts,
               source_bindings=x_sources, based_on=[xa], bridge=[bridges[9], bridges[10]])
    links[9].append(xe); links[10].append(xe)
    b.add('Claim', 'x3d-frames', 'The recorded authored X3D4 frame documents passed the pinned checks',
          'All authored saved frame documents; no XSD3.3 or native rendering claim.',
          subjects=list(datasets.values()), scope_terms=['78-authored-x3d4-frame-documents'],
          facets=['syntax.xsd4', 'syntax.semantic_vocabulary4-1'], required_state='executed', evidence=[xe])
    blender_tool = b.add('ToolBuild', 'blender-5.2.4', 'Recorded Blender 5.2.4 LTS',
                         'Version declared in the executed receipts. The adapter does not launch or independently authenticate this binary.',
                         version='5.2.4 LTS', based_on=[b.artifact(study/'evidence/blender-runtime.json', role='receipt')])
    for kind, case in [('flow', 'flow-balanced'), ('tensor', 'tensor-correlated'), ('modes', 'modes-degenerate')]:
        transfer_evidence = None; transfer_frame = None
        for action, filename, facets in [
            ('transfer', 'blender_bridge.py', ['geometry.coordinates', 'geometry.topology', 'geometry.color_attributes']),
            ('render', 'render_blender.py', ['appearance.offline_render_execution']),
            ('glb', 'export_glb.py', ['geometry.glb_serialized', 'geometry.glb_reimport'])]:
            path = study/f'evidence/blender-{action}-{kind}.json'; r = read_json(path)
            artifact = b.artifact(path, role='receipt'); tool_artifact = b.artifact(study/'tools'/filename, r['tool_sha256'], 'producer')
            sources = sorted(set(producer + [tool_artifact]))
            arts = [artifact, b.artifact(study/'web/bank'/next(x for x in bank['cases'] if x['id']==case)['packet'], r.get('packet_sha256', r.get('source_packet_sha256')), 'scientific-packet')]
            if action == 'transfer':
                arts += [b.artifact(study/f'exports/blender/{kind}-roundtrip.json', role='roundtrip'), b.artifact(study/f'exports/blender/scientific-{kind}.blend', role='native-scientific-scene')]
            elif action == 'render':
                arts += [b.artifact(study/f'docs/assets/{kind}.png', r['image_sha256'], 'render', r['image_bytes']),
                         b.artifact(study/f'exports/blender/{kind}.blend', role='authored-studio-scene')]
            else:
                arts += [b.artifact(study/f'exports/blender/{kind}.glb', r['glb_sha256'], 'export', r['glb_bytes']),
                         b.artifact(study/'exports/blender'/r['source_blend_name'], r['source_blend_sha256'], 'native-scientific-scene')]
            tool_id = b.add('ToolBuild', action+'-'+kind, 'Recorded '+action+' tool: '+kind,
                            r['scope'] if 'scope' in r else r['check']['scope'],
                            version=r['schema'], source_artifacts=[tool_artifact], based_on=[blender_tool])
            run_id = b.add('ValidationRun', action+'-'+kind, 'Recorded Blender '+action+': '+kind,
                           r['scope'] if 'scope' in r else r['check']['scope'], execution='recorded', outcome=r['status'],
                           tool=tool_id, ended_at=r['created_utc'], artifacts=arts)
            e = b.add('EvidenceRecord', action+'-'+kind, 'Blender '+action+' receipt: '+kind,
                      r['scope'] if 'scope' in r else r['check']['scope'], evidence_state='executed', outcome=r['status'],
                      observed_at=r['created_utc'], run=run_id, subjects=[datasets[case]],
                      scope_terms=['published-case:'+case, 'owned-geometry-subset', 'saved-frame:'+str(r.get('frame_index', next(x for x in bank['cases'] if x['id']==case)['export_frame']))],
                      facets=facets, artifacts=arts, source_bindings=sources, based_on=[artifact],
                      bridge=[bridges[10], bridges[12], bridges[26] if action=='glb' else bridges[27]],
                      measurements=r, historical_solver_measurements_recomputed=False)
            for number in (10, 12, 26 if action=='glb' else 27): links[number].append(e)
            if action == 'transfer': transfer_evidence = e; transfer_frame = r['frame_index']
            if action == 'glb':
                b.add('Loss', 'glb-color-'+kind, 'Measured Blender glTF color reimport quantization',
                      r['color_retention'], subjects=[datasets[case]], based_on=[artifact],
                      loss_kind='quantization', maximum_observed=r['max_reimport_linear_vertex_color_difference'],
                      bound=r['reimport_color_quantization_bound'], units='linear RGB component')
        b.add('Claim', 'blender-geometry-'+kind, 'Owned Blender geometry round trip: '+kind,
              'Selected saved frame only. No arbitrary modifier, appearance parity or post-edit solver certification.',
              subjects=[datasets[case]], facets=['geometry.coordinates', 'geometry.topology', 'geometry.color_attributes'],
              scope_terms=['published-case:'+case, 'owned-geometry-subset', 'saved-frame:'+str(transfer_frame)],
              required_state='executed', evidence=[transfer_evidence])
        for suffix, facet, title in [('browser', 'appearance.native_browser_visibility', 'Native browser pixels are not established'),
                                      ('post-edit', 'science.after_geometry_edit', 'Post-edit science is not established')]:
            b.add('Claim', suffix+'-'+kind, title+': '+kind,
                  'Deliberately unsupported control: a passing geometry transfer cannot supply this facet.',
                  subjects=[datasets[case]], facets=[facet], required_state='executed', evidence=[transfer_evidence])
            b.nodes['urn:x3d-scivis:claim:'+suffix+'-'+kind]['scope_terms'] = ['published-case:'+case, 'owned-geometry-subset']
    # The source release explicitly says browser execution is absent.
    browser_run = b.add('ValidationRun', 'native-browser', 'Native X_ITE browser rendering',
                        release['browser']['reason'], execution='not_run', outcome='unknown',
                        artifacts=[release_artifact])
    b.add('EvidenceRecord', 'native-browser', 'Recorded absence of native browser execution',
          release['browser']['reason'], evidence_state='inspected', outcome='unknown',
          run=browser_run, subjects=list(datasets.values()), facets=['appearance.native_browser_visibility'],
          scope_terms=['native-browser', 'not-executed'],
          artifacts=[release_artifact], source_bindings=[], based_on=[release_artifact])
    if historical_notes:
        notes = Path(historical_notes).resolve()
        if notes.is_file():
            path, notes = notes, notes.parent
        else:
            path = notes/'FLYWHEEL-SYNERGY-v1 (2).md'
            if not path.exists():
                path = notes/'FLYWHEEL-SYNERGY-v1.md'
        artifact = b.artifact(path, role='historical-source', root_label='review_inputs', root_path=notes)
        text = path.read_text()
        fragments = [m.group(0) for pattern in (r'.{0,50}3,058.{0,90}', r'.{0,50}585-scene.{0,90}', r'.{0,50}568 imports.{0,90}')
                     for m in re.finditer(pattern, text)][:8]
        historical = b.add('Dataset', 'historical-spine-description', 'Historical scene-spine description',
                           'A described corpus whose original manifest and every scene have not been re-censused by this adapter.',
                           based_on=[artifact], synthetic=False)
        e = b.add('EvidenceRecord', 'historical-corpus-counts', 'Reported historical corpus counts',
                  'Textual source assertions, with internally disputed denominators. No present-day corpus measurement.',
                  evidence_state='reported', outcome='unknown', subjects=[historical], facets=['corpus.inventory_count'],
                  scope_terms=['historical-spine-description'], artifacts=[artifact], source_bindings=[],
                  source_assertions=fragments, source_grade_policy='Original grades remain source assertions; no promotion.', based_on=[artifact])
        b.add('Claim', 'historical-corpus-counts-current', 'Current corpus counts are established',
              'Deliberately unsupported: historical prose cannot establish a fresh current corpus census.',
              subjects=[historical], facets=['corpus.inventory_count'], scope_terms=['historical-spine-description'],
              required_state='executed', evidence=[e])
    if private_workspace:
        workspace = Path(private_workspace).resolve()
        def private_artifact(relative, expected=None, role='receipt'):
            return b.artifact(workspace/relative, expected, role, root_label='private_workspace', root_path=workspace)
        for key, receipt_path, source_path, source_field, output_path, facets, numbers in [
            ('local-origin', 'private/probes/precision-control.json', 'private/probes/blender_precision_probe.py',
             'source_sha256', 'private/probes/precision-control.blend',
             ['geometry.binary32_local_origin_comparison', 'artifact.blend_save_reopen'], [10,12,21]),
            ('native53', 'private/native53/results/native53-result.json', 'private/native53/probe_native53.py',
             'probe_source_sha256', 'private/native53/results/native53-controls.blend',
             ['data.native_splat_attribute_layout', 'geometry.splat_apply_transform_observed'], [1,10,13])]:
            r = read_json(workspace/receipt_path)
            need(r['status'] == 'pass', 'PRIVATE_PROBE_NOT_PASSING: '+key)
            receipt_artifact = private_artifact(receipt_path)
            source_artifact = private_artifact(source_path, r[source_field], 'producer')
            artifacts = [receipt_artifact, private_artifact(output_path, r['blend_sha256'], 'native-scientific-scene')]
            if key == 'native53':
                artifacts += [private_artifact('private/native53/results/native-four-sh3.ply', r['fixture_sha256'], 'fixture'),
                              private_artifact('private/native53/results/native-fork-roundtrip.x3d', r['fork_roundtrip']['x3d_sha256'], 'export')]
            subject = b.add('Dataset', key+'-probe', 'Bounded '+key+' probe data', r['scope'],
                            based_on=artifacts, synthetic=True)
            tool = b.add('ToolBuild', key+'-probe', 'Recorded '+key+' probe tool', r['scope'],
                         version=r['schema'], source_artifacts=[source_artifact],
                         blender_version=r['blender_version'], blender_build_hash=r['blender_build_hash'])
            run_id = b.add('ValidationRun', key+'-probe', 'Recorded '+key+' execution', r['scope'],
                           execution='recorded', outcome='pass', ended_at=r['created_utc'], tool=tool, artifacts=artifacts)
            e = b.add('EvidenceRecord', key+'-probe', 'Recorded '+key+' measurements', r['scope'],
                      evidence_state='executed', outcome='pass', observed_at=r['created_utc'], run=run_id,
                      subjects=[subject], scope_terms=[key+'-bounded-synthetic-probe'], facets=facets,
                      artifacts=artifacts, source_bindings=[source_artifact], measurements=r,
                      based_on=[receipt_artifact], bridge=[bridges[n] for n in numbers])
            for n in numbers: links.setdefault(n, []).append(e)
            b.add('Claim', key+'-probe', 'The recorded bounded '+key+' probe passed', r['scope'],
                  subjects=[subject], scope_terms=[key+'-bounded-synthetic-probe'], facets=facets,
                  required_state='executed', evidence=[e])
        for kind, case in [('flow','flow-balanced'),('tensor','tensor-correlated'),('modes','modes-degenerate')]:
            relative = f'private/figure-links/{kind}-figure-link.json'; r = read_json(workspace/relative)
            need(r['status']=='pass' and r['render_reexecuted'] is False, 'FIGURE_LINK_SCOPE_DIFFERS')
            receipt_artifact = private_artifact(relative)
            protocol_artifact = private_artifact('adapters/vendor/x3dprov.py', r['protocol_sha256'], 'producer')
            adapter_artifact = private_artifact('adapters/x3dprov_link.py', r['adapter_sha256'], 'producer')
            arts = [receipt_artifact, private_artifact(f'private/figure-links/{kind}-linked.x3d', r['linked_scene_byte_sha256'], 'linked-scene')]
            for asset in r['assets']:
                need(asset['hash_method']==HASH_METHOD and asset['locator'].startswith('study://'), 'FIGURE_ASSET_METHOD_OR_LOCATOR_DIFFERS')
                arts.append(b.artifact(study/asset['locator'][8:], asset['sha256'], asset['role'], asset['bytes']))
            scope = 'Retrospective binding of an existing render using the existing x3dprov protocol. No render was reexecuted and no science was recertified.'
            tool = b.add('ToolBuild', 'figure-link-'+kind, 'Existing x3dprov figure-link adapter', scope,
                         version=r['schema'], source_artifacts=[protocol_artifact,adapter_artifact],
                         protocol_source=r['protocol_source'])
            run_id = b.add('ValidationRun', 'figure-link-'+kind, 'Recorded retrospective figure binding: '+kind,
                           scope, execution='recorded', outcome='pass', ended_at=r['created_utc'], tool=tool, artifacts=arts)
            e = b.add('EvidenceRecord', 'figure-link-'+kind, 'Recorded existing-render link: '+kind,
                      scope, evidence_state='executed', outcome='pass', observed_at=r['created_utc'], run=run_id,
                      subjects=[datasets[case]], scope_terms=['published-case:'+case,'retrospective-existing-render-link'],
                      facets=['provenance.existing_figure_link'], artifacts=arts,
                      source_bindings=[protocol_artifact,adapter_artifact], based_on=[receipt_artifact], bridge=[bridges[12]],
                      original_content_hash={'hash_method':r['content_hash_method'],'value':r['scene_content_sha256'],
                                             'branch':r['hash_branch'],'relationship_to_file_sha256':'different-identity-not-interchangeable'},
                      render_reexecuted=False)
            links[12].append(e)
    graph = {'schema': SCHEMA, '@context': CONTEXT, '@graph': list(b.nodes.values()),
             'created_at': datetime.now(timezone.utc).isoformat(), 'confidentiality': 'private',
             'adapter_identity': {'path':'integration/inventory.py', 'hash_method':HASH_METHOD,
                                  'sha256':digest(Path(__file__).read_bytes())},
             'source_root_labels': sorted({n['locator']['root'] for n in b.nodes.values() if entity_type(n)=='Artifact'}),
             'adapter_scope': 'Private inventory overlay for original receipts. No original grades, x3dprov hashes or files are rewritten.',
             'limitations': ['Hash identity is not publisher authentication.', 'Recorded execution is not fresh execution by this adapter.',
                            'No universal scalar grade; facet support is local to named subjects and scope.',
                            'No private historical kit is claimed reproduced merely because the corresponding Research Loom method exists.']}
    validate(graph)
    bridge_map = {'schema': 'scivis.bridge-alignment/1', 'scope': 'Method overlap, not historical bridge confirmation or completion.',
                  'bridges': [{'bridge': f'B{i:02d}', 'inventory_node': bridges[i], 'related_current_evidence': links.get(i, []),
                               'relationship': 'method-overlap' if links.get(i) else 'awaits-scoped-evidence',
                               'historical_grade_changed': False} for i in range(1,28)]}
    return graph, bridge_map


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    imp = sub.add_parser('import-research-loom'); imp.add_argument('--study', required=True, type=Path)
    imp.add_argument('--output', required=True, type=Path); imp.add_argument('--bridge-map', type=Path)
    imp.add_argument('--historical-notes', type=Path)
    imp.add_argument('--private-workspace', type=Path)
    check = sub.add_parser('verify'); check.add_argument('inventory', type=Path); check.add_argument('--root', action='append', default=[])
    check.add_argument('--output', type=Path)
    query = sub.add_parser('support'); query.add_argument('inventory', type=Path); query.add_argument('claim')
    query.add_argument('--inspection', required=True, type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'import-research-loom':
            graph, bridge_map = import_research_loom(args.study, args.historical_notes, args.private_workspace); write_json(args.output, graph)
            if args.bridge_map: write_json(args.bridge_map, bridge_map)
            print(json.dumps({'status':'pass', 'entities':dict(Counter(entity_type(n) for n in graph['@graph'])), 'output':str(args.output)})); return 0
        graph = read_json(args.inventory)
        if args.command == 'verify':
            roots = {}
            for item in args.root:
                key, sep, value = item.partition('='); need(sep and key not in roots, 'ROOT_EXPECTS_UNIQUE_LABEL_EQUALS_PATH'); roots[key] = value
            result = verify(graph, roots)
            if args.output: write_json(args.output, result)
            print(json.dumps({'status':result['status'],'artifact_count':result['artifact_count'],'fresh_execution':False})); return 0 if result['status']=='pass' else 1
        result = support(graph, args.claim, read_json(args.inspection)); print(json.dumps(result, indent=2)); return 0 if result['status']=='supported_within_declared_scope' else 2
    except (OSError, ValueError, KeyError) as error:
        print(json.dumps({'status':'fail', 'reason':str(error)}), file=sys.stderr); return 1


if __name__ == '__main__':
    raise SystemExit(main())
