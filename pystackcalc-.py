"""PyStackCalc - terminal stack machine & math REPL. Pure standard Python 3.

M1 O(1) Stack + tokenizer (numbers, names, operators, unary 'u-'/'u+'); M2
Shunting-Yard infix->postfix (precedence ^ > * / % > + -, right-associative ^,
mismatch detection); M3 RPN evaluator (variables, safe maths errors, trace
mode); M4 REPL with let / vars / history / trace / undo / redo / exit over
copied variable snapshots.  Extra credit: unary functions sqrt(16) or sqrt 16
(sqrt abs sin cos tan asin acos atan sinh cosh tanh exp ln log log2 floor ceil
round degrees radians).  Usage: python3 pystackcalc.py [--trace] [expr]
"""
import math
import re
import sys

HELP = """PyStackCalc - commands
  Operators  + - * / % ^ ( )   precedence: ^  >  * / %  >  + -   (^ is right-assoc)
  Examples   2 + 3 * 4 = 14   2 ^ 3 ^ 2 = 512   -2 ^ 2 = -4   10 % 3 = 1
  Signs      -5, 2 * -3, (-2), 2 ^ -3 all work;  10 / 0 -> math error, no crash
  Functions  sqrt(16) or sqrt 16 = 4 | sqrt abs sin cos tan asin acos atan sinh
             cosh tanh exp ln log log2 floor ceil round degrees radians | pi, e
  Variables  let x = 2 + 3   (x = 2 + 3 also works)   pi * radius ^ 2
  Commands   vars | history | undo | redo | trace <expr> | help | exit"""

class CalcError(Exception):
    """Recoverable syntax/math/command error: printed, the REPL keeps running."""

class Stack:
    """Milestone 1: LIFO stack; push / pop / peek are all O(1) (list.append / list.pop)."""
    def __init__(self):
        self._items = []
    def push(self, item):
        self._items.append(item)
    def pop(self):
        """Remove and return the TOP item - list.pop() is the O(1) LIFO removal."""
        if not self._items: raise IndexError("pop from empty stack")
        return self._items.pop()
    def peek(self):
        if not self._items: raise IndexError("peek from empty stack")
        return self._items[-1]
    def is_empty(self):
        return not self._items
    def size(self):
        return len(self._items)
    def __iter__(self):
        return iter(self._items)

OPERATORS = {"+", "-", "*", "/", "%", "^", "u-", "u+"}
PRECEDENCE = {"+": 1, "-": 1, "*": 2, "/": 2, "%": 2, "u-": 3, "u+": 3, "^": 4}
FUNC_PREC = 5
FUNCS = {"abs": abs, "sqrt": math.sqrt, "exp": math.exp, "ln": math.log,
         "log": math.log10, "log2": math.log2, "sin": math.sin, "cos": math.cos,
         "tan": math.tan, "asin": math.asin, "acos": math.acos, "atan": math.atan,
         "sinh": math.sinh, "cosh": math.cosh, "tanh": math.tanh, "floor": math.floor,
         "ceil": math.ceil, "round": round, "degrees": math.degrees, "radians": math.radians}
TOKEN_RE = re.compile(r"\s*(?:((?:\d+\.\d*|\.\d+|\d+)(?:[eE][+-]?\d+)?)"
                      r"|([A-Za-z_]\w*)|([-+*/%^()=]))")

def tokenize(text):
    """Split text into number / name / operator tokens: -5, 2 * -3, (-2), 2 ^ -3."""
    tokens, pos, expect_value = [], 0, True
    while pos < len(text):
        match = TOKEN_RE.match(text, pos)
        if match is None: raise CalcError(f"Syntax error: bad character {text[pos]!r} at position {pos + 1}")
        pos = match.end()
        number, name, op = match.groups()
        if number is not None or name is not None:
            tokens.append(float(number) if number and any(c in number for c in ".eE")
                          else int(number) if number else name)
            expect_value = False
        else:
            if op in "+-" and expect_value:
                op = "u-" if op == "-" else "u+"
            tokens.append(op)
            expect_value = op != ")"
    return tokens

def infix_to_postfix(tokens):
    """Milestone 2: Dijkstra's shunting-yard - infix tokens -> postfix (RPN)."""
    output, operators = [], Stack()
    expect_value = True
    for index, token in enumerate(tokens):
        if token in OPERATORS:
            if token in ("u-", "u+"):
                operators.push(token)
            else:
                if expect_value: raise CalcError(f"Syntax error: operator '{token}' is missing an operand")
                while operators.size() and operators.peek() != "(" and (
                        PRECEDENCE.get(operators.peek(), FUNC_PREC) > PRECEDENCE[token] or
                        (PRECEDENCE.get(operators.peek(), FUNC_PREC) == PRECEDENCE[token]
                         and token != "^")):
                    output.append(operators.pop())
                operators.push(token)
            expect_value = True
        elif token == "(":
            if not expect_value: raise CalcError("Syntax error: unexpected '(' (missing operator?)")
            operators.push(token)
        elif token == ")":
            if expect_value: raise CalcError("Syntax error: unexpected ')' - empty parentheses or no operand")
            while operators.size() and operators.peek() != "(":
                output.append(operators.pop())
            if operators.is_empty(): raise CalcError("Syntax error: mismatched ')' - no matching '('")
            operators.pop()
            if not operators.is_empty() and operators.peek() in FUNCS:
                output.append(operators.pop())
            expect_value = False
        else:
            if not expect_value: raise CalcError(f"Syntax error: unexpected {token!r} (missing operator?)")
            if token == "=": raise CalcError("Syntax error: unexpected '=' (assign with: let name = expr)")
            if token in FUNCS:
                nxt = tokens[index + 1] if index + 1 < len(tokens) else None
                if nxt is None or nxt in OPERATORS or nxt in (")", "="):
                    raise CalcError(f"Syntax error: {token}() needs an argument, e.g. {token}(9)")
                operators.push(token)
            else:
                output.append(token)
                expect_value = False
    while operators.size():
        top = operators.pop()
        if top == "(": raise CalcError("Syntax error: unclosed '(' - missing ')'")
        output.append(top)
    if expect_value: raise CalcError("Syntax error: expression ends with an operator (missing operand)")
    if not output: raise CalcError("Syntax error: empty expression")
    return output

def fmt(value):
    """Readable output: integers stay exact, floats lose 1e-17 noise."""
    if isinstance(value, float) and not (value.is_integer() and abs(value) < 1e16): return f"{value:.12g}"
    return str(int(value)) if isinstance(value, float) else str(value)

def apply_op(op, a, b):
    """Apply a binary operator to a (left) and b (right); unary signs included."""
    if op in ("u-", "u+"): return -a if op == "u-" else a
    if op == "+": return a + b
    if op == "-": return a - b
    if op == "*": return a * b
    if op in ("/", "%"):
        if b == 0: raise CalcError("Math error: " + ("division" if op == "/" else "modulo") + " by zero")
        return a / b if op == "/" else a % b
    if op == "^":
        if abs(a) > 1 and abs(b) > 10000: raise CalcError("Math error: exponent is too large")
        if a < 0 and isinstance(b, float) and not b.is_integer():
            inverse = 1 / b
            if inverse < 1e6 and abs(inverse - round(inverse)) < 1e-9 and round(inverse) % 2:
                return -((-a) ** b)
            raise CalcError("Math error: negative base with a fractional exponent is not real")
        try:
            result = a ** b
        except ZeroDivisionError:
            raise CalcError("Math error: 0 cannot be raised to a negative power")
        except OverflowError:
            raise CalcError("Math error: result too large to represent")
        if isinstance(result, complex): raise CalcError("Math error: the result would not be a real number")
        return result
    raise CalcError(f"Syntax error: unknown operator '{op}'")

def apply_func(name, value):
    """Call a unary function, turning domain / overflow problems into CalcError."""
    try: return FUNCS[name](value)
    except (ValueError, OverflowError) as exc:
        raise CalcError(f"Math error: {name}({fmt(value)}) is undefined ({exc})")

def evaluate(postfix, variables, trace=False):
    """Milestone 3: evaluate postfix - b = pop(), a = pop() -> a op b."""
    stack = Stack()
    if trace: print("  RPN     : " + " ".join(fmt(t) for t in postfix))
    for token in postfix:
        if isinstance(token, (int, float)):
            result, note = token, f"push {fmt(token)}"
        elif token in ("u-", "u+") or token in FUNCS:
            if stack.is_empty(): raise CalcError(f"Syntax error: '{token}' is missing an operand")
            x = stack.pop()
            result = apply_func(token, x) if token in FUNCS else apply_op(token, x, 0)
            note = f"{token} {fmt(x)}" if token in ("u-", "u+") else f"{token}({fmt(x)})"
            note += f" = {fmt(result)}"
        elif token in OPERATORS:
            if stack.size() < 2: raise CalcError(f"Syntax error: operator '{token}' is missing an operand")
            b, a = stack.pop(), stack.pop()
            result = apply_op(token, a, b)
            note = f"{fmt(a)} {token} {fmt(b)} = {fmt(result)}"
        else:
            if token not in variables:
                raise CalcError(f"Name error: variable '{token}' is not defined (try: let {token} = 1)")
            result, note = variables[token], f"load {token} = {fmt(variables[token])}"
        if isinstance(result, float) and math.isinf(result):
            raise CalcError("Math error: result too large to represent")
        stack.push(result)
        if trace: print(f"  {note:<26} stack: [{', '.join(fmt(item) for item in stack)}]")
    if stack.size() != 1: raise CalcError("Syntax error: malformed expression (leftover operands)")
    return stack.pop()

def vars_str(variables):
    return ("{" + ", ".join(f"{k} = {fmt(v)}" for k, v in sorted(variables.items())) + "}"
            if variables else "{}   (no variables defined)")

def history_str(items):
    return "\n".join(f"  {i:>3}. {item}" for i, item in enumerate(items, 1)) or "(no history yet)"

ASSIGN_RE = re.compile(r"([A-Za-z_]\w*)\s*=\s*(.+)", re.S)

class Calculator:
    """Milestone 4: REPL state - variables, dual-stack undo/redo snapshots."""
    def __init__(self, trace=False):
        self.variables = {"pi": math.pi, "e": math.e}
        self.undo_stack = Stack()
        self.redo_stack = Stack()
        self.history = []
        self.trace = trace
    def assign(self, name, value):
        """Store a variable after pushing a COPY of the old dictionary on undo_stack."""
        if name in FUNCS or name == "let": raise CalcError(f"Syntax error: '{name}' is a reserved name")
        self.undo_stack.push(dict(self.variables))
        self.redo_stack = Stack()
        self.variables[name] = value
        return value
    def _restore(self, source, target):
        """Move a snapshot from source into the live variables, saving the old state."""
        if source.is_empty(): return None
        target.push(dict(self.variables))
        self.variables = source.pop()
        return self.variables
    def undo(self):
        """Restore the previous variable snapshot; None when nothing can be undone."""
        return self._restore(self.undo_stack, self.redo_stack)
    def redo(self):
        """Re-apply the most recently undone snapshot; None when there is none."""
        return self._restore(self.redo_stack, self.undo_stack)
    def eval_expr(self, text, trace=False):
        tokens = tokenize(text)
        if trace: print("  tokens  : " + " ".join(fmt(t) for t in tokens))
        return evaluate(infix_to_postfix(tokens), self.variables, trace)
    def run(self, line):
        """Execute one REPL line; returns False only when the user wants to exit."""
        line, low = line.strip(), line.strip().lower()
        if not line: return True
        if low in ("exit", "quit", "q", "exit()", "quit()"): return False
        if low in ("help", "?", "h"): print(HELP, "\n"); return True
        if low in ("vars", "history"):
            print(vars_str(self.variables) if low == "vars" else history_str(self.history)); return True
        if low in ("undo", "redo"):
            snapshot = self.undo() if low == "undo" else self.redo()
            print(f"(nothing to {low})" if snapshot is None else
                  f"{low.capitalize()}  ->  {vars_str(self.variables)}"); return True
        trace = self.trace
        if low == "trace" or low.startswith("trace "):
            trace, line = True, line[5:].strip()
            if not line: raise CalcError("Usage: trace <expression>   e.g. trace 2 + 3 * 4")
        is_let = low == "let" or low.startswith("let ")
        match = ASSIGN_RE.fullmatch(line[3:].strip() if is_let else line)
        if is_let and match is None: raise CalcError("Syntax error: use 'let <name> = <expression>'")
        if match:
            name, expression = match.group(1), match.group(2)
            result = f"{name} = {fmt(self.assign(name, self.eval_expr(expression, trace)))}"
        else:
            result = fmt(self.eval_expr(line, trace))
        self.history.append(f"{line:<26} ->  {result}")
        print(result if match else f"= {result}")
        return True

def repl(trace=False):
    """Read-Eval-Print Loop: never raises, never exits by accident."""
    calculator, interactive = Calculator(trace), sys.stdin.isatty()
    if interactive: print("PyStackCalc - stack machine & math REPL. Type 'help' for commands.")
    while True:
        try:
            line = input("calc> " if interactive else "")
        except EOFError:
            print(); break
        except KeyboardInterrupt:
            print("\n(use 'exit' or Ctrl-D to quit)"); continue
        try:
            if not calculator.run(line): break
        except CalcError as exc: print(f"Error: {exc}")
        except KeyboardInterrupt: print("^C (input aborted)")
        except Exception as exc:
            print(f"Internal error ({type(exc).__name__}): {exc}")
    print("Bye!")

def main(argv):
    """No expression arguments -> interactive REPL; otherwise evaluate and exit."""
    trace = "-t" in argv or "--trace" in argv
    expressions = [a for a in argv[1:] if a not in ("-t", "--trace", "-h", "--help")]
    bad = [a for a in argv[1:] if a.startswith("--") and a[2:3].isalpha()
           and a not in ("--trace", "--help")]
    if "-h" in argv or "--help" in argv:
        print(HELP, "\n\nUsage: python3 pystackcalc.py [--trace] [\"expression\" ...]"); return 0
    if bad: print(f"Unknown option '{bad[0]}' (try --help)"); return 2
    if not expressions: repl(trace); return 0
    calculator, ok = Calculator(trace), True
    for expression in expressions:
        try: calculator.run(expression)
        except CalcError as exc: print(f"Error: {exc}"); ok = False
    return 0 if ok else 1

if __name__ == "__main__": sys.exit(main(sys.argv))
