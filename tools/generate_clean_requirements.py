from pathlib import Path

root = Path.cwd()
installed_file = root / 'uv_installed_clean.txt'
used_file = root / 'used_imports.txt'
installed = []
used = set()
if not installed_file.exists() or not used_file.exists():
    print('Missing files')
    raise SystemExit(1)
for line in installed_file.read_text(encoding='utf-8').splitlines():
    line=line.strip()
    if not line: continue
    pkg = line.split('==')[0]
    installed.append((pkg, line))
for line in used_file.read_text(encoding='utf-8').splitlines():
    used.add(line.strip())

used_l = {u.lower() for u in used}

# mapping some package->module names
mapping = {
    'opencv-python':'cv2',
    'pillow':'PIL',
    'pyglm':'glm',
    'pygltflib':'pygltflib',
    'scikit-learn':'sklearn',
    'scikit-learn-extra':'sklearn_extra',
    'python-dateutil':'dateutil',
    'typing-extensions':'typing_extensions',
    'pyglm':'glm',
    'pyglm':'glm',
}

selected = []
matched_modules = set()
for pkg, line in installed:
    name = pkg.lower()
    candidates = {name, name.replace('-', '_'), name.split('-')[0]}
    # add mapping value if present
    if name in mapping:
        candidates.add(mapping[name].lower())
    matched = False
    for c in candidates:
        if c in used_l:
            selected.append(line)
            matched = True
            matched_modules.add(c)
            break
    if not matched:
        # also match if any used import startswith package name
        for u in used_l:
            if u.startswith(name):
                selected.append(line)
                matched = True
                matched_modules.add(u)
                break

# Always include numpy and scipy if present (common)
always = ['numpy','scipy','matplotlib']
for pkg, line in installed:
    if pkg.lower() in always and line not in selected:
        selected.insert(0, line)

out_req = root / 'requirements.clean.txt'
out_req.write_text('\n'.join(selected), encoding='utf-8')

# write summary
root.joinpath('requirements_clean_report.txt').write_text('\n'.join([
    'SELECTED PACKAGES:',
    *selected,
    '',
    'UNUSED INSTALLED PACKAGES (candidates):',
    *[l for (p,l) in installed if l not in selected],
    '',
    'USED IMPORTS NOT MATCHED TO INSTALLED PACKAGES:',
    *sorted([u for u in used if u.lower() not in {m.lower() for m in matched_modules}]),
]), encoding='utf-8')
print('WROTE', out_req, 'and report')
