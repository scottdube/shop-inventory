"""Find names a function USES but never BINDS — Python's runtime-only bug.

Written 2026-08-23 after `/api/identify` spent days dead on its main path.
Commit f25e3f0 added a `site` argument to `drawer_contents()` and updated
three of the four call sites. The fourth sat inside `api_identify`, which has
no `site` parameter, so every identify with a drawer selected raised
NameError, returned a plain-text 500, and reached the phone as:

    SyntaxError: The string did not match the expected pattern.

That is Safari's message for `Response.json()` on a non-JSON body. It names
neither the endpoint nor the variable, so the visible symptom pointed nowhere
near the cause -- and because the failing branch is a guard that the UI is
supposed to avoid, nothing else exercised it.

This is exactly the bug class a compiler catches for free and Python does not.
The file imports cleanly, every test passes, and the call is still wrong.

    python3 scripts/unbound_names.py binscan/app.py

Prints one line per suspect and exits non-zero if any are found. Handles
nested functions properly: a name bound by an enclosing scope is fine, and a
nested function's own parameters bind within it -- a first version missed that
and reported `_norm(t)` inside `api_newpart` as unbound.
"""
import ast, builtins, sys

SAFE = set(dir(builtins)) | {"__file__", "__name__", "__doc__"}


def _bindings(node):
    """Names bound directly in this scope, not descending into nested ones."""
    out = set()
    if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda)):
        a = node.args
        for arg in a.posonlyargs + a.args + a.kwonlyargs:
            out.add(arg.arg)
        if a.vararg:
            out.add(a.vararg.arg)
        if a.kwarg:
            out.add(a.kwarg.arg)

    body = node.body if isinstance(node.body, list) else [node.body]
    stack = list(body)
    while stack:
        n = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            out.add(n.name)          # the name binds here; its body is its own scope
            continue
        if isinstance(n, ast.Lambda):
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, (ast.Store, ast.Del)):
            out.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                out.add((al.asname or al.name).split(".")[0])
        elif isinstance(n, ast.ExceptHandler) and n.name:
            out.add(n.name)
        elif isinstance(n, (ast.Global, ast.Nonlocal)):
            out.update(n.names)
        stack.extend(ast.iter_child_nodes(n))
    return out


def _loads(node):
    """Name reads in this scope, not descending into nested function bodies."""
    out = []
    body = node.body if isinstance(node.body, list) else [node.body]
    stack = [(c, False) for c in body]
    # decorators and defaults evaluate in the ENCLOSING scope, so they are not
    # walked here; the enclosing scope's own pass covers them.
    while stack:
        n, _ = stack.pop()
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.Lambda,
                          ast.ClassDef)):
            continue
        if isinstance(n, ast.Name) and isinstance(n.ctx, ast.Load):
            out.append((n.id, n.lineno))
        stack.extend((c, False) for c in ast.iter_child_nodes(n))
    return out


def scan(path):
    tree = ast.parse(open(path).read(), filename=path)

    module = set()
    for n in ast.walk(tree):
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            module.add(n.name)
        elif isinstance(n, ast.Name) and isinstance(n.ctx, ast.Store):
            module.add(n.id)
        elif isinstance(n, (ast.Import, ast.ImportFrom)):
            for al in n.names:
                module.add((al.asname or al.name).split(".")[0])

    found = []

    def walk(node, enclosing):
        here = _bindings(node) | enclosing
        for name, line in _loads(node):
            if name not in here and name not in SAFE:
                found.append((getattr(node, "name", "<module>"), name, line))
        for child in _nested(node):
            walk(child, here)

    def _nested(node):
        body = node.body if isinstance(node.body, list) else [node.body]
        out, stack = [], list(body)
        while stack:
            n = stack.pop()
            if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
                out.append(n)
                continue
            stack.extend(ast.iter_child_nodes(n))
        return out

    for fn in _nested(tree):
        walk(fn, module | SAFE)

    return found


if __name__ == "__main__":
    targets = sys.argv[1:] or ["binscan/app.py"]
    bad = 0
    for t in targets:
        hits = scan(t)
        seen = set()
        for fname, name, line in hits:
            if (fname, name) in seen:
                continue
            seen.add((fname, name))
            print(f"  {t}:{line}  {name!r} used in {fname}() but never bound")
            bad += 1
    print("clean" if not bad else f"{bad} suspect reference(s)")
    sys.exit(1 if bad else 0)
