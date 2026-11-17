"""Owned, measured Blender adapter for Research Loom scientific geometry.

The public helpers import no bpy. Blender functions import it lazily. A transfer
is a frame geometry round trip, not a reconstruction of the scientific solver.
"""
from __future__ import annotations

import copy
import base64
import hashlib
import json
import math
from pathlib import Path
import zlib

ADAPTER = "stemloom.blender-frame/1"
SCIENCE_COLLECTION = "ResearchLoom_Science"
DECORATION_COLLECTION = "ResearchLoom_Presentation"
COLOR_LAYER = "stemloom_color"


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, allow_nan=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def encode_source(packet):
    """Bound line length before Blender Text insertion; avoid quadratic long-line writes."""
    raw = canonical(packet).encode('utf-8')
    encoded = base64.b85encode(zlib.compress(raw, 9)).decode('ascii')
    return json.dumps({'encoding': 'stemloom.zlib-base85/1',
                       'decoded_sha256': hashlib.sha256(raw).hexdigest(),
                       'decoded_bytes': len(raw),
                       'chunks': [encoded[i:i+96] for i in range(0,len(encoded),96)]}, indent=2)


def decode_source(text):
    envelope = json.loads(text)
    if envelope.get('encoding') != 'stemloom.zlib-base85/1':
        return envelope  # Legacy owned scenes stored a plain JSON packet.
    size = envelope['decoded_bytes']
    if isinstance(size, bool) or not isinstance(size, int) or not 0 <= size <= 64*1024*1024:
        raise ValueError('Retained source exceeds the case byte budget')
    inflater = zlib.decompressobj()
    raw = inflater.decompress(base64.b85decode(''.join(envelope['chunks'])), size+1)
    if not inflater.eof or inflater.unused_data or inflater.unconsumed_tail:
        raise ValueError('Invalid compressed source packet framing')
    if len(raw) != envelope['decoded_bytes'] or hashlib.sha256(raw).hexdigest() != envelope['decoded_sha256']:
        raise ValueError('Retained source packet is corrupt')
    return json.loads(raw)


def to_blender(p):
    """A proper +90 degree X rotation, determinant +1; Y-up becomes Z-up."""
    return [float(p[0]), -float(p[2]), float(p[1])]


def from_blender(p):
    return [float(p[0]), float(p[2]), -float(p[1])]


def srgb_to_linear(value):
    return value/12.92 if value <= .04045 else ((value+.055)/1.055)**2.4


def linear_to_srgb(value):
    return 12.92*value if value <= .0031308 else 1.055*value**(1/2.4)-.055


def validate_frame(frame):
    if not isinstance(frame, dict):
        raise ValueError("A frame object is required")
    ids = set()
    count = 0
    for kind in ("meshes", "lines", "points"):
        for record in frame.get(kind, []):
            name = record.get("id")
            if not isinstance(name, str) or not name or name in ids:
                raise ValueError("Geometry IDs must be nonempty and unique")
            ids.add(name)
            positions = record.get("positions", [])
            if not positions or any(len(p) != 3 or any(isinstance(v, bool) or
                    not isinstance(v, (int, float)) or not math.isfinite(v) for v in p)
                    for p in positions):
                raise ValueError("Geometry requires finite three-dimensional positions")
            count += len(positions)
            if kind == "lines" and len(positions) < 2:
                raise ValueError("A line needs at least two positions")
            color = record.get("color", [.7, .8, .9])
            colors = record.get("colors", [color] * len(positions))
            if len(colors) != len(positions) or any(len(c) != 3 or
                    any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) or
                        not 0 <= v <= 1 for v in c) for c in colors):
                raise ValueError("Colors must be RGB values in [0,1], one per position")
            opacity = record.get("opacity", 1.)
            if isinstance(opacity, bool) or not isinstance(opacity, (int, float)) or not math.isfinite(opacity) or not 0 <= opacity <= 1:
                raise ValueError("Opacity must lie in [0,1]")
            radius = record.get("radius", .012 if kind == "lines" else .035)
            if isinstance(radius, bool) or not isinstance(radius, (int, float)) or not math.isfinite(radius) or radius <= 0:
                raise ValueError("Glyph radius must be finite and positive")
            for face in record.get("faces", []):
                if len(face) < 3 or any(isinstance(i, bool) or not isinstance(i, int)
                                       or not 0 <= i < len(positions) for i in face):
                    raise ValueError("Face indices must reference existing positions")
    if count > 30_000 or len(ids) > 250:
        raise ValueError("Frame exceeds the declared scientific geometry budget")
    return frame


def compare_frames(expected, actual, tolerance=3e-6):
    """Compare measured coordinates, topology, color, radii and record identity."""
    worst = 0.; color_worst = 0.; records = 0; positions = 0
    issues = []
    for kind in ("meshes", "lines", "points"):
        left = {r["id"]: r for r in expected.get(kind, [])}
        right = {r["id"]: r for r in actual.get(kind, [])}
        if left.keys() != right.keys():
            issues.append(kind + ": record identity mismatch")
            continue
        for name, a in left.items():
            b = right[name]; records += 1
            if len(a["positions"]) != len(b["positions"]):
                issues.append(name + ": position count mismatch"); continue
            positions += len(a["positions"])
            for p, q in zip(a["positions"], b["positions"]):
                worst = max(worst, *(abs(x-y) for x, y in zip(p, q)))
            if a.get("faces", []) != b.get("faces", []):
                issues.append(name + ": connectivity mismatch")
            ac = a.get("colors", [a.get("color", [.7, .8, .9])] * len(a["positions"]))
            bc = b.get("colors", [b.get("color", [.7, .8, .9])] * len(b["positions"]))
            for p, q in zip(ac, bc):
                color_worst = max(color_worst, *(abs(x-y) for x, y in zip(p, q)))
            for key, default in (("opacity", 1.), ("radius", .012 if kind == "lines" else .035)):
                if abs(a.get(key, default)-b.get(key, default)) > tolerance:
                    issues.append(name + ": " + key + " mismatch")
    return {"status": "pass" if not issues and worst <= tolerance and color_worst <= tolerance else "fail",
            "records": records, "scientific_positions": positions,
            "max_coordinate_absolute_difference": worst, "max_color_absolute_difference": color_worst,
            "absolute_tolerance": tolerance, "issues": issues,
            "scope": "Selected frame geometry, retained scalar appearance and record IDs. No solver or imported domain variables are recomputed."}


def _collection(name):
    import bpy
    collection = bpy.data.collections.get(name)
    if collection is None:
        collection = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(collection)
    return collection


def _material(name, opacity=1.):
    import bpy
    material = bpy.data.materials.new(name)
    material.use_nodes = True
    nodes = material.node_tree.nodes
    principled = nodes.get("Principled BSDF")
    attr = nodes.new("ShaderNodeVertexColor"); attr.layer_name = COLOR_LAYER
    material.node_tree.links.new(attr.outputs["Color"], principled.inputs["Base Color"])
    principled.inputs["Metallic"].default_value = .12
    principled.inputs["Roughness"].default_value = .28
    principled.inputs["Alpha"].default_value = opacity
    # Thin scientific glyphs remain legible in the authored studio lighting.
    if "Emission Color" in principled.inputs:
        material.node_tree.links.new(attr.outputs["Color"], principled.inputs["Emission Color"])
        principled.inputs["Emission Strength"].default_value = .045
    if hasattr(material, "surface_render_method"):
        material.surface_render_method = 'DITHERED'
    material.diffuse_color = (.45, .7, .8, opacity)
    return material


def _tube(positions, radius, sides=8):
    from mathutils import Vector
    vertices = []; faces = []
    for i, position in enumerate(positions):
        p = Vector(position)
        tangent = Vector(positions[min(i+1, len(positions)-1)])-Vector(positions[max(0, i-1)])
        if tangent.length < 1e-12:
            tangent = Vector((1, 0, 0))
        tangent.normalize()
        reference = Vector((0, 0, 1)) if abs(tangent.z) < .9 else Vector((0, 1, 0))
        normal = tangent.cross(reference).normalized(); binormal = tangent.cross(normal).normalized()
        for j in range(sides):
            angle = 2*math.pi*j/sides
            vertices.append(list(p+radius*(math.cos(angle)*normal+math.sin(angle)*binormal)))
        if i:
            for j in range(sides):
                a = (i-1)*sides+j; b = (i-1)*sides+(j+1) % sides
                c = i*sides+(j+1) % sides; d = i*sides+j
                faces.append([a, b, c, d])
    return vertices, faces, sides


def _point_glyphs(positions, radius):
    import bmesh
    bm = bmesh.new(); bmesh.ops.create_icosphere(bm, subdivisions=2, radius=1.)
    bm.verts.ensure_lookup_table()
    template = [list(v.co) for v in bm.verts]
    index = {v: i for i, v in enumerate(bm.verts)}
    faces = [[index[v] for v in f.verts] for f in bm.faces]
    bm.free()
    vertices = []; result_faces = []
    for p in positions:
        offset = len(vertices)
        vertices.extend([[p[j]+radius*q[j] for j in range(3)] for q in template])
        result_faces.extend([[offset+i for i in face] for face in faces])
    return vertices, result_faces, len(template)


def import_case(packet, frame_index=0, clear=True):
    """Create owned science meshes; line tubes and point glyphs retain grouping."""
    import bpy
    frame = validate_frame(packet["frames"][frame_index])
    if clear:
        for obj in list(bpy.data.objects):
            bpy.data.objects.remove(obj, do_unlink=True)
    collection = _collection(SCIENCE_COLLECTION)
    source_hash = digest(packet)
    for kind in ("meshes", "lines", "points"):
        for record in frame.get(kind, []):
            positions = [to_blender(p) for p in record["positions"]]
            if kind == "meshes":
                vertices, faces, stride = positions, record["faces"], 1
            elif kind == "lines":
                vertices, faces, stride = _tube(positions, record.get("radius", .012))
            else:
                vertices, faces, stride = _point_glyphs(positions, record.get("radius", .035))
            mesh = bpy.data.meshes.new(record["id"] + "_geometry")
            mesh.from_pydata(vertices, [], faces); mesh.update()
            colors = record.get("colors", [record.get("color", [.7, .8, .9])] * len(positions))
            attribute = mesh.color_attributes.new(name=COLOR_LAYER, type='FLOAT_COLOR', domain='POINT')
            # Convert explicitly: Blender's color_srgb convenience accessor
            # uses a fast approximation that measured ~3.5e-5 on a control.
            # The piecewise sRGB transfer below retains float32-level error.
            for i, datum in enumerate(attribute.data):
                datum.color = (*[srgb_to_linear(c) for c in colors[i//stride]], 1.)
            obj = bpy.data.objects.new(record["id"], mesh); collection.objects.link(obj)
            mesh.materials.append(_material(record["id"] + "_appearance", record.get("opacity", 1.)))
            for polygon in mesh.polygons:
                polygon.use_smooth = True
            obj["stemloom_kind"] = kind
            obj["stemloom_id"] = record["id"]
            obj["stemloom_stride"] = stride
            obj["stemloom_source_count"] = len(positions)
            obj["stemloom_source_faces"] = canonical(record.get("faces", []))
            obj["stemloom_appearance"] = canonical({k: record[k] for k in ("color", "opacity", "radius") if k in record})
            obj["stemloom_source_packet_sha256"] = source_hash
    scene = bpy.context.scene
    scene["stemloom_adapter"] = ADAPTER
    scene["stemloom_frame_index"] = frame_index
    scene["stemloom_packet_sha256"] = source_hash
    text = bpy.data.texts.get("ResearchLoom_Source.json") or bpy.data.texts.new("ResearchLoom_Source.json")
    text.clear(); text.write(encode_source(packet))
    return {"source_packet_sha256": source_hash, "case_id": packet.get("id"),
            "frame_index": frame_index, "time": frame.get("time", 0),
            "scientific_objects": len(collection.objects)}


def export_case():
    """Read actual owned scientific geometry, not the retained source positions."""
    import bpy
    scene = bpy.context.scene
    if scene.get("stemloom_adapter") != ADAPTER:
        raise ValueError("The active scene is not an owned Research Loom transfer")
    source = decode_source(bpy.data.texts["ResearchLoom_Source.json"].as_string())
    frame_index = int(scene["stemloom_frame_index"])
    old = source["frames"][frame_index]
    frame = {"time": old.get("time", 0), "metrics": copy.deepcopy(old.get("metrics", [])),
             "meshes": [], "lines": [], "points": []}
    collection = bpy.data.collections.get(SCIENCE_COLLECTION)
    if collection is None:
        raise ValueError("Scientific collection was removed")
    for obj in collection.objects:
        kind = obj.get("stemloom_kind")
        if kind not in ("meshes", "lines", "points") or obj.type != 'MESH':
            raise ValueError("Unsupported object in scientific collection: " + obj.name)
        if obj.modifiers:
            raise ValueError("Apply or remove modifiers before a measured owned-subset export")
        stride = int(obj["stemloom_stride"]); count = int(obj["stemloom_source_count"])
        if len(obj.data.vertices) != stride*count:
            raise ValueError("Edited topology changed scientific vertex/glyph grouping: " + obj.name)
        positions = []
        for i in range(count):
            ring = [obj.matrix_world @ obj.data.vertices[i*stride+j].co for j in range(stride)]
            positions.append(from_blender([math.fsum(v[a] for v in ring)/stride for a in range(3)]))
        attribute = obj.data.color_attributes.get(COLOR_LAYER)
        if attribute is None or attribute.domain != 'POINT':
            raise ValueError("Scientific point-color attribute is missing: " + obj.name)
        colors = [[max(0., min(1., linear_to_srgb(math.fsum(
                   attribute.data[i*stride+j].color[a] for j in range(stride))/stride)))
                   for a in range(3)] for i in range(count)]
        record = {"id": obj["stemloom_id"], "positions": positions, "colors": colors,
                  **json.loads(obj["stemloom_appearance"])}
        if obj.data.materials:
            principled = obj.data.materials[0].node_tree.nodes.get('Principled BSDF')
            if principled is None or not principled.inputs['Base Color'].is_linked:
                raise ValueError('Owned vertex-color material was replaced: '+obj.name)
            record['opacity'] = float(principled.inputs['Alpha'].default_value)
        if kind != 'meshes':
            scale = [obj.matrix_world.to_3x3().col[i].length for i in range(3)]
            if max(scale)-min(scale) > 1e-6:
                raise ValueError('Nonuniform glyph scaling is outside the circular-radius export subset: '+obj.name)
            if 'radius' in record:
                record['radius'] *= sum(scale)/3
        if kind == "meshes":
            record["faces"] = [list(p.vertices) for p in obj.data.polygons]
        frame[kind].append(record)
    validate_frame(frame)
    result = copy.deepcopy(source)
    result["frames"] = [frame]
    result["source_frame_index"] = frame_index
    result["transfer"] = {"adapter": ADAPTER, "source_packet_sha256": scene["stemloom_packet_sha256"],
                          "coordinate_map": "X3D(x,y,z) -> Blender(x,-z,y)",
                          "scope": "Selected actual geometry and appearance. Historical measurements/witnesses are retained provenance, not recomputed evidence for edits."}
    return result


def save_json(path, value):
    path = Path(path); path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False, allow_nan=False) + "\n")
