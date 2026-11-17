#!/usr/bin/env python3
"""Render a saved scientific frame with an explicitly authored Blender studio.

Run inside Blender, e.g. blender -b -t 2 --python tools/render_blender.py --
  --packet cases/tensor-correlated.json --frame 4 --output docs/tensor.png
  --output-blend exports/tensor.blend --receipt evidence/blender-render-tensor.json
"""
from __future__ import annotations
import argparse
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from stemloom.blender_io import (DECORATION_COLLECTION, SCIENCE_COLLECTION,
                                digest, import_case, save_json)


def main():
    import bpy
    from mathutils import Vector
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--packet', type=Path, required=True)
    parser.add_argument('--frame', type=int, default=0)
    parser.add_argument('--output', type=Path, required=True)
    parser.add_argument('--output-blend', type=Path)
    parser.add_argument('--receipt', type=Path, required=True)
    parser.add_argument('--width', type=int, default=1280)
    parser.add_argument('--height', type=int, default=960)
    parser.add_argument('--samples', type=int, default=32)
    args = parser.parse_args(sys.argv[sys.argv.index('--')+1:] if '--' in sys.argv else [])
    if not (256 <= args.width <= 4096 and 256 <= args.height <= 4096 and 8 <= args.samples <= 256):
        raise ValueError('Render dimensions or sample budget outside the declared range')
    packet = json.loads(args.packet.read_text()); state = import_case(packet, args.frame)
    scene = bpy.context.scene
    presentation = bpy.data.collections.new(DECORATION_COLLECTION)
    scene.collection.children.link(presentation)

    def present(obj):
        for collection in list(obj.users_collection):
            collection.objects.unlink(obj)
        presentation.objects.link(obj)
        return obj

    all_points = [obj.matrix_world @ vertex.co for obj in bpy.data.collections[SCIENCE_COLLECTION].objects
                  for vertex in obj.data.vertices]
    lower = Vector([min(p[j] for p in all_points) for j in range(3)])
    upper = Vector([max(p[j] for p in all_points) for j in range(3)])
    center = (lower+upper)/2
    span = max((upper-lower).length, .1)
    radius = span/2
    # Factory startup need not auto-enable the packaged Cycles add-on.
    bpy.ops.preferences.addon_enable(module='cycles')
    scene.render.engine = 'CYCLES'
    scene.cycles.device = 'CPU'
    scene.cycles.samples = args.samples
    scene.cycles.use_denoising = True
    scene.cycles.seed = 82417
    scene.cycles.adaptive_threshold = .04
    scene.cycles.max_bounces = 8
    scene.cycles.transparent_max_bounces = 12
    scene.render.resolution_x = args.width; scene.render.resolution_y = args.height
    scene.render.resolution_percentage = 100
    scene.render.image_settings.file_format = 'PNG'
    scene.render.image_settings.color_mode = 'RGBA'
    scene.render.film_transparent = False
    scene.render.threads_mode = 'FIXED'; scene.render.threads = 2
    scene.view_settings.view_transform = 'Standard'
    scene.view_settings.look = 'None'
    scene.view_settings.exposure = 0; scene.view_settings.gamma = 1
    world = bpy.data.worlds.new('ResearchLoom_StudioWorld')
    world.use_nodes = True
    world.node_tree.nodes['Background'].inputs['Color'].default_value = (.028, .05, .08, 1)
    world.node_tree.nodes['Background'].inputs['Strength'].default_value = .15
    scene.world = world

    bpy.ops.mesh.primitive_plane_add(size=span*20, location=(center.x, center.y, lower.z-radius*.12))
    floor = present(bpy.context.object); floor.name = 'Presentation floor (not scientific data)'
    material = bpy.data.materials.new('Midnight ceramic studio')
    material.use_nodes = True
    principled = material.node_tree.nodes.get('Principled BSDF')
    principled.inputs['Base Color'].default_value = (.009, .02, .033, 1)
    principled.inputs['Roughness'].default_value = .32
    principled.inputs['Metallic'].default_value = .25
    floor.data.materials.append(material)

    def light(name, relative, energy, color, size):
        data = bpy.data.lights.new(name, 'AREA'); data.energy = energy; data.color = color
        data.shape = 'DISK'; data.size = size
        obj = bpy.data.objects.new(name, data); presentation.objects.link(obj)
        obj.location = center+Vector(relative)*radius
        obj.rotation_euler = (center-obj.location).to_track_quat('-Z', 'Y').to_euler()

    light('Warm key / authored appearance', (1.2, -1.2, 2.4), 35*span*span, (1., .89, .77), span*1.2)
    light('Cool rim / authored appearance', (-1.5, .5, 1.1), 25*span*span, (.35, .72, 1.), span*.8)
    light('Soft fill / authored appearance', (.4, 1.5, .8), 14*span*span, (.7, 1., .9), span)
    camera_data = bpy.data.cameras.new('Research Loom editorial camera')
    camera = bpy.data.objects.new('Research Loom editorial camera', camera_data)
    presentation.objects.link(camera)
    direction = Vector((1.2, -1.7, 1.05)).normalized()
    camera.location = center+direction*span*2.6
    camera.rotation_euler = (center-camera.location).to_track_quat('-Z', 'Y').to_euler()
    camera_data.type = 'ORTHO'
    aspect = args.width/args.height
    # Fit the actual projected geometry in both image dimensions. A 3-D bounds
    # diagonal divided by aspect can clip long membrane/covariance views.
    rotation = camera.rotation_euler.to_quaternion()
    right, up = rotation @ Vector((1,0,0)), rotation @ Vector((0,1,0))
    xx = [(p-center).dot(right) for p in all_points]
    yy = [(p-center).dot(up) for p in all_points]
    center += right*((min(xx)+max(xx))/2)+up*((min(yy)+max(yy))/2)
    camera.location = center+direction*span*2.6
    camera_data.ortho_scale = max(max(xx)-min(xx), (max(yy)-min(yy))*aspect, .1)*1.15
    camera_data.lens = 45; camera_data.clip_end = max(1000., span*20)
    scene.camera = camera
    scene['stemloom_render_scope'] = 'Tier C authored studio render of one measured saved frame; no claim of browser-identical pixels.'
    args.output.parent.mkdir(parents=True, exist_ok=True)
    scene.render.filepath = str(args.output.resolve())
    if args.output_blend:
        args.output_blend.parent.mkdir(parents=True, exist_ok=True)
        bpy.ops.wm.save_as_mainfile(filepath=str(args.output_blend.resolve()))
    started = time.perf_counter(); bpy.ops.render.render(write_still=True); elapsed = time.perf_counter()-started
    raw = args.output.read_bytes()
    if not raw.startswith(b'\x89PNG\r\n\x1a\n'):
        raise RuntimeError('Rendered output is not a PNG')
    receipt = {'schema': 'stemloom.blender-render/1', 'status': 'pass',
               'created_utc': datetime.now(timezone.utc).isoformat(), 'blender_version': bpy.app.version_string,
               'engine': 'Cycles', 'device': 'CPU', 'threads': 2, 'samples': args.samples,
               'width': args.width, 'height': args.height, 'elapsed_seconds': elapsed,
               'image_sha256': hashlib.sha256(raw).hexdigest(), 'image_bytes': len(raw),
               'packet_sha256': digest(packet), **state,
               'frame_sha256': digest(packet['frames'][args.frame]),
               'camera': {'projection': 'orthographic', 'scale': camera_data.ortho_scale,
                          'location': list(camera.location), 'rotation_euler': list(camera.rotation_euler)},
               'sampling_seed': scene.cycles.seed,
               'adapter_sha256': hashlib.sha256((ROOT/'stemloom/blender_io.py').read_bytes()).hexdigest(),
               'tool_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
               'appearance': 'Authored studio lights, Standard display transform, dark ceramic floor, vertex-color PBR, tube and point glyph radii.',
               'scientific_change': 'None: scientific object geometry is imported from the retained frame.',
               'scope': 'Offline Tier C still, not native X_ITE browser pixels, real-time frame rate, or GPU benchmark.'}
    save_json(args.receipt, receipt)
    print('RESEARCH_LOOM_RENDER', json.dumps(receipt, sort_keys=True))


if __name__ == '__main__':
    main()
