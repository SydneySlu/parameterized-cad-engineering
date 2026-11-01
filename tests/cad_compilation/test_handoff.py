#!/usr/bin/env python3
"""Small, repository-tracked CAD-005/006 successor handoff smoke test.

This checks only the fixed BenchCAD API snapshot and its preflight/build
boundary.  It does not claim that CAD-005/006 or a STEP validator exists.
The source snapshot is read from ``work/`` and is never modified.
"""

from __future__ import annotations

import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[2]
SNAPSHOT_COMMIT = "035f467142888edfd0bd7cd73906f9b155c8f43c"
SNAPSHOT = REPO_ROOT / "work" / "benchcad-source" / "api-snapshot-035f467"
FAMILY = SNAPSHOT / "designs" / "set_screw_shaft_collar"


def _blocked(reason: str) -> int:
    print(f"status=blocked\nreason={reason}")
    return 2


def _install_compatibility_shim() -> None:
    """Record the CQ 2.3/OCP 7.9 HashCode compatibility shim explicitly."""

    from OCP.TopoDS import (
        TopoDS_Compound,
        TopoDS_CompSolid,
        TopoDS_Edge,
        TopoDS_Face,
        TopoDS_Shape,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Vertex,
        TopoDS_Wire,
    )

    for cls in (
        TopoDS_Shape,
        TopoDS_Face,
        TopoDS_Edge,
        TopoDS_Vertex,
        TopoDS_Wire,
        TopoDS_Shell,
        TopoDS_Solid,
        TopoDS_Compound,
        TopoDS_CompSolid,
    ):
        if not hasattr(cls, "HashCode"):
            cls.HashCode = lambda self, ub=2147483647: id(self) % ub


def _shape_from_result(result):
    import cadquery as cq

    if isinstance(result, cq.Assembly):
        return result.toCompound()
    return result.val() if hasattr(result, "val") else result


def _solid_count(shape) -> int:
    import cadquery as cq

    return int(cq.Workplane(obj=shape).solids().size())


def main() -> int:
    if not SNAPSHOT.is_dir():
        return _blocked(f"fixed snapshot missing: {SNAPSHOT}")
    if not FAMILY.joinpath("part.py").is_file() or not FAMILY.joinpath("spec.py").is_file():
        return _blocked(f"fixed family files missing under: {FAMILY}")

    try:
        import cadquery  # noqa: F401  # environment gate
        from bench2.loader import load_family
    except Exception as exc:  # pragma: no cover - environment dependent
        return _blocked(f"CadQuery/BenchCAD import unavailable: {type(exc).__name__}: {exc}")

    _install_compatibility_shim()
    part, spec = load_family(FAMILY)

    legal = {
        "bore_d": 20,
        "outer_d": 32,
        "width": 14,
        "screw_d": 6,
        "screw_len": 8,
        "second_screw": 0,
    }
    rejected = dict(legal, second_screw=1)

    legal_errors = list(spec.check(dict(legal)))
    if legal_errors:
        print(f"status=fail\ncase=legal_catalog_row\nerrors={legal_errors}")
        return 1
    legal_shape = _shape_from_result(part.build(**legal))
    legal_solids = _solid_count(legal_shape)
    if legal_solids != 1:
        print(f"status=fail\ncase=legal_catalog_row\nsolids={legal_solids}")
        return 1

    rejected_errors = list(spec.check(dict(rejected)))
    if not rejected_errors:
        print("status=fail\ncase=second_screw_rule\nerrors=[]")
        return 1

    print("status=pass")
    print(f"snapshot_commit={SNAPSHOT_COMMIT}")
    print("compatibility_shim=OCP.TopoDS.HashCode fallback for CQ 2.3/OCP 7.9")
    print(f"legal_catalog_row=check_pass,build_pass,solids={legal_solids}")
    print(f"rule_rejected_second_screw=check_rejected,errors={rejected_errors}")
    return 0


if __name__ == "__main__":
    # The tracked snapshot uses the framework package plus its repository root.
    sys.path.insert(0, str(SNAPSHOT / "framework"))
    sys.path.insert(0, str(SNAPSHOT))
    raise SystemExit(main())
