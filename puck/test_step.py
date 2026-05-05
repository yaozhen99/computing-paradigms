import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

print("Step 1: importing win32gui...", flush=True)
import win32gui
print("Step 2: importing win32con...", flush=True)
import win32con
print("Step 3: importing win32api...", flush=True)
import win32api
print("Step 4: all imports OK", flush=True)

print("Step 5: searching windows...", flush=True)
candidates = []
def enum_top(hwnd, _):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if '智谱AI开放平台' in title:
            candidates.append((hwnd, title[:60]))
    return True

win32gui.EnumWindows(enum_top, None)
print(f"Step 6: found {len(candidates)} windows", flush=True)
for h, t in candidates:
    print(f"  hwnd={h} title={t}", flush=True)
