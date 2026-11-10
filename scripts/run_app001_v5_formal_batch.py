#!/usr/bin/env python3
"""APP-001-V5-FORMAL-EFFECT-EVALUATION batch runner script.

Batch ID  : app001-phase1-v5-20261111-01
Authorization: project owner instructed v5 real-model evaluation on 2026-11-11;
               scope and batch ID are recorded in the task authorization file.
Baseline commit: 2c702257ed56b3d9e49209f0455c2aaffb608b8b

Run from the repository root:

    cd "/Users/syd/Desktop/参数化 cad 工程辅助设计"
    PYTHONPATH=src /opt/homebrew/bin/python3.11 scripts/run_app001_v5_formal_batch.py

Requirements:
  - Python 3.11 at /opt/homebrew/bin/python3.11
  - Ollama running locally at http://127.0.0.1:11434 with qwen3:8b loaded
  - DEEPSEEK_API_KEY present in .env (root of repo)
  - No prior run directory for this batch ID

Commit policy:
  HEAD must be BASELINE_COMMIT or a descendant of it.  Later commits (e.g.
  adding this script, tests, and docs) are allowed only if every production
  path listed in PRODUCTION_PATHS is byte-for-byte identical to the baseline.
  Any diff in those paths causes an immediate abort before any model call.

Batch directory policy:
  If work/app001-runs/<BATCH_ID> already exists for any reason, abort
  immediately.  Do not attempt to resume, overwrite, or delete.

This script never prints or logs API key values, Authorization headers,
or any .env content.  It aborts with a clear message if any preflight
check fails.
"""

from __future__ import annotations

import hashlib
import json
import os
import subprocess
import sys
import time
import urllib.request
from pathlib import Path
from typing import Callable

# ── repository root ──────────────────────────────────────────────────────────

_REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(_REPO_ROOT / "src"))

BATCH_ID = "app001-phase1-v5-20261111-01"

# The reviewed v5 activation commit. HEAD must equal this or be a descendant
# with no production-path diffs and a clean working tree.
BASELINE_COMMIT = "2c702257ed56b3d9e49209f0455c2aaffb608b8b"

EXPECTED_SCOPE_HASH = "dd7801f24ccc47911458df0dea4a4e251de2b09469bc40baa55807f74736a5b1"
EXPECTED_MANIFEST_SHA256 = "b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297"
EXPECTED_ACTIVATION_MANIFEST_SHA256 = "a7eeed5fea5ef993fd2a100bae0b8f3d972678ffb989036018ef82af75dd0e16"
EXPECTED_PROMPT_FILE_SHA256 = "18cc180fca975da89ed01e10b750ecf023cf800a30e84f99664191ede2faafe9"
EXPECTED_ACCEPTANCE_SET_SHA256 = "ed59e2b6ba7a20fa1870fab90aad1f2bb74d9547cedefcf6b2dd52f83923cbdf"
OLLAMA_HOST = "http://127.0.0.1:11434"
OLLAMA_EXPECTED_VERSION = "0.40.14"
OLLAMA_EXPECTED_DIGEST_PREFIX = "500a1f067a9f"
OLLAMA_EXPECTED_FORMAT_SCHEMA_SHA256 = "7c201710fae0ff3cc3b811c28739393762f1886a5e79bd255cbda8671ac03143"
OLLAMA_MODEL = "qwen3:8b"

# Production paths that must be unchanged from BASELINE_COMMIT to HEAD.
# These cover all code, prompt, schema, budget, authorization, and runner
# logic.  Any diff in these paths relative to the baseline aborts the run.
PRODUCTION_PATHS: tuple[str, ...] = (
    "src/llm/",
    "src/retrieval/",
    "src/schema/",
    "src/cad_compilation/",
    "agent-work/llm/APP-001-v5-activation/prompt-v5.md",
    "agent-work/llm/APP-001-v5-activation/manifest.json",
    "agent-work/llm/APP-001-v4-activation/prompt-v4.md",
    "agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json",
    "agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json",
    "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl",
)

# ── helpers ───────────────────────────────────────────────────────────────────

def _abort(msg: str) -> None:
    print(f"\n[ABORT] {msg}", file=sys.stderr)
    sys.exit(1)

def _ok(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  [ok]  {label}{suffix}")

def _fail(label: str, detail: str = "") -> None:
    suffix = f"  ({detail})" if detail else ""
    print(f"  [FAIL] {label}{suffix}")

def _sha256_file(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def _git(args: list[str], *, cwd: Path = _REPO_ROOT) -> subprocess.CompletedProcess:
    return subprocess.run(
        ["git"] + args,
        cwd=cwd,
        capture_output=True,
        text=True,
    )

# ── load .env (key names only logged, never values) ───────────────────────────

def _load_env() -> None:
    env_path = _REPO_ROOT / ".env"
    if not env_path.exists():
        _abort(f".env not found at {env_path}")
    loaded = []
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, _ = line.partition("=")
        key = key.strip()
        if key:
            raw = line[len(key) + 1:]
            if key not in os.environ:
                os.environ[key] = raw
            loaded.append(key)
    print(f"  .env keys loaded: {loaded}  (values not printed)")

# ── commit validation (factored for testability) ─────────────────────────────

def verify_commit(
    baseline: str = BASELINE_COMMIT,
    production_paths: tuple[str, ...] = PRODUCTION_PATHS,
    *,
    git_runner: Callable[[list[str]], subprocess.CompletedProcess] | None = None,
    repo_root: Path = _REPO_ROOT,
) -> str:
    """Verify the repository commit state.

    Returns the actual HEAD commit hash on success.  Raises SystemExit on
    any violation.  Never makes network calls.

    Rules:
    1. HEAD must equal ``baseline`` OR be a descendant of it
       (merge-base --is-ancestor).
    2. If HEAD != baseline, git diff of PRODUCTION_PATHS from baseline to
       HEAD must be empty — no production code, prompt, schema, budget,
       authorization, or runner changes are permitted.

    ``git_runner`` is injectable for tests; defaults to the module-level
    ``_git`` wrapper bound to ``repo_root``.
    """
    if git_runner is None:
        def git_runner(args: list[str]) -> subprocess.CompletedProcess:  # type: ignore[misc]
            return subprocess.run(
                ["git"] + args,
                cwd=repo_root,
                capture_output=True,
                text=True,
            )

    # HEAD hash
    head_result = git_runner(["rev-parse", "HEAD"])
    if head_result.returncode != 0:
        _abort(f"git rev-parse HEAD failed: {head_result.stderr.strip()}")
    actual_commit = head_result.stdout.strip()

    if actual_commit == baseline:
        _ok("HEAD commit is baseline", f"{actual_commit[:12]}")
        return actual_commit

    # HEAD != baseline: must be a descendant
    ancestor_result = git_runner(["merge-base", "--is-ancestor", baseline, actual_commit])
    if ancestor_result.returncode != 0:
        _fail("HEAD is not the baseline and not a descendant of baseline",
              f"HEAD={actual_commit[:12]}  baseline={baseline[:12]}")
        _abort(
            f"HEAD commit {actual_commit[:12]} is not the authorized baseline "
            f"({baseline[:12]}) and is not a descendant of it.\n"
            "  Run from the correct branch with the authorized commit reachable."
        )

    # Descendant: check production paths are unchanged
    diff_result = git_runner(
        ["diff", "--name-only", baseline, actual_commit, "--"] + list(production_paths)
    )
    if diff_result.returncode != 0:
        _abort(f"git diff failed: {diff_result.stderr.strip()}")

    changed = [l.strip() for l in diff_result.stdout.splitlines() if l.strip()]
    if changed:
        _fail("production paths changed since baseline",
              f"{len(changed)} file(s) differ")
        for f in changed:
            print(f"    CHANGED: {f}", file=sys.stderr)
        _abort(
            f"HEAD ({actual_commit[:12]}) differs from the authorized baseline "
            f"({baseline[:12]}) in production paths.\n"
            "  Only documentation, scripts, and test commits are allowed as "
            "descendants.\n"
            "  Changed files listed above."
        )

    _ok(
        "HEAD is clean descendant of baseline",
        f"HEAD={actual_commit[:12]}  baseline={baseline[:12]}  "
        f"production diff=0 files",
    )
    return actual_commit


def verify_clean_worktree(*, git_runner=None, repo_root: Path = _REPO_ROOT) -> None:
    """Refuse execution when tracked or untracked workspace changes exist."""
    if git_runner is None:
        def git_runner(args: list[str]):
            return subprocess.run(
                ["git"] + args, cwd=repo_root, capture_output=True, text=True
            )
    result = git_runner(["status", "--porcelain", "--untracked-files=all"])
    if result.returncode != 0:
        _abort(f"git status failed: {result.stderr.strip()}")
    if result.stdout.strip():
        _abort("working tree is not clean; commit or remove all changes before preflight")
    _ok("working tree clean")

# ── extracted preflight helpers ───────────────────────────────────────────────

def ensure_batch_dir_absent(batch_dir: Path) -> None:
    """Abort if the batch directory already exists for any reason.

    Raises SystemExit immediately if ``batch_dir`` exists, regardless of
    whether it is empty or contains files.  Never deletes or modifies the
    existing directory.

    Args:
        batch_dir: Absolute path to the candidate batch output directory.
    """
    if batch_dir.exists():
        _fail("batch directory already exists", str(batch_dir))
        _abort(
            f"batch directory already exists: {batch_dir}\n"
            "  Refusing to overwrite or resume any existing batch.\n"
            "  If this is a leftover empty directory, remove it manually before running."
        )
    _ok("batch dir absent", batch_dir.name)


def check_ollama_runtime(
    *,
    host: str = OLLAMA_HOST,
    model: str = OLLAMA_MODEL,
    expected_digest_prefix: str = OLLAMA_EXPECTED_DIGEST_PREFIX,
    expected_version: str = OLLAMA_EXPECTED_VERSION,
    urlopen_fn: Callable = urllib.request.urlopen,
) -> str:
    """Verify that Ollama is running and the expected model is loaded.

    Performs two HTTP calls via ``urlopen_fn`` (injectable for tests):
    1. GET ``<host>/api/version`` — confirms Ollama is reachable.
    2. GET ``<host>/api/tags``    — confirms ``model`` is listed with the
       expected digest prefix.

    Returns the full digest string on success.
    Raises SystemExit on any connectivity error, missing model, or digest
    mismatch.

    Args:
        host: Base URL of the local Ollama service.
        model: Model name to look for in ``/api/tags``.
        expected_digest_prefix: Required prefix of the model digest.
        urlopen_fn: Callable with the same signature as
            ``urllib.request.urlopen``.  Defaults to the stdlib function;
            override in tests to avoid real network calls.
    """
    print("  checking Ollama connectivity and model identity...")

    # Step 1: version check
    try:
        with urlopen_fn(f"{host}/api/version", timeout=5) as resp:
            version_data = json.loads(resp.read().decode())
        ollama_version = version_data.get("version", "unknown")
        if ollama_version != expected_version:
            _fail("Ollama version mismatch", f"expected {expected_version}, got {ollama_version}")
            _abort("Ollama runtime differs from the ADR-0015 frozen version")
        _ok("Ollama reachable", f"version={ollama_version}")
    except Exception as exc:
        _fail(f"Ollama not reachable at {host}", str(exc))
        _abort(
            f"Ollama must be running at {host} with {model} loaded.\n"
            "  Start Ollama: brew services start ollama\n"
            f"  Pull model:  ollama pull {model}"
        )

    # Step 2: model digest check
    try:
        with urlopen_fn(f"{host}/api/tags", timeout=10) as resp:
            tags_data = json.loads(resp.read().decode())
        models = tags_data.get("models", [])
        found = [m for m in models if m.get("name") == model]
        if not found:
            _abort(f"{model} not found in Ollama; run: ollama pull {model}")
        digest = found[0].get("digest", "")
        if not digest.startswith(expected_digest_prefix):
            _fail("Ollama model digest mismatch",
                  f"expected prefix {expected_digest_prefix!r}, got {digest[:20]!r}")
            _abort("Wrong model version — re-pull or check Ollama")
        _ok(f"Ollama {model} digest", f"{digest[:20]}...")
        return digest
    except SystemExit:
        raise
    except Exception as exc:
        _abort(f"Ollama /api/tags check failed: {exc}")
        return ""  # unreachable; keeps type checkers happy


# ── preflight ─────────────────────────────────────────────────────────────────

def preflight() -> None:
    print("\n=== PREFLIGHT ===")

    # 1. Git commit
    verify_commit()

    # 2. Python version
    pv = sys.version_info
    _ok(f"Python {pv.major}.{pv.minor}.{pv.micro}")
    if (pv.major, pv.minor, pv.micro) != (3, 11, 18):
        _abort(f"Python 3.11.18 required; got {pv.major}.{pv.minor}.{pv.micro}")

    # Refuse to run source that is not represented by the verified commit.
    verify_clean_worktree()

    # 3. Acceptance-set sha256
    aset_path = _REPO_ROOT / "agent-work/llm/APP-001-baseline-prep/acceptance-set-v0.json"
    if not aset_path.exists():
        _abort(f"acceptance-set not found: {aset_path}")
    actual_aset_sha = _sha256_file(aset_path)
    if actual_aset_sha == EXPECTED_ACCEPTANCE_SET_SHA256:
        _ok("acceptance-set sha256", actual_aset_sha[:16])
    else:
        _fail("acceptance-set sha256 mismatch")
        _abort(f"expected {EXPECTED_ACCEPTANCE_SET_SHA256[:16]}... got {actual_aset_sha[:16]}...")

    # 4. Prompt file sha256
    prompt_path = _REPO_ROOT / "agent-work/llm/APP-001-v5-activation/prompt-v5.md"
    if not prompt_path.exists():
        _abort(f"prompt-v5.md not found: {prompt_path}")
    actual_prompt_sha = _sha256_file(prompt_path)
    if actual_prompt_sha == EXPECTED_PROMPT_FILE_SHA256:
        _ok("prompt-v5.md file sha256", actual_prompt_sha[:16])
    else:
        _fail("prompt-v5.md sha256 mismatch")
        _abort(f"expected {EXPECTED_PROMPT_FILE_SHA256[:16]}... got {actual_prompt_sha[:16]}...")

    # 6. Activation manifest sha256
    activation_manifest = _REPO_ROOT / "agent-work/llm/APP-001-v5-activation/manifest.json"
    if not activation_manifest.exists():
        _abort(f"v5 activation manifest not found: {activation_manifest}")
    actual_activation_manifest_sha = _sha256_file(activation_manifest)
    if actual_activation_manifest_sha != EXPECTED_ACTIVATION_MANIFEST_SHA256:
        _abort("v5 activation manifest sha256 mismatch")
    _ok("v5 activation manifest sha256", actual_activation_manifest_sha[:16])

    # 5. Retrieval manifest sha256
    from retrieval.config import DEFAULT_CONFIG_REL_PATH, RetrievalConfig
    cfg = RetrievalConfig.from_path(_REPO_ROOT / DEFAULT_CONFIG_REL_PATH, repo_root=_REPO_ROOT)
    if cfg.manifest_sha256 == EXPECTED_MANIFEST_SHA256:
        _ok("RET-002 manifest sha256", cfg.manifest_sha256[:16])
    else:
        _fail("RET-002 manifest sha256 mismatch")
        _abort(f"expected {EXPECTED_MANIFEST_SHA256[:16]}... got {cfg.manifest_sha256[:16]}...")

    # 7. Ollama structured-output schema identity
    from llm.providers import OLLAMA_FORMAT_SCHEMA_SHA256
    if OLLAMA_FORMAT_SCHEMA_SHA256 != OLLAMA_EXPECTED_FORMAT_SCHEMA_SHA256:
        _abort("Ollama format schema hash differs from ADR-0015")
    _ok("Ollama format schema sha256", OLLAMA_FORMAT_SCHEMA_SHA256[:16])

    # 8. Authorization scope hash
    from llm.authorization import authorize_phase1_run
    auth_check = authorize_phase1_run(batch_id=BATCH_ID)
    if auth_check.scope_hash() == EXPECTED_SCOPE_HASH:
        _ok("authorization scope hash", auth_check.scope_hash()[:16])
    else:
        _fail("scope hash mismatch")
        _abort(f"expected {EXPECTED_SCOPE_HASH[:16]}... got {auth_check.scope_hash()[:16]}...")

    # 9. Batch directory must not exist at all
    batch_dir = _REPO_ROOT / "work/app001-runs" / BATCH_ID
    ensure_batch_dir_absent(batch_dir)

    # 10. DEEPSEEK_API_KEY present (value not checked or printed)
    _load_env()
    if not os.environ.get("DEEPSEEK_API_KEY", "").strip():
        _abort("DEEPSEEK_API_KEY is missing or empty — check .env")
    _ok("DEEPSEEK_API_KEY present (value not shown)")

    # 11. Ollama reachable + model identity
    check_ollama_runtime()

    print("  [ok]  all preflight checks passed")

# ── build retrieval index ─────────────────────────────────────────────────────

def build_retrieval_index():
    from retrieval import RetrievalIndex
    from retrieval.config import DEFAULT_CONFIG_REL_PATH
    print("\n=== RETRIEVAL INDEX ===")
    config_path = _REPO_ROOT / DEFAULT_CONFIG_REL_PATH
    idx = RetrievalIndex.from_config(config_path, repo_root=_REPO_ROOT)
    _ok("RetrievalIndex built",
        f"sha256={idx.manifest_sha256[:16]}... roles={idx.candidate_roles} top_k={idx.default_top_k}")
    return idx

# ── run batch ─────────────────────────────────────────────────────────────────

def run_batch(retrieval_index) -> None:
    from llm.authorization import authorize_phase1_run
    from llm.runner import App001Runner

    print(f"\n=== FORMAL BATCH: {BATCH_ID} ===")
    print(f"  36 logical runs  ×  up to 3 attempts  =  max 108 physical requests")
    print(f"  providers: DeepSeek/deepseek-flash (54)  +  Ollama/qwen3:8b (54)")
    print(f"  conditions: C0 (no retrieval)  +  C1 (RET-002 retrieval)")
    print(f"  C2 / IR / CAD / geometry / STEP: disabled")
    print()

    auth = authorize_phase1_run(batch_id=BATCH_ID)
    print(f"  authorization scope hash : {auth.scope_hash()}")
    print(f"  starting at              : {_utc_now()}")
    print()

    runner = App001Runner(retrieval_index=retrieval_index)
    t0 = time.monotonic()
    summary = runner.run_formal(auth)
    elapsed = time.monotonic() - t0

    _print_summary(summary, elapsed)

def _utc_now() -> str:
    from datetime import datetime, timezone
    return datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def _print_summary(summary, elapsed: float) -> None:
    print("\n=== BATCH SUMMARY ===")
    print(f"  batch_id          : {summary.batch_id}")
    print(f"  mode              : {summary.mode}")
    print(f"  planned_runs      : {summary.planned_runs}")
    print(f"  completed_runs    : {summary.completed_runs}")
    print(f"  successful_runs   : {summary.successful_runs}")
    print(f"  failed_runs       : {summary.failed_runs}")
    print(f"  blocked_runs      : {summary.blocked_runs}")
    print(f"  total_attempts    : {summary.total_attempts}")
    print(f"  elapsed_seconds   : {elapsed:.1f}")
    if summary.run_record_paths:
        print(f"  runs_jsonl        : {summary.run_record_paths[0]}")

    batch_dir = _REPO_ROOT / "work/app001-runs" / BATCH_ID
    runs_jsonl = batch_dir / "runs.jsonl"
    if runs_jsonl.exists():
        _print_jsonl_stats(runs_jsonl)

def _print_jsonl_stats(runs_jsonl: Path) -> None:
    records = []
    with open(runs_jsonl, encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if line:
                try:
                    records.append(json.loads(line))
                except json.JSONDecodeError:
                    pass

    print(f"\n=== RUN RECORD STATISTICS ({len(records)} records in {runs_jsonl.name}) ===")

    from collections import Counter
    provider_outcomes: dict[str, Counter] = {}
    condition_outcomes: dict[str, Counter] = {}
    decisions: Counter = Counter()
    schema_pass = schema_fail = schema_missing = 0
    raw_retained = raw_missing = 0

    for r in records:
        prov = r.get("provider") or r.get("configured_provider", "unknown")
        cond = r.get("condition_id", "unknown")
        outcome = r.get("final_outcome", "unknown")
        provider_outcomes.setdefault(prov, Counter())[outcome] += 1
        condition_outcomes.setdefault(cond, Counter())[outcome] += 1

        dec = r.get("decision") or (r.get("extracted_parameters") and "answer") or None
        if dec:
            decisions[dec] += 1

        for stage in r.get("stages", []):
            if isinstance(stage, dict) and stage.get("stage") == "schema":
                s = stage.get("status", "unknown")
                if s == "pass":
                    schema_pass += 1
                elif s in ("fail", "error"):
                    schema_fail += 1
                else:
                    schema_missing += 1

        if r.get("raw_response_path"):
            raw_retained += 1
        elif r.get("final_outcome") == "success":
            raw_missing += 1

    print(f"\n  Per-provider outcomes:")
    for prov in sorted(provider_outcomes):
        ctr = provider_outcomes[prov]
        total = sum(ctr.values())
        print(f"    {prov:20s}  total={total:3d}  " +
              "  ".join(f"{k}={v}" for k, v in sorted(ctr.items())))

    print(f"\n  Per-condition outcomes:")
    for cond in sorted(condition_outcomes):
        ctr = condition_outcomes[cond]
        total = sum(ctr.values())
        print(f"    {cond:6s}  total={total:3d}  " +
              "  ".join(f"{k}={v}" for k, v in sorted(ctr.items())))

    if decisions:
        print(f"\n  Decision distribution: " +
              "  ".join(f"{k}={v}" for k, v in sorted(decisions.items())))

    print(f"  Schema: pass={schema_pass}  fail={schema_fail}  other={schema_missing}")
    if raw_retained or raw_missing:
        print(f"  Raw retention: retained={raw_retained}  missing={raw_missing}")

# ── entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print(f"APP-001-V5-FORMAL-EFFECT-EVALUATION")
    print(f"batch_id  : {BATCH_ID}")
    print(f"baseline  : {BASELINE_COMMIT[:12]}")

    preflight()
    retrieval_index = build_retrieval_index()
    run_batch(retrieval_index)

    print(f"\n[DONE] {_utc_now()}")
    print(f"Append the run summary above to docs/WORKLOG.md and commit.")
