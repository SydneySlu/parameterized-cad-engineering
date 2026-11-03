#!/usr/bin/env python3
"""
RET-003 C1 检索级诊断脚本（规范版本）

修正项：
1. 使用正确的 results 字段（非 candidates）
2. 从正确层级读取 query.query_status
3. 从嵌套 error.error 对象读取 code/stage/fields
4. 五个合法查询各自跨独立进程复跑
5. fail-closed：任何失败都返回非零退出码
6. 环境门保护正式执行和 worker 模式（worker 先检查环境再加载数据）
7. 环境门可注入测试（验证不匹配环境被拒绝）
8. 规范输出路径（不使用 -v2 后缀）

只执行已获 Codex 中枢批准的 C1 检索级诊断：
- 3 个 held-out 主查询（逐例记录）
- 2 个接口诊断（分开报告）
- 1 个结构化失败诊断

不运行 C0、C2O 或公平 C2；不调权重；不声称端到端收益。
"""

import json
import sys
import hashlib
import subprocess
import os
import platform
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple


# 固定输入路径和预期值
MANIFEST_PATH = "agent-work/data/RET-001-retrieval-manifest/manifest-v0.jsonl"
MANIFEST_EXPECTED_SHA256 = "b7b6c737ec19986d005f3a2df3904929b1e05bb85d0efc35e6110112b2e7f297"
CONFIG_PATH = "agent-work/integration/RET-002-retrieval-baseline/retrieval-config.json"
QUERY_SET_PATH = "agent-work/integration/RET-003-retrieval-evaluation/query-set-draft.json"
PROTOCOL_VERSION = "RET-003.protocol.v0.1-draft"
QUERY_SET_VERSION = "RET-003.query-set.v0-draft"

# 规范输出路径（不再使用 -v2 后缀）
OUTPUT_JSON_PATH = "agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json"
OUTPUT_REPORT_PATH = "agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md"

# 环境要求
REQUIRED_PYTHON_VERSION = "3.11.18"
REQUIRED_PLATFORM = "darwin"
REQUIRED_MACHINE = "arm64"


def fail(message: str, exit_code: int = 1) -> None:
    """Fail-closed: 打印错误并退出"""
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(exit_code)


def check_environment_gate(mode: str = "formal",
                          injected_python: Optional[str] = None,
                          injected_platform: Optional[str] = None,
                          injected_machine: Optional[str] = None) -> Tuple[str, str, str]:
    """
    环境门：检查 Python 版本、平台和架构

    mode: "formal" 严格检查，"test" 仅记录
    injected_*: 用于测试的注入值（None 则使用实际环境）
    Returns: (python_version, platform_name, machine_arch)
    """
    # 获取实际或注入的环境值
    if injected_python is not None:
        python_version = injected_python
    else:
        python_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"

    if injected_platform is not None:
        platform_name = injected_platform
    else:
        platform_name = sys.platform

    if injected_machine is not None:
        machine_arch = injected_machine
    else:
        machine_arch = platform.machine()

    if mode == "test":
        # 测试模式：仅记录环境，不强制
        return python_version, platform_name, machine_arch

    # 正式模式：严格验证
    errors = []

    if python_version != REQUIRED_PYTHON_VERSION:
        errors.append(f"Python version mismatch: required {REQUIRED_PYTHON_VERSION}, got {python_version}")

    if platform_name != REQUIRED_PLATFORM:
        errors.append(f"Platform mismatch: required {REQUIRED_PLATFORM}, got {platform_name}")

    if machine_arch != REQUIRED_MACHINE:
        errors.append(f"Machine architecture mismatch: required {REQUIRED_MACHINE}, got {machine_arch}")

    if errors:
        print("Environment gate check FAILED:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        print("\nFormal C1 diagnostic requires Python 3.11.18 / macOS arm64.", file=sys.stderr)
        sys.exit(1)

    return python_version, platform_name, machine_arch


def compute_sha256(file_path: Path) -> str:
    """计算文件 SHA-256"""
    h = hashlib.sha256()
    with open(file_path, 'rb') as f:
        for chunk in iter(lambda: f.read(8192), b''):
            h.update(chunk)
    return h.hexdigest()


def load_manifest(manifest_path: Path) -> Dict[str, Any]:
    """加载 manifest 并构建 sample_id -> record 映射"""
    records = {}
    with open(manifest_path, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            record = json.loads(line)
            sample_id = record['sample_id']
            records[sample_id] = record
    return records


def parse_retrieval_error(exception: Exception) -> Dict[str, Any]:
    """
    解析 RetrievalError 的嵌套错误对象

    RET-002 错误结构：
    {
      "ok": false,
      "error": {
        "code": "...",
        "stage": "...",
        "fields": [...],
        "message": "...",
        "details": {...}
      }
    }
    """
    error_envelope = {}
    if hasattr(exception, 'as_dict'):
        error_envelope = exception.as_dict()

    # 从嵌套的 error 对象中提取
    nested_error = error_envelope.get('error', {})

    return {
        'code': nested_error.get('code'),
        'stage': nested_error.get('stage'),
        'fields': nested_error.get('fields'),
        'message': nested_error.get('message'),
        'details': nested_error.get('details'),
        'full_envelope': error_envelope
    }


def validate_error_structure(parsed_error: Dict[str, Any],
                            expected_code: str,
                            expected_stage: str,
                            expected_fields: List[str]) -> None:
    """
    严格验证错误结构
    """
    actual_code = parsed_error.get('code')
    actual_stage = parsed_error.get('stage')
    actual_fields = parsed_error.get('fields')

    if actual_code != expected_code:
        fail(f"Error code mismatch: expected {expected_code}, got {actual_code}")

    if actual_stage != expected_stage:
        fail(f"Error stage mismatch: expected {expected_stage}, got {actual_stage}")

    if actual_fields != expected_fields:
        fail(f"Error fields mismatch: expected {expected_fields}, got {actual_fields}")


def run_single_query_worker(sample_id: str, manifest_records: Dict[str, Any],
                            config_path: str) -> Dict[str, Any]:
    """
    Worker 模式：运行单个查询并返回 canonical 结果
    用于独立进程复跑

    Worker 模式也需要环境门保护
    """
    sys.path.insert(0, 'src')
    from retrieval import RetrievalIndex

    if sample_id not in manifest_records:
        fail(f"sample_id not found in manifest: {sample_id}")

    record = manifest_records[sample_id]
    params = record['parameters']['normalized']

    # 构建索引并查询
    index = RetrievalIndex.from_config(config_path)
    result = index.query(
        family_id="set_screw_shaft_collar",
        parameters=params,
        top_k=3
    )

    # 返回 canonical JSON（无时间戳、稳定排序）
    return json.loads(result.to_canonical_json())


def run_query_with_cross_process_check(query_id: str, sample_id: str,
                                       manifest_records: Dict[str, Any]) -> Dict[str, Any]:
    """
    运行查询并进行独立进程确定性检查
    """
    record = manifest_records[sample_id]
    params = record['parameters']['normalized']
    split_role = record['split']['role']

    # 第一次运行（主进程）
    sys.path.insert(0, 'src')
    from retrieval import RetrievalIndex

    index = RetrievalIndex.from_config(CONFIG_PATH)

    try:
        result = index.query(
            family_id="set_screw_shaft_collar",
            parameters=params,
            top_k=3
        )
    except Exception as e:
        # 查询失败
        parsed_error = parse_retrieval_error(e)

        return {
            "query_id": query_id,
            "sample_id": sample_id,
            "split_role": split_role,
            "error": parsed_error,
            "error_type": type(e).__name__
        }

    # 序列化结果
    result_dict = json.loads(result.to_json())
    canonical_json = result.to_canonical_json()
    run1_sha = result.sha256()

    # 第二次运行（独立进程）
    worker_cmd = [
        sys.executable,
        __file__,
        '--worker-single-query',
        sample_id
    ]

    try:
        proc = subprocess.run(
            worker_cmd,
            capture_output=True,
            text=True,
            timeout=60,
            cwd=os.getcwd(),
            env={**os.environ, 'PYTHONPATH': 'src'}
        )

        if proc.returncode != 0:
            fail(f"Worker process failed for {sample_id}: {proc.stderr}")

        run2_canonical = proc.stdout.strip()
        run2_dict = json.loads(run2_canonical)
        run2_sha = hashlib.sha256(run2_canonical.encode('utf-8')).hexdigest()

        deterministic = (run1_sha == run2_sha)

        if not deterministic:
            fail(f"Cross-process determinism check failed for {sample_id}: "
                 f"run1={run1_sha[:16]}... run2={run2_sha[:16]}...")

    except subprocess.TimeoutExpired:
        fail(f"Worker process timeout for {sample_id}")
    except Exception as e:
        fail(f"Worker process error for {sample_id}: {e}")

    # 使用正确的 results 字段（不是 candidates）
    results_list = result_dict.get('results', [])
    if not results_list:
        fail(f"Query {query_id} returned empty results list")

    # 从正确层级读取 query_status
    query_status = result_dict.get('query', {}).get('query_status')
    if query_status is None:
        fail(f"Query {query_id} has null query_status")

    # 对主查询：计算逐候选相对真值的字段误差
    if split_role == "heldout_evaluation":
        truth_params = params
        for cand in results_list:
            cand_params = cand['parameters']['normalized']
            field_errors = {}
            for field in ['bore_d', 'outer_d', 'screw_d', 'screw_len', 'width', 'second_screw']:
                truth_val = truth_params[field]
                cand_val = cand_params[field]
                field_errors[field] = abs(cand_val - truth_val)
            cand['absolute_error_vs_query_truth'] = field_errors

    # 验证候选角色
    for cand in results_list:
        cand_role = cand.get('split', {}).get('role')
        if cand_role != 'retrieval_source':
            fail(f"Invalid candidate role {cand_role} in query {query_id}, expected retrieval_source")

    return {
        "query_id": query_id,
        "sample_id": sample_id,
        "split_role": split_role,
        "query_status": query_status,
        "result": result_dict,
        "determinism": {
            "run1_sha256": run1_sha,
            "run2_sha256": run2_sha,
            "cross_process_deterministic": deterministic
        }
    }


def run_failure_diagnostic(manifest_records: Dict[str, Any]) -> Dict[str, Any]:
    """
    结构化失败诊断：从 catalog-bore-020 复制参数后删除 outer_d

    严格验证嵌套错误对象的 code/stage/fields
    """
    base_sample_id = "set_screw_shaft_collar/catalog-bore-020"
    if base_sample_id not in manifest_records:
        fail(f"Base sample not found: {base_sample_id}")

    params = manifest_records[base_sample_id]['parameters']['normalized'].copy()
    del params['outer_d']  # 删除一个字段

    sys.path.insert(0, 'src')
    from retrieval import RetrievalIndex

    index = RetrievalIndex.from_config(CONFIG_PATH)

    try:
        result = index.query(
            family_id="set_screw_shaft_collar",
            parameters=params,
            top_k=3
        )
        # 不应该成功
        fail("Failure diagnostic unexpectedly succeeded (missing outer_d should fail)")

    except Exception as e:
        # 解析嵌套错误对象
        parsed_error = parse_retrieval_error(e)

        # 严格验证 code, stage, fields
        expected_code = "RETRIEVAL_MISSING_FIELD"
        expected_stage = "query"
        expected_fields = ["outer_d"]

        validate_error_structure(parsed_error, expected_code, expected_stage, expected_fields)

        return {
            "query_id": "diagnostic-missing-field-from-bore-020",
            "base_sample_id": base_sample_id,
            "transformation": "remove normalized.outer_d at runtime",
            "expected_error": expected_code,
            "actual_error": parsed_error['code'],
            "error_details": parsed_error['full_envelope'],
            "code": parsed_error['code'],
            "stage": parsed_error['stage'],
            "fields": parsed_error['fields']
        }


def test_environment_gate_logic() -> None:
    """
    测试环境门逻辑（可注入环境值）

    验证：
    1. 正确环境通过
    2. Python 版本不匹配被拒绝
    3. 平台不匹配被拒绝
    4. 架构不匹配被拒绝
    """
    print("  Test 5: environment gate logic (injected values)")

    # 子测试 1: 正确环境应通过
    try:
        py_ver, plat, mach = check_environment_gate(
            mode="formal",
            injected_python="3.11.18",
            injected_platform="darwin",
            injected_machine="arm64"
        )
        print("    ✓ Correct environment accepted (3.11.18/darwin/arm64)")
    except SystemExit:
        fail("Environment gate rejected correct environment")

    # 子测试 2: Python 版本不匹配应拒绝
    try:
        check_environment_gate(
            mode="formal",
            injected_python="3.10.12",
            injected_platform="darwin",
            injected_machine="arm64"
        )
        fail("Environment gate should reject Python 3.10.12")
    except SystemExit as e:
        if e.code == 1:
            print("    ✓ Python version mismatch rejected (3.10.12)")
        else:
            fail(f"Wrong exit code for Python mismatch: {e.code}")

    # 子测试 3: 平台不匹配应拒绝
    try:
        check_environment_gate(
            mode="formal",
            injected_python="3.11.18",
            injected_platform="linux",
            injected_machine="arm64"
        )
        fail("Environment gate should reject linux platform")
    except SystemExit as e:
        if e.code == 1:
            print("    ✓ Platform mismatch rejected (linux)")
        else:
            fail(f"Wrong exit code for platform mismatch: {e.code}")

    # 子测试 4: 架构不匹配应拒绝
    try:
        check_environment_gate(
            mode="formal",
            injected_python="3.11.18",
            injected_platform="darwin",
            injected_machine="x86_64"
        )
        fail("Environment gate should reject x86_64 architecture")
    except SystemExit as e:
        if e.code == 1:
            print("    ✓ Machine architecture mismatch rejected (x86_64)")
        else:
            fail(f"Wrong exit code for architecture mismatch: {e.code}")


def contract_test() -> None:
    """
    契约测试：验证关键接口行为和错误解析

    契约测试在当前环境运行（test 模式），不写正式输出
    """
    print("Running contract tests...")

    # 记录环境（test 模式，不强制）
    python_ver, platform_name, machine = check_environment_gate(mode="test")
    print(f"  Test environment: Python {python_ver} / {platform_name} {machine}")

    sys.path.insert(0, 'src')
    from retrieval import RetrievalIndex

    # 加载 manifest
    manifest_records = load_manifest(Path(MANIFEST_PATH))
    index = RetrievalIndex.from_config(CONFIG_PATH)

    # Test 1: results 字段存在且非空
    print("  Test 1: results field exists and non-empty")
    result = index.query(
        family_id="set_screw_shaft_collar",
        parameters=manifest_records["set_screw_shaft_collar/catalog-bore-020"]['parameters']['normalized'],
        top_k=3
    )
    result_dict = json.loads(result.to_json())

    if 'results' not in result_dict:
        fail("Contract test failed: 'results' field not found in result")

    if not result_dict['results']:
        fail("Contract test failed: 'results' list is empty")

    print(f"    ✓ results field exists with {len(result_dict['results'])} candidates")

    # Test 2: query_status 从正确层级读取
    print("  Test 2: query_status at correct level")
    query_status = result_dict.get('query', {}).get('query_status')

    if query_status is None:
        fail("Contract test failed: query_status is None (wrong level?)")

    print(f"    ✓ query_status = {query_status}")

    # Test 3: 缺字段拒绝并返回正确的嵌套错误结构
    print("  Test 3: missing field rejection with correct error structure")
    try:
        params_missing = manifest_records["set_screw_shaft_collar/catalog-bore-020"]['parameters']['normalized'].copy()
        del params_missing['bore_d']
        result_fail = index.query(
            family_id="set_screw_shaft_collar",
            parameters=params_missing,
            top_k=3
        )
        fail("Contract test failed: missing field should be rejected")
    except Exception as e:
        parsed_error = parse_retrieval_error(e)

        # 验证嵌套结构
        if parsed_error['code'] != 'RETRIEVAL_MISSING_FIELD':
            fail(f"Contract test failed: expected RETRIEVAL_MISSING_FIELD, got {parsed_error['code']}")

        if parsed_error['stage'] != 'query':
            fail(f"Contract test failed: expected stage=query, got {parsed_error['stage']}")

        if 'bore_d' not in parsed_error['fields']:
            fail(f"Contract test failed: expected fields to contain 'bore_d', got {parsed_error['fields']}")

        print(f"    ✓ missing field correctly rejected")
        print(f"      code={parsed_error['code']}, stage={parsed_error['stage']}, fields={parsed_error['fields']}")

    # Test 4: 候选角色纯度
    print("  Test 4: candidate role purity")
    for cand in result_dict['results']:
        role = cand.get('split', {}).get('role')
        if role != 'retrieval_source':
            fail(f"Contract test failed: invalid candidate role {role}")
    print(f"    ✓ all candidates have role=retrieval_source")

    # Test 5: 环境门逻辑（可注入测试）
    test_environment_gate_logic()

    print("Contract tests PASSED\n")


def main():
    """主执行流程"""
    # Worker 模式：单查询执行（先检查环境门再加载数据）
    if len(sys.argv) > 1 and sys.argv[1] == '--worker-single-query':
        if len(sys.argv) != 3:
            fail("Worker mode requires sample_id")

        # Worker 先检查环境门，再加载 manifest
        check_environment_gate(mode="formal")

        sample_id = sys.argv[2]
        manifest_records = load_manifest(Path(MANIFEST_PATH))
        canonical_result = run_single_query_worker(sample_id, manifest_records, CONFIG_PATH)

        # 输出 canonical JSON（无额外空格）
        print(json.dumps(canonical_result, sort_keys=True, separators=(',', ':')))
        return 0

    # 契约测试模式（test 环境，不写正式输出）
    if len(sys.argv) > 1 and sys.argv[1] == '--contract-test':
        contract_test()
        return 0

    # 主诊断流程（需要环境门）
    print("RET-003 C1 检索级诊断（规范版本）")
    print("=" * 60)

    # 环境门：检查 Python 3.11.18 / macOS arm64
    print("\n环境门检查...")
    python_ver, platform_name, machine = check_environment_gate(mode="formal")
    print(f"  Python: {python_ver} ✓")
    print(f"  Platform: {platform_name} ✓")
    print(f"  Machine: {machine} ✓")

    # 1. 校验 manifest hash
    manifest_path = Path(MANIFEST_PATH)
    print(f"\n1. 校验 manifest hash...")
    actual_sha256 = compute_sha256(manifest_path)
    print(f"   预期: {MANIFEST_EXPECTED_SHA256}")
    print(f"   实际: {actual_sha256}")

    if actual_sha256 != MANIFEST_EXPECTED_SHA256:
        fail(f"Manifest hash mismatch")
    print(f"   ✓ PASS")

    # 2. 运行契约测试
    print(f"\n2. 契约测试（在正式环境验证）...")
    contract_test()

    # 3. 加载查询集
    print(f"3. 加载查询集...")
    with open(QUERY_SET_PATH, 'r', encoding='utf-8') as f:
        query_set = json.load(f)

    print(f"   协议版本: {PROTOCOL_VERSION}")
    print(f"   查询集版本: {query_set['query_set_version']}")
    print(f"   主查询: {len(query_set['primary_queries'])}")
    print(f"   诊断查询: {len(query_set['diagnostic_queries'])}")
    print(f"   失败诊断: {len(query_set['failure_diagnostics'])}")

    # 4. 加载 manifest
    print(f"\n4. 加载 manifest...")
    manifest_records = load_manifest(manifest_path)
    print(f"   记录数: {len(manifest_records)}")

    # 5. 运行 3 个主查询（带独立进程确定性检查）
    print(f"\n5. 运行主查询（带独立进程确定性检查）...")
    primary_results = []
    for q in query_set['primary_queries']:
        query_id = q['query_id']
        sample_id = q['sample_id']
        print(f"   查询: {query_id} ({sample_id})")

        result = run_query_with_cross_process_check(query_id, sample_id, manifest_records)
        primary_results.append(result)

        if 'error' in result:
            fail(f"Primary query {query_id} failed: {result['error']}")

        top1_id = result['result']['results'][0]['sample_id']
        print(f"      top-1: {top1_id}")
        print(f"      状态: {result['query_status']}")
        print(f"      确定性: ✓")

    # 6. 运行 2 个接口诊断（带独立进程确定性检查）
    print(f"\n6. 运行接口诊断（带独立进程确定性检查）...")
    diagnostic_results = []
    for q in query_set['diagnostic_queries']:
        query_id = q['query_id']
        sample_id = q['sample_id']
        print(f"   诊断: {query_id} ({sample_id})")

        result = run_query_with_cross_process_check(query_id, sample_id, manifest_records)
        diagnostic_results.append(result)

        if 'error' in result:
            fail(f"Diagnostic query {query_id} failed: {result['error']}")

        top1_id = result['result']['results'][0]['sample_id']
        print(f"      top-1: {top1_id}")
        print(f"      确定性: ✓")

    # 7. 运行失败诊断
    print(f"\n7. 运行失败诊断...")
    failure_result = run_failure_diagnostic(manifest_records)
    print(f"   预期错误: {failure_result['expected_error']}")
    print(f"   实际错误: {failure_result['actual_error']}")
    print(f"   Stage: {failure_result['stage']}")
    print(f"   Fields: {failure_result['fields']}")
    print(f"   ✓ PASS")

    # 8. 输出结果文件
    print(f"\n8. 输出结果...")
    output = {
        "protocol_version": PROTOCOL_VERSION,
        "query_set_version": QUERY_SET_VERSION,
        "manifest_sha256": actual_sha256,
        "policy_id": "RET-002.parametric_distance.v1",
        "split_status": "provisional_small_n",
        "environment": {
            "python_version": python_ver,
            "platform": platform_name,
            "machine": machine
        },
        "primary_queries": primary_results,
        "diagnostic_queries": diagnostic_results,
        "failure_diagnostic": failure_result,
        "notes": [
            "This is C1 retrieval-level diagnostic only.",
            "Distance represents parameter proximity, not geometric equivalence.",
            "split_status=provisional_small_n is not a frozen benchmark.",
            "Endpoint-level metrics (Schema/CAD/STEP) are not_measured until APP-001.",
            "Each legal query executed with cross-process determinism check.",
            "Failure diagnostic validates nested error.error.{code,stage,fields}."
        ]
    }

    output_path = Path(OUTPUT_JSON_PATH)
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"   ✓ 已写入: {output_path}")

    print(f"\n✓ C1 诊断完成（规范版本）")
    return 0


if __name__ == "__main__":
    sys.exit(main())
