#!/usr/bin/env python3
"""Independent checks of published Research Loom bytes, geometry and hub readers.

This is a local scientific/transfer instrument, not native browser evidence or
certification by an external Loom profile. Missing optional VTK yields partial.
"""
from __future__ import annotations

import argparse
import copy
import csv
from datetime import datetime, timezone
import hashlib
import io
import json
import math
from pathlib import Path
import platform
import subprocess
import sys
import time
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import numpy as np
from stemloom.core import canonical, source_hashes, validate_case, verify_packet
from stemloom.exchange import from_x3d, to_x3d, validate_frame

GROUPS = ('meshes', 'lines', 'points')


def need(condition, message):
    if not condition:
        raise ArithmeticError(message)


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def geometry_difference(expected, actual, tolerance=2e-13):
    """Compare actual decoded coordinates/topology/appearance, ignoring provenance."""
    worst = 0.
    for group in GROUPS:
        left = {row['id']: row for row in expected.get(group, [])}
        right = {row['id']: row for row in actual.get(group, [])}
        need(left.keys() == right.keys(), 'Geometry identities differ: ' + group)
        for key, a in left.items():
            b = right[key]
            for name in ('positions', 'color'):
                x, y = np.asarray(a[name], dtype=float), np.asarray(b[name], dtype=float)
                need(x.shape == y.shape, 'Geometry array shape differs: ' + key + '/' + name)
                worst = max(worst, float(np.max(np.abs(x-y))))
            if 'colors' in a or 'colors' in b:
                need(('colors' in a) == ('colors' in b), 'Vertex-color presence differs')
                x, y = np.asarray(a['colors']), np.asarray(b['colors'])
                need(x.shape == y.shape, 'Color shape differs')
                worst = max(worst, float(np.max(np.abs(x-y))))
            worst = max(worst, abs(a.get('opacity', 1)-b.get('opacity', 1)))
            if group == 'meshes':
                need(a['faces'] == b['faces'], 'Actual face topology differs: ' + key)
            else:
                worst = max(worst, abs(a.get('radius', .012 if group == 'lines' else .035)-b['radius']))
    need(worst <= tolerance, f'Actual geometry difference {worst} exceeds {tolerance}')
    return worst


def fixture():
    frame = {'time': 0., 'meshes': [{'id': 'asymmetric-tetra',
        'positions': [[0.,0.,0.], [2.,0.,0.], [.25,3.,0.], [.4,.7,4.]],
        'faces': [[0,2,1], [0,1,3], [1,2,3], [2,0,3]],
        'color': [.2,.5,.8], 'opacity': .83,
        'colors': [[.1,.2,.3], [.4,.5,.6], [.7,.8,.9], [.2,.4,.6]],
        'point_data': {'temperature': {'values': [1.,2.,3.,4.], 'components': 1, 'units': 'K'}}}],
        'lines': [{'id': 'centerline', 'positions': [[1.,2.,3.], [2.,4.,6.]],
                   'color': [.8,.3,.2], 'radius': .023, 'opacity': .7}],
        'points': [{'id': 'observation', 'positions': [[-.1,.2,.8]], 'color': [.3,.8,.2],
                    'radius': .041, 'opacity': 1.}],
        'metrics': [{'id': 'control', 'label': 'Control', 'value': 1, 'unit': '', 'note': ''}]}
    return {'id': 'independent-fixture', 'kind': 'tensor', 'title': 'Asymmetric transfer fixture',
            'question': 'Does actual geometry survive?', 'description': 'A non-coplanar reference.',
            'scope': 'Geometry fixture only.', 'axes': 'Right-handed Y-up.', 'units': {'position': 'm'},
            'parameters': {}, 'frames': [frame], 'measurements': {},
            'sources': [{'title': 'Local generated fixture', 'url': 'https://www.web3d.org/', 'note': 'Control'}],
            'witnesses': [{'id': 'reference', 'pass': True, 'observed': 0., 'limit': 1e-12,
                           'rule': 'at most', 'note': 'Control'}]}


def negative_controls():
    sample = fixture()
    raw = canonical(sample)
    caught = []
    try:
        verify_packet(raw+b' ', sha(raw))
    except Exception:
        caught.append('changed-packet-byte')
    else:
        raise ArithmeticError('Digest control accepted changed bytes')
    red = copy.deepcopy(sample)
    red['witnesses'][0].update(observed=1., limit=0., **{'pass': False})
    try:
        validate_case(red)
    except Exception:
        caught.append('red-scientific-witness')
    else:
        raise ArithmeticError('Red witness was accepted')
    red['witnesses'][0]['pass'] = True
    try:
        validate_case(red)
    except Exception:
        caught.append('inconsistent-witness-boolean')
    else:
        raise ArithmeticError('Inconsistent witness was accepted')
    xml = ET.fromstring(to_x3d(sample))
    coords = xml.find('.//Coordinate')
    values = coords.get('point').split()
    values[0] = str(float(values[0])+.125)
    coords.set('point', ' '.join(values))
    changed = from_x3d(ET.tostring(xml, encoding='unicode'))
    need(not changed['metadata']['geometry_matches_declared_hash'], 'Tampered-node digest still matches')
    try:
        geometry_difference(sample['frames'][0], changed)
    except ArithmeticError:
        caught.append('changed-actual-coordinate-with-unchanged-metadata')
    else:
        raise ArithmeticError('Actual coordinate control accepted a displaced node')
    # This exercises the real core gate in an optimized child, not a copied predicate.
    code = "import sys,json;from stemloom.core import validate_case; c=json.load(sys.stdin);validate_case(c)"
    process = subprocess.run([sys.executable, '-O', '-c', code], input=json.dumps(red),
                             text=True, capture_output=True, cwd=ROOT, timeout=20)
    need(process.returncode != 0 and 'WITNESS_INCONSISTENT' in process.stderr,
         'Optimized Python failed to reject the inconsistent scientific witness')
    # Use an ordinary red false predicate separately from the inconsistent control.
    red['witnesses'][0]['pass'] = False
    process = subprocess.run([sys.executable, '-O', '-c', code], input=json.dumps(red),
                             text=True, capture_output=True, cwd=ROOT, timeout=20)
    need(process.returncode != 0 and 'SCIENCE_REJECTED' in process.stderr,
         'Optimized Python accepted a red scientific witness')
    caught.append('optimized-python-red-gate')
    xyz = np.asarray(sample['frames'][0]['meshes'][0]['positions'])
    rotated = xyz @ np.array([[1.,0.,0.], [0.,0.,1.], [0.,-1.,0.]])
    restored = rotated @ np.array([[1.,0.,0.], [0.,0.,-1.], [0.,1.,0.]])
    need(np.array_equal(xyz, restored), 'Coordinate-pair inverse mismatch')
    def volume(points):
        return float(np.linalg.det(np.asarray(points[1:])-points[0]))/6
    need(volume(xyz)*volume(rotated) > 0 and abs(volume(xyz)-volume(rotated)) < 1e-12,
         'Y-up to Z-up reference reverses orientation or scale')
    return {'caught': caught, 'count': len(caught), 'asymmetric_signed_volume': volume(xyz),
            'rotated_signed_volume': volume(rotated), 'note': 'Coordinate-pair reference is independent of Blender execution.'}


def flattened(frame):
    records = [row for group in GROUPS for row in frame[group]]
    xyz = np.asarray([p for row in records for p in row['positions']], dtype=float)
    rgba = np.asarray([[*c, row.get('opacity', 1)] for row in records
                       for c in row.get('colors', [row['color']]*len(row['positions']))])
    return records, xyz, rgba


def vtk_check(path, frame, vtk, case=None):
    reader = vtk.vtkXMLPolyDataReader()
    reader.SetFileName(str(path))
    errors = []
    reader.AddObserver('ErrorEvent', lambda *_: errors.append('VTK reader error'))
    reader.Update()
    need(not errors and reader.GetErrorCode() == 0, 'Actual VTK reader rejected PolyData')
    data = reader.GetOutput()
    field = data.GetFieldData()
    time_array = field.GetArray('TimeValue')
    need(time_array is not None and abs(time_array.GetTuple1(0)-frame['time']) < 2e-13,
         'VTK actual field-data time is missing or changed')
    metadata_array = field.GetArray('stemloom_metadata_utf8')
    need(metadata_array is not None, 'VTK source metadata field is missing')
    metadata = json.loads(bytes(int(metadata_array.GetTuple1(i))
                                for i in range(metadata_array.GetNumberOfTuples())).decode('utf-8'))
    if case is not None:
        need(metadata['case_id'] == case['id'] and metadata['units'] == case['units'],
             'VTK actual field-data case identity/units differ')
    records, expected, rgba = flattened(frame)
    need(data.GetNumberOfPoints() == len(expected), 'VTK point count differs')
    actual = np.asarray([data.GetPoint(i) for i in range(data.GetNumberOfPoints())])
    error = float(np.max(np.abs(expected-actual)))
    need(error < 2e-13, 'VTK actual point coordinates differ')
    need(data.GetNumberOfVerts() == sum(len(r['positions']) for r in frame['points']), 'VTK vertex-cell count differs')
    need(data.GetNumberOfLines() == len(frame['lines']), 'VTK line-cell count differs')
    need(data.GetNumberOfPolys() == sum(len(r['faces']) for r in frame['meshes']), 'VTK polygon count differs')
    # Read every actual cell's connectivity in the VTK-defined verts/lines/polys order.
    offset, vertices, lines, polys = 0, [], [], []
    for group in GROUPS:
        for row in frame[group]:
            if group == 'meshes':
                polys.extend([[offset+i for i in face] for face in row['faces']])
            elif group == 'lines':
                lines.append(list(range(offset, offset+len(row['positions']))))
            else:
                vertices.extend([[offset+i] for i in range(len(row['positions']))])
            offset += len(row['positions'])
    for index, cell in enumerate(vertices+lines+polys):
        ids = data.GetCell(index).GetPointIds()
        need([ids.GetId(i) for i in range(ids.GetNumberOfIds())] == cell, 'VTK cell connectivity differs')
    colors = data.GetPointData().GetArray('ColorRGBA')
    need(colors is not None and colors.GetNumberOfComponents() == 4, 'VTK RGBA missing')
    quantized = np.asarray([colors.GetTuple(i) for i in range(len(expected))])
    color_error = float(np.max(np.abs(quantized/255-rgba)))
    need(color_error <= .5/255+1e-14, 'VTK RGBA quantization exceeds half an 8-bit step')
    names = sorted({name for row in records for name in row.get('point_data', {})})
    scientific_array = field.GetArray('stemloom_scientific_arrays_utf8')
    scientific_metadata = {}
    if names:
        need(scientific_array is not None, 'VTK scientific-array units metadata is missing')
        scientific_metadata = json.loads(bytes(int(scientific_array.GetTuple1(i))
                                               for i in range(scientific_array.GetNumberOfTuples())).decode('utf-8'))
    for name in names:
        array = data.GetPointData().GetArray(name)
        mask = data.GetPointData().GetArray(name+'__valid')
        need(array is not None and mask is not None, 'VTK scientific array or availability mask missing')
        cursor = 0
        for row in records:
            descriptor = row.get('point_data', {}).get(name)
            if descriptor is not None:
                need(scientific_metadata[name]['units'] == descriptor['units'] and
                     scientific_metadata[name]['components'] == descriptor['components'],
                     'VTK scientific-array units/components metadata differ')
            for local in range(len(row['positions'])):
                need(int(mask.GetTuple1(cursor)) == int(descriptor is not None), 'VTK availability mask differs')
                if descriptor is not None:
                    expected_value = np.atleast_1d(descriptor['values'][local])
                    actual_value = np.asarray(array.GetTuple(cursor))
                    need(expected_value.shape == actual_value.shape and
                         np.max(np.abs(expected_value-actual_value)) < 2e-13,
                         'VTK scientific values differ')
                else:
                    need(max(abs(x) for x in array.GetTuple(cursor)) == 0., 'Missing VTK value is not declared zero fill')
                cursor += 1
    return {'points': len(expected), 'max_position_difference': error,
            'max_rgba_quantization_difference': color_error, 'scientific_arrays': names}


def text_hub_checks(directory, frame):
    records, expected, rgba = flattened(frame)
    csv_rows = list(csv.DictReader(io.StringIO((directory/'coordinates.csv').read_text())))
    need(len(csv_rows) == len(expected), 'CSV vertex count differs')
    csv_xyz = np.asarray([[float(r[k]) for k in ('x','y','z')] for r in csv_rows])
    need(np.max(np.abs(csv_xyz-expected)) < 2e-13, 'CSV actual coordinates differ')
    obj = (directory/'geometry.obj').read_text().splitlines()
    obj_xyz = np.asarray([[float(x) for x in line.split()[1:]] for line in obj if line.startswith('v ')])
    need(obj_xyz.shape == expected.shape and np.max(np.abs(obj_xyz-expected)) < 2e-13, 'OBJ actual coordinates differ')
    need(sum(line.startswith('f ') for line in obj) == sum(len(r['faces']) for r in frame['meshes']), 'OBJ face count differs')
    need(sum(line.startswith('l ') for line in obj) == len(frame['lines']), 'OBJ line count differs')
    ply = (directory/'geometry.ply').read_text().splitlines()
    header = ply[:ply.index('end_header')+1]
    n = int(next(s for s in header if s.startswith('element vertex ')).split()[-1])
    need(n == len(expected), 'PLY point count differs')
    vertices = np.asarray([[float(x) for x in line.split()] for line in ply[len(header):len(header)+n]])
    need(np.max(np.abs(vertices[:,:3]-expected)) < 2e-13, 'PLY actual coordinates differ')
    need(np.max(np.abs(vertices[:,3:]/255-rgba)) <= .5/255+1e-14, 'PLY RGBA quantization differs')
    faces = sum(len(r['faces']) for r in frame['meshes'])
    edges = sum(len(r['positions'])-1 for r in frame['lines'])
    need(int(next(s for s in header if s.startswith('element face ')).split()[-1]) == faces, 'PLY face count differs')
    need(int(next(s for s in header if s.startswith('element edge ')).split()[-1]) == edges, 'PLY edge count differs')
    return {'display_samples': n, 'ply_edges': edges, 'polygons': faces,
            'losses': 'OBJ loses appearance and scientific arrays; PLY has RGB8/opacity quantization and loses group identity/units/arrays; CSV is display samples, not source observations.'}


def science_check(case):
    """Recompute selected scientific quantities from stored data, not witness booleans."""
    kind, values = case['kind'], case['measurements']
    if kind == 'tensor':
        samples = np.asarray(values['observations'])
        mean = np.asarray([math.fsum(samples[:,i])/len(samples) for i in range(3)])
        covariance = np.empty((3,3))
        for i in range(3):
            for j in range(3):
                covariance[i,j] = math.fsum((row[i]-mean[i])*(row[j]-mean[j]) for row in samples)/(len(samples)-1)
        discrepancy = float(np.max(np.abs(covariance-values['sample_covariance'])))
        need(discrepancy < 2e-12, 'Stored covariance differs from independent centered sums')
        return {'reference': 'math.fsum centered cross-products, N−1 denominator', 'max_covariance_difference': discrepancy}
    if kind == 'flow':
        grid = case['datasets']['velocity_grid']
        xyz = np.asarray(grid['positions'])
        a,b,c = (case['parameters'][name] for name in ('A','B','C'))
        expected = np.asarray([[a*math.sin(z)+c*math.cos(y), b*math.sin(x)+a*math.cos(z),
                                c*math.sin(y)+b*math.cos(x)] for x,y,z in xyz])
        difference = float(np.max(np.abs(expected-grid['velocity'])))
        need(difference < 2e-14, 'ABC grid values differ from scalar trigonometric reference')
        if case.get('preset') == 'integrable':
            paths = np.asarray(values['trajectories_unwrapped'])
            times = np.asarray(values['times'])
            seeds = np.asarray(values['seeds'])
            exact = seeds[:,None,:]+times[None,:,None]*np.column_stack((np.sin(seeds[:,2]),np.cos(seeds[:,2]),np.zeros(len(seeds))))[:,None,:]
            need(paths.shape == exact.shape and np.max(np.abs(paths-exact)) < 3e-12, 'Exact integrable ABC trajectories differ')
        return {'reference': 'Scalar Python math trigonometric ABC field', 'max_velocity_grid_difference': difference}
    pars = case['parameters']
    frequencies = [math.sqrt((m['m']/pars['length_x'])**2+(m['n']/pars['length_z'])**2)*pars['wave_speed']/2 for m in pars['components']]
    difference = max(abs(a-b) for a,b in zip(frequencies, values['frequencies']))
    need(difference < 2e-14, 'Membrane frequencies differ from continuum reference')
    mesh = next(row for row in case['frames'][0]['meshes'] if row['id'] == 'membrane')
    xyz = np.asarray(mesh['positions'])
    displacement = np.asarray(mesh['point_data']['displacement']['values'])
    need(np.max(np.abs(xyz[:,1]-pars['vertical_display_scale']*displacement)) < 2e-14,
         'Emitted membrane height differs from unexaggerated scientific array')
    need(values['observed_order'] > 1.9, 'Stored membrane refinement fails second-order expectation')
    return {'reference': 'Continuum rectangular frequency and actual mesh/field pairing', 'max_frequency_difference': difference,
            'discretization_observed_order': values['observed_order']}


def verify_bank(directory=ROOT, vtk_enabled=True):
    directory = Path(directory).resolve()
    start_hashes = source_hashes()
    bank = json.loads((directory/'web/bank/index.json').read_text())
    need(bank.get('schema') == 'stemloom.bank/1', 'Unknown bank schema')
    need(len(bank['cases']) == 9 and {r['kind'] for r in bank['cases']} == {'flow','tensor','modes'}, 'Expected three studies with three cases each')
    need(all(sum(r['kind'] == kind for r in bank['cases']) == 3 for kind in ('flow','tensor','modes')), 'Incomplete preset collection')
    source_match = bank.get('source_sha256') == start_hashes
    vtk = None
    if vtk_enabled:
        try:
            import vtk
        except ImportError:
            vtk = None
    rows = []
    for row in bank['cases']:
        packet_path = directory/'web/bank'/row['packet']
        need(packet_path.resolve().is_relative_to((directory/'web/bank').resolve()), 'Packet path leaves bank')
        raw = packet_path.read_bytes()
        need(len(raw) == row['bytes'], 'Packet length differs: '+row['id'])
        case = verify_packet(raw, row['sha256'])
        source_match = source_match and case.get('source_sha256') == start_hashes
        frame = validate_frame(case['frames'][row['export_frame']])
        directory_export = None
        for name, info in row['exports'].items():
            path = directory/info['file']
            need(path.resolve().is_relative_to(directory), 'Export path leaves study')
            content = path.read_bytes()
            need(sha(content) == info['sha256'] and len(content) == info['bytes'], 'Export bytes differ: '+name)
            directory_export = path.parent
        position_error = 0.
        for filename in ('scene.x3d','portable-3.3.x3d'):
            imported = from_x3d((directory_export/filename).read_text())
            position_error = max(position_error, geometry_difference(frame, imported))
            need(imported['metadata']['geometry_matches_declared_hash'], 'Generated X3D geometry hash differs')
        record = {'id': row['id'], 'frames': len(case['frames']), 'witnesses': len(case['witnesses']),
                  'status': 'pass', 'x3d_max_geometry_difference': position_error,
                  'text_hubs': text_hub_checks(directory_export, frame), 'science': science_check(case)}
        if vtk is not None:
            record['vtk'] = vtk_check(directory_export/'geometry.vtp', frame, vtk, case)
        else:
            record['vtk'] = {'status': 'not_run', 'reason': 'VTK disabled or unavailable'}
        rows.append(record)
    return {'status': 'pass' if vtk is not None and source_match and source_hashes() == start_hashes else 'partial',
            'cases': rows, 'case_count': len(rows), 'frame_count': sum(r['frames'] for r in rows),
            'source_sha256': start_hashes, 'published_source_matches_current': source_match,
            'source_drift': 'none' if source_hashes() == start_hashes else 'changed',
            'vtk_version': vtk.vtkVersion.GetVTKVersion() if vtk is not None else None}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, default=ROOT)
    parser.add_argument('--output', type=Path, default=ROOT/'evidence/verification.json')
    parser.add_argument('--no-vtk', action='store_true')
    args = parser.parse_args()
    started = time.perf_counter()
    report = {'schema': 'stemloom.verification/1', 'started_utc': datetime.now(timezone.utc).isoformat(),
              'instrument_sha256': sha(Path(__file__).read_bytes()),
              'runtime': {'python': platform.python_version(), 'numpy': np.__version__},
              'scope': 'Published static geometry and local scientific/transfer checks; no native browser, GPU, Blender execution or external Loom-profile certification.'}
    try:
        report['controls'] = negative_controls()
        report.update(verify_bank(args.study, not args.no_vtk))
    except FileNotFoundError as error:
        report.update(status='partial', error='Required published bank is unavailable: '+str(error))
    except Exception as error:
        report.update(status='fail', error=type(error).__name__+': '+str(error))
    report['duration_seconds'] = time.perf_counter()-started
    report['finished_utc'] = datetime.now(timezone.utc).isoformat()
    report['report_sha256'] = sha(canonical(report))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(json.dumps(report, indent=2, ensure_ascii=False, allow_nan=False)+'\n')
    print(json.dumps({key:report.get(key) for key in ('status','case_count','frame_count','duration_seconds','error')}))
    return 0 if report['status'] == 'pass' else 2 if report['status'] == 'partial' else 1


if __name__ == '__main__':
    raise SystemExit(main())
