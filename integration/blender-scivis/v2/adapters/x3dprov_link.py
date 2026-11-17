#!/usr/bin/env python3
"""Link existing Research Loom figures through the existing x3dprov/0.1 protocol.

This records a retrospective linkage operation, not a newly executed render.
Original packets, scenes, receipts and figures remain unchanged.
"""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
from pathlib import Path
import re
import sys
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parent
PROV_SHA = 'dbc54523ac6bcd10a9005379b1d723f2b033a60ed093c125b942e90bd1dee40e'
PIN = 'c1634f5c4f29c4220a092510807a430ce4cbfd2e'
SELECTION = {'flow': ('flow-balanced', 4), 'tensor': ('tensor-correlated', 4),
             'modes': ('modes-degenerate', 1)}


def need(value, message):
    if not value:
        raise ValueError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode()


def load_prov():
    path = ROOT / 'vendor/x3dprov.py'
    need(sha(path.read_bytes()) == PROV_SHA, 'Pinned x3dprov source changed')
    spec = importlib.util.spec_from_file_location('owned_x3dprov_01', path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def well_formed(xml):
    need('<!DOCTYPE' not in xml.upper() and '<!ENTITY' not in xml.upper(),
         'DTD/entity input is outside this adapter')
    root = ET.fromstring(xml)
    need(root.tag == 'X3D', 'Expected an unnamespaced owned X3D document')
    return root


def append_verified(prov, before, step):
    """Refuse stale input BEFORE appending; a later step cannot repair history."""
    root = well_formed(before)
    # Legacy read_steps is deliberately regex based. Well-formed XML can carry
    # a record it does not recognize (for example, reordered meta attributes).
    # Never confuse that condition with an actually unstamped input.
    markers = [m for m in root.iter('meta') if m.get('name', '').startswith('x3dprov.')]
    if markers:
        heads = root.findall('head')
        need(len(heads) == 1 and all(m in list(heads[0]) for m in markers),
             'Unrecognized provenance marker location')
        parsed = []
        versions = []
        for m in markers:
            name = m.get('name')
            if name == 'x3dprov.version':
                versions.append(m.get('content'))
                continue
            match = re.fullmatch(r'x3dprov\.step\.(\d+)', name)
            need(match is not None and 'content' in m.attrib, 'Unrecognized provenance marker')
            parsed.append((int(match.group(1)), m.get('content')))
        need(versions == [prov.SCHEMA] and bool(parsed), 'Unrecognized provenance version/record')
        need(len({n for n, _ in parsed}) == len(parsed), 'Duplicate provenance step')
        need(sorted(parsed) == prov.read_steps(before), 'Unrecognized provenance serialization')
    verdict = prov.verify(before)
    need(verdict['status'] in ('no-record', 'verified'),
         'Refusing stale or broken provenance input: ' + verdict['status'])
    result = prov.add_step(before, step)
    need(prov.verify(result)['status'] == 'verified', 'Produced chain does not verify')
    return result


def bound_file(study, item):
    path = (study / item['file']).resolve()
    need(path.is_relative_to(study.resolve()), 'Artifact path escapes study')
    raw = path.read_bytes()
    need(sha(raw) == item['sha256'] and len(raw) == item['bytes'], 'Artifact identity differs')
    return raw


def link_one(study, output, kind, bank, prov):
    case_id, index = SELECTION[kind]
    row = next(r for r in bank['cases'] if r['id'] == case_id)
    raw = (study / 'web/bank' / row['packet']).read_bytes()
    need(sha(raw) == row['sha256'] and len(raw) == row['bytes'], 'Packet identity differs')
    packet = json.loads(raw)
    need(packet['id'] == case_id and row['eligible'] is True, 'Ineligible case')
    for name, expected in bank['source_sha256'].items():
        need(sha((study/name).read_bytes()) == expected, 'Producer source changed: ' + name)
    need(packet['source_sha256'] == bank['source_sha256'], 'Packet producer identity differs')
    sys.path.insert(0, str(study))
    from stemloom.core import validate_case
    validate_case(packet)  # Recheck eligibility predicates, without re-running the scientific models.
    frame = packet['frames'][index]
    scene_item = row['frame_exports'][index]
    xml_raw = bound_file(study, scene_item)
    xml = xml_raw.decode()
    frame_sha = sha(canonical(frame))
    receipt_path = study/'evidence'/f'blender-render-{kind}.json'
    receipt_raw = receipt_path.read_bytes()
    receipt = json.loads(receipt_raw)
    need(receipt['status'] == 'pass' and receipt['case_id'] == case_id and
         receipt['packet_sha256'] == row['sha256'] and receipt['frame_index'] == index and
         receipt['frame_sha256'] == frame_sha and receipt['time'] == frame['time'],
         'Render receipt is bound to a different case/frame')
    need(receipt['tool_sha256'] == sha((study/'tools/render_blender.py').read_bytes()) and
         receipt['adapter_sha256'] == sha((study/'stemloom/blender_io.py').read_bytes()),
         'Recorded render tool source changed')
    image_path = study/'docs/assets'/f'{kind}.png'
    image_raw = image_path.read_bytes()
    need(sha(image_raw) == receipt['image_sha256'] and len(image_raw) == receipt['image_bytes'],
         'Recorded image bytes changed')
    # Use the owned decoder, not scene metadata alone, to check retained geometry.
    sys.path.insert(0, str(study))
    from stemloom.exchange import from_x3d, validate_frame
    decoded = from_x3d(xml)
    m = decoded['metadata']
    export_frame_sha = sha(canonical(validate_frame(frame)))
    need(m['case_sha256'] == row['sha256'] and m['frame_sha256'] == export_frame_sha and
         m['geometry_matches_declared_hash'] is True, 'Actual X3D geometry identity differs')
    now = datetime.now(timezone.utc).isoformat()
    chain = append_verified(prov, xml, {
        'op': 'ingest_reference', 'timestamp': now, 'tool': 'research-loom-figure-link/1',
        'source_byte_sha256': sha(xml_raw), 'packet_byte_sha256': row['sha256'],
        'frame_sha256': frame_sha, 'export_normalized_frame_sha256': export_frame_sha,
        'case_id': case_id, 'frame_index': index,
        'scope': 'Existing saved scene accepted by byte, producer and decoded-geometry bindings.'})
    assets = [
        {'role': 'render-receipt', 'locator': f'study://evidence/{receipt_path.name}',
         'sha256': sha(receipt_raw), 'bytes': len(receipt_raw), 'hash_method': 'sha256-file-bytes'},
        {'role': 'existing-render', 'locator': f'study://docs/assets/{kind}.png',
         'sha256': sha(image_raw), 'bytes': len(image_raw), 'hash_method': 'sha256-file-bytes'}]
    chain = append_verified(prov, chain, {
        'op': 'link_existing_render', 'timestamp': now,
        'reported_render_timestamp': receipt['created_utc'], 'tool': 'research-loom-figure-link/1',
        'case_id': case_id, 'frame_index': index, 'renderer': receipt['blender_version'],
        'assets': assets,
        'scope': 'Retrospective binding check. Renderer was not re-executed by this operation.'})
    need(prov.content_hash(chain) == prov.content_hash(xml), 'Provenance changed scene content')
    out = output/f'{kind}-linked.x3d'
    out.write_text(chain)
    sidecar = {'schema': 'scivis.figure-link/1', 'status': 'pass', 'confidentiality': 'private',
        'created_utc': now, 'case_id': case_id, 'frame_index': index,
        'operation': 'link_existing_render', 'render_reexecuted': False,
        'packet_sha256': row['sha256'], 'frame_sha256': frame_sha,
        'export_normalized_frame_sha256': export_frame_sha,
        'frame_hash_methods': {'frame_sha256': 'sha256-canonical-original-packet-frame',
                               'export_normalized_frame_sha256': 'sha256-canonical-exchange.validate_frame'},
        'input_scene_byte_sha256': sha(xml_raw), 'linked_scene_byte_sha256': sha(out.read_bytes()),
        'scene_content_sha256': prov.content_hash(chain),
        'content_hash_method': 'x3dprov/0.1:strip-comments-provenance-whitespace-only-then-c14n',
        'hash_branch': 'well-formed-xml-c14n', 'protocol_sha256': PROV_SHA,
        'protocol_source': {'repository': 'hagopjay/x3d.ml', 'base_commit': PIN, 'path': 'src/x3dprov.py',
                            'local_patch': 'literal replacement callback in _inject_meta; regression-tested'},
        'adapter_sha256': sha(Path(__file__).read_bytes()), 'assets': assets,
        'chain_verdict': prov.verify(chain),
        'meaning': 'Hash continuity and current referenced bytes; no signature, publisher authentication or new science certification.'}
    (output/f'{kind}-figure-link.json').write_text(json.dumps(sidecar, indent=2)+'\n')
    return {k: sidecar[k] for k in ('case_id', 'frame_index', 'status', 'render_reexecuted')}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    study = args.study.resolve()
    args.output.mkdir(parents=True, exist_ok=True)
    bank = json.loads((study/'web/bank/index.json').read_text())
    need(bank['schema'] == 'stemloom.bank/1', 'Unsupported bank schema')
    prov = load_prov()
    results = [link_one(study, args.output, k, bank, prov) for k in SELECTION]
    print(json.dumps({'status': 'pass', 'results': results}))


if __name__ == '__main__':
    main()
