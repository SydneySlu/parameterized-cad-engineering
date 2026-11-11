#!/usr/bin/env python3
"""Offline unified CAD pipeline CLI.

Runs the full: synthetic v5 envelope → parse → gate → Schema → IR → CAD → STEP
pipeline and writes run evidence to work/integration-runs/<run_id>/.

Usage
-----
PYTHONPATH=src:. <python> scripts/run_cad_pipeline.py \\
    --request "请按 GN 705 做一个轴环，孔径 24 mm" \\
    --synthetic-envelope tests/integration/fixtures/answer-bore24.json \\
    --output-root work/integration-runs \\
    [--run-id my-custom-id] \\
    [--json]

Exit codes
----------
0  success – STEP file produced and verified
1  ask / refuse / blocked – gate or model decision blocked construction
2  failed / error – CAD failure or parse error (non-zero in both cases)

The --synthetic-envelope flag is REQUIRED and signals that the envelope is a
test fixture, not a real model response.  extraction_source is always set to
"synthetic_fixture" in the output.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Repo root on sys.path so ``src/`` modules are importable.
# When PYTHONPATH=src:. is set by the caller this is a no-op.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_cad_pipeline.py",
        description=(
            "Offline CAD pipeline: synthetic v5 envelope → real local STEP.\n"
            "No model calls, no network, no key/env reads."
        ),
    )
    p.add_argument(
        "--request", required=True,
        help="Natural language requirement text (provenance; not re-parsed).",
    )
    p.add_argument(
        "--synthetic-envelope", required=True, metavar="PATH",
        help=(
            "Path to a JSON fixture file containing a synthetic v5 envelope. "
            "Must be explicitly labelled synthetic; arbitrary files are not accepted."
        ),
    )
    p.add_argument(
        "--output-root", default="work/integration-runs", metavar="DIR",
        help="Root directory for run directories (default: work/integration-runs).",
    )
    p.add_argument(
        "--run-id", default=None,
        help="Override the auto-generated UUID run ID (optional).",
    )
    p.add_argument(
        "--json", action="store_true",
        help="Output structured JSON instead of human-readable text.",
    )
    return p


def _exit_code(status: str) -> int:
    if status == "success":
        return 0
    if status in ("ask", "refuse", "blocked"):
        return 1
    return 2  # failed / error


def main(argv: list[str] | None = None) -> None:
    parser = _build_parser()
    args = parser.parse_args(argv)

    # --- Read the synthetic envelope fixture ---
    envelope_path = Path(args.synthetic_envelope)
    if not envelope_path.is_file():
        _die(f"Synthetic envelope file not found: {envelope_path}", args.json)

    try:
        raw_envelope = envelope_path.read_bytes()
    except OSError as exc:
        _die(f"Cannot read synthetic envelope: {exc}", args.json)

    # Determine output root (relative paths resolved from repo root).
    out_root_arg = args.output_root
    out_root = Path(out_root_arg)
    if not out_root.is_absolute():
        out_root = _REPO_ROOT / out_root_arg

    # --- Import pipeline (lazy to give cleaner import-error messages) ---
    try:
        from integration.pipeline import run_pipeline
    except ImportError as exc:
        _die(
            f"Cannot import integration.pipeline: {exc}\n"
            "Run with: PYTHONPATH=src:. python scripts/run_cad_pipeline.py ...",
            args.json,
        )

    # --- Run pipeline ---
    result = run_pipeline(
        request_text=args.request,
        raw_envelope=raw_envelope,
        output_root=out_root,
        envelope_fixture_label=str(envelope_path),
        run_id=args.run_id,
    )

    # --- Output ---
    if args.json:
        print(json.dumps(result.as_dict(), ensure_ascii=False, indent=2))
    else:
        _print_human(result)

    sys.exit(_exit_code(result.status))


def _print_human(result) -> None:
    """Print a human-readable summary to stdout."""
    status_icon = {
        "success": "✓",
        "ask": "?",
        "refuse": "✗",
        "blocked": "✗",
        "failed": "✗",
        "error": "✗",
    }.get(result.status, "?")

    print(f"\n{status_icon} run_id:  {result.run_id}")
    print(f"  status:  {result.status} (stage: {result.stage})")
    print(f"  source:  {result.extraction_source}")
    print(f"  fixture: {result.envelope_fixture_label}")

    if result.status == "success":
        print(f"  STEP:    {result.step_path}")
        if result.parameters:
            params = result.parameters
            print("  params:")
            for k in ["bore_d", "outer_d", "screw_d", "screw_len",
                      "second_screw", "width"]:
                if k in params:
                    print(f"    {k:12s} = {params[k]}")
        if result.ir_index:
            print(f"  ir_sha:  {result.ir_index.get('input_ir_sha256', '')[:16]}…")
            print(f"  step_sha:{result.ir_index.get('step_sha256', '')[:16]}…")
    elif result.status == "ask":
        print("  questions:")
        for q in result.questions:
            print(f"    - {q}")
    elif result.errors:
        print("  errors:")
        for e in result.errors[:5]:
            code = e.get("code", "?")
            msg = e.get("message", "")
            print(f"    [{code}] {msg}")

    if result.run_dir:
        print(f"  run_dir: {result.run_dir}")
    print()


def _die(message: str, as_json: bool) -> None:
    if as_json:
        print(json.dumps({"status": "error", "message": message},
                         ensure_ascii=False))
    else:
        print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(2)


if __name__ == "__main__":
    main()
