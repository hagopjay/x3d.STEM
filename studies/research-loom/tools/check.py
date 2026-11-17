#!/usr/bin/env python3
"""Reproduce the scoped Research Loom release checks and retain their output."""
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import platform
import re
import subprocess
import struct
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
REPO=ROOT.parents[1]
sys.path.insert(0,str(ROOT))


def identity():
    paths=[p for folder in ('stemloom','tools','tests','web') for p in (ROOT/folder).rglob('*')
           if p.is_file() and p.suffix in ('.py','.js','.cjs','.html','.css') and
           '__pycache__' not in p.parts and 'vendor' not in p.parts]
    paths += [ROOT/'serve.py']
    return {str(p.relative_to(ROOT)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(set(paths))}


def blender_checks(bank):
    """Verify all recorded Blender routes against current packets and actual files.

    This does not rerun Blender. It reopens the retained transfer JSON, PNG and
    GLB files, checks their measured contents and binds executed receipts to
    their current tools, packets and scientific .blend source bytes.
    """
    from stemloom.blender_io import compare_frames,digest
    spec=importlib.util.spec_from_file_location('release_glb_reader',ROOT/'tools/export_glb.py')
    glb_reader=importlib.util.module_from_spec(spec);spec.loader.exec_module(glb_reader)
    cases={row['id']:row for row in bank['cases']}
    adapter=hashlib.sha256((ROOT/'stemloom/blender_io.py').read_bytes()).hexdigest()
    def require(value,message):
        if not value:raise ValueError(message)
    def blob(path,expected,size=None):
        raw=path.read_bytes()
        require(hashlib.sha256(raw).hexdigest()==expected,'Artifact hash differs: '+str(path.relative_to(ROOT)))
        if size is not None:require(len(raw)==size,'Artifact byte count differs: '+str(path.relative_to(ROOT)))
        return raw
    def finite_limit(value,limit,label):
        require(isinstance(value,(int,float)) and math.isfinite(value) and value<=limit,label)
    def version(value):
        match=re.match(r'^(\d+)\.(\d+)',str(value))
        require(match is not None and tuple(map(int,match.groups()))>=(5,2),'Executed Blender version is below 5.2')
    rows=[]
    for kind in ('flow','tensor','modes'):
        transfer=None;packet=None;frame=None
        for action,tool in (('transfer','blender_bridge.py'),('render','render_blender.py'),('glb','export_glb.py')):
            row={'kind':kind,'action':action,'status':'fail'}
            path=ROOT/'evidence'/f'blender-{action}-{kind}.json'
            try:
                r=json.loads(path.read_text())
                require(r.get('status')=='pass','Executed receipt does not pass')
                version(r.get('blender_version'))
                require(r.get('tool_sha256')==hashlib.sha256((ROOT/'tools'/tool).read_bytes()).hexdigest(),
                        'Executed tool source changed')
                if action=='transfer':
                    transfer=r;current=cases.get(r.get('case_id'))
                    require(current is not None and current['kind']==kind,'Transfer names an unexpected case')
                    raw=blob(ROOT/'web/bank'/current['packet'],current['sha256'],current['bytes'])
                    packet=json.loads(raw)
                    require(r.get('packet_sha256')==current['sha256'] and r.get('source_packet_sha256')==current['sha256'],
                            'Transfer packet identity differs from final bank')
                    index=r.get('frame_index')
                    require(isinstance(index,int) and not isinstance(index,bool) and 0<=index<len(packet['frames']),
                            'Transfer frame index is invalid')
                    frame=packet['frames'][index]
                    require(r.get('adapter_sha256')==adapter,'Transfer adapter changed')
                    require(r.get('coordinate_rotation_determinant')==1,'Transfer rotation changes handedness')
                    require(abs(r['time']-frame['time'])<1e-13,'Transfer time differs from selected frame')
                    require(r.get('changed_geometry_control',{}).get('caught') is True,'Actual-coordinate bad control was not caught')
                    finite_limit(r['check']['max_coordinate_absolute_difference'],3e-6,'Recorded coordinate discrepancy exceeds declared subset')
                    finite_limit(r['check']['max_color_absolute_difference'],3e-6,'Recorded color discrepancy exceeds declared subset')
                    require(r['check'].get('status')=='pass' and not r['check'].get('issues'),'Recorded transfer comparison is not green')
                    back_path=ROOT/'exports/blender'/f'{kind}-roundtrip.json'
                    back=json.loads(back_path.read_text())
                    require(back.get('source_frame_index')==index and back.get('transfer',{}).get('source_packet_sha256')==current['sha256'],
                            'Retained roundtrip identity/frame differs')
                    measured=compare_frames(frame,back['frames'][0],tolerance=3e-6)
                    require(measured['status']=='pass','Actual retained roundtrip geometry differs from final packet')
                    row['retained_roundtrip_sha256']=hashlib.sha256(back_path.read_bytes()).hexdigest()
                    row['measured_geometry']=measured
                elif action=='render':
                    require(transfer is not None and packet is not None,'Matching transfer receipt unavailable')
                    require(r.get('case_id')==transfer['case_id'] and r.get('frame_index')==transfer['frame_index'],
                            'Render and transfer select different cases/frames')
                    require(r.get('packet_sha256')==transfer['packet_sha256'] and r.get('source_packet_sha256')==transfer['packet_sha256'],
                            'Render packet differs from transferred scientific source')
                    require(r.get('adapter_sha256')==adapter,'Render adapter changed')
                    require(r.get('frame_sha256')==digest(frame),'Rendered frame content identity differs')
                    require(abs(r['time']-frame['time'])<1e-13,'Render time differs from selected frame')
                    require(r.get('engine')=='Cycles' and r.get('device')=='CPU','Unexpected pixel-source classification')
                    image=ROOT/'docs/assets'/f'{kind}.png'
                    raw=blob(image,r.get('image_sha256'),r.get('image_bytes'))
                    require(raw[:8]==b'\x89PNG\r\n\x1a\n' and raw[12:16]==b'IHDR','Retained image is not PNG')
                    require(struct.unpack('>II',raw[16:24])==(r['width'],r['height']),'PNG dimensions differ from render receipt')
                    row['image_sha256']=r['image_sha256']
                else:
                    require(transfer is not None and packet is not None,'Matching transfer receipt unavailable')
                    require(r.get('source_packet_sha256')==transfer['packet_sha256'],'GLB source packet differs from final transfer')
                    require(r.get('source_blend_name')==f'scientific-{kind}.blend','Unexpected scientific .blend source')
                    source=ROOT/'exports/blender'/r['source_blend_name']
                    blob(source,r.get('source_blend_sha256'))
                    raw=blob(ROOT/'exports/blender'/f'{kind}.glb',r.get('glb_sha256'),r.get('glb_bytes'))
                    document,structure=glb_reader.inspect_glb(raw)
                    require(structure==r.get('structure'),'Retained GLB structure differs from executed receipt')
                    expected={g['id']:g for key in ('meshes','lines','points') for g in frame[key]}
                    nodes=[node for node in document.get('nodes',[]) if 'mesh' in node]
                    require(len(nodes)==len(expected)==r.get('scientific_objects'),'GLB scientific-object count differs')
                    require({node.get('extras',{}).get('stemloom_id') for node in nodes}==expected.keys(),
                            'GLB actual identity extras differ')
                    for node in nodes:
                        extra=node['extras'];original=expected[extra['stemloom_id']]
                        require(extra.get('stemloom_source_packet_sha256')==transfer['packet_sha256'] and
                                extra.get('stemloom_source_count')==len(original['positions']),
                                'GLB actual source extras/count differ')
                    finite_limit(r.get('symmetric_geometry_distance'),1e-5,'GLB reimport geometry exceeded tolerance')
                    finite_limit(r.get('serialized_coordinate_difference'),1e-5,'GLB serialized geometry exceeded tolerance')
                    finite_limit(r.get('serialized_linear_color_difference'),5e-7,'GLB serialized color exceeded tolerance')
                    finite_limit(r.get('max_reimport_linear_vertex_color_difference'),r['reimport_color_quantization_bound'],
                                 'GLB importer color quantization exceeded measured bound')
                    require(not r.get('missing_color_records') and r.get('malformed_glb_controls_caught')==3,
                            'GLB colors or parser bad controls are incomplete')
                    require(r.get('original_expanded_vertices')==r.get('reimported_vertices'),'GLB expanded vertex count changed')
                    row['glb_sha256']=r['glb_sha256'];row['source_blend_sha256']=r['source_blend_sha256']
                require(r.get('scientific_objects')==sum(len(frame[key]) for key in ('meshes','lines','points')),
                        'Scientific object count differs from retained frame')
                row.update(status='pass',blender_version=r['blender_version'],
                           receipt_sha256=hashlib.sha256(path.read_bytes()).hexdigest())
            except Exception as error:
                row['error']=type(error).__name__+': '+str(error)
            rows.append(row)
    return rows


def main():
    before=identity();report={'schema':'stemloom.release-checks/1','status':'not_run','started_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':before,'python':platform.python_version(),'commands':[],
        'scope':'Local model, transfer, HTTP and UI-adapter checks. Native X_ITE browser rendering is not claimed.'}
    commands=[([sys.executable,'-m','unittest','discover','-s','tests','-q'],ROOT),
              ([sys.executable,'-O','-m','unittest','discover','-s','tests','-q'],ROOT),
              (['node','tests/scene.test.cjs'],ROOT),
              ([sys.executable,'-E','-s','-m','unittest','discover','-s','lib/stemkit/tests','-t','lib','-q'],REPO),
              ([sys.executable,'-O','-E','-s','-m','unittest','discover','-s','lib/stemkit/tests','-t','lib','-q'],REPO),
              ([sys.executable,'tools/verify.py'],ROOT),
              ([sys.executable,'tools/validate_x3d.py'],ROOT)]
    passed=True
    vendor=ROOT/'web'/'vendor'/'x_ite'
    origin=json.loads((vendor/'ORIGIN.json').read_text())
    asset_ok=all(hashlib.sha256((vendor/name).read_bytes()).hexdigest()==expected
                 for name,expected in origin['files_sha256'].items())
    report['vendored_runtime']={'status':'pass' if asset_ok else 'fail','files':len(origin['files_sha256'])}
    passed=passed and asset_ok
    for command,cwd in commands:
        t=time.perf_counter();result=subprocess.run(command,cwd=cwd,capture_output=True,text=True,timeout=180)
        row={'command':command[1:],'cwd':'study' if cwd==ROOT else 'repository','exit_code':result.returncode,
             'seconds':time.perf_counter()-t,'stdout':result.stdout,'stderr':result.stderr}
        match=re.search(r'Ran (\d+) tests',result.stderr)
        if match:row['tests_run']=int(match.group(1))
        if result.returncode or 'skipped=' in result.stderr:passed=False
        report['commands'].append(row);print(('PASS' if result.returncode==0 else 'FAIL'),' '.join(command[1:]),flush=True)
    # Recorded Blender transfers/renders are independently bound to actual files.
    bank=json.loads((ROOT/'web'/'bank'/'index.json').read_text())
    blender=blender_checks(bank)
    passed=passed and all(row['status']=='pass' for row in blender)
    report['blender']=blender;report['source_drift']='none' if before==identity() else 'changed'
    report['status']='pass' if passed and report['source_drift']=='none' else 'fail'
    report['browser']={'status':'not_run','reason':'This host blocks native browser socket operations; actual Blender CPU render receipts are separate.'}
    report['finished_utc']=datetime.now(timezone.utc).isoformat()
    (ROOT/'evidence'/'release.json').write_text(json.dumps(report,indent=2,ensure_ascii=False,allow_nan=False)+'\n')
    print(json.dumps({'status':report['status'],'instruments':len(commands),'source_drift':report['source_drift']}))
    return 0 if report['status']=='pass' else 1


if __name__=='__main__':raise SystemExit(main())
