#!/usr/bin/env python3
"""Run inside Blender: import, save, reopen and measure a Research Loom frame."""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import json
import hashlib
import importlib.util
from pathlib import Path
import subprocess
import sys
import tempfile
import xml.etree.ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stemloom.blender_io import (SCIENCE_COLLECTION, compare_frames, digest,
                                export_case, import_case, save_json)


def probe_extension(source, route, receipt_path):
    """Execute a bounded fixture through a separately registered hub extension."""
    import bpy
    version = '4.0' if route == 'fork' else '3.3'
    material = ('<PhysicalMaterial baseColor="0.2 0.6 0.8" metallic="0.2" roughness="0.4"/>'
                if route == 'fork' else '<Material diffuseColor="0.2 0.6 0.8"/>')
    fixture = ('<?xml version="1.0" encoding="UTF-8"?><X3D profile="Immersive" version="'+version+'">'
      '<head><meta name="stemloom.case" content="hub-fixture"/></head><Scene>'
      '<WorldInfo title="Research Loom hub fixture"/>'
      '<Shape DEF="Triangle"><MetadataString name="stemloom.units" value=\'"dimensionless"\'/>'
      '<Appearance>'+material+'</Appearance><IndexedFaceSet coordIndex="0 1 2 -1" solid="false">'
      '<Coordinate point="0 0 0 1.2 -0.4 0.2 0.3 1.1 0.5"/>'
      '<Color color="1 0 0 0 1 0 0 0 1"/></IndexedFaceSet></Shape>'
      '<Shape DEF="Path"><Appearance><Material emissiveColor="0.2 0.7 0.9"/></Appearance>'
      '<IndexedLineSet coordIndex="0 1 2 -1"><Coordinate point="-0.3 0 1 0.1 0.4 0.7 0.6 0.7 0.9"/>'
      '<Color color="0.2 0.7 0.9 0.3 0.8 0.7 0.5 0.8 0.4"/></IndexedLineSet></Shape>'
      '<Shape DEF="Observations"><Appearance><Material diffuseColor="0.7 0.3 0.2"/></Appearance>'
      '<PointSet><Coordinate point="0.25 -0.2 0.9 0.2 0.3 -0.1"/>'
      '<Color color="0.7 0.3 0.2 0.1 0.4 0.8"/></PointSet></Shape></Scene></X3D>')
    report = {'schema': 'stemloom.blender-extension-probe/1', 'route': route,
              'blender_version': bpy.app.version_string, 'input_x3d_version': version,
              'fixture_sha256': hashlib.sha256(fixture.encode()).hexdigest(),
              'status': 'not_run', 'scope': 'One executed bounded fixture, not general extension conformance.'}
    try:
        report['extension_commit'] = subprocess.check_output(
            ['git', '-C', str(source.parent), 'rev-parse', 'HEAD'], text=True).strip()
        report['manifest'] = (source/'blender_manifest.toml').read_text()
        name = 'research_loom_hub_extension'
        spec = importlib.util.spec_from_file_location(name, source/'__init__.py',
                                                      submodule_search_locations=[str(source)])
        extension = importlib.util.module_from_spec(spec); sys.modules[name] = extension
        spec.loader.exec_module(extension); extension.register()
        for obj in list(bpy.data.objects): bpy.data.objects.remove(obj, do_unlink=True)
        with tempfile.TemporaryDirectory(prefix='research-loom-hub-') as folder:
            path = Path(folder)/'fixture.x3d'; path.write_text(fixture)
            result = bpy.ops.import_scene.x3d(filepath=str(path))
            if 'FINISHED' not in result: raise RuntimeError('Importer did not finish: '+str(result))
            snapshot = []
            for obj in bpy.data.objects:
                row = {'name': obj.name, 'type': obj.type,
                       'x3d_properties': sorted(k for k in obj.keys() if k.startswith('x3d'))}
                if obj.type == 'MESH':
                    row.update(vertices=len(obj.data.vertices), edges=len(obj.data.edges),
                               faces=len(obj.data.polygons),
                               color_attributes=[{'name': a.name, 'domain': a.domain} for a in obj.data.color_attributes])
                elif obj.type == 'CURVE': row['splines'] = len(obj.data.splines)
                snapshot.append(row)
            report['imported_objects'] = snapshot
            out = Path(folder)/'back.x3d'
            options = {'filepath': str(out), 'check_existing': False}
            if route == 'fork': options['x3d_version'] = 'X3D40'
            result = bpy.ops.export_scene.x3d(**options)
            if 'FINISHED' not in result: raise RuntimeError('Exporter did not finish: '+str(result))
            xml = ET.fromstring(out.read_bytes())
            report.update(output_x3d_version=xml.get('version'), output_bytes=out.stat().st_size,
                          output_node_counts={tag: len(xml.findall('.//'+tag)) for tag in
                              ('IndexedFaceSet','IndexedLineSet','PointSet','PhysicalMaterial','Material','Color','ColorRGBA','MetadataString')},
                          output_head_meta=[{'name': n.get('name'), 'content': n.get('content')} for n in xml.findall('./head/meta')])
            report['requested_version_preserved'] = xml.get('version') == version
            counts = report['output_node_counts']
            report['retention_status'] = 'retained_fixture' if (report['requested_version_preserved'] and
                counts['IndexedFaceSet'] and counts['IndexedLineSet'] and counts['PointSet'] and
                counts['MetadataString'] and (counts['Color'] or counts['ColorRGBA'])) else 'lossy'
            # This gate says the behavior probe executed and retained its mesh
            # control. It does not promote observed losses to round-trip success.
            report['status'] = 'pass' if any(r.get('faces') == 1 and r.get('vertices') == 3
                                            for r in snapshot) else 'fail'
            report['status_meaning'] = 'Executed import/export behavior probe; consult retention_status for preservation.'
            report['loss_interpretation'] = ['Inspect imported primitive types and output node counts: geometry can be baked or omitted.',
                'Classic stock path advertises X3D 3.3; the ecosystem fork has its own modern 4.0 path.',
                'This fixture is separate from the owned packet geometry adapter and its coordinate/metadata contract.']
        extension.unregister()
    except Exception as error:
        report.update(status='fail', error=type(error).__name__+': '+str(error))
    save_json(receipt_path, report)
    print('RESEARCH_LOOM_EXTENSION', json.dumps(report, sort_keys=True))
    if report['status'] != 'pass': raise RuntimeError('Extension fixture failed')


def main():
    import bpy
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path)
    parser.add_argument('--frame', type=int, default=0)
    parser.add_argument('--output-blend', type=Path)
    parser.add_argument('--roundtrip', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--probe-extension', type=Path, help='Path to the extension source package directory')
    parser.add_argument('--extension-route', choices=('stock', 'fork'), default='stock')
    argv = sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    args = parser.parse_args(argv)
    if args.probe_extension:
        return probe_extension(args.probe_extension.resolve(), args.extension_route, args.receipt)
    if not all((args.packet, args.output_blend, args.roundtrip)):
        parser.error('--packet, --output-blend and --roundtrip are required for an owned transfer')
    packet = json.loads(args.packet.read_text())
    if not 0 <= args.frame < len(packet.get('frames', [])):
        raise ValueError('Frame is outside the saved case bank')
    imported = import_case(packet, args.frame)
    args.output_blend.parent.mkdir(parents=True, exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    # Reopening tests the actual .blend serialization, not only in-memory data.
    bpy.ops.wm.open_mainfile(filepath=str(args.output_blend.resolve()))
    back = export_case()
    save_json(args.roundtrip, back)
    measured = json.loads(args.roundtrip.read_text())
    check = compare_frames(packet['frames'][args.frame], measured['frames'][0])
    # A changed real Blender coordinate must be visible to the exporter even
    # when cached source JSON and custom identity metadata remain unchanged.
    obj = next(iter(bpy.data.collections[SCIENCE_COLLECTION].objects))
    original = obj.data.vertices[0].co.copy()
    obj.data.vertices[0].co.x += .01*int(obj['stemloom_stride'])
    changed = compare_frames(packet['frames'][args.frame], export_case()['frames'][0])
    obj.data.vertices[0].co = original
    negative = {'caught': changed['status'] == 'fail',
                'changed': 'One actual Blender geometry coordinate, with source metadata unchanged.',
                'max_coordinate_absolute_difference': changed['max_coordinate_absolute_difference']}
    receipt = {'schema': 'stemloom.blender-roundtrip/1', 'created_utc': datetime.now(timezone.utc).isoformat(),
               'blender_version': bpy.app.version_string, 'blender_version_tuple': list(bpy.app.version),
               'packet': args.packet.name, 'packet_sha256': digest(packet), **imported,
               'check': check, 'status': check['status'],
               'changed_geometry_control': negative,
               'coordinate_rotation_determinant': 1,
               'adapter_sha256': hashlib.sha256((ROOT/'stemloom/blender_io.py').read_bytes()).hexdigest(),
               'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'extension_required': False,
               'limits': ['Owned meshes, sampled polyline tubes and point glyphs only.',
                          'Line/point radii are authored glyph appearance, not field measurements.',
                          'Preserved historical solver measurements are not rerun after Blender edits.',
                          'No arbitrary Blender material, modifier or animation round-trip claim.']}
    save_json(args.receipt, receipt)
    print('RESEARCH_LOOM_BLENDER', json.dumps(receipt, sort_keys=True))
    if check['status'] != 'pass' or not negative['caught']:
        raise RuntimeError('Measured Blender geometry round trip failed')


if __name__ == '__main__':
    main()
