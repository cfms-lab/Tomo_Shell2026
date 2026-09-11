import ast
import os
import sys

root = os.path.abspath(os.getcwd())
used = set()

for dirpath, dirnames, filenames in os.walk(root):
    # skip virtualenv folders
    if any(part in ('uv', '.venv', 'venv', 'env') for part in dirpath.split(os.sep)):
        continue
    # skip hidden directories
    if os.path.basename(dirpath).startswith('.'):
        continue
    for fn in filenames:
        if not fn.endswith('.py'):
            continue
        path = os.path.join(dirpath, fn)
        try:
            with open(path, 'r', encoding='utf-8') as f:
                src = f.read()
        except Exception:
            try:
                with open(path, 'r', encoding='latin-1') as f:
                    src = f.read()
            except Exception:
                continue
        try:
            tree = ast.parse(src, filename=path)
        except Exception:
            continue
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for n in node.names:
                    top = n.name.split('.')[0]
                    used.add(top)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    top = node.module.split('.')[0]
                    used.add(top)

out_path = os.path.join(root, 'used_imports.txt')
with open(out_path, 'w', encoding='utf-8') as wf:
    for m in sorted(used):
        wf.write(m + '\n')
print('WROTE', out_path)
