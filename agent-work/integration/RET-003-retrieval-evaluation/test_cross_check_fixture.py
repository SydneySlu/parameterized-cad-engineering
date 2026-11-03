#!/usr/bin/env python3
"""
临时 fixture 测试：验证 cross_check.py 对异常 JSON 的边界处理

测试场景（至少 8 项）：
1. 合法 JSON + 报告：通过
2. failure_diagnostic 为 null
3. failure_diagnostic 为字符串
4. failure_diagnostic 为列表
5. 缺少 code/stage/fields
6. code/stage 为非字符串类型
7. code/stage 为空字符串
8. fields 为非列表类型
9. fields 包含非字符串元素
10. fields 包含空字符串元素
11. code 值与报告不一致
12. stage 值与报告不一致
13. fields 值与报告不一致
14. 报告 stage 篡改
15. 报告 fields 篡改

不修改仓库中的正式 JSON/报告
"""

import json
import tempfile
import subprocess
import sys
from pathlib import Path


def create_minimal_valid_json(temp_dir: Path) -> Path:
    """创建最小合法 JSON"""
    data = {
        "primary_queries": [
            {
                "query_id": "test-query-1",
                "sample_id": "test/sample-1",
                "query_status": "test_status",
                "result": {
                    "results": [
                        {
                            "sample_id": "test/candidate-1",
                            "distance": {"total": 0.123456}
                        }
                    ]
                },
                "determinism": {"cross_process_deterministic": True}
            }
        ],
        "diagnostic_queries": [],
        "failure_diagnostic": {
            "code": "RETRIEVAL_MISSING_FIELD",
            "stage": "query",
            "fields": ["outer_d"]
        }
    }

    json_path = temp_dir / "test.json"
    with open(json_path, 'w') as f:
        json.dump(data, f, indent=2)

    return json_path


def create_minimal_valid_report(temp_dir: Path) -> Path:
    """创建最小合法报告"""
    report_lines = [
        "# Test Report",
        "",
        "## 2. 主查询结果",
        "",
        "### 2.1 test-query-1",
        "",
        "- **查询样本**: `test/sample-1`",
        "- **Query status**: `test_status`",
        "",
        "**Top-3 候选**:",
        "",
        "| Rank | Sample ID | Total Distance |",
        "|---:|---|---:|",
        "| 1 | test/candidate-1 | 0.123456 |",
        "",
        "## 4. 结构化失败诊断",
        "",
        "- **Code**: `RETRIEVAL_MISSING_FIELD`",
        "- **Stage**: `query`",
        "- **Fields**: `['outer_d']`",
        "",
        "## 5. 确定性验证",
        "",
        "✓ PASS",
        "",
        "## 6. 候选角色纯度",
        "",
        "**候选总数**: 1",
        "",
        "## 9.2 逐例主查询摘要",
        "",
        "| Query ID | Truth Sample | Query Status | Top-1 | Top-1 Distance | Deterministic |",
        "|---|---|---|---|---:|---|",
        "| test-query-1 | sample-1 | test_status | candidate-1 | 0.123456 | ✓ |",
        "",
    ]

    report_path = temp_dir / "test-report.md"
    with open(report_path, 'w') as f:
        f.write('\n'.join(report_lines))

    return report_path


def run_cross_check_on_files(json_path: Path, report_path: Path) -> tuple:
    """运行 cross_check.py 并返回 (exit_code, stdout, stderr)"""
    # 临时修改 cross_check.py 中的路径
    cross_check_code = Path("agent-work/integration/RET-003-retrieval-evaluation/cross_check.py").read_text()

    # 创建临时脚本，替换默认路径
    temp_script = tempfile.NamedTemporaryFile(mode='w', suffix='.py', delete=False)
    modified_code = cross_check_code.replace(
        'json_path = Path("agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json")',
        f'json_path = Path("{json_path}")'
    ).replace(
        'report_path = Path("agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md")',
        f'report_path = Path("{report_path}")'
    )

    temp_script.write(modified_code)
    temp_script.close()

    result = subprocess.run(
        [sys.executable, temp_script.name, '--no-self-test'],
        capture_output=True,
        text=True
    )

    Path(temp_script.name).unlink()

    return result.returncode, result.stdout, result.stderr


def main():
    print("临时 fixture 测试：cross_check.py 边界处理")
    print("=" * 60)

    test_count = 0
    pass_count = 0

    with tempfile.TemporaryDirectory() as temp_dir:
        temp_path = Path(temp_dir)

        # 测试 1: 合法 JSON + 报告应通过
        test_count += 1
        print(f"\n测试 {test_count}: 合法 JSON + 报告")
        json_path = create_minimal_valid_json(temp_path)
        report_path = create_minimal_valid_report(temp_path)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code == 0:
            print("  ✓ 合法输入通过")
            pass_count += 1
        else:
            print(f"  ❌ 合法输入应通过，但返回 {exit_code}")
            print(f"  输出: {stdout[:200]}")
            return 1

        # 测试 2: failure_diagnostic 为 null
        test_count += 1
        print(f"\n测试 {test_count}: failure_diagnostic 为 null")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic'] = None
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "缺少 failure_diagnostic 字段" in stdout:
            print("  ✓ failure_diagnostic=null 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 null，exit_code={exit_code}")
            return 1

        # 测试 3: failure_diagnostic 为字符串
        test_count += 1
        print(f"\n测试 {test_count}: failure_diagnostic 为字符串")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic'] = "invalid"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "类型错误" in stdout and "期望 dict" in stdout:
            print("  ✓ failure_diagnostic=字符串 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝字符串类型，exit_code={exit_code}")
            return 1

        # 测试 4: failure_diagnostic 为列表
        test_count += 1
        print(f"\n测试 {test_count}: failure_diagnostic 为列表")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic'] = ["invalid"]
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "类型错误" in stdout and "期望 dict" in stdout:
            print("  ✓ failure_diagnostic=列表 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝列表类型，exit_code={exit_code}")
            return 1

        # 测试 5: 缺少 code
        test_count += 1
        print(f"\n测试 {test_count}: 缺少 code")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        del data['failure_diagnostic']['code']
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "缺少 'code' 字段" in stdout:
            print("  ✓ 缺少 code 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝缺少 code，exit_code={exit_code}")
            return 1

        # 测试 6: 缺少 stage
        test_count += 1
        print(f"\n测试 {test_count}: 缺少 stage")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        del data['failure_diagnostic']['stage']
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "缺少 'stage' 字段" in stdout:
            print("  ✓ 缺少 stage 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝缺少 stage，exit_code={exit_code}")
            return 1

        # 测试 7: 缺少 fields
        test_count += 1
        print(f"\n测试 {test_count}: 缺少 fields")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        del data['failure_diagnostic']['fields']
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "缺少 'fields' 字段" in stdout:
            print("  ✓ 缺少 fields 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝缺少 fields，exit_code={exit_code}")
            return 1

        # 测试 8: code 为整数
        test_count += 1
        print(f"\n测试 {test_count}: code 为整数类型")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['code'] = 123
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'code' 类型错误" in stdout and "期望 str" in stdout:
            print("  ✓ code=整数 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 code 类型错误，exit_code={exit_code}")
            return 1

        # 测试 9: stage 为整数
        test_count += 1
        print(f"\n测试 {test_count}: stage 为整数类型")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['stage'] = 456
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'stage' 类型错误" in stdout and "期望 str" in stdout:
            print("  ✓ stage=整数 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 stage 类型错误，exit_code={exit_code}")
            return 1

        # 测试 10: code 为空字符串
        test_count += 1
        print(f"\n测试 {test_count}: code 为空字符串")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['code'] = ""
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'code' 为空字符串" in stdout:
            print("  ✓ code=空字符串 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 code 空字符串，exit_code={exit_code}")
            return 1

        # 测试 11: stage 为空字符串
        test_count += 1
        print(f"\n测试 {test_count}: stage 为空字符串")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['stage'] = ""
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'stage' 为空字符串" in stdout:
            print("  ✓ stage=空字符串 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 stage 空字符串，exit_code={exit_code}")
            return 1

        # 测试 12: fields 为字符串（而非列表）
        test_count += 1
        print(f"\n测试 {test_count}: fields 为字符串（非列表）")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['fields'] = "outer_d"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'fields' 类型错误" in stdout and "期望 list" in stdout:
            print("  ✓ fields=字符串 被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 fields 类型错误，exit_code={exit_code}")
            return 1

        # 测试 13: fields 包含整数元素
        test_count += 1
        print(f"\n测试 {test_count}: fields 包含整数元素")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['fields'] = ["outer_d", 123]
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'fields[1]' 类型错误" in stdout and "期望 str" in stdout:
            print("  ✓ fields 含非字符串元素被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 fields 元素类型错误，exit_code={exit_code}")
            return 1

        # 测试 14: fields 包含空字符串元素
        test_count += 1
        print(f"\n测试 {test_count}: fields 包含空字符串元素")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['fields'] = ["outer_d", ""]
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "'fields[1]' 为空字符串" in stdout:
            print("  ✓ fields 含空字符串元素被明确拒绝")
            pass_count += 1
        else:
            print(f"  ❌ 应拒绝 fields 空元素，exit_code={exit_code}")
            return 1

        # 测试 15: code 值与报告不一致
        test_count += 1
        print(f"\n测试 {test_count}: code 值与报告不一致")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['code'] = "DIFFERENT_ERROR_CODE"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "code 不在报告中" in stdout:
            print("  ✓ code 值不一致被检测")
            pass_count += 1
        else:
            print(f"  ❌ 应检测 code 不一致，exit_code={exit_code}")
            return 1

        # 测试 16: stage 值与报告不一致
        test_count += 1
        print(f"\n测试 {test_count}: stage 值与报告不一致")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['stage'] = "config"
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "stage 不匹配" in stdout:
            print("  ✓ stage 值不一致被检测")
            pass_count += 1
        else:
            print(f"  ❌ 应检测 stage 不一致，exit_code={exit_code}")
            return 1

        # 测试 17: fields 值与报告不一致
        test_count += 1
        print(f"\n测试 {test_count}: fields 值与报告不一致")
        json_path = create_minimal_valid_json(temp_path)
        with open(json_path, 'r') as f:
            data = json.load(f)
        data['failure_diagnostic']['fields'] = ["bore_d", "width"]
        with open(json_path, 'w') as f:
            json.dump(data, f, indent=2)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "fields 不匹配" in stdout:
            print("  ✓ fields 值不一致被检测")
            pass_count += 1
        else:
            print(f"  ❌ 应检测 fields 不一致，exit_code={exit_code}")
            return 1

        # 测试 18: 报告 stage 篡改（使用合法 JSON）
        test_count += 1
        print(f"\n测试 {test_count}: 报告 stage 篡改")
        json_path = create_minimal_valid_json(temp_path)
        report_path = create_minimal_valid_report(temp_path)

        # 篡改报告
        report_text = report_path.read_text()
        mutated_report = report_text.replace('**Stage**: `query`', '**Stage**: `index`')
        report_path.write_text(mutated_report)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "stage 不匹配" in stdout:
            print("  ✓ 报告 stage 篡改被检测")
            pass_count += 1
        else:
            print(f"  ❌ 应检测 stage 篡改，exit_code={exit_code}")
            return 1

        # 测试 19: 报告 fields 篡改
        test_count += 1
        print(f"\n测试 {test_count}: 报告 fields 篡改")
        json_path = create_minimal_valid_json(temp_path)
        report_path = create_minimal_valid_report(temp_path)

        # 篡改报告
        report_text = report_path.read_text()
        mutated_report = report_text.replace("**Fields**: `['outer_d']`", "**Fields**: `['bore_d']`")
        report_path.write_text(mutated_report)

        exit_code, stdout, stderr = run_cross_check_on_files(json_path, report_path)

        if exit_code != 0 and "fields 不匹配" in stdout:
            print("  ✓ 报告 fields 篡改被检测")
            pass_count += 1
        else:
            print(f"  ❌ 应检测 fields 篡改，exit_code={exit_code}")
            return 1

    print("\n" + "=" * 60)
    print(f"✓ 所有测试通过: {pass_count}/{test_count}")
    print("\n覆盖场景:")
    print("  - 合法输入通过")
    print("  - failure_diagnostic 类型验证（null/字符串/列表）")
    print("  - 缺少 code/stage/fields")
    print("  - code/stage 类型错误（整数）")
    print("  - code/stage 空字符串")
    print("  - fields 类型错误（字符串）")
    print("  - fields 元素类型错误（整数）")
    print("  - fields 元素为空字符串")
    print("  - code/stage/fields 值与报告不一致")
    print("  - 报告 stage/fields 篡改")
    return 0


if __name__ == "__main__":
    sys.exit(main())
