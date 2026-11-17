#!/usr/bin/env python3
"""Actual Blender mesh storage precision, save/reopen, and local-origin probe.

Run with Blender --background --factory-startup --threads 2 --python-exit-code 1
--python THIS_FILE -- --output DIRECTORY. No GPU or add-on is required.
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

import bpy


OFFSETS = [[0., 0., 0.], [.01, .02, .03], [1.2345, -.06789, .000123],
           [123.456789, 12.3456789, -1.23456789]]
ORIGINS = {'utm_like': [500000., 4649776., 120.],
           'ecef_like': [6378137., 1400000., 3000000.]}


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), allow_nan=False)


def need(value, message):
    if not value:
        raise RuntimeError(message)


def error(left, right):
    return max(abs(a-b) for p,q in zip(left,right) for a,b in zip(p,q))


def f32(value):
    return struct.unpack('<f', struct.pack('<f', value))[0]


def f32_spacing(value):
    v = abs(float(value))
    return 2.**(math.floor(math.log2(v))-23) if v else 2.**-149


def positions(obj):
    # Actual reopened data vertices: no source-coordinate cache is used here.
    return [[float(c) for c in v.co] for v in obj.data.vertices]


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    blend=args.output/'precision-control.blend'
    receipt=args.output/'precision-control.json'
    bpy.ops.object.select_all(action='SELECT');bpy.ops.object.delete(use_global=False)
    expected={}
    for label, origin in ORIGINS.items():
        world=[[origin[i]+p[i] for i in range(3)] for p in OFFSETS]
        # Subtract in binary64 before the Blender mesh border. Keep the full
        # decimal origin in source metadata; do not place it in matrix_world.
        local=[[p[i]-origin[i] for i in range(3)] for p in world]
        expected[label]={'origin':origin,'world':world,'local':local}
        for route, pts in (('direct',world),('local_origin',local)):
            mesh=bpy.data.meshes.new(label+'-'+route)
            mesh.from_pydata(pts,[],[]);mesh.update()
            obj=bpy.data.objects.new(label+'-'+route,mesh)
            bpy.context.scene.collection.objects.link(obj)
            obj['precision_route']=route;obj['case_id']=label
    text=bpy.data.texts.new('Precision_Source.json')
    text.write(canonical({'coordinate_units':'m','expected':expected}))
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    retained=json.loads(bpy.data.texts['Precision_Source.json'].as_string())
    need(retained=={'coordinate_units':'m','expected':expected},'Source decimal metadata changed')
    results=[]
    for label, source in retained['expected'].items():
        origin=source['origin'];world=source['world'];local=source['local']
        direct_obj=bpy.data.objects[label+'-direct']
        local_obj=bpy.data.objects[label+'-local_origin']
        direct=positions(direct_obj);stored_local=positions(local_obj)
        restored=[[origin[i]+p[i] for i in range(3)] for p in stored_local]
        direct_error=error(world,direct);local_error=error(local,stored_local)
        restored_error=error(world,restored)
        quantized=[[f32(v) for v in p] for p in world]
        need(direct==quantized,'Direct mesh did not match binary32 reference')
        need(direct_error>=.01,'Control did not reveal a centimetre-scale loss')
        need(restored_error<=1e-5,'Local-origin route exceeded ten-micrometre bound')
        # Tamper a real reopened vertex, while metadata remains unchanged.
        old=local_obj.data.vertices[1].co.x
        local_obj.data.vertices[1].co.x+=.125
        changed=positions(local_obj)
        altered=[[origin[i]+p[i] for i in range(3)] for p in changed]
        caught=error(world,altered)>.1
        local_obj.data.vertices[1].co.x=old
        need(caught,'Actual-vertex mutation was not detected')
        results.append({'case_id':label,'units':'m','origin':origin,
            'float32_spacing_at_origin_m':[f32_spacing(v) for v in origin],
            'direct_world_max_abs_error_m':direct_error,
            'local_storage_max_abs_error_m':local_error,
            'restored_world_max_abs_error_m':restored_error,
            'local_origin_improvement_factor':direct_error/max(restored_error,1e-300),
            'direct_matches_binary32_reference':True,'actual_vertex_mutation_caught':caught,
            'direct_readback':direct,'local_readback':stored_local,'restored_world':restored})
    report={'schema':'scivis.precision-probe/1','status':'pass',
        'created_utc':datetime.now(timezone.utc).isoformat(),
        'blender_version':bpy.app.version_string,
        'blender_version_tuple':list(bpy.app.version),
        'blender_build_hash':bpy.app.build_hash.decode(),
        'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
        'blend_sha256':hashlib.sha256(blend.read_bytes()).hexdigest(),
        'save_reopen_executed':True,'origin_metadata_retained':True,
        'coordinate_type':'Reopened Blender MeshVertex.co, compared with binary32 struct reference',
        'cases':results,
        'scope':'Two synthetic metric-coordinate controls on actual Blender5.2.4 mesh storage; no native X3D or splat import, renderer/GPU precision, or arbitrary scale guarantee.',
        'limitations':['Origin restoration occurs in Python binary64 outside Blender world transforms.',
            'Adding a large origin to Blender matrix_world may reintroduce precision loss.',
            'Centering is a reversible coordinate mapping, not rescaling or changing physical units.',
            'Do not infer a universal 1e-6 absolute tolerance from float32 storage.']}
    receipt.write_text(json.dumps(report,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':'pass','receipt':str(receipt),'errors':[
        {k:r[k] for k in ('case_id','direct_world_max_abs_error_m','restored_world_max_abs_error_m')}
        for r in results]}))


if __name__=='__main__':main()
