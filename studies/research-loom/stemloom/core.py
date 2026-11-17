"""Local Research Loom gates; immutable packets become visible only through a green bank."""
from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
import sys

STUDY = Path(__file__).resolve().parents[1]
REPO = STUDY.parents[1]
sys.path.insert(0, str(REPO / 'lib'))
from stemkit.core import Rejected, atomic_bytes, need, sha


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def source_hashes():
    paths = list((STUDY / 'stemloom').glob('*.py'))
    paths += [STUDY / 'tools' / 'build.py']
    result={str(p.relative_to(STUDY)): sha(p.read_bytes()) for p in sorted(paths)}
    result['../../lib/stemkit/core.py']=sha((REPO/'lib/stemkit/core.py').read_bytes())
    return result


def validate_case(case):
    from .exchange import validate_frame
    need(isinstance(case, dict), 'CASE_OBJECT')
    for key in ('id', 'kind', 'title', 'question', 'description', 'scope', 'axes'):
        need(isinstance(case.get(key), str) and bool(case[key]), 'CASE_TEXT', key)
    need(case['kind'] in ('flow', 'tensor', 'modes'), 'CASE_KIND')
    need(all(c in 'abcdefghijklmnopqrstuvwxyz0123456789-_' for c in case['id']), 'CASE_ID')
    need(isinstance(case.get('units'), dict) and case['units'], 'CASE_UNITS')
    need(isinstance(case.get('frames'), list) and 1 <= len(case['frames']) <= 12, 'CASE_FRAMES')
    previous = -float('inf')
    for frame in case['frames']:
        t = frame.get('time')
        need(not isinstance(t, bool) and isinstance(t, (float, int)) and math.isfinite(t), 'FRAME_TIME')
        need(t >= previous, 'FRAME_ORDER')
        previous = t
        validate_frame(frame)
        geometry = frame.get('meshes', []) + frame.get('lines', []) + frame.get('points', [])
        need(len(geometry) <= 250, 'FRAME_RECORD_BUDGET')
        need(sum(len(g['positions']) for g in geometry) <= 30_000, 'FRAME_POINT_BUDGET')
        need(sum(len(g.get('faces', [])) for g in geometry) <= 10_000, 'FRAME_FACE_BUDGET')
        need(bool(frame.get('metrics')), 'FRAME_METRICS')
    need(isinstance(case.get('witnesses'), list) and bool(case['witnesses']), 'WITNESSES_MISSING')
    for w in case['witnesses']:
        need(isinstance(w.get('pass'), bool), 'WITNESS_BOOL', w.get('id', '?'))
        observed, limit = w.get('observed'), w.get('limit')
        need(all(isinstance(v, (int, float)) and not isinstance(v, bool) and math.isfinite(v)
                 for v in (observed, limit)), 'WITNESS_FINITE', w.get('id', '?'))
        need(w.get('rule') in ('at most', 'at least'), 'WITNESS_RULE')
        expected = observed <= limit if w['rule'] == 'at most' else observed >= limit
        need(w['pass'] == expected, 'WITNESS_INCONSISTENT', w.get('id', '?'))
        need(w['pass'], 'SCIENCE_REJECTED', w.get('id', '?'))
    need(bool(case.get('sources')), 'SOURCES_MISSING')
    for source in case['sources']:
        need(source.get('url', '').startswith('https://'), 'SOURCE_URL')
    # This rejects NumPy arrays, NaN and unsupported objects before publication.
    raw = canonical(case)
    need(len(raw) < 64 * 1024 * 1024, 'CASE_BYTES_BUDGET')
    return raw


def publish(path, raw):
    atomic_bytes(Path(path), raw)
    back = Path(path).read_bytes()
    need(back == raw, 'PUBLICATION_REOPEN')
    return {'sha256': sha(back), 'bytes': len(back)}


def verify_packet(raw, expected_digest):
    need(sha(raw) == expected_digest, 'PACKET_DIGEST')
    case = json.loads(raw)
    validate_case(case)
    return case
