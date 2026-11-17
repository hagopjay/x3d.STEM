#!/usr/bin/env python3
"""Four asymmetric SH3 splats: actual native Blender import and transform probe.

Adapted conceptually from the recovered historical seven-question probe. The
expected values below derive from the declared reference PLY layout rather than
the tested fork. Run in Blender with --output DIRECTORY [--addon-root PATH].
"""
from __future__ import annotations
import argparse
from datetime import datetime,timezone
import hashlib
import importlib.util
import json
import math
from pathlib import Path
import struct
import subprocess
import sys
import xml.etree.ElementTree as ET
import bpy
from mathutils import Matrix,Quaternion,Vector

C0=0.28209479177387814


def need(value,message):
    if not value:raise RuntimeError(message)


def sha(path):return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def maxdiff(left,right):
    def flatten(value):
        for v in value:
            if isinstance(v,(list,tuple)):yield from flatten(v)
            else:yield float(v)
    a=list(flatten(left));b=list(flatten(right))
    return max((abs(x-y) for x,y in zip(a,b)),default=0.) if len(a)==len(b) else float('inf')


def attribute_values(attribute):
    spec={'FLOAT':('value',1),'FLOAT_VECTOR':('vector',3),'FLOAT4':('vector',4),
          'QUATERNION':('value',4),'FLOAT_COLOR':('color',4),'BYTE_COLOR':('color',4)}
    if attribute.data_type not in spec:return None
    key,width=spec[attribute.data_type];raw=[0.]*(width*len(attribute.data))
    attribute.data.foreach_get(key,raw)
    return [raw[i*width:(i+1)*width] for i in range(len(attribute.data))]


def snapshot(obj):
    return {'name':obj.name,'object_type':obj.type,'data_type':getattr(obj.data,'type',None),
        'matrix_world':[list(r) for r in obj.matrix_world],
        'attributes':{a.name:{'type':a.data_type,'domain':a.domain,'values':attribute_values(a)}
            for a in obj.data.attributes if not a.name.startswith('.')},
        'data_custom_properties':{str(k):str(obj.data[k]) for k in obj.data.keys()},
        'color_related_rna':[{ 'name':p.identifier,'type':p.type }
            for p in obj.data.bl_rna.properties if any(t in p.identifier.lower() for t in ('color','radiance','gamma'))]}


def world_covariances(obj):
    scale=attribute_values(obj.data.attributes['scale'])
    rotation=attribute_values(obj.data.attributes['rotation'])
    m=obj.matrix_world.to_3x3()
    out=[]
    for s,q in zip(scale,rotation):
        r=Quaternion(q).normalized().to_matrix()
        c=m@r@Matrix.Diagonal(Vector([v*v for v in s]))@r.transposed()@m.transposed()
        out.append([list(row) for row in c])
    return out


def main():
    argv=sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else []
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',type=Path,required=True)
    parser.add_argument('--addon-root',type=Path)
    args=parser.parse_args(argv);args.output.mkdir(parents=True,exist_ok=True)
    bpy.ops.wm.read_factory_settings(use_empty=True)
    cases=[([1.,2.,3.],[0.,0.,0.],0.,[.1,.2,.3],[1.,0.,0.,0.]),
           ([-1.,.5,2.5],[1.,-1.,.5],2.,[.05,.05,.4],[.5,.5,.5,.5]),
           ([0.,-2.,1.],[-2.,2.5,.25],-3.,[.3,.1,.02],[0.,1.,0.,0.]),
           ([4.,0.,-1.],[.3,.2,.1],5.,[.01,.015,.02],[2**-.5,0.,2**-.5,0.])]
    rows=[]
    for i,(position,dc,logit,scales,quaternion) in enumerate(cases):
        # Source3DGSf_rest is channel-major:15R,15G,15B atSH3.
        rest=[round(.001*(k+1)*(1+.1*i),6) for k in range(45)]
        rows.append([*position,0.,0.,0.,*dc,*rest,logit,*[math.log(v) for v in scales],*quaternion])
    names=['x','y','z','nx','ny','nz','f_dc_0','f_dc_1','f_dc_2']+[f'f_rest_{k}' for k in range(45)]+['opacity','scale_0','scale_1','scale_2','rot_0','rot_1','rot_2','rot_3']
    ply=args.output/'native-four-sh3.ply'
    header=('ply\nformat binary_little_endian 1.0\nelement vertex 4\n'+''.join(f'property float {n}\n' for n in names)+'end_header\n').encode()
    # Expected values are based on exactly serializedfloat32 inputs.
    raw_rows=[struct.pack('<62f',*r) for r in rows]
    ply.write_bytes(header+b''.join(raw_rows))
    rows=[list(struct.unpack('<62f',r)) for r in raw_rows]
    imported=list(bpy.ops.wm.ply_import(filepath=str(ply.resolve())))
    objects=[o for o in bpy.context.scene.objects if o.type=='POINTCLOUD']
    need(len(objects)==1,'NativePLYdidnotproduceonePointCloud')
    obj=objects[0];obj.name='Native_SH3_Oracle'
    snap=snapshot(obj);attrs=snap['attributes']
    need(snap['data_type']=='GAUSSIAN_SPLAT','PointCloudisnotGAUSSIAN_SPLAT')
    base=attrs['radiance:base']['values']
    source_dc=[r[6:9] for r in rows]
    reconstructed=[[.5+C0*v for v in r[6:9]] for r in rows]
    sigmoid=[[1/(1+math.exp(-r[54]))] for r in rows]
    expected_scale=[[math.exp(v) for v in r[55:58]] for r in rows]
    expected_rotation=[]
    for r in rows:
        q=r[58:62];n=math.sqrt(sum(v*v for v in q));expected_rotation.append([v/n for v in q])
    sh=[]
    for k in range(15):
        observed=attrs.get(f'radiance:sh_{k}',{}).get('values')
        expected=[[r[9+k],r[9+15+k],r[9+30+k]] for r in rows]
        sh.append({'attribute':f'radiance:sh_{k}','max_abs_error':maxdiff(observed or [],expected),
            'expected_first_splat_rgb':expected[0],'observed_first_splat_rgb':observed[0] if observed else None})
    world_positions=[list(obj.matrix_world@Vector(p)) for p in attrs['position']['values']]
    source_positions=[r[:3] for r in rows]
    answers={'Q1_base_xyz_raw_dc_max_error':maxdiff([r[:3] for r in base],source_dc),
        'Q1_base_xyz_reconstructed_rgb_max_error':maxdiff([r[:3] for r in base],reconstructed),
        'Q2_opacity_sigmoid_max_error':maxdiff([[r[3]] for r in base],sigmoid),
        'Q3_scale_exp_max_error':maxdiff(attrs['scale']['values'],expected_scale),
        'Q4_rotation_normalized_wxyz_max_error':maxdiff(attrs['rotation']['values'],expected_rotation),
        'Q5_all15_channel_major_rgb_slots':sh,
        'Q6_raw_position_vs_source_max_error':maxdiff(attrs['position']['values'],source_positions),
        'Q6_world_position_vs_source_max_error':maxdiff(world_positions,source_positions),
        'Q6_object_matrix_world':snap['matrix_world'],
        'Q7_color_related_rna':snap['color_related_rna'],
        'Q7_color_custom_properties':snap['data_custom_properties'],
        'Q7_scope':'No dedicated color-encoding property found by these checks is not proof that all Blender internal color metadata is absent.'}
    need(answers['Q2_opacity_sigmoid_max_error']<1e-6,'Opacityactivationmismatch')
    need(answers['Q3_scale_exp_max_error']<1e-6,'Scaletransformationmismatch')
    need(answers['Q4_rotation_normalized_wxyz_max_error']<1e-6,'Quaternionordermismatch')
    need(max(s['max_abs_error'] for s in sh)<1e-6,'SH3channelmajormappingmismatch')
    # A realvertex mutation distinguishes datareadback fromretainedsource.
    attr=obj.data.attributes['position'];old=list(attr.data[0].vector)
    attr.data[0].vector.x+=.125
    bad=maxdiff(attribute_values(attr),source_positions)>.1
    attr.data[0].vector=old;need(bad,'Actualnativepositionmutationnotdetected')
    transform_obj=obj.copy();transform_obj.data=obj.data.copy();transform_obj.name='Native_ApplyTransform_Control'
    bpy.context.scene.collection.objects.link(transform_obj)
    transform_obj.location=(1.,2.,3.);transform_obj.rotation_euler=(.2,-.3,.4);transform_obj.scale=(1.5,.75,2.)
    bpy.context.view_layer.update()
    before=snapshot(transform_obj);cov_before=world_covariances(transform_obj)
    points_before=[list(transform_obj.matrix_world@Vector(p)) for p in before['attributes']['position']['values']]
    bpy.ops.object.select_all(action='DESELECT');transform_obj.select_set(True);bpy.context.view_layer.objects.active=transform_obj
    applied=list(bpy.ops.object.transform_apply(location=True,rotation=True,scale=True))
    after=snapshot(transform_obj);cov_after=world_covariances(transform_obj)
    points_after=[list(transform_obj.matrix_world@Vector(p)) for p in after['attributes']['position']['values']]
    transform={'operator_result':applied,'before':before,'after':after,
       'world_position_max_abs_change':maxdiff(points_before,points_after),
       'world_covariance_max_abs_change':maxdiff(cov_before,cov_after),
       'preservation_status':'loss_reproduced' if maxdiff(cov_before,cov_after)>1e-5 else 'preserved_within_bound',
       'covariance_comparison_tolerance':1e-5,
       'covariance_units':'arbitrary fixture units squared',
       'covariance_before':cov_before,'covariance_after':cov_after,
       'scope':'Covariance reconstructed from actual scale/quaternion attributes and object matrix; SH directional radiance is not render-tested.'}
    bpy.ops.object.select_all(action='DESELECT');obj.select_set(True);bpy.context.view_layer.objects.active=obj
    fork={'status':'not_run'}
    if args.addon_root:
        package='scivis_native53_x3d_io'
        spec=importlib.util.spec_from_file_location(package,args.addon_root/'source/__init__.py',submodule_search_locations=[str(args.addon_root/'source')])
        module=importlib.util.module_from_spec(spec);sys.modules[package]=module;spec.loader.exec_module(module);module.register()
        x3d=args.output/'native-fork-roundtrip.x3d'
        outcome=list(bpy.ops.export_scene.x3d(filepath=str(x3d.resolve()),x3d_version='X3D41',use_selection=True,axis_forward='Y',axis_up='Z'))
        tree=ET.fromstring(x3d.read_text());nodes=tree.findall('.//GaussianSplats')
        need(len(nodes)==1,'ForkdidnotexportoneGaussianSplatsnode')
        node=nodes[0]
        # IndependentXMLreadback checksrawattributes, nottheforkparsermetadata.
        xml_values={k:[float(v) for v in s.split()] for k,s in node.attrib.items() if k in ('positions','scales','orientations','opacities') or k.startswith('sphericalHarmonics')}
        need(len(xml_values.get('positions',[]))==12,'Forkpositioncountdiffers')
        # Reference mappings derive from the written PLY schema, independently
        # of the fork's parser and native extraction functions.
        def flat(values):return [v for row in values for v in row]
        expected_xml={'positions':flat(source_positions),'scales':flat(expected_scale),
            'orientations':flat([[*q[1:],q[0]] for q in expected_rotation]),
            'opacities':flat(sigmoid),'sphericalHarmonicsDegree0Coef0':flat(source_dc)}
        for degree in (1,2,3):
            for coef in range(2*degree+1):
                k=degree*degree-1+coef
                expected_xml[f'sphericalHarmonicsDegree{degree}Coef{coef}']=flat([[r[9+k],r[24+k],r[39+k]] for r in rows])
        xml_errors={name:maxdiff(xml_values.get(name,[]),value) for name,value in expected_xml.items()}
        need(max(xml_errors.values())<1e-6,'Independent X3D scalar mapping differs from declared PLY semantics')
        import_result=list(bpy.ops.import_scene.x3d(filepath=str(x3d.resolve()),axis_forward='Y',axis_up='Z'))
        new_objs=[o for o in bpy.context.scene.objects if o.type=='POINTCLOUD' and o!=obj and o!=transform_obj]
        need(len(new_objs)==1,'ForkreimportdidnotcreateonenativePointCloud')
        returned=snapshot(new_objs[0])
        errors={name:maxdiff(data['values'],returned['attributes'].get(name,{}).get('values') or []) for name,data in attrs.items() if name in ('position','scale','rotation','radiance:base') or name.startswith('radiance:sh_')}
        need(max(errors.values())<2e-6,'Forknativerawattributesdidnotroundtrip')
        fork={'status':'pass','export_result':outcome,'import_result':import_result,
              'x3d_sha256':sha(x3d),'x3d_version':tree.get('version'),
              'native_attribute_max_abs_errors':errors,'actual_xml_values':xml_values,
              'independent_xml_max_abs_errors':xml_errors,
              'fork_commit':subprocess.check_output(['git','-C',str(args.addon_root),'rev-parse','HEAD'],text=True).strip(),
              'fork_worktree_status':subprocess.check_output(['git','-C',str(args.addon_root),'status','--porcelain'],text=True),
              'fork_source_sha256':{str(p.relative_to(args.addon_root)):sha(p) for p in sorted((args.addon_root/'source').rglob('*.py'))},
              'returned_native_object':returned,'scope':'Bounded four-splat SH3 native PointCloud to fork X3D4.1 and back, with matching identity-axis export settings. Schema and native X_ITE pixels are separate checks.'}
    blend=args.output/'native53-controls.blend'
    named_snapshots={o.name:snapshot(o) for o in bpy.context.scene.objects if o.type=='POINTCLOUD'}
    bpy.ops.wm.save_as_mainfile(filepath=str(blend.resolve()))
    bpy.ops.wm.open_mainfile(filepath=str(blend.resolve()))
    reopened={name:snapshot(bpy.data.objects[name]) for name in named_snapshots}
    reopened_errors={name:max((maxdiff(a['values'],reopened[name]['attributes'].get(key,{}).get('values') or [])
        for key,a in snap['attributes'].items() if a['values'] is not None),default=0.) for name,snap in named_snapshots.items()}
    need(max(reopened_errors.values())==0.,'Native attributes changed after blend save/reopen')
    receipt={'schema':'scivis.native53-probe/1','status':'pass','created_utc':datetime.now(timezone.utc).isoformat(),
        'blender_version':bpy.app.version_string,'blender_build_hash':bpy.app.build_hash.decode(),
        'status_meaning':'The bounded probe executed and its declared mapping checks passed; inspect apply_transform.preservation_status for the deliberately tested loss.',
        'probe_source_sha256':sha(__file__),'fixture_sha256':sha(ply),'fixture_vertex_count':4,'fixture_max_sh_degree':3,
        'fixture_payload_float32_bytes':4*62*4,'fixture_header_bytes':len(header),'fixture_rows_float32':rows,
        'pointcloud_type_enum':[i.identifier for i in bpy.types.PointCloud.bl_rna.properties['type'].enum_items],
        'native_import_result':imported,'native_snapshot':snap,'answers':answers,
        'actual_position_mutation_caught':bad,'apply_transform':transform,'fork_roundtrip':fork,
        'blend_sha256':sha(blend),'save_reopen_attribute_errors':reopened_errors,
        'scope':'Executed native Blender5.3.0 four-splat SH3 data/mapping probe; not a corpus or performance benchmark, nor proof of pixels, physics or general conformance.'}
    (args.output/'native53-result.json').write_text(json.dumps(receipt,indent=2,allow_nan=False)+'\n')
    print(json.dumps({'status':receipt['status'],'version':receipt['blender_version'],'Q1_raw_error':answers['Q1_base_xyz_raw_dc_max_error'],
        'Q1_rgb_error':answers['Q1_base_xyz_reconstructed_rgb_max_error'],'Q5_max_sh_error':max(v['max_abs_error'] for v in sh),
        'apply_transform_covariance_change':transform['world_covariance_max_abs_change'],'fork_status':fork['status']}))


if __name__=='__main__':main()
