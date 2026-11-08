"""
Calculator Tool — Safely evaluates mathematical expressions using Python's AST.
No eval() — completely safe against code injection.
"""
import ast
import math
import operator
from app.models import CalculatorRequest, CalculatorResponse

# Allowed binary/unary operators
OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Pow: operator.pow,
    ast.Mod: operator.mod,
    ast.FloorDiv: operator.floordiv,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

# Safe math constants and functions
SAFE_NAMES = {
    "pi": math.pi,
    "e": math.e,
    "tau": math.tau,
    "inf": math.inf,
    "sqrt": math.sqrt,
    "cbrt": lambda x: x ** (1 / 3),
    "sin": math.sin,
    "cos": math.cos,
    "tan": math.tan,
    "asin": math.asin,
    "acos": math.acos,
    "atan": math.atan,
    "atan2": math.atan2,
    "log": math.log,
    "log2": math.log2,
    "log10": math.log10,
    "exp": math.exp,
    "abs": abs,
    "round": round,
    "floor": math.floor,
    "ceil": math.ceil,
    "factorial": math.factorial,
    "gcd": math.gcd,
    "hypot": math.hypot,
    "degrees": math.degrees,
    "radians": math.radians,
}


def _eval_node(node: ast.AST) -> float:
    """Recursively evaluate an AST node."""
    if isinstance(node, ast.Constant):
        if isinstance(node.value, (int, float)):
            return float(node.value)
        raise ValueError(f"Unsupported constant type: {type(node.value).__name__}")

    if isinstance(node, ast.Name):
        if node.id in SAFE_NAMES:
            val = SAFE_NAMES[node.id]
            if callable(val):
                raise ValueError(f"'{node.id}' is a function — call it with arguments, e.g. sqrt(9)")
            return float(val)
        raise ValueError(f"Unknown name: '{node.id}'")

    if isinstance(node, ast.BinOp):
        op_func = OPERATORS.get(type(node.op))
        if not op_func:
            raise ValueError(f"Unsupported operator: {type(node.op).__name__}")
        left = _eval_node(node.left)
        right = _eval_node(node.right)
        if isinstance(node.op, ast.Div) and right == 0:
            raise ValueError("Division by zero")
        return float(op_func(left, right))

    if isinstance(node, ast.UnaryOp):
        op_func = OPERATORS.get(type(node.op))
        if not op_func:
            raise ValueError(f"Unsupported unary operator: {type(node.op).__name__}")
        return float(op_func(_eval_node(node.operand)))

    if isinstance(node, ast.Call):
        if not isinstance(node.func, ast.Name):
            raise ValueError("Only built-in math functions are allowed")
        func_name = node.func.id
        if func_name not in SAFE_NAMES or not callable(SAFE_NAMES[func_name]):
            raise ValueError(f"Unknown function: '{func_name}'")
        args = [_eval_node(a) for a in node.args]
        return float(SAFE_NAMES[func_name](*args))

    raise ValueError(f"Unsupported expression type: {type(node).__name__}")


async def calculate(request: CalculatorRequest) -> CalculatorResponse:
    """Safely evaluate a math expression and return the result."""
    expr = request.expression.strip()

    if len(expr) > 500:
        raise ValueError("Expression is too long (max 500 characters)")

    try:
        tree = ast.parse(expr, mode="eval")
        result = _eval_node(tree.body)
    except ZeroDivisionError:
        raise ValueError("Division by zero")
    except ValueError:
        raise
    except Exception as e:
        raise ValueError(f"Could not evaluate expression: {e}")

    # Format result: integer if whole number, else 10 decimal places
    if result == int(result) and abs(result) < 1e15:
        result_str = str(int(result))
    else:
        result_str = f"{result:.10g}"

    return CalculatorResponse(
        expression=expr,
        result=result,
        result_str=result_str,
    )
