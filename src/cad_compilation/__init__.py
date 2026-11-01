"""
CAD-005/006: IR v0 编译器和几何验证器

此模块实现：
- IR v0 JSON 解析和语义检查
- 白名单 IR → CadQuery/OCP 编译
- 实体有效性、STEP 回读验证
- 结构化错误报告

使用示例：
    compiler = IRv0Compiler()
    result = compiler.compile(ir_json_obj)
    if result.success:
        solid = result.solid
        validation = result.validate_step("output.step")
"""

__all__ = [
    "IRv0Compiler",
    "CompilationResult",
    "ValidationResult",
    "IRSemanticValidator",
    "GeometryValidator",
]

from .compiler import IRv0Compiler
from .result import CompilationResult, ValidationResult
from .semantic import IRSemanticValidator
from .geometry import GeometryValidator
