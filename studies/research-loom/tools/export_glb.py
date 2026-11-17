#!/usr/bin/env python3
"""Export/re-import scientific Blender geometry through the bundled glTF2 hub.

Run inside Blender with --input-blend, --output and --receipt. The pure
--self-check option validates GLB framing controls without importing bpy.
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import struct
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stemloom.blender_io import SCIENCE_COLLECTION, save_json, srgb_to_linear


def inspect_glb(raw):
    if len(raw) < 20:
        raise ValueError('GLB is too short')
    magic, version, length = struct.unpack_from('<4sII', raw)
    if magic != b'glTF' or version != 2 or length != len(raw):
        raise ValueError('GLB magic/version/length mismatch')
    offset = 12; chunks = []
    while offset < length:
        if offset+8 > length: raise ValueError('Incomplete GLB chunk header')
        size, kind = struct.unpack_from('<II', raw, offset); offset += 8
        if size % 4 or offset+size > length: raise ValueError('Invalid GLB chunk boundary')
        chunks.append((kind, raw[offset:offset+size])); offset += size
    if not chunks or chunks[0][0] != 0x4E4F534A:
        raise ValueError('First GLB chunk must be JSON')
    document = json.loads(chunks[0][1].decode('utf-8'))
    if document.get('asset', {}).get('version') != '2.0':
        raise ValueError('Expected glTF2 asset')
    binary = next((payload for kind, payload in chunks if kind == 0x004E4942), b'')
    for view in document.get('bufferViews', []):
        if view.get('buffer', 0) != 0 or view.get('byteOffset', 0)+view['byteLength'] > len(binary):
            raise ValueError('BufferView exceeds the GLB binary payload')
    for accessor in document.get('accessors', []):
        if not isinstance(accessor.get('count'), int) or accessor['count'] < 0:
            raise ValueError('Invalid accessor count')
        for key in ('min', 'max'):
            if key in accessor and any(not math.isfinite(v) for v in accessor[key]):
                raise ValueError('Nonfinite accessor bounds')
    return document, {'header_version': version, 'declared_length': length,
        'json_bytes': len(chunks[0][1]), 'binary_bytes': len(binary),
        'nodes': len(document.get('nodes', [])), 'meshes': len(document.get('meshes', [])),
        'accessors': len(document.get('accessors', [])), 'buffer_views': len(document.get('bufferViews', [])),
        'colored_primitives': sum('COLOR_0' in p.get('attributes', {}) for m in document.get('meshes', []) for p in m.get('primitives', []))}


def self_check():
    payload = json.dumps({'asset': {'version': '2.0'}}).encode()
    payload += b' '*(-len(payload) % 4)
    good = struct.pack('<4sII', b'glTF', 2, 20+len(payload))+struct.pack('<II', len(payload), 0x4E4F534A)+payload
    inspect_glb(good)
    caught = 0
    for changed in (b'bad!'+good[4:], good[:-1], good[:4]+struct.pack('<I', 1)+good[8:]):
        try: inspect_glb(changed)
        except ValueError: caught += 1
    if caught != 3: raise RuntimeError('GLB parser negative controls escaped')
    return caught


def accessor_values(raw, document, index):
    """Read the interleaved scalar/vector encodings emitted by the official exporter."""
    offset = 12; binary = None
    while offset < len(raw):
        size, kind = struct.unpack_from('<II', raw, offset); offset += 8
        if kind == 0x004E4942: binary = memoryview(raw)[offset:offset+size]
        offset += size
    if binary is None: raise ValueError('Missing BIN chunk')
    accessor = document['accessors'][index]
    if 'sparse' in accessor: raise ValueError('Sparse accessors are outside this measured exporter subset')
    view = document['bufferViews'][accessor['bufferView']]
    count = {'SCALAR':1,'VEC2':2,'VEC3':3,'VEC4':4}[accessor['type']]
    code, size, maximum = {5121:('B',1,255),5123:('H',2,65535),5125:('I',4,2**32-1),
                           5126:('f',4,1)}[accessor['componentType']]
    start = view.get('byteOffset',0)+accessor.get('byteOffset',0)
    stride = view.get('byteStride', count*size)
    result = []
    for i in range(accessor['count']):
        values = struct.unpack_from('<'+code*count,binary,start+i*stride)
        result.append([v/maximum if accessor.get('normalized') else v for v in values])
    return result


def snapshot(objects):
    result = {}
    for obj in objects:
        if obj.type != 'MESH' or 'stemloom_id' not in obj: continue
        attribute = obj.data.color_attributes.get('stemloom_color')
        if attribute is None and obj.data.color_attributes:
            attribute = obj.data.color_attributes[0]
        colors = None
        if attribute is not None:
            if attribute.domain == 'POINT':
                colors = [list(d.color[:3]) for d in attribute.data]
            elif attribute.domain == 'CORNER':
                colors = [[0., 0., 0.] for _ in obj.data.vertices]; count = [0]*len(colors)
                for loop, datum in zip(obj.data.loops, attribute.data):
                    count[loop.vertex_index] += 1
                    for j in range(3): colors[loop.vertex_index][j] += datum.color[j]
                colors = [[v/max(1,n) for v in c] for c,n in zip(colors,count)]
        result[obj['stemloom_id']] = {'positions': [list(obj.matrix_world @ v.co) for v in obj.data.vertices],
                                     'colors': colors, 'faces': len(obj.data.polygons)}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--input-blend', type=Path)
    parser.add_argument('--output', type=Path)
    parser.add_argument('--receipt', type=Path)
    parser.add_argument('--self-check', action='store_true')
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else sys.argv[1:]
    args = parser.parse_args(argv)
    caught = self_check()
    if args.self_check:
        print('PASS GLB header/chunk framing and three malformed twins'); return
    if not all((args.input_blend, args.output, args.receipt)):
        parser.error('--input-blend, --output and --receipt are required')
    import bpy
    from mathutils.kdtree import KDTree
    bpy.ops.preferences.addon_enable(module='io_scene_gltf2')
    bpy.ops.wm.open_mainfile(filepath=str(args.input_blend.resolve()))
    collection = bpy.data.collections.get(SCIENCE_COLLECTION)
    if collection is None: raise ValueError('Owned scientific collection is missing')
    before = snapshot(collection.objects)
    if not before: raise ValueError('No scientific meshes found')
    source_packet = bpy.context.scene.get('stemloom_packet_sha256')
    bpy.ops.object.select_all(action='DESELECT')
    for obj in collection.objects: obj.select_set(True)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.export_scene.gltf(filepath=str(args.output.resolve()), export_format='GLB',
                             use_selection=True, export_apply=False, export_extras=True,
                             export_cameras=False, export_lights=False)
    raw = args.output.read_bytes(); document, structure = inspect_glb(raw)
    # Verify the serialized glTF float colors before the importer's display
    # storage conversion. Generated owned objects have identity node transforms.
    serialized_color_worst = 0.; serialized_position_worst = 0.
    for node in document.get('nodes', []):
        if 'mesh' not in node: continue
        key = node.get('extras', {}).get('stemloom_id')
        if key not in before: raise RuntimeError('Unexpected non-scientific exported node')
        if any(k in node for k in ('matrix','translation','rotation','scale')):
            raise RuntimeError('This generated-identity fixture received an unmeasured node transform')
        reference = before[key]
        tree = KDTree(len(reference['positions']))
        for i,p in enumerate(reference['positions']): tree.insert((p[0],p[2],-p[1]),i)
        tree.balance()
        for primitive in document['meshes'][node['mesh']]['primitives']:
            positions = accessor_values(raw,document,primitive['attributes']['POSITION'])
            colors = accessor_values(raw,document,primitive['attributes']['COLOR_0'])
            for p,c in zip(positions,colors):
                _, index, distance = tree.find(p)
                serialized_position_worst = max(serialized_position_worst,distance)
                serialized_color_worst = max(serialized_color_worst,*(abs(x-y) for x,y in zip(c,reference['colors'][index])))
    for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
    bpy.ops.import_scene.gltf(filepath=str(args.output.resolve()))
    after = snapshot(bpy.data.objects)
    if before.keys() != after.keys():
        raise RuntimeError('Scientific identity extras did not survive glTF round trip')
    worst = 0.; color_worst = 0.; missing_colors = []
    before_vertices = after_vertices = 0
    for key, original in before.items():
        restored = after[key]
        before_vertices += len(original['positions']); after_vertices += len(restored['positions'])
        # Both directed distances allow glTF's normal/color-driven vertex splits.
        for left, right in ((original, restored), (restored, original)):
            tree = KDTree(len(right['positions']))
            for i,p in enumerate(right['positions']): tree.insert(p,i)
            tree.balance()
            for i,p in enumerate(left['positions']):
                _, index, distance = tree.find(p); worst = max(worst,distance)
                if left['colors'] is not None and right['colors'] is not None:
                    color_worst = max(color_worst,*(abs(x-y) for x,y in zip(left['colors'][i],right['colors'][index])))
        if original['colors'] is not None and restored['colors'] is None: missing_colors.append(key)
    # Blender 5.2's glTF importer intentionally allocates BYTE_COLOR. Bound that
    # observed sRGB display quantization separately from serialized float color.
    quantization_bound = 1-srgb_to_linear(254.5/255)+1e-4
    status = 'pass' if (worst <= 1e-5 and serialized_position_worst <= 1e-5 and
        serialized_color_worst <= 5e-7 and color_worst <= quantization_bound and not missing_colors) else 'fail'
    report = {'schema': 'stemloom.blender-glb/1', 'status': status,
              'created_utc': datetime.now(timezone.utc).isoformat(), 'blender_version': bpy.app.version_string,
              'source_packet_sha256': source_packet, 'source_blend_name': args.input_blend.name,
              'source_blend_sha256': hashlib.sha256(args.input_blend.read_bytes()).hexdigest(),
              'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
              'glb_sha256': hashlib.sha256(raw).hexdigest(), 'glb_bytes': len(raw),
              'structure': structure, 'scientific_objects': len(before),
              'original_expanded_vertices': before_vertices, 'reimported_vertices': after_vertices,
              'symmetric_geometry_distance': worst, 'geometry_tolerance': 1e-5,
              'serialized_coordinate_difference': serialized_position_worst,
              'serialized_linear_color_difference': serialized_color_worst,
              'serialized_color_tolerance': 5e-7,
              'max_reimport_linear_vertex_color_difference': color_worst,
              'reimport_color_quantization_bound': quantization_bound,
              'color_retention': 'GLB FLOAT colors measured separately; Blender5.2 re-import uses BYTE_COLOR and is display-quantized.',
              'missing_color_records': missing_colors, 'malformed_glb_controls_caught': caught,
              'scope': 'Executed glTF2 export/import of expanded mesh/tube/glyph geometry and identity extras. Triangulation and vertex splitting are permitted; original centerline topology and solver semantics are not a glTF round-trip claim.'}
    save_json(args.receipt, report)
    print('RESEARCH_LOOM_GLB',json.dumps(report,sort_keys=True))
    if status != 'pass': raise RuntimeError('Measured glTF2 transfer failed')


if __name__ == '__main__':
    main()
