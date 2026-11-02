"""CadQuery 2.3 regression for Workplane XZ revolve mapping and source bbox."""
from __future__ import annotations

import math
import sys
import unittest
from pathlib import Path

import cadquery as cq
from OCP.TopoDS import (
    TopoDS_Compound, TopoDS_CompSolid, TopoDS_Edge, TopoDS_Face,
    TopoDS_Shape, TopoDS_Shell, TopoDS_Solid, TopoDS_Vertex, TopoDS_Wire,
)

ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT = ROOT / "work/benchcad-source/api-snapshot-035f467"
FAMILY = SNAPSHOT / "designs/set_screw_shaft_collar"
sys.path.insert(0, str(SNAPSHOT / "framework"))
sys.path.insert(0, str(SNAPSHOT))


def install_hash_compatibility():
    for cls in (TopoDS_Shape, TopoDS_Face, TopoDS_Edge, TopoDS_Vertex,
                TopoDS_Wire, TopoDS_Shell, TopoDS_Solid, TopoDS_Compound,
                TopoDS_CompSolid):
        if not hasattr(cls, "HashCode"):
            cls.HashCode = lambda self, ub=2147483647: id(self) % ub


class WorkplaneAxisRegressionTests(unittest.TestCase):
    def test_xz_local_y_maps_to_world_positive_z(self):
        point = cq.Workplane("XZ").plane.toWorldCoords((0, 1, 0))
        values = (point.x, point.y, point.z)
        for actual, expected in zip(values, (0, 0, 1)):
            self.assertAlmostEqual(actual, expected, places=12)

    def test_fixed_source_build_bbox_has_axial_width_on_world_z(self):
        if not FAMILY.is_dir():
            self.fail(f"fixed BenchCAD source snapshot missing: {FAMILY}")
        from bench2.loader import load_family

        install_hash_compatibility()
        part, spec = load_family(FAMILY)
        params = {
            "bore_d": 20, "outer_d": 32, "width": 14,
            "screw_d": 6, "screw_len": 8, "second_screw": 0,
        }
        self.assertEqual(list(spec.check(dict(params))), [])
        result = part.build(**params)
        if isinstance(result, cq.Assembly):
            shape = result.toCompound()
        else:
            shape = result.val() if hasattr(result, "val") else result
        bbox = shape.BoundingBox()
        self.assertAlmostEqual(bbox.xlen, 32.0000002, delta=1e-4)
        self.assertAlmostEqual(bbox.ylen, 32.0000002, delta=1e-4)
        self.assertAlmostEqual(bbox.zlen, 14.0, delta=1e-7)


if __name__ == "__main__":
    unittest.main()
