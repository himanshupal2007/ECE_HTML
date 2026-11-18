import ast
import math
import operator
import sys

# ---------------------------------------------------------------- engine

BINARY_OPS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.FloorDiv: operator.floordiv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
}
UNARY_OPS = {ast.UAdd: operator.pos, ast.USub: operator.neg}


class Calculator:
    def __init__(self):
        self.degrees = False   # trig in degrees instead of radians
        self.memory = 0.0
        self.ans = 0.0
        self.history = []

    # ----- trig helpers that respect degree mode
    def _in(self, x):
        return math.radians(x) if self.degrees else x

    def _out(self, x):
        return math.degrees(x) if self.degrees else x

    def _functions(self):
        return {
            "sqrt": math.sqrt,
            "cbrt": lambda x: math.copysign(abs(x) ** (1 / 3), x),
            "sin": lambda x: math.sin(self._in(x)),
            "cos": lambda x: math.cos(self._in(x)),
            "tan": lambda x: math.tan(self._in(x)),
            "asin": lambda x: self._out(math.asin(x)),
            "acos": lambda x: self._out(math.acos(x)),
            "atan": lambda x: self._out(math.atan(x)),
            "sinh": math.sinh,
            "cosh": math.cosh,
            "tanh": math.tanh,
            "log": lambda x, b=10: math.log(x, b),
            "log2": math.log2,
            "ln": math.log,
            "exp": math.exp,
            "abs": abs,
            "round": round,
            "floor": math.floor,
            "ceil": math.ceil,
            "factorial": lambda x: math.factorial(self._int(x)),
            "fact": lambda x: math.factorial(self._int(x)),
            "gcd": lambda a, b: math.gcd(self._int(a), self._int(b)),
            "lcm": lambda a, b: math.lcm(self._int(a), self._int(b)),
            "pow": pow,
            "max": max,
            "min": min,
            "deg": math.degrees,
            "rad": math.radians,
            "perm": lambda n, k: math.perm(self._int(n), self._int(k)),
            "comb": lambda n, k: math.comb(self._int(n), self._int(k)),
        }

    @staticmethod
    def _int(x):
        if float(x) != int(x):
            raise ValueError("needs a whole number")
        return int(x)

    def _constants(self):
        return {
            "pi": math.pi,
            "e": math.e,
            "tau": math.tau,
            "ans": self.ans,
            "mem": self.memory,
        }

    # ----- safe evaluation (no eval of arbitrary code)
    def _eval(self, node):
        if isinstance(node, ast.Expression):
            return self._eval(node.body)
        if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
            return node.value
        if isinstance(node, ast.Name):
            consts = self._constants()
            if node.id in consts:
                return consts[node.id]
            raise ValueError(f"unknown name '{node.id}'")
        if isinstance(node, ast.BinOp) and type(node.op) in BINARY_OPS:
            left, right = self._eval(node.left), self._eval(node.right)
            if isinstance(node.op, ast.Pow) and abs(right) > 10000:
                raise ValueError("exponent too large")
            return BINARY_OPS[type(node.op)](left, right)
        if isinstance(node, ast.UnaryOp) and type(node.op) in UNARY_OPS:
            return UNARY_OPS[type(node.op)](self._eval(node.operand))
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            funcs = self._functions()
            if node.func.id not in funcs or node.keywords:
                raise ValueError(f"unknown function '{node.func.id}'")
            return funcs[node.func.id](*[self._eval(a) for a in node.args])
        raise ValueError("invalid expression")

    @staticmethod
    def _prepare(text):
        text = text.strip().lower()
        text = text.replace("×", "*").replace("÷", "/").replace("^", "**")
        text = text.replace("π", "pi").replace("√", "sqrt")
        text = text.replace("−", "-")
        # "50%" -> "(50/100)" when % is not followed by an operand;
        # "10 % 3" stays a modulo.
        out, num = "", ""
        for i, ch in enumerate(text):
            if ch.isdigit() or ch == ".":
                num += ch
                continue
            if ch == "%" and num:
                rest = text[i + 1:].lstrip()
                if not (rest and (rest[0].isalnum() or rest[0] in ".(")):
                    out += f"({num}/100)"
                    num = ""
                    continue
            out += num + ch
            num = ""
        return (out + num).strip()

    def calculate(self, text):
        """Evaluate text and return the result. Raises ValueError on problems."""
        if not text.strip():
            raise ValueError("empty expression")
        try:
            tree = ast.parse(self._prepare(text), mode="eval")
            result = self._eval(tree)
        except ZeroDivisionError:
            raise ValueError("cannot divide by zero")
        except (SyntaxError, TypeError):
            raise ValueError("invalid expression")
        except OverflowError:
            raise ValueError("number too large")
        if isinstance(result, complex):
            raise ValueError("result is not a real number")
        if isinstance(result, float):
            if math.isnan(result) or math.isinf(result):
                raise ValueError("result is undefined")
            result = round(result, 12)
            if result == int(result) and abs(result) < 1e15:
                result = int(result)
        self.ans = result
        self.history.append(f"{text.strip()} = {result}")
        return result

    # ----- memory
    def mem_add(self, value):
        self.memory += value

    def mem_sub(self, value):
        self.memory -= value

    def mem_clear(self):
        self.memory = 0.0


# ---------------------------------------------------------------- terminal

HELP = """
Type any expression, for example:
   2 + 3 * 4          (2+3)^2          10 % 3          17 // 5
   sqrt(81)           sin(30)          log(1000)       ln(e)
   factorial(5)       200 * 15%        ans * 2

Commands:
   deg / rad     switch trig mode        m+ / m-   add / subtract ans to memory
   mr            recall memory           mc        clear memory
   history       show past calculations  clear     clear history
   help          show this text          quit      exit
"""


def run_cli():
    calc = Calculator()
    print("Scientific Calculator  (type 'help' for examples, 'quit' to exit)")
    while True:
        try:
            line = input(f"[{'DEG' if calc.degrees else 'RAD'}] > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        cmd = line.lower()
        if cmd in ("quit", "exit", "q"):
            break
        elif cmd == "help":
            print(HELP)
        elif cmd == "deg":
            calc.degrees = True
            print("Degrees mode")
        elif cmd == "rad":
            calc.degrees = False
            print("Radians mode")
        elif cmd == "m+":
            calc.mem_add(calc.ans)
            print("Memory:", calc.memory)
        elif cmd == "m-":
            calc.mem_sub(calc.ans)
            print("Memory:", calc.memory)
        elif cmd == "mr":
            print("Memory:", calc.memory)
        elif cmd == "mc":
            calc.mem_clear()
            print("Memory cleared")
        elif cmd == "history":
            print("\n".join(calc.history) or "No history yet")
        elif cmd == "clear":
            calc.history.clear()
            print("History cleared")
        elif cmd:
            try:
                print("=", calc.calculate(line))
            except ValueError as err:
                print("Error:", err)


# ---------------------------------------------------------------- window

def run_gui():
    try:
        import tkinter as tk
    except ImportError:
        print("Tkinter is not installed. Run without --gui for the terminal version.")
        return

    calc = Calculator()
    root = tk.Tk()
    root.title("Calculator")
    root.configure(bg="#1e1e2e")
    root.resizable(False, False)

    expr = tk.StringVar()
    result = tk.StringVar(value="0")
    mode = tk.StringVar(value="RAD")

    tk.Label(root, textvariable=mode, anchor="w", bg="#1e1e2e", fg="#9399b2",
             font=("Helvetica", 10)).grid(row=0, column=0, columnspan=3, sticky="we", padx=10, pady=(8, 0))
    tk.Label(root, textvariable=expr, anchor="e", bg="#1e1e2e", fg="#9399b2",
             font=("Helvetica", 14)).grid(row=1, column=0, columnspan=6, sticky="we", padx=10)
    tk.Label(root, textvariable=result, anchor="e", bg="#1e1e2e", fg="#cdd6f4",
             font=("Helvetica", 30, "bold")).grid(row=2, column=0, columnspan=6, sticky="we", padx=10, pady=(0, 8))

    def press(token):
        expr.set(expr.get() + token)

    def clear():
        expr.set("")
        result.set("0")

    def back():
        expr.set(expr.get()[:-1])

    def equals():
        try:
            value = calc.calculate(expr.get())
            result.set(str(value))
            expr.set("")
        except ValueError as err:
            result.set(f"Error: {err}")

    def toggle_mode():
        calc.degrees = not calc.degrees
        mode.set("DEG" if calc.degrees else "RAD")

    def mem(action):
        try:
            value = calc.calculate(expr.get()) if expr.get() else calc.ans
        except ValueError as err:
            result.set(f"Error: {err}")
            return
        if action == "M+":
            calc.mem_add(value)
        elif action == "M-":
            calc.mem_sub(value)
        elif action == "MC":
            calc.mem_clear()
        elif action == "MR":
            press(str(calc.memory))
            return
        result.set(f"Memory: {calc.memory}")

    layout = [
        [("MC", lambda: mem("MC")), ("MR", lambda: mem("MR")), ("M+", lambda: mem("M+")),
         ("M-", lambda: mem("M-")), ("DEG/RAD", toggle_mode), ("⌫", back)],
        [("sin(", None), ("cos(", None), ("tan(", None), ("log(", None), ("ln(", None), ("C", clear)],
        [("sqrt(", None), ("^", None), ("(", None), (")", None), ("%", None), ("/", None)],
        [("7", None), ("8", None), ("9", None), ("factorial(", None), ("pi", None), ("*", None)],
        [("4", None), ("5", None), ("6", None), ("abs(", None), ("e", None), ("-", None)],
        [("1", None), ("2", None), ("3", None), ("//", None), ("ans", None), ("+", None)],
        [("0", None), (".", None), ("mod", lambda: press("%%")), ("=", equals)],
    ]
    # "mod" button inserts the % operator between two numbers
    layout[6][2] = ("Mod", lambda: press(" % "))

    for r, row in enumerate(layout, start=3):
        for c, (label, action) in enumerate(row):
            span = 3 if label == "=" else 1
            if label == "=":
                c = 3
            bg = "#a6e3a1" if label == "=" else "#45475a" if label.isdigit() or label == "." else "#313244"
            fg = "#1e1e2e" if label == "=" else "#cdd6f4"
            cmd = action if action else (lambda t=label: press(t))
            tk.Button(root, text=label, command=cmd, bg=bg, fg=fg, relief="flat",
                      font=("Helvetica", 12), width=7, height=2,
                      activebackground="#585b70").grid(row=r, column=c, columnspan=span,
                                                       padx=2, pady=2, sticky="nsew")

    root.bind("<Return>", lambda _e: equals())
    root.bind("<BackSpace>", lambda _e: back())
    root.bind("<Escape>", lambda _e: clear())
    root.bind("<Key>", lambda e: press(e.char) if e.char and e.char in "0123456789.+-*/()%^" else None)
    root.mainloop()


if __name__ == "__main__":
    if "--gui" in sys.argv:
        run_gui()
    else:
        run_cli()