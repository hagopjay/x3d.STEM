"""Actual cross-format geometry checks and refusal controls for Research Loom."""
import copy
import csv
import io
import json
import math
import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET

from stemloom.exchange import (to_x3d, from_x3d, to_vtp, to_obj, to_ply,
                               points_csv, validate_frame, dataset_to_vti)


def specimen():
    return {"id": "exchange-control", "title": "Coordinates and colours / 坐标",
            "kind": "tensor", "axes": "Right-handed X,Y,Z; Y up", "units": {"length": "mm"},
            "scope": "Synthetic exchange control, not a measurement",
            "frames": [{"time": .125, "metrics": [],
                "meshes": [{"id": "plane-a", "positions": [[.1,0,0],[2,0,0],[2,1,0],[.1,1,0]],
                            "faces": [[0,1,2,3]], "color": [.2,.3,.4], "opacity": .35,
                            "colors": [[1,0,0],[0,1,0],[0,0,1],[1,1,1]],
                            "point_data": {"displacement": {"values": [.1,.2,.3,.4],"components":1,"units":"mm"}}}],
                "lines": [{"id": "curve-b", "positions": [[0,0,0],[1,1,1],[2,0,2]],
                           "color": [.7,.8,.9], "opacity": 1, "radius": .012}],
                "points": [{"id": "probe-c", "positions": [[-1,2,-3]],
                            "color": [.6,.4,.2], "opacity": .8, "radius": .035}]}]}


def expected_geometry(case):
    frame = validate_frame(case["frames"][0])
    return {group: [{k:v for k,v in row.items() if k != "point_data"} for row in frame[group]]
            for group in ("meshes","lines","points")}


class X3DExchangeTests(unittest.TestCase):
    def test_both_versions_preserve_actual_coordinates_topology_and_rgb(self):
        case = specimen()
        for version in ("3.3", "4.0"):
            with self.subTest(version=version):
                xml = to_x3d(case, version=version)
                back = from_x3d(xml)
                self.assertEqual(back["time"], .125)
                for group, records in expected_geometry(case).items():
                    self.assertEqual(back[group], records)
                self.assertEqual(back["metadata"]["units"], {"length":"mm"})
                self.assertTrue(back["metadata"]["geometry_matches_declared_hash"])
                self.assertNotIn("point_data", back["meshes"][0], "Scientific arrays stay in packet/VTK, not invented from a mesh")

    def test_unmodified_opacity_complement_roundoff_does_not_fake_geometry_edit(self):
        for opacity in (.1, .18, .3, .35, .7, .99):
            case=specimen();case["frames"][0]["meshes"][0]["opacity"]=opacity
            imported=from_x3d(to_x3d(case))
            self.assertAlmostEqual(imported["meshes"][0]["opacity"],opacity)
            self.assertTrue(imported["metadata"]["geometry_matches_declared_hash"])

    def test_camera_is_case_wide_rather_than_following_each_frame(self):
        case=specimen();later=copy.deepcopy(case["frames"][0]);later["time"]=1
        later["points"][0]["positions"]=[[100,0,0]];case["frames"].append(later)
        a=ET.fromstring(to_x3d(case,0)).find(".//Viewpoint").attrib
        b=ET.fromstring(to_x3d(case,1)).find(".//Viewpoint").attrib
        self.assertEqual(a,b)

    def test_import_reads_edited_geometry_instead_of_recovering_metadata_copy(self):
        root = ET.fromstring(to_x3d(specimen()))
        coords = root.find(".//IndexedFaceSet/Coordinate")
        words = coords.get("point").split(); words[0] = "17.25"; coords.set("point", " ".join(words))
        frame = from_x3d(ET.tostring(root, encoding="unicode"))
        self.assertEqual(frame["meshes"][0]["positions"][0][0], 17.25)
        self.assertFalse(frame["metadata"]["geometry_matches_declared_hash"])

    def test_unsafe_and_unsupported_xml_refused(self):
        xml = to_x3d(specimen())
        bad = [xml.replace("<Scene>", "<Scene><Script/>"),
               xml.replace("<Scene>", '<Scene><Inline url="https://example.org/a.x3d"/>'),
               xml.replace("<Scene>", "<Scene><Transform/>"),
               xml.replace("<X3D ", '<!DOCTYPE X3D [<!ENTITY x "a">]><X3D ', 1),
               xml.replace("<Coordinate ", '<Coordinate USE="somewhere" ', 1)]
        for content in bad:
            with self.subTest(content=content[:80]), self.assertRaises(ValueError):
                from_x3d(content)

    def test_bad_numeric_indices_rgb_and_sanitized_identity_collision_refuse(self):
        for mutate in (
                lambda c:c["frames"][0]["meshes"][0]["positions"][0].__setitem__(0, float("nan")),
                lambda c:c["frames"][0]["meshes"][0].__setitem__("faces", [[0,1,999]]),
                lambda c:c["frames"][0]["meshes"][0].__setitem__("colors", [[1,0,0]]),
                lambda c:c["frames"][0]["meshes"][0].__setitem__("color", [2,0,0]),
                lambda c:c["frames"][0]["lines"][0].__setitem__("radius", 0)):
            case=specimen(); mutate(case)
            with self.assertRaises(ValueError):to_x3d(case)
        case=specimen();case["frames"][0]["lines"][0]["id"]="plane_a"
        with self.assertRaises(ValueError):to_x3d(case)

    def test_unsupported_structure_attributes_and_ambiguous_metadata_refuse(self):
        xml=to_x3d(specimen())
        for wrong in (xml.replace("<Scene>","<Scene><Coordinate point=\"0 0 0\"/>"),
                      xml.replace("solid=\"false\"", "solid=\"false\" ccw=\"false\"",1)):
            with self.assertRaises(ValueError):from_x3d(wrong)
        root=ET.fromstring(xml);record=root.find("./Scene/WorldInfo/MetadataString")
        record.set("value",json.dumps('{"adapter":"stemloom.exchange/1","adapter":"stemloom.exchange/1"}'))
        with self.assertRaises(ValueError):from_x3d(ET.tostring(root,encoding="unicode"))

    def test_geometry_edit_to_invalid_topology_refuses(self):
        root=ET.fromstring(to_x3d(specimen()))
        root.find(".//IndexedFaceSet").set("coordIndex", "0 1 90 -1")
        with self.assertRaises(ValueError):from_x3d(ET.tostring(root, encoding="unicode"))
        root=ET.fromstring(to_x3d(specimen()))
        root.find(".//IndexedLineSet").set("coordIndex", "0 2 1 -1")
        with self.assertRaises(ValueError):from_x3d(ET.tostring(root, encoding="unicode"))


class OtherWritersTests(unittest.TestCase):
    def test_obj_indices_and_point_line_face_types_are_standard_geometry(self):
        text=to_obj(specimen())
        self.assertEqual(len([l for l in text.splitlines() if l.startswith("v ")]),8)
        self.assertIn("f 1 2 3 4\n",text)
        self.assertIn("l 5 6 7\n",text)
        self.assertIn("p 8\n",text)
        self.assertIn("LOSS",text)

    def test_ply_ascii_has_color_vertices_face_and_edges(self):
        text=to_ply(specimen());header,body=text.split("end_header\n")
        self.assertIn("element vertex 8",header)
        self.assertIn("element face 1",header)
        self.assertIn("element edge 2",header)
        lines=body.splitlines()
        self.assertEqual(len(lines),11)
        self.assertEqual(lines[8],"4 0 1 2 3")
        self.assertEqual(lines[9:], ["4 5","5 6"])
        self.assertEqual(list(map(float,lines[0].split()[:3])),[.1,0,0])
        self.assertEqual(list(map(int,lines[0].split()[3:6])),[255,0,0])

    def test_csv_has_long_form_identity_and_exact_numeric_positions(self):
        rows=list(csv.DictReader(io.StringIO(points_csv(specimen()))))
        self.assertEqual(len(rows),8)
        self.assertEqual(rows[-1]["group"],"points")
        self.assertEqual(rows[-1]["id"],"probe-c")
        self.assertEqual(float(rows[0]["x"]),.1)
        self.assertEqual(float(rows[-1]["z"]),-3)

    def test_actual_vtk_polydata_reader_observes_geometry_and_masked_science(self):
        try:import vtk
        except ImportError:self.skipTest("Optional VTK unavailable")
        with tempfile.TemporaryDirectory() as d:
            path=Path(d)/"fixture.vtp";path.write_text(to_vtp(specimen()))
            reader=vtk.vtkXMLPolyDataReader();reader.SetFileName(str(path));reader.Update();data=reader.GetOutput()
        self.assertEqual(data.GetNumberOfPoints(),8)
        self.assertEqual(data.GetNumberOfVerts(),1)
        self.assertEqual(data.GetNumberOfLines(),1)
        self.assertEqual(data.GetNumberOfPolys(),1)
        self.assertEqual(data.GetPoint(0),(.1,0,0))
        self.assertEqual(data.GetPoint(7),(-1,2,-3))
        colors=data.GetPointData().GetArray("ColorRGBA")
        self.assertEqual(colors.GetTuple4(0),(255,0,0,89))
        field=data.GetPointData().GetArray("displacement")
        mask=data.GetPointData().GetArray("displacement__valid")
        self.assertAlmostEqual(field.GetValue(3),.4)
        self.assertEqual(mask.GetValue(3),1)
        self.assertEqual(mask.GetValue(4),0)
        self.assertEqual(field.GetValue(4),0)
        metadata=data.GetFieldData().GetArray("stemloom_metadata_utf8")
        raw=bytes(int(metadata.GetValue(i)) for i in range(metadata.GetNumberOfValues()))
        self.assertEqual(json.loads(raw)["units"],{"length":"mm"})

    def test_point_array_missing_and_shape_controls(self):
        case=specimen();case["frames"][0]["meshes"][0]["point_data"]["displacement"]["values"]=[1]
        with self.assertRaises(ValueError):to_vtp(case)
        case=specimen();case["frames"][0]["meshes"][0]["point_data"]["ColorRGBA"]={"values":[1]*4,"components":1,"units":"1"}
        with self.assertRaises(ValueError):to_vtp(case)


class RegularGridTests(unittest.TestCase):
    def grid(self):
        # Deliberately z-fast input. Writer must establish VTK x-fast ordering.
        xyz=[[i,j,k] for i in range(2) for j in range(3) for k in range(2)]
        return {"shape":[2,3,2],"origin":[0,0,0],"spacing":[1,1,1],"association":"point",
                "positions":xyz,"velocity":[[x+10*y+100*z,2*x,3*y] for x,y,z in xyz],"units":{"length":"m","velocity":"m/s"}}

    def test_actual_vtk_image_reader_ordering(self):
        try:import vtk
        except ImportError:self.skipTest("Optional VTK unavailable")
        with tempfile.TemporaryDirectory() as d:
            p=Path(d)/"grid.vti";p.write_text(dataset_to_vti(self.grid()))
            reader=vtk.vtkXMLImageDataReader();reader.SetFileName(str(p));reader.Update();data=reader.GetOutput()
        self.assertEqual(data.GetDimensions(),(2,3,2))
        self.assertEqual(data.GetNumberOfPoints(),12)
        vectors=data.GetPointData().GetVectors()
        for i in range(data.GetNumberOfPoints()):
            x,y,z=data.GetPoint(i)
            self.assertEqual(vectors.GetTuple3(i),(x+10*y+100*z,2*x,3*y))

    def test_duplicate_and_nonregular_locations_refused(self):
        data=self.grid();data["positions"][0]=data["positions"][1]
        with self.assertRaises(ValueError):dataset_to_vti(data)
        data=self.grid();data["positions"][0][0]=.01
        with self.assertRaises(ValueError):dataset_to_vti(data)


if __name__=="__main__":unittest.main()
