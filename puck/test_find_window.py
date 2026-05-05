import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import win32gui
found = []
def cb(h, _):
    t = win32gui.GetWindowText(h)
    if '智谱' in t or 'bigmodel' in t.lower() or 'GLM' in t or 'Coding' in t:
        found.append((h, t))
    return True

win32gui.EnumWindows(cb, None)
for h, t in found[:10]:
    print(f"hwnd={h} title={t[:80]}")
