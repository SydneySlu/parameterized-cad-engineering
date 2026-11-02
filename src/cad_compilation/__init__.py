"""Typed CAD IR v0 compiler and single-family geometry validator.

The public entry point accepts serialized JSON only. CADQuery is imported lazily
so schema and semantic validation remain usable without the native CAD runtime.
"""

from .compiler import CompilationResult, compile_ir, validate_ir

__all__ = ["CompilationResult", "compile_ir", "validate_ir"]
