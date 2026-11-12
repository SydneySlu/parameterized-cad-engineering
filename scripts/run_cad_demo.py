#!/usr/bin/env python3
"""Startup script for APP-003-C1 local CAD demo server (ADR-0022).

Usage
-----
    # From repo root with the fixed CAD venv:
    PYTHONPATH=src:. work/benchcad-output/venv/bin/python scripts/run_cad_demo.py

    # With optional port and output-root overrides:
    PYTHONPATH=src:. work/benchcad-output/venv/bin/python scripts/run_cad_demo.py \\
        --port 8080 \\
        --output-root work/demo-runs

Constraints (ADR-0022)
----------------------
- Binds only to 127.0.0.1; no remote access.
- No LLM calls, no network requests, no .env reads.
- Reuses existing schema/IR/CAD pipeline with manually confirmed parameters.
- Each run uses a new UUID and isolated directory.
- Only successful runs expose STEP for download.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# ---------------------------------------------------------------------------
# Add repo root and src/ to sys.path so ``src/`` modules are importable.
# When PYTHONPATH=src:. is already set by the caller, this is a no-op.
# ---------------------------------------------------------------------------
_SCRIPT_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _SCRIPT_DIR.parent
if str(_REPO_ROOT / "src") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "src"))
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="run_cad_demo.py",
        description=(
            "APP-003-C1 local CAD demo server.\n\n"
            "Starts a localhost-only HTTP server for manual parameter input,\n"
            "real STEP generation via the existing CAD pipeline, and STEP download.\n\n"
            "Requires the fixed CAD venv (Python 3.11.18 / CadQuery 2.3.0 / OCP 7.9.3.0):\n"
            "  work/benchcad-output/venv/bin/python scripts/run_cad_demo.py\n\n"
            "LIMITATIONS (ADR-0022):\n"
            "  - Single family: set_screw_shaft_collar (GN 705 metric table)\n"
            "  - Fixed CAD environment; not portable\n"
            "  - Thread model: revolved ring approximation (not helical)\n"
            "  - STEP verification does not constitute manufacturing certification\n"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument(
        "--port", type=int, default=8080,
        help="TCP port to listen on (default: 8080; bound to 127.0.0.1 only)",
    )
    p.add_argument(
        "--output-root", type=Path, default=None,
        help=(
            "Directory for per-run output (default: work/demo-runs/). "
            "Must be writable. Each run creates an isolated UUID subdirectory."
        ),
    )
    return p


def main() -> int:
    args = _build_parser().parse_args()

    # Import after path setup
    try:
        from demo.server import run_server
    except ImportError as exc:
        print(f"ERROR: cannot import demo.server: {exc}", file=sys.stderr)
        print("Make sure PYTHONPATH=src:. is set and you are using the CAD venv.", file=sys.stderr)
        return 2

    # Validate port
    if not (1024 <= args.port <= 65535):
        print(f"ERROR: --port must be between 1024 and 65535, got {args.port}", file=sys.stderr)
        return 1

    print("[demo] APP-003-C1 Local CAD Demo", file=sys.stderr)
    print("[demo] LIMITATIONS: single-family, fixed env, no LLM, localhost only", file=sys.stderr)
    print("[demo] STEP pass ≠ manufacturing certification", file=sys.stderr)

    run_server(port=args.port, output_root=args.output_root)
    return 0


if __name__ == "__main__":
    sys.exit(main())
