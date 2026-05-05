import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import win32gui
import win32con

candidates = []
def enum_top(hwnd, _):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if '智谱AI开放平台' in title:
            rect = win32gui.GetWindowRect(hwnd)
            w = rect[2] - rect[0]
            h = rect[3] - rect[1]
            candidates.append((hwnd, title[:80], rect, w, h))
    return True

win32gui.EnumWindows(enum_top, None)
print(f"找到 {len(candidates)} 个智谱窗口:")
for h, t, rect, w, hh in candidates:
    print(f"  hwnd={h} size={w}x{hh} pos=({rect[0]},{rect[1]}) title={t}")

import datetime
now = datetime.datetime.now()
print(f"\n当前时间: {now.strftime('%H:%M:%S')}")
