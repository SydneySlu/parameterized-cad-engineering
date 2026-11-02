#!/usr/bin/env python3
"""Run one RET-002 example query and print its canonical result hash.

Used by `run_smoke.py` to prove that the same query produces byte-identical
canonical JSON in two independent processes.  This is a smoke helper, not a
production interface.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


HERE = Path(__file__).resolve()
REPO_ROOT = HERE.parents[3]
sys.path.insert(0, str(REPO_ROOT / "src"))

from retrieval import RetrievalIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", default=str(HERE.parent / "retrieval-config.json"))
    parser.add_argument("--case", required=True)
    parser.add_argument("--top-k", type=int, default=None)
    args = parser.parse_args()

    case = json.loads(Path(args.case).read_text(encoding="utf-8"))
    index = RetrievalIndex.from_config(args.config)
    top_k = args.top_k if args.top_k is not None else case.get("top_k")
    result = index.query(
        family_id=case["family_id"],
        parameters=case["parameters"],
        top_k=top_k,
    )
    payload = result.as_dict()
    print("sha256=" + result.sha256())
    print("query_status=" + payload["query"]["query_status"])
    print("top1=" + (payload["results"][0]["sample_id"] if payload["results"] else "-"))
    print("results=" + str(len(payload["results"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
