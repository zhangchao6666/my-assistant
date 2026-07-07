import ast
import operator
from typing import Callable

from app.models.tool import ToolResult


Number = int | float

_BINARY_OPERATORS: dict[type[ast.operator], Callable[[Number, Number], Number]] = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}

_UNARY_OPERATORS: dict[type[ast.unaryop], Callable[[Number], Number]] = {
    ast.UAdd: operator.pos,
    ast.USub: operator.neg,
}


def _evaluate(node: ast.AST) -> Number:
    if isinstance(node, ast.Expression):
        return _evaluate(node.body)

    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value

    if isinstance(node, ast.BinOp):
        operator_func = _BINARY_OPERATORS.get(type(node.op))
        if operator_func is None:
            raise ValueError("unsupported operator")
        return operator_func(_evaluate(node.left), _evaluate(node.right))

    if isinstance(node, ast.UnaryOp):
        operator_func = _UNARY_OPERATORS.get(type(node.op))
        if operator_func is None:
            raise ValueError("unsupported unary operator")
        return operator_func(_evaluate(node.operand))

    raise ValueError("unsupported expression")


def calculator_tool(expression: str | None) -> ToolResult:
    if not expression:
        return ToolResult(
            matched=False,
            tool_name="calculator",
            message="Missing calculator expression.",
        )

    try:
        parsed = ast.parse(expression, mode="eval")
        result = _evaluate(parsed)
    except Exception:
        return ToolResult(
            matched=False,
            tool_name="calculator",
            message="The expression cannot be calculated.",
        )

    return ToolResult(
        matched=True,
        tool_name="calculator",
        content=f"{expression} = {result}",
    )
