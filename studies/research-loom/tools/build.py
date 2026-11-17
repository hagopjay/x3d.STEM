#!/usr/bin/env python3
"""Build all nine verified cases, portable hub exports and a browser case bank."""
from __future__ import annotations

import argparse
from datetime import datetime, timezone
import json
from pathlib import Path
import platform
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stemloom.core import canonical, need, publish, sha, source_hashes, validate_case


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=ROOT)
    args = parser.parse_args()
    from stemloom import flow, tensor, modes
    from stemloom.exchange import to_x3d, to_vtp, to_obj, to_ply, points_csv, dataset_to_vti
    import numpy as np
    import scipy
    before = source_hashes()
    candidates = []
    for module in (flow, tensor, modes):
        for preset in module.PRESETS:
            case = module.build_case(preset)
            case.update(schema='stemloom.case/1', preset=preset,
                        coordinates={'up': 'Y', 'handedness': 'right'},
                        source_sha256=before,
                        runtime={'python': platform.python_version(), 'numpy': np.__version__,
                                 'scipy': scipy.__version__})
            raw = validate_case(case)
            candidates.append((case, raw))
            print('CHECK', case['id'], len(case['frames']), 'frames', len(raw), 'bytes', flush=True)
    need(source_hashes() == before, 'SOURCE_DRIFT')
    bank = {'schema': 'stemloom.bank/1', 'source_sha256': before, 'cases': [],
            'eligibility': 'All declared local scientific and geometry gates pass.',
            'scope': 'Synthetic/analytic research demonstrations, not measured experimental datasets.'}
    output = args.output.resolve()
    for case, raw in candidates:
        digest = sha(raw)
        filename = case['id'] + '.' + digest[:16] + '.json'
        packet_path = output / 'web' / 'bank' / filename
        packet_info = publish(packet_path, raw)
        # Read the scientific candidate back, then export the exact reloaded frame.
        reloaded = json.loads(packet_path.read_bytes())
        frame = len(case['frames']) // 2
        directory = output / 'exports' / case['id'] / digest[:16]
        exports = {}
        representations = {
            'scene.x3d': to_x3d(reloaded, frame, version='4.0'),
            'portable-3.3.x3d': to_x3d(reloaded, frame, version='3.3'),
            'geometry.vtp': to_vtp(reloaded, frame),
            'geometry.ply': to_ply(reloaded, frame),
            'geometry.obj': to_obj(reloaded, frame),
            'coordinates.csv': points_csv(reloaded, frame),
        }
        for name, text in representations.items():
            info = publish(directory / name, text.encode('utf-8'))
            exports[name] = {'file': str((directory / name).relative_to(output)), **info}
        publish(directory / 'packet.json', raw)
        frame_exports = []
        for i in range(len(case['frames'])):
            path = directory / ('frame-' + str(i).zfill(2) + '.x3d')
            info = publish(path, to_x3d(reloaded, i, version='4.0').encode('utf-8'))
            frame_exports.append({'file': str(path.relative_to(output)), **info})
        if 'velocity_grid' in case.get('datasets', {}):
            path = directory / 'velocity-grid.vti'
            info = publish(path, dataset_to_vti(case['datasets']['velocity_grid']).encode('utf-8'))
            exports[path.name] = {'file': str(path.relative_to(output)), **info}
        bank['cases'].append({'id': case['id'], 'kind': case['kind'], 'title': case['title'],
                              'question': case['question'], 'description': case['description'],
                              'scope': case['scope'], 'preset': case['preset'],
                              'frames': len(case['frames']), 'packet': filename, **packet_info,
                              'witnesses': len(case['witnesses']), 'eligible': True,
                              'export_frame': frame, 'exports': exports, 'frame_exports': frame_exports})
    need(source_hashes() == before, 'SOURCE_DRIFT')
    # Publication of the index is the only operation that makes this bank discoverable.
    # It occurs after every candidate, re-read packet and export succeeds.
    publish(output / 'web' / 'bank' / 'index.json', canonical(bank))
    report = {'schema': 'stemloom.build/1', 'status': 'pass',
              'finished_utc': datetime.now(timezone.utc).isoformat(),
              'source_sha256': before, 'cases': bank['cases'],
              'scope': 'Local Research Loom gates, not a claim of an unavailable external Loom profile certification.'}
    publish(output / 'evidence' / 'build.json', canonical(report))
    print(json.dumps({'status': 'pass', 'cases': len(bank['cases']),
                      'frames': sum(c['frames'] for c in bank['cases'])}), flush=True)


if __name__ == '__main__':
    main()
