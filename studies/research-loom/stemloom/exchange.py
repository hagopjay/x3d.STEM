"""Bounded scientific geometry exchange, with explicit representation losses.

X3D import accepts this adapter's static, world-coordinate subset only. It never
executes scripts, follows URLs, or reconstructs a scientific solver from meshes.
All writers validate first. Binary64 numbers receive 17 significant digits;
X3D Coordinate is still an MFVec3f renderer boundary.
"""
from __future__ import annotations

import csv
import hashlib
import io
import json
import math
import re
import xml.etree.ElementTree as ET
from collections.abc import Mapping

ADAPTER = "stemloom.exchange/1"
MAX_BYTES = 32 * 1024 * 1024
MAX_POSITIONS = 30_000
MAX_FACES = 10_000
MAX_RECORDS = 250
MAX_ABS = 1e12
GROUPS = ("meshes", "lines", "points")


def canonical(value):
    try:
        return json.dumps(value, sort_keys=True, separators=(",", ":"),
                          ensure_ascii=False, allow_nan=False)
    except (TypeError, ValueError, OverflowError) as exc:
        raise ValueError("EXCHANGE_JSON: expected finite JSON data") from exc


def _number(value, label, lo=None, hi=MAX_ABS):
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError("EXCHANGE_NUMBER: " + label)
    try:
        value = float(value)
    except OverflowError as exc:
        raise ValueError("EXCHANGE_NUMBER: " + label) from exc
    if not math.isfinite(value) or abs(value) > hi or (lo is not None and value < lo):
        raise ValueError("EXCHANGE_RANGE: " + label)
    return value


def _vector(value, label, lo=None, hi=MAX_ABS):
    if not isinstance(value, (list, tuple)) or len(value) != 3:
        raise ValueError("EXCHANGE_VECTOR: " + label)
    return [_number(n, label, lo, hi) for n in value]


def _text(value, label, maximum=256):
    if not isinstance(value, str) or not value or len(value) > maximum:
        raise ValueError("EXCHANGE_TEXT: " + label)
    if any(not (ord(c) in (9, 10, 13) or 32 <= ord(c) <= 0xD7FF or
                0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise ValueError("EXCHANGE_XML_TEXT: " + label)
    return value


def _f(value):
    return "0" if value == 0 else format(float(value), ".17g")


def _nums(values):
    return " ".join(_f(x) for x in values)


def _mfstring(text):
    return json.dumps(text, ensure_ascii=False)


def _def(identity):
    return "RL_" + re.sub(r"[^A-Za-z0-9_]", "_", identity)


def validate_frame(frame):
    """Validate and normalize one frame without relying on Python assertions."""
    if not isinstance(frame, Mapping):
        raise ValueError("EXCHANGE_FRAME: expected object")
    result = {"time": _number(frame.get("time", 0), "time"), "metrics": frame.get("metrics", [])}
    ids, defs = set(), set()
    count = faces = records = 0
    for group in GROUPS:
        rows = frame.get(group, [])
        if not isinstance(rows, list):
            raise ValueError("EXCHANGE_GROUP: " + group)
        out = []
        for row in rows:
            records += 1
            if records > MAX_RECORDS or not isinstance(row, Mapping):
                raise ValueError("EXCHANGE_RECORD_BUDGET")
            identity = _text(row.get("id"), "id", 160)
            clean_def = _def(identity)
            if identity in ids or clean_def in defs:
                raise ValueError("EXCHANGE_DUPLICATE_ID: " + identity)
            ids.add(identity); defs.add(clean_def)
            positions = row.get("positions")
            minimum = {"meshes": 3, "lines": 2, "points": 1}[group]
            if not isinstance(positions, (list, tuple)) or len(positions) < minimum:
                raise ValueError("EXCHANGE_POSITIONS: " + identity)
            count += len(positions)
            if count > MAX_POSITIONS:
                raise ValueError("EXCHANGE_POSITION_BUDGET")
            item = {"id": identity,
                    "positions": [_vector(p, "position") for p in positions],
                    "color": _vector(row.get("color", [.4, .8, 1]), "color", 0, 1),
                    "opacity": _number(row.get("opacity", 1), "opacity", 0, 1)}
            if "colors" in row:
                colors = row["colors"]
                if not isinstance(colors, (list, tuple)) or len(colors) != len(positions):
                    raise ValueError("EXCHANGE_COLORS: one RGB per position")
                item["colors"] = [_vector(c, "colors", 0, 1) for c in colors]
            if "point_data" in row:
                arrays = row["point_data"]
                if not isinstance(arrays, Mapping) or len(arrays) > 16:
                    raise ValueError("EXCHANGE_POINT_DATA")
                item["point_data"] = {}
                for name, descriptor in arrays.items():
                    _text(name, "point data name", 80)
                    if not isinstance(descriptor, Mapping):
                        raise ValueError("EXCHANGE_POINT_DATA_DESCRIPTOR")
                    components = descriptor.get("components", 1)
                    values = descriptor.get("values")
                    if not isinstance(components, int) or isinstance(components, bool) or components not in (1, 3) or not isinstance(values, (list, tuple)) or len(values) != len(positions):
                        raise ValueError("EXCHANGE_POINT_DATA_SHAPE")
                    parsed = [_number(v, name) for v in values] if components == 1 else [_vector(v, name) for v in values]
                    units = descriptor.get("units", "unspecified")
                    _text(units, "point data units", 120)
                    item["point_data"][name] = {"values": parsed, "components": components, "units": units}
            if group == "meshes":
                polygons = row.get("faces")
                if not isinstance(polygons, (list, tuple)) or not polygons:
                    raise ValueError("EXCHANGE_FACES: " + identity)
                item["faces"] = []
                for face in polygons:
                    faces += 1
                    if faces > MAX_FACES or not isinstance(face, (list, tuple)) or not 3 <= len(face) <= 4:
                        raise ValueError("EXCHANGE_FACE_BUDGET: triangles or quads only")
                    if any(isinstance(i, bool) or not isinstance(i, int) or
                           not 0 <= i < len(positions) for i in face) or len(set(face)) != len(face):
                        raise ValueError("EXCHANGE_INDEX: " + identity)
                    item["faces"].append(list(face))
            else:
                item["radius"] = _number(row.get("radius", .012 if group == "lines" else .035), "radius", 0)
                if item["radius"] <= 0:
                    raise ValueError("EXCHANGE_RADIUS")
            out.append(item)
        result[group] = out
    if records == 0:
        raise ValueError("EXCHANGE_EMPTY_FRAME")
    canonical(result)
    return result


def _geometry_identity(frame):
    # X3D stores transparency=1-opacity. Normalize through that exact stored
    # representation so harmless complement roundoff is not labeled an edit.
    geometry = {}
    for group in GROUPS:
        geometry[group] = []
        for row in frame[group]:
            normalized = {k:v for k,v in row.items() if k not in ("point_data", "opacity")}
            normalized["transparency"] = 1-row["opacity"]
            geometry[group].append(normalized)
    return hashlib.sha256(canonical(geometry).encode()).hexdigest()


def _selected(case, frame_index):
    if not isinstance(case, Mapping) or not isinstance(case.get("frames"), list):
        raise ValueError("EXCHANGE_CASE: frames required")
    if isinstance(frame_index, bool) or not isinstance(frame_index, int) or not 0 <= frame_index < len(case["frames"]):
        raise ValueError("EXCHANGE_FRAME_INDEX")
    frame = validate_frame(case["frames"][frame_index])
    metadata = {"adapter": ADAPTER, "case_id": _text(case.get("id"), "case id", 160),
                "title": _text(case.get("title", case["id"]), "title", 256),
                "kind": case.get("kind", "scientific"), "frame_index": frame_index,
                "time": frame["time"], "units": case.get("units", {}),
                "axes": case.get("axes", ""), "scope": case.get("scope", ""),
                "frame_sha256": hashlib.sha256(canonical(frame).encode()).hexdigest(),
                "geometry_sha256": _geometry_identity(frame),
                "case_sha256": hashlib.sha256(canonical(case).encode()).hexdigest(),
                "coordinates": "right-handed Y-up; no implicit unit normalization"}
    if len(canonical(metadata).encode()) > 65_536:
        raise ValueError("EXCHANGE_METADATA_BUDGET")
    return frame, metadata


def _bounds(frame):
    all_points = [p for group in GROUPS for row in frame[group] for p in row["positions"]]
    lower = [min(p[i] for p in all_points) for i in range(3)]
    upper = [max(p[i] for p in all_points) for i in range(3)]
    center = [(a+b)/2 for a,b in zip(lower, upper)]
    size = [max(b-a, .2) for a,b in zip(lower, upper)]
    radius = math.sqrt(sum(x*x for x in size))/2
    return center, size, max(radius, .5)


def to_x3d(case, frame_index=0, version="4.0"):
    """Write native X3D 4.0 or a portable 3.3 static geometry projection."""
    if version not in ("4.0", "3.3"):
        raise ValueError("EXCHANGE_X3D_VERSION")
    frame, metadata = _selected(case, frame_index)
    root = ET.Element("X3D", profile="Interchange", version=version)
    head = ET.SubElement(root, "head")
    ET.SubElement(head, "meta", name="title", content=metadata["title"])
    ET.SubElement(head, "meta", name="generator", content=ADAPTER)
    scene = ET.SubElement(root, "Scene")
    info = ET.SubElement(scene, "WorldInfo", title=metadata["title"])
    ET.SubElement(info, "MetadataString", name="stemloom_case", containerField="metadata",
                  value=_mfstring(canonical(metadata)))
    ET.SubElement(scene, "Background", skyColor="0.018 0.029 0.055")
    ET.SubElement(scene, "NavigationInfo", type='"EXAMINE" "ANY"', headlight="true")
    # Use one camera envelope for the complete saved bank. Frame selection
    # changes scientific state without silently changing viewing scale.
    envelope = {group: [] for group in GROUPS}
    for source_frame in case["frames"]:
        normalized = validate_frame(source_frame)
        for group in GROUPS:
            envelope[group].extend(normalized[group])
    center, size, radius = _bounds(envelope)
    unit = [.38, .28, 1.]
    norm = math.sqrt(sum(x*x for x in unit)); unit = [x/norm for x in unit]
    distance = radius/math.sin(.32)*1.12
    axis = [-unit[1], unit[0], 0]; an = math.hypot(*axis[:2])
    ET.SubElement(scene, "Viewpoint", DEF="ResearchLoomView", description="Research Loom overview",
                  position=_nums([center[i]+distance*unit[i] for i in range(3)]),
                  centerOfRotation=_nums(center), fieldOfView="0.64",
                  orientation=_nums([axis[0]/an, axis[1]/an, 0, math.acos(unit[2])]))
    ET.SubElement(scene, "DirectionalLight", direction="-0.4 -0.8 -1", intensity="0.85", color="0.78 0.89 1")
    ET.SubElement(scene, "DirectionalLight", direction="0.5 0.4 0.8", intensity="0.45", color="1 0.73 0.48")
    group_node = ET.SubElement(scene, "Group", DEF="ResearchLoomGeometry")
    for group in GROUPS:
        for row in frame[group]:
            shape = ET.SubElement(group_node, "Shape", DEF=_def(row["id"]))
            item_meta = {"id": row["id"], "source_kind": group, "color": row["color"]}
            if "radius" in row:
                item_meta["radius"] = row["radius"]
            ET.SubElement(shape, "MetadataString", name="stemloom_geometry", containerField="metadata",
                          value=_mfstring(canonical(item_meta)))
            appearance = ET.SubElement(shape, "Appearance")
            line = group != "meshes"
            ET.SubElement(appearance, "Material", diffuseColor=_nums(row["color"]),
                          emissiveColor=_nums([v*(.65 if line else .025) for v in row["color"]]),
                          specularColor="0.32 0.36 0.42", shininess="0.45",
                          transparency=_f(1-row["opacity"]))
            if group == "meshes":
                indices = " ".join(" ".join(str(i) for i in face)+" -1" for face in row["faces"])
                geometry = ET.SubElement(shape, "IndexedFaceSet", coordIndex=indices, solid="false",
                                          colorPerVertex="true", creaseAngle="0.7")
            elif group == "lines":
                geometry = ET.SubElement(shape, "IndexedLineSet", coordIndex=" ".join(map(str, range(len(row["positions"]))))+" -1",
                                          colorPerVertex="true")
            else:
                geometry = ET.SubElement(shape, "PointSet")
            ET.SubElement(geometry, "Coordinate", point=" ".join(_nums(p) for p in row["positions"]))
            if "colors" in row:
                ET.SubElement(geometry, "Color", color=" ".join(_nums(c) for c in row["colors"]))
    ET.indent(root, space="  ")
    text = '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root, encoding="unicode")+'\n'
    if len(text.encode()) > MAX_BYTES:
        raise ValueError("EXCHANGE_BYTE_BUDGET")
    return text


def _parse_numbers(text, label, vector=False, integer=False):
    try:
        words = (text or "").replace(",", " ").split()
        values = [int(x) if integer else float(x) for x in words]
    except (ValueError, TypeError, OverflowError) as exc:
        raise ValueError("EXCHANGE_PARSE: " + label) from exc
    if len(values) > 150_000:
        raise ValueError("EXCHANGE_ARRAY_BUDGET")
    if not integer and any(not math.isfinite(x) or abs(x) > MAX_ABS for x in values):
        raise ValueError("EXCHANGE_PARSE_RANGE: " + label)
    if vector:
        if len(values) % 3:
            raise ValueError("EXCHANGE_PARSE_VECTOR: " + label)
        return [values[i:i+3] for i in range(0, len(values), 3)]
    return values


def _unique_pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("Duplicate JSON metadata key")
        result[key] = value
    return result


def _metadata(node, name):
    records = [n for n in node.findall("MetadataString") if n.get("name") == name]
    if len(records) != 1:
        raise ValueError("EXCHANGE_METADATA_RECORD: " + name)
    try:
        encoded = records[0].get("value", "")
        if len(encoded.encode()) > 65_536:
            raise ValueError("Metadata exceeds its budget")
        raw = json.loads(encoded, object_pairs_hook=_unique_pairs)
        if not isinstance(raw, str):
            raise ValueError("MFString must contain one item")
        obj = json.loads(raw, object_pairs_hook=_unique_pairs)
        if not isinstance(obj, dict):
            raise ValueError("Object required")
        canonical(obj)
        return obj
    except (ValueError, TypeError, RecursionError) as exc:
        raise ValueError("EXCHANGE_METADATA_PARSE: " + name) from exc


def from_x3d(text):
    """Read this adapter's static subset from geometry, never from cached coordinates.

    The declared hash is provenance, not authentication. Edited valid coordinates
    are returned as edited coordinates and marked by a reconstructed frame hash.
    """
    if not isinstance(text, str) or not 1 <= len(text.encode()) <= MAX_BYTES:
        raise ValueError("EXCHANGE_XML_BYTE_BUDGET")
    if re.search(r"<!\s*(?:DOCTYPE|ENTITY)\b", text, re.I):
        raise ValueError("EXCHANGE_XML_DECLARATION_REFUSED")
    try:
        root = ET.fromstring(text)
    except (ET.ParseError, RecursionError) as exc:
        raise ValueError("EXCHANGE_XML_PARSE") from exc
    allowed = {"X3D", "head", "meta", "Scene", "WorldInfo", "MetadataString", "Background",
               "NavigationInfo", "Viewpoint", "DirectionalLight", "Group", "Shape", "Appearance",
               "Material", "IndexedFaceSet", "IndexedLineSet", "PointSet", "Coordinate", "Color"}
    children = {"X3D": {"head", "Scene"}, "head": {"meta"},
                "Scene": {"WorldInfo", "Background", "NavigationInfo", "Viewpoint", "DirectionalLight", "Group"},
                "WorldInfo": {"MetadataString"}, "Group": {"Shape"},
                "Shape": {"MetadataString", "Appearance", "IndexedFaceSet", "IndexedLineSet", "PointSet"},
                "Appearance": {"Material"}, "IndexedFaceSet": {"Coordinate", "Color"},
                "IndexedLineSet": {"Coordinate", "Color"}, "PointSet": {"Coordinate", "Color"}}
    attributes = {"X3D": {"profile", "version"}, "meta": {"name", "content"},
                  "WorldInfo": {"title"}, "MetadataString": {"name", "containerField", "value"},
                  "Background": {"skyColor"}, "NavigationInfo": {"type", "headlight"},
                  "Viewpoint": {"DEF", "description", "position", "centerOfRotation", "fieldOfView", "orientation"},
                  "DirectionalLight": {"direction", "intensity", "color"}, "Group": {"DEF"}, "Shape": {"DEF"},
                  "Material": {"diffuseColor", "emissiveColor", "specularColor", "shininess", "transparency"},
                  "IndexedFaceSet": {"coordIndex", "solid", "colorPerVertex", "creaseAngle"},
                  "IndexedLineSet": {"coordIndex", "colorPerVertex"}, "Coordinate": {"point"}, "Color": {"color"}}
    stack = [(root, 0)]; count = 0
    while stack:
        node, depth = stack.pop(); count += 1
        if depth > 12 or count > 10_000 or node.tag not in allowed:
            raise ValueError("EXCHANGE_XML_SUBSET: " + str(node.tag))
        if any(key not in attributes.get(node.tag, set()) for key in node.attrib):
            raise ValueError("EXCHANGE_XML_ATTRIBUTE_SUBSET: " + str(node.tag))
        if any(child.tag not in children.get(node.tag, set()) for child in node):
            raise ValueError("EXCHANGE_XML_STRUCTURE_SUBSET: " + str(node.tag))
        stack.extend((child, depth+1) for child in node)
    if root.tag != "X3D" or root.get("version") not in ("3.3", "4.0") or root.get("profile") != "Interchange":
        raise ValueError("EXCHANGE_XML_ROOT")
    scenes = root.findall("Scene")
    if len(scenes) != 1:
        raise ValueError("EXCHANGE_XML_SCENE")
    scene = scenes[0]; info = scene.findall("WorldInfo")
    if len(scene.findall("Group")) != 1:
        raise ValueError("EXCHANGE_XML_GROUP_COUNT")
    if len(info) != 1:
        raise ValueError("EXCHANGE_XML_WORLDINFO")
    metadata = _metadata(info[0], "stemloom_case")
    if metadata.get("adapter") != ADAPTER:
        raise ValueError("EXCHANGE_XML_ADAPTER")
    frame = {"time": metadata.get("time"), "meshes": [], "lines": [], "points": [], "metrics": []}
    all_shapes = scene.findall(".//Shape")
    direct_shapes = scene.findall("./Group/Shape")
    if len(all_shapes) != len(direct_shapes):
        raise ValueError("EXCHANGE_XML_GROUPING")
    for shape in direct_shapes:
        item = _metadata(shape, "stemloom_geometry")
        group = item.get("source_kind")
        tag = {"meshes": "IndexedFaceSet", "lines": "IndexedLineSet", "points": "PointSet"}.get(group)
        if tag is None:
            raise ValueError("EXCHANGE_XML_GEOMETRY_KIND")
        geometries = [n for n in shape if n.tag in ("IndexedFaceSet", "IndexedLineSet", "PointSet")]
        if len(geometries) != 1 or geometries[0].tag != tag:
            raise ValueError("EXCHANGE_XML_GEOMETRY_COUNT")
        geometry = geometries[0]
        coordinates = geometry.findall("Coordinate")
        if len(coordinates) != 1:
            raise ValueError("EXCHANGE_XML_COORDINATE")
        row = {"id": item.get("id"), "positions": _parse_numbers(coordinates[0].get("point"), "positions", True),
               "color": item.get("color"), "opacity": 1.}
        materials = shape.findall("./Appearance/Material")
        if len(materials) != 1:
            raise ValueError("EXCHANGE_XML_MATERIAL")
        row["color"] = _parse_numbers(materials[0].get("diffuseColor"), "diffuseColor")
        row["opacity"] = 1-_number(float(materials[0].get("transparency", "0")), "transparency", 0, 1)
        colors = geometry.findall("Color")
        if len(colors) > 1:
            raise ValueError("EXCHANGE_XML_COLOR_COUNT")
        if colors:
            if geometry.get("colorPerVertex", "true") != "true":
                raise ValueError("EXCHANGE_XML_PER_FACE_COLOR_UNSUPPORTED")
            row["colors"] = _parse_numbers(colors[0].get("color"), "colors", True)
        if group in ("meshes", "lines"):
            indices = _parse_numbers(geometry.get("coordIndex"), "indices", integer=True)
            runs, run = [], []
            for index in indices:
                if index == -1:
                    if not run:
                        raise ValueError("EXCHANGE_XML_EMPTY_INDEX_RUN")
                    runs.append(run); run = []
                elif index < 0:
                    raise ValueError("EXCHANGE_XML_NEGATIVE_INDEX")
                else:
                    run.append(index)
            if run:
                runs.append(run)
            if group == "meshes":
                row["faces"] = runs
            elif len(runs) != 1 or runs[0] != list(range(len(row["positions"]))):
                raise ValueError("EXCHANGE_XML_LINE_TOPOLOGY_SUBSET")
        if group != "meshes":
            row["radius"] = item.get("radius")
        frame[group].append(row)
    result = validate_frame(frame)
    metadata["import_geometry_sha256"] = _geometry_identity(result)
    metadata["geometry_matches_declared_hash"] = metadata["import_geometry_sha256"] == metadata.get("geometry_sha256")
    metadata["import_scope"] = "Actual static geometry decoded; declared case identity is unauthenticated provenance. Scientific arrays and metrics are not reconstructed."
    result["metadata"] = metadata
    return result


def _flatten(frame):
    positions, colors, ids, groups, local_indices = [], [], [], [], []
    verts, lines, polys = [], [], []
    records = []
    for group_index, group in enumerate(GROUPS):
        for row in frame[group]:
            offset = len(positions)
            positions.extend(row["positions"])
            colors.extend([[*c, row["opacity"]] for c in row.get("colors", [row["color"]]*len(row["positions"]))])
            ids.extend([len(records)]*len(row["positions"])); groups.extend([group_index]*len(row["positions"]))
            local_indices.extend(range(len(row["positions"])))
            if group == "meshes":
                polys.extend([[offset+i for i in face] for face in row["faces"]])
            elif group == "lines":
                lines.append(list(range(offset, len(positions))))
            else:
                verts.extend([[i] for i in range(offset, len(positions))])
            records.append({"id": row["id"], "group": group, "offset": offset, "count": len(row["positions"]),
                            "radius": row.get("radius")})
    return positions, colors, ids, groups, local_indices, verts, lines, polys, records


def _array(parent, name, values, vtk_type="Float64", components=1):
    attrs = {"type": vtk_type, "Name": name, "NumberOfComponents": str(components), "format": "ascii"}
    array = ET.SubElement(parent, "DataArray", **attrs)
    array.text = " ".join(_f(v) if vtk_type.startswith("Float") else str(v) for v in values)
    return array


def to_vtp(case, frame_index=0):
    """Write actual VTK XML PolyData, including vertices, polylines and polygons."""
    frame, metadata = _selected(case, frame_index)
    xyz, rgba, ids, groups, local, verts, lines, polys, records = _flatten(frame)
    root = ET.Element("VTKFile", type="PolyData", version="0.1", byte_order="LittleEndian")
    data = ET.SubElement(root, "PolyData")
    field = ET.SubElement(data, "FieldData")
    raw = canonical({**metadata, "geometry_records": records}).encode()
    a = _array(field, "stemloom_metadata_utf8", list(raw), "UInt8")
    a.set("NumberOfTuples", str(len(raw)))
    t = _array(field, "TimeValue", [frame["time"]]); t.set("NumberOfTuples", "1")
    piece = ET.SubElement(data, "Piece", NumberOfPoints=str(len(xyz)), NumberOfVerts=str(len(verts)),
                          NumberOfLines=str(len(lines)), NumberOfStrips="0", NumberOfPolys=str(len(polys)))
    point_data = ET.SubElement(piece, "PointData", Scalars="ColorRGBA")
    _array(point_data, "ColorRGBA", [max(0, min(255, round(v*255))) for c in rgba for v in c], "UInt8", 4)
    _array(point_data, "geometry_record", ids, "Int32")
    _array(point_data, "geometry_kind", groups, "UInt8")
    _array(point_data, "local_index", local, "Int32")
    reserved = {"ColorRGBA", "geometry_record", "geometry_kind", "local_index"}
    descriptors = {}
    for group in GROUPS:
        for row in frame[group]:
            for name, descriptor in row.get("point_data", {}).items():
                if name in reserved or name.endswith("__valid"):
                    raise ValueError("EXCHANGE_POINT_DATA_RESERVED_NAME: " + name)
                old = descriptors.get(name)
                signature = (descriptor["components"], descriptor["units"])
                if old is not None and old != signature:
                    raise ValueError("EXCHANGE_POINT_DATA_INCONSISTENT: " + name)
                descriptors[name] = signature
    scientific_meta = {}
    for name, (components, units) in sorted(descriptors.items()):
        values, valid = [], []
        for group in GROUPS:
            for row in frame[group]:
                descriptor = row.get("point_data", {}).get(name)
                n = len(row["positions"])
                valid.extend([int(descriptor is not None)]*n)
                if descriptor is None:
                    values.extend([0.]*(n*components))
                elif components == 1:
                    values.extend(descriptor["values"])
                else:
                    values.extend(v for value in descriptor["values"] for v in value)
        _array(point_data, name, values, "Float64", components)
        _array(point_data, name+"__valid", valid, "UInt8")
        scientific_meta[name] = {"components": components, "units": units, "missing": "zero-filled; __valid=0 means unavailable, not measured zero"}
    if scientific_meta:
        raw_science = canonical(scientific_meta).encode()
        science_array = _array(field, "stemloom_scientific_arrays_utf8", list(raw_science), "UInt8")
        science_array.set("NumberOfTuples", str(len(raw_science)))
    pts = ET.SubElement(piece, "Points")
    _array(pts, "Points", [v for p in xyz for v in p], "Float64", 3)
    for label, cells in (("Verts", verts), ("Lines", lines), ("Polys", polys)):
        section = ET.SubElement(piece, label)
        connectivity, offsets = [], []
        for cell in cells:
            connectivity.extend(cell); offsets.append(len(connectivity))
        _array(section, "connectivity", connectivity, "Int64")
        _array(section, "offsets", offsets, "Int64")
    ET.SubElement(piece, "Strips")
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root, encoding="unicode")+'\n'


def to_obj(case, frame_index=0):
    """OBJ geometry only: RGB/opacity/radii/units and scientific arrays are lost."""
    frame, metadata = _selected(case, frame_index)
    xyz, _, _, _, _, verts, lines, polys, records = _flatten(frame)
    rows = ["# Research Loom geometry projection", "# "+canonical(metadata),
            "# LOSS: no material colors, opacity, tube/point radii, units schema or scientific arrays"]
    rows.extend("v "+_nums(p) for p in xyz)
    for i, record in enumerate(records):
        rows.append("g "+_def(record["id"]))
        offset, count = record["offset"], record["count"]
        source = frame[record["group"]][sum(1 for r in records[:i] if r["group"] == record["group"])]
        if record["group"] == "meshes":
            rows.extend("f "+" ".join(str(offset+j+1) for j in face) for face in source["faces"])
        elif record["group"] == "lines":
            rows.append("l "+" ".join(str(j+1) for j in range(offset, offset+count)))
        else:
            rows.append("p "+" ".join(str(j+1) for j in range(offset, offset+count)))
    return "\n".join(rows)+"\n"


def to_ply(case, frame_index=0):
    """ASCII PLY with RGB8 vertices, faces and optional edge records.

    Edges preserve centerline connectivity but not grouped polyline identity.
    Metadata is a comment; it is not a universally supported PLY convention.
    """
    frame, metadata = _selected(case, frame_index)
    xyz, rgba, _, _, _, _, lines, polys, _ = _flatten(frame)
    edges = [(a,b) for line in lines for a,b in zip(line, line[1:])]
    rows = ["ply", "format ascii 1.0", "comment "+ADAPTER,
            "comment case_sha256 "+metadata["case_sha256"],
            "comment LOSS units/scientific arrays/group identities/radii; RGB and opacity quantized to 8-bit",
            f"element vertex {len(xyz)}", "property double x", "property double y", "property double z",
            "property uchar red", "property uchar green", "property uchar blue", "property uchar alpha",
            f"element face {len(polys)}", "property list uchar int vertex_indices",
            f"element edge {len(edges)}", "property int vertex1", "property int vertex2", "end_header"]
    rows.extend(_nums(p)+" "+" ".join(str(max(0,min(255,round(v*255)))) for v in c) for p,c in zip(xyz,rgba))
    rows.extend(str(len(face))+" "+" ".join(map(str,face)) for face in polys)
    rows.extend(f"{a} {b}" for a,b in edges)
    return "\n".join(rows)+"\n"


def points_csv(case, frame_index=0):
    """All geometry vertices in long form; these are display samples, not raw observations."""
    frame, _ = _selected(case, frame_index)
    out = io.StringIO(newline="")
    writer = csv.writer(out, lineterminator="\n")
    writer.writerow(["group", "id", "index", "x", "y", "z", "r", "g", "b"])
    for group in GROUPS:
        for row in frame[group]:
            colors = row.get("colors", [row["color"]]*len(row["positions"]))
            for index, (point, color) in enumerate(zip(row["positions"], colors)):
                writer.writerow([group, row["id"], index, *[_f(v) for v in point+color]])
    return out.getvalue()


def dataset_to_vti(dataset):
    """Write a complete regular vector grid as VTK ImageData, x fastest.

    Input positions establish ordering rather than trusting an undocumented
    flatten convention. Every lattice location must occur exactly once.
    """
    if not isinstance(dataset, Mapping) or dataset.get("association", "point") != "point":
        raise ValueError("EXCHANGE_VTI_POINT_GRID_REQUIRED")
    shape = dataset.get("shape")
    if not isinstance(shape, (list, tuple)) or len(shape) != 3 or any(
            isinstance(n, bool) or not isinstance(n, int) or not 2 <= n <= 128 for n in shape):
        raise ValueError("EXCHANGE_VTI_SHAPE")
    total = math.prod(shape)
    if total > 250_000:
        raise ValueError("EXCHANGE_VTI_BUDGET")
    origin = _vector(dataset.get("origin"), "grid origin")
    spacing = _vector(dataset.get("spacing"), "grid spacing", 0)
    if min(spacing) <= 0:
        raise ValueError("EXCHANGE_VTI_SPACING")
    positions, vectors = dataset.get("positions"), dataset.get("velocity")
    if not isinstance(positions, (list, tuple)) or not isinstance(vectors, (list, tuple)) or len(positions) != total or len(vectors) != total:
        raise ValueError("EXCHANGE_VTI_ARRAY_SHAPE")
    ordered = [None]*total
    for position, vector in zip(positions, vectors):
        point = _vector(position, "grid point"); velocity = _vector(vector, "grid velocity")
        ijk = [round((point[i]-origin[i])/spacing[i]) for i in range(3)]
        if any(not 0 <= ijk[i] < shape[i] or
               abs(point[i]-(origin[i]+ijk[i]*spacing[i])) > 1e-8*(1+abs(point[i])) for i in range(3)):
            raise ValueError("EXCHANGE_VTI_NOT_ON_GRID")
        index = ijk[0]+shape[0]*(ijk[1]+shape[1]*ijk[2])
        if ordered[index] is not None:
            raise ValueError("EXCHANGE_VTI_DUPLICATE_GRID_POINT")
        ordered[index] = velocity
    if any(v is None for v in ordered):
        raise ValueError("EXCHANGE_VTI_MISSING_GRID_POINT")
    extent = " ".join(str(v) for n in shape for v in (0, n-1))
    root = ET.Element("VTKFile", type="ImageData", version="0.1", byte_order="LittleEndian")
    image = ET.SubElement(root, "ImageData", WholeExtent=extent, Origin=_nums(origin), Spacing=_nums(spacing))
    field = ET.SubElement(image, "FieldData")
    raw = canonical({"adapter": ADAPTER, "association": "point", "ordering": "VTK x fastest",
                     "units": dataset.get("units", {}), "shape": shape,
                     "source_positions_order": "explicitly mapped from supplied regular-grid coordinates"}).encode()
    m = _array(field, "stemloom_metadata_utf8", list(raw), "UInt8"); m.set("NumberOfTuples", str(len(raw)))
    piece = ET.SubElement(image, "Piece", Extent=extent)
    point_data = ET.SubElement(piece, "PointData", Vectors="Velocity")
    _array(point_data, "Velocity", [x for v in ordered for x in v], "Float64", 3)
    _array(point_data, "Speed", [math.sqrt(sum(x*x for x in v)) for v in ordered])
    ET.SubElement(piece, "CellData")
    ET.indent(root, space="  ")
    return '<?xml version="1.0" encoding="UTF-8"?>\n'+ET.tostring(root, encoding="unicode")+'\n'
