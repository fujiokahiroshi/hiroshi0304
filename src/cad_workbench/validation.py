from __future__ import annotations

import ast
from typing import Any

ALLOWED_IMPORTS = {"cadquery", "math"}
BLOCKED_CALLS = {
    "breakpoint",
    "compile",
    "eval",
    "exec",
    "globals",
    "input",
    "locals",
    "open",
    "vars",
    "__import__",
}


class UnsafeCodeError(ValueError):
    pass


class CadCodeValidator(ast.NodeVisitor):
    """Reject obvious host access. This is a guardrail, not a security sandbox."""

    def visit_Import(self, node: ast.Import) -> None:
        for alias in node.names:
            if alias.name.split(".")[0] not in ALLOWED_IMPORTS:
                raise UnsafeCodeError(f"importは禁止されています: {alias.name}")
        self.generic_visit(node)

    def visit_ImportFrom(self, node: ast.ImportFrom) -> None:
        module = (node.module or "").split(".")[0]
        if module not in ALLOWED_IMPORTS:
            raise UnsafeCodeError(f"importは禁止されています: {node.module}")
        self.generic_visit(node)

    def visit_Attribute(self, node: ast.Attribute) -> None:
        if node.attr.startswith("__"):
            raise UnsafeCodeError("dunder属性へのアクセスは禁止されています")
        self.generic_visit(node)

    def visit_Call(self, node: ast.Call) -> None:
        if isinstance(node.func, ast.Name) and node.func.id in BLOCKED_CALLS:
            raise UnsafeCodeError(f"関数は禁止されています: {node.func.id}")
        self.generic_visit(node)


def validate_code(code: str) -> None:
    if len(code) > 80_000:
        raise UnsafeCodeError("コードが長すぎます（上限80,000文字）")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise UnsafeCodeError(f"Python構文エラー: {exc}") from exc
    CadCodeValidator().visit(tree)


def extract_literal_steps(code: str) -> list[str]:
    """Read a top-level literal `steps = [...]` without executing generated code."""
    tree = ast.parse(code, mode="exec")
    for node in tree.body:
        if not isinstance(node, (ast.Assign, ast.AnnAssign)):
            continue
        targets: list[Any] = node.targets if isinstance(node, ast.Assign) else [node.target]
        if not any(isinstance(target, ast.Name) and target.id == "steps" for target in targets):
            continue
        try:
            value = ast.literal_eval(node.value)
        except (ValueError, TypeError):
            return []
        if isinstance(value, list):
            return [str(item)[:300] for item in value[:100]]
    return []
