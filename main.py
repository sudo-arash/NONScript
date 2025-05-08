import math, numpy as np
import os


#─── Global State ────────────────────────────────────────────────────────────────

vars = {}         # variable store
functions = {}    # user‐defined functions
builtin_functions = {}

vars["pi"] = math.pi
vars["e"] = math.e

for name in dir(math):
    func = getattr(math, name)
    if callable(func):
        builtin_functions[name] = func

# Numpy functions (optional and larger)
for name in dir(np):
    if name.startswith("_"): continue
    func = getattr(np, name)
    if callable(func):
        builtin_functions[name] = func

        
#─── Expression Parser ────────────────────────────────────────────────────────────

def parse_factor(tokens):
    token = tokens.pop(0)
    
    # Check for function call or parenthesized expression
    if tokens and tokens[0] == "(":
        tokens.pop(0)  # Consume "("
        args = []
        if tokens and tokens[0] != ")":
            args.append(eval_expr(tokens))
            while tokens and tokens[0] == ",":
                tokens.pop(0)
                args.append(eval_expr(tokens))
        if not tokens:
            raise ValueError("Unclosed parenthesis")
        tokens.pop(0)  # Consume ")"

        # Check if it's a built-in function
        if token in builtin_functions:
            try:
                return builtin_functions[token](*args)
            except Exception as e:
                raise ValueError(f"Error in builtin function {token}: {e}")
        
        # Check if it's a user-defined function
        if token in functions:
            res = run_function_call(token, args)
            return res[0] if res else 0.0

        # If no match, raise an error for unknown functions
        raise ValueError(f"Unknown function: {token}")

    # Parenthesized without function name (just an expression)
    if token == "(":
        v = eval_expr(tokens)
        if not tokens or tokens.pop(0) != ")":
            raise ValueError("Expected closing parenthesis")
        return v

    # Look up variable
    if token in vars:
        return vars[token]

    # Convert to float or raise error if not a number
    try:
        return float(token)
    except ValueError:
        raise ValueError(f"Unrecognized token or variable: {token}")

def parse_exponent(tokens):
    v = parse_factor(tokens)
    while tokens and tokens[0] == "^":
        tokens.pop(0)
        v = v ** parse_factor(tokens)
    return v

def parse_term(tokens):
    v = parse_exponent(tokens)
    while tokens and tokens[0] in ("*", "/"):
        op = tokens.pop(0)
        rhs = parse_exponent(tokens)
        if op == "*":
            v *= rhs
        else:
            if rhs == 0:
                raise ValueError("Division by zero")
            v /= rhs
    return v

def eval_expr(tokens):
    v = parse_term(tokens)
    while tokens and tokens[0] in ("+", "-"):
        op = tokens.pop(0)
        rhs = parse_term(tokens)
        v = v + rhs if op == "+" else v - rhs
    return v

#─── Tokenizer ───────────────────────────────────────────────────────────────────

def tokenize(s):
    tokens = []
    i = 0
    while i < len(s):
        c = s[i]
        if c in "()+-*/^,[]":
            tokens.append(c)
            i += 1
        elif c.isspace():
            i += 1
        else:
            j = i
            while j < len(s) and (s[j].isalnum() or s[j] == "."):
                j += 1
            tokens.append(s[i:j])
            i = j
    return tokens

#─── Function Definition ─────────────────────────────────────────────────────────

def parse_function_definition(lines):
    header = lines[0].strip()
    
    # Check if the function definition starts with an assignment, then extract the function part
    if "= def" in header:
        out_part, rest = header.split("=", 1)
        func_part = rest.strip()
    else:
        raise ValueError(f"Invalid function definition header: {header}")
    
    # Extract function name and arguments
    if "def" not in func_part:
        raise ValueError(f"Invalid function definition header: {func_part}")
    
    func_part = func_part.split("def", 1)[1].strip()
    name, args_str = func_part.split("(", 1)
    args = [a.strip() for a in args_str.rstrip(")").split(",") if a.strip()]
    outputs = [o.strip() for o in out_part.strip()[1:-1].split(",") if o.strip()]
    body = lines[1:-1]  # The function body is everything except the header and "end"
    
    functions[name.strip()] = {"args": args, "outputs": outputs, "body": body}

#─── Load .nm Files ──────────────────────────────────────────────────────────────

def load_functions_from_file(path):
    lines = [l.rstrip("\n") for l in open(path)]
    buf = []
    for line in lines:
        if "= def" in line:
            buf = [line]
        elif buf:
            buf.append(line)
            if line.strip() == "end":
                parse_function_definition(buf)
                buf = []

def load_functions_from_directory(dir):
    for root, dirs, files in os.walk(dir):
        for fn in files:
            if fn.endswith(".nm"):
                load_functions_from_file(os.path.join(root, fn))

#─── Function Execution ─────────────────────────────────────────────────────────

def run_function_call(name, args):
    # First check if it's a built-in function
    if name in builtin_functions:
        try:
            return [builtin_functions[name](*args)]
        except Exception as e:
            raise ValueError(f"Error in builtin function {name}: {e}")
    
    # If it's not a built-in function, check for user-defined functions
    if name not in functions:
        raise ValueError(f"Function not defined: {name}")
    
    f = functions[name]
    if len(args) != len(f["args"]):
        raise ValueError(f"Arg count mismatch for: {name}")
    
    saved = vars.copy()
    vars.clear()
    
    for arg_name, arg_val in zip(f["args"], args):
        vars[arg_name] = arg_val
    
    for line in f["body"]:
        if "=" in line:
            lhs, expr = line.split("=", 1)
            lhs = lhs.strip(); expr = expr.strip()
            toks = tokenize(expr)
            vars[lhs] = eval_expr(toks)
    
    res = [vars.get(o, 0.0) for o in f["outputs"]]
    
    vars.clear()
    vars.update(saved)
    
    return res

#─── REPL ───────────────────────────────────────────────────────────────────────

def main_loop():
    while True:
        inp = input("> ").strip()
        if not inp: continue
        if inp == "exit": break
        if inp == "who":
            for k, v in vars.items(): 
                print(f"{k} = {v}")
            continue
        if inp == "clear":
            vars.clear(); print("Cleared."); continue
        if inp == "cls":
            os.system("clear"); continue
        
        if inp == "help":
            print("Available built-in functions:")
            for k in sorted(builtin_functions.keys()):
                print("  ", k)
            continue

        # define function
        if "= def" in inp:
            buf = [inp]
            while True:
                nxt = input(">> ").rstrip("\n")
                buf.append(nxt)
                if nxt.strip() == "end": break
            parse_function_definition(buf)
            continue

        # assignment with function call
        if "=" in inp and "(" in inp:
            left, call = inp.split("=", 1)
            outs = [o.strip() for o in left.strip()[1:-1].split(",")]
            name, rest = call.split("(", 1)
            
            # Modify argument parsing to handle variables like pi
            args = []
            for arg in rest.rstrip(")").split(","):
                arg = arg.strip()
                # Check if the argument is a variable
                if arg in vars:
                    args.append(vars[arg])
                else:
                    # Convert to float if it's a number
                    try:
                        args.append(float(arg))
                    except ValueError:
                        raise ValueError(f"Invalid argument: {arg}")
            
            res = run_function_call(name.strip(), args)
            for o, val in zip(outs, res):
                vars[o] = val
                print(f"{o} = {val}")
            continue

        # bare function call
        if "(" in inp:
            name, rest = inp.split("(", 1)
            
            # Modify argument parsing to handle variables like pi
            args = []
            for arg in rest.rstrip(")").split(","):
                arg = arg.strip()
                # Check if the argument is a variable
                if arg in vars:
                    args.append(vars[arg])
                else:
                    # Convert to float if it's a number
                    try:
                        args.append(float(arg))
                    except ValueError:
                        raise ValueError(f"Invalid argument: {arg}")
            
            res = run_function_call(name.strip(), args)
            if res:
                print(res[0] if len(res) == 1 else res)
            continue

        # simple assignment
        if "=" in inp:
            n, e = inp.split("=", 1)
            v = eval_expr(tokenize(e.strip()))
            vars[n.strip()] = v
            print(f"{n.strip()} = {v}")
            continue

        # variable lookup or expression
        if inp in vars:
            print(f"{inp} = {vars[inp]}")
        else:
            print("Result =", eval_expr(tokenize(inp)))


if __name__ == "__main__":
    load_functions_from_directory("Data")
    main_loop()
