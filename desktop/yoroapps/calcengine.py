"""Safe arithmetic expression evaluator (no eval())."""

import ast
import operator

_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}


def evaluate(expression):
    """Evaluate +-*/%() arithmetic, return float. Raises ValueError."""
    expression = (expression.replace("×", "*").replace("÷", "/")
                  .replace("−", "-").replace(",", ".").replace(" ", ""))
    if not expression:
        raise ValueError("empty")

    def _eval(node):
        if isinstance(node, ast.Expression):
            return _eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return float(node.value)
        if isinstance(node, ast.BinOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.left), _eval(node.right))
        if isinstance(node, ast.UnaryOp) and type(node.op) in _OPS:
            return _OPS[type(node.op)](_eval(node.operand))
        raise ValueError("unsupported")

    try:
        tree = ast.parse(expression, mode="eval")
    except SyntaxError as exc:
        raise ValueError("syntax") from exc
    return _eval(tree)


def format_result(value):
    if value == int(value) and abs(value) < 1e15:
        return str(int(value))
    return f"{value:.10f}".rstrip("0").rstrip(".")
