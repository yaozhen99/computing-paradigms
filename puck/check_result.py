import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import win32gui
import datetime

candidates = []
def cb(h, _):
    if win32gui.IsWindowVisible(h):
        t = win32gui.GetWindowText(h)
        if any(kw in t for kw in ['智谱', '确认订单', '支付', '售罄', '订单', 'bigmodel', 'Coding']):
            candidates.append((h, t[:120]))
    return True

win32gui.EnumWindows(cb, None)
now = datetime.datetime.now().strftime('%H:%M:%S')
print(f"[{now}] 窗口列表:")
for h, t in candidates:
    print(f"  hwnd={h} title={t}")
