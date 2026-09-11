import sys
from pathlib import Path
p = Path('uv_installed.txt')
out = Path('uv_installed_clean.txt')
encs = ['utf-8', 'utf-16', 'latin-1']
text = None
for e in encs:
    try:
        text = p.read_text(encoding=e)
        break
    except Exception:
        continue
if text is None:
    print('FAILED')
    sys.exit(1)
# normalize lines
lines = [l.strip() for l in text.splitlines() if l.strip()]
out.write_text('\n'.join(lines), encoding='utf-8')
print('WROTE', out)
