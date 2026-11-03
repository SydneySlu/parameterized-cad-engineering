#!/usr/bin/env python3
"""
交叉核对：验证 Markdown 报告与 JSON 结果的一致性

增强验证：
1. 主查询摘要表和详细章节
2. 候选数量
3. 失败诊断的 code/stage/fields 逐字段验证（增强错误处理）
4. 确定性验证
5. 负例测试：篡改报告中的 stage/fields，验证能检测出不一致

规范路径：
- 输入 JSON：c1-diagnostic-results.json
- 输入报告：c1-diagnostic-report.md
"""

import json
import re
import sys
import tempfile
import shutil
from pathlib import Path
from typing import List, Tuple, Optional


def extract_table_values(report_text: str, section: str) -> list:
    """从报告中提取表格值"""
    lines = report_text.split('\n')
    in_section = False
    values = []

    for line in lines:
        if section in line:
            in_section = True
        elif in_section and line.startswith('|') and not line.startswith('|---'):
            # 跳过表头
            if 'Query ID' in line or 'Rank' in line:
                continue
            values.append(line)
        elif in_section and line.startswith('##') and section not in line:
            break

    return values


def check_failure_diagnostic(data: dict, report: str) -> List[str]:
    """
    严格验证失败诊断的 code/stage/fields

    增强边界验证：
    - failure_diagnostic 必须是 dict
    - code/stage 必须是非空字符串
    - fields 必须是字符串列表，元素非空
    - 所有值必须与报告一致
    对缺失、类型错误、空值、不一致均返回清楚的错误消息，不抛出异常
    """
    errors = []

    # 验证 failure_diagnostic 存在且为 dict
    fail_diag = data.get('failure_diagnostic')
    if fail_diag is None:
        errors.append("JSON 缺少 failure_diagnostic 字段")
        return errors

    if not isinstance(fail_diag, dict):
        errors.append(f"JSON failure_diagnostic 类型错误: 期望 dict，实际 {type(fail_diag).__name__}")
        return errors

    # 提取失败诊断章节
    section_match = re.search(r'## 4\. 结构化失败诊断.*?(?=\n##|\Z)', report, re.DOTALL)
    if not section_match:
        errors.append("失败诊断章节未找到")
        return errors

    section_text = section_match.group(0)

    # 验证 code
    if 'code' not in fail_diag:
        errors.append("JSON failure_diagnostic 缺少 'code' 字段")
    else:
        expected_code = fail_diag['code']

        if not isinstance(expected_code, str):
            errors.append(f"JSON failure_diagnostic 'code' 类型错误: 期望 str，实际 {type(expected_code).__name__}")
        elif not expected_code:
            errors.append("JSON failure_diagnostic 'code' 为空字符串")
        elif f"**Code**: `{expected_code}`" not in section_text:
            errors.append(f"失败诊断 code 不在报告中: 期望 `{expected_code}`")

    # 验证 stage
    if 'stage' not in fail_diag:
        errors.append("JSON failure_diagnostic 缺少 'stage' 字段")
    else:
        expected_stage = fail_diag['stage']

        if not isinstance(expected_stage, str):
            errors.append(f"JSON failure_diagnostic 'stage' 类型错误: 期望 str，实际 {type(expected_stage).__name__}")
        elif not expected_stage:
            errors.append("JSON failure_diagnostic 'stage' 为空字符串")
        elif f"**Stage**: `{expected_stage}`" not in section_text:
            errors.append(f"失败诊断 stage 不匹配: 期望 `{expected_stage}`")

    # 验证 fields
    if 'fields' not in fail_diag:
        errors.append("JSON failure_diagnostic 缺少 'fields' 字段")
    else:
        expected_fields = fail_diag['fields']

        if not isinstance(expected_fields, list):
            errors.append(f"JSON failure_diagnostic 'fields' 类型错误: 期望 list，实际 {type(expected_fields).__name__}")
        else:
            # 验证 fields 列表元素
            for i, field in enumerate(expected_fields):
                if not isinstance(field, str):
                    errors.append(f"JSON failure_diagnostic 'fields[{i}]' 类型错误: 期望 str，实际 {type(field).__name__}")
                elif not field:
                    errors.append(f"JSON failure_diagnostic 'fields[{i}]' 为空字符串")

            # 如果元素类型都正确，检查与报告的一致性
            if not any("fields[" in e for e in errors):
                if f"**Fields**: `{expected_fields}`" not in section_text:
                    errors.append(f"失败诊断 fields 不匹配: 期望 `{expected_fields}`")

    return errors


def mutate_report_stage(report_text: str) -> str:
    """
    变异报告：篡改失败诊断的 stage
    """
    # 将 stage: query 改为 stage: index
    return report_text.replace('**Stage**: `query`', '**Stage**: `index`')


def mutate_report_fields(report_text: str) -> str:
    """
    变异报告：篡改失败诊断的 fields
    """
    # 将 fields: ['outer_d'] 改为 fields: ['bore_d']
    return report_text.replace("**Fields**: `['outer_d']`", "**Fields**: `['bore_d']`")


def run_self_test(json_path: Path, report_path: Path) -> Tuple[bool, List[str]]:
    """
    自测：验证交叉核对能检测出报告变异

    1. 验证原始报告通过
    2. 变异 stage，验证检测失败
    3. 变异 fields，验证检测失败
    """
    print("\n自测：负例验证")
    print("-" * 60)

    with open(json_path, 'r') as f:
        data = json.load(f)

    with open(report_path, 'r') as f:
        original_report = f.read()

    # 测试 1: 原始报告应该通过
    print("  测试 1: 原始报告")
    errors = check_failure_diagnostic(data, original_report)
    if errors:
        print(f"    ❌ 原始报告检查失败: {errors}")
        return False, ["原始报告本应通过，但检测到错误"]

    print("    ✓ 原始报告通过")

    # 测试 2: 篡改 stage 应该失败
    print("  测试 2: 篡改 stage (query → index)")
    mutated_stage = mutate_report_stage(original_report)
    errors_stage = check_failure_diagnostic(data, mutated_stage)

    if not errors_stage:
        print("    ❌ 未检测到 stage 篡改")
        return False, ["stage 变异未被检测"]

    print(f"    ✓ 检测到 stage 不一致")

    # 测试 3: 篡改 fields 应该失败
    print("  测试 3: 篡改 fields (['outer_d'] → ['bore_d'])")
    mutated_fields = mutate_report_fields(original_report)
    errors_fields = check_failure_diagnostic(data, mutated_fields)

    if not errors_fields:
        print("    ❌ 未检测到 fields 篡改")
        return False, ["fields 变异未被检测"]

    print(f"    ✓ 检测到 fields 不一致")

    print("\n自测通过：交叉核对能正确检测 stage 和 fields 变异")
    return True, []


def main(run_self_test_flag: bool = True):
    json_path = Path("agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-results.json")
    report_path = Path("agent-work/integration/RET-003-retrieval-evaluation/c1-diagnostic-report.md")

    print("交叉核对：JSON vs 报告")
    print("=" * 60)

    # 检查文件存在
    if not json_path.exists():
        print(f"ERROR: JSON 文件不存在: {json_path}", file=sys.stderr)
        return 1

    if not report_path.exists():
        print(f"ERROR: 报告文件不存在: {report_path}", file=sys.stderr)
        return 1

    # 加载 JSON
    try:
        with open(json_path, 'r') as f:
            data = json.load(f)
    except json.JSONDecodeError as e:
        print(f"ERROR: JSON 解析失败: {e}", file=sys.stderr)
        return 1

    # 加载报告
    with open(report_path, 'r') as f:
        report = f.read()

    errors = []

    # 检查 1: 主查询逐例摘要表
    print("\n检查 1: 主查询逐例摘要表")
    summary_section = extract_table_values(report, "9.2 逐例主查询摘要")

    primary_queries = data.get('primary_queries', [])
    if len(summary_section) != len(primary_queries):
        errors.append(f"摘要表应有 {len(primary_queries)} 行，实际 {len(summary_section)} 行")

    for i, query in enumerate(primary_queries):
        qid = query['query_id']
        results = query.get('result', {}).get('results', [])
        if not results:
            errors.append(f"{qid}: 查询结果为空")
            continue

        top1_id = results[0]['sample_id'].split('/')[-1]
        top1_dist = results[0]['distance']['total']
        status = query.get('query_status')

        # 在报告中查找对应行
        found = False
        for line in summary_section:
            if qid in line:
                found = True
                # 检查 top-1
                if top1_id not in line:
                    errors.append(f"{qid}: 报告 top-1 不匹配，JSON={top1_id}")
                # 检查距离（保留 6 位小数）
                dist_str = f"{top1_dist:.6f}"
                if dist_str not in line:
                    errors.append(f"{qid}: 报告距离不匹配，JSON={dist_str}")
                # 检查状态
                if status and status not in line:
                    errors.append(f"{qid}: 报告状态不匹配，JSON={status}")
                break

        if not found:
            errors.append(f"{qid}: 在摘要表中未找到")

    if len([e for e in errors if '摘要表' in e or '在摘要表' in e]) == 0:
        print("  ✓ 摘要表一致")

    # 检查 2: 主查询详细章节
    print("\n检查 2: 主查询详细章节")

    for i, query in enumerate(primary_queries, 1):
        qid = query['query_id']

        # 在报告中查找该查询的章节（使用正则匹配）
        section_pattern = f"### 2\\.{i} {re.escape(qid)}"
        if not re.search(section_pattern, report):
            errors.append(f"{qid}: 详细章节未找到")
            continue

        # 提取该章节（从当前章节到下一个 ### 或 ##）
        section_match = re.search(section_pattern, report)
        section_start = section_match.start()

        # 查找下一个同级或更高级标题
        next_section = re.search(r'\n##', report[section_start + 1:])
        if next_section:
            section_end = section_start + next_section.start() + 1
        else:
            section_end = len(report)

        section_text = report[section_start:section_end]

        # 检查 top-1 sample_id
        results = query.get('result', {}).get('results', [])
        if results:
            top1_id = results[0]['sample_id']
            if top1_id not in section_text:
                errors.append(f"{qid}: 详细章节缺少 top-1 {top1_id}")

            # 检查距离（6位小数格式）
            top1_dist = results[0]['distance']['total']
            dist_str = f"{top1_dist:.6f}"
            if dist_str not in section_text:
                errors.append(f"{qid}: 详细章节距离不匹配，期望 {dist_str}")

    if len([e for e in errors if '详细章节' in e]) == 0:
        print("  ✓ 详细章节一致")

    # 检查 3: 候选数量
    print("\n检查 3: 候选数量")

    total_candidates_json = 0
    for query in primary_queries + data.get('diagnostic_queries', []):
        results = query.get('result', {}).get('results', [])
        total_candidates_json += len(results)

    # 在报告中查找候选总数
    match = re.search(r'候选总数\*\*: (\d+)', report)
    if match:
        total_candidates_report = int(match.group(1))
        if total_candidates_json != total_candidates_report:
            errors.append(f"候选总数不匹配：JSON={total_candidates_json}, 报告={total_candidates_report}")
        else:
            print(f"  ✓ 候选总数一致: {total_candidates_json}")
    else:
        errors.append("报告中未找到候选总数")

    # 检查 4: 失败诊断（增强验证）
    print("\n检查 4: 失败诊断（code/stage/fields）")

    fail_errors = check_failure_diagnostic(data, report)
    errors.extend(fail_errors)

    if not fail_errors:
        print("  ✓ 失败诊断 code/stage/fields 一致")

    # 检查 5: 确定性验证
    print("\n检查 5: 确定性验证")

    for query in primary_queries + data.get('diagnostic_queries', []):
        qid = query['query_id']
        determ = query.get('determinism', {})
        if not determ.get('cross_process_deterministic'):
            errors.append(f"{qid}: JSON 显示确定性检查失败")

    # 在报告中检查确定性表格
    if "✓ PASS" not in report:
        errors.append("报告中未找到确定性 PASS 标记")

    if len([e for e in errors if '确定性' in e]) == 0:
        print("  ✓ 确定性验证一致")

    # 运行自测（负例验证）
    if run_self_test_flag:
        self_test_pass, self_test_errors = run_self_test(json_path, report_path)
        if not self_test_pass:
            errors.extend(self_test_errors)

    # 总结
    print("\n" + "=" * 60)
    if errors:
        print(f"❌ 发现 {len(errors)} 个不一致:")
        for error in errors:
            print(f"  - {error}")
        return 1
    else:
        print("✓ 所有检查通过：报告与 JSON 结果一致")
        if run_self_test_flag:
            print("✓ 负例测试通过：能正确检测 stage 和 fields 变异")
        return 0


if __name__ == "__main__":
    # 支持 --no-self-test 跳过自测
    run_self_test_flag = '--no-self-test' not in sys.argv
    sys.exit(main(run_self_test_flag))
