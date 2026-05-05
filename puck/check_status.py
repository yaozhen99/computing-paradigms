import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import win32gui
import win32con
import time

# 查找智谱窗口并检查状态
candidates = []
def enum_top(hwnd, _):
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if '智谱AI开放平台' in title:
            candidates.append((hwnd, title[:80]))
    return True

win32gui.EnumWindows(enum_top, None)
print(f"找到 {len(candidates)} 个智谱窗口:")
for h, t in candidates:
    # 检查是否有coding相关
    is_coding = 'coding' in t.lower() or 'glm' in t.lower()
    print(f"  hwnd={h} coding={is_coding} title={t}")
    
    # 找渲染子窗口
    render_hwnd = [h]
    def enum_child(ch, _):
        if win32gui.IsWindowVisible(ch):
            cls = win32gui.GetClassName(ch)
            if cls == "Chrome_RenderWidgetHostHWND":
                render_hwnd[0] = ch
                return False
        return True
    win32gui.EnumChildWindows(h, enum_child, None)
    print(f"    render_hwnd={render_hwnd[0]}")

# 检查当前时间
import datetime
now = datetime.datetime.now()
print(f"\n当前时间: {now.strftime('%H:%M:%S')}")
print(f"距离10:00: 还有 {(10*3600 - now.hour*3600 - now.minute*60 - now.second)} 秒")
