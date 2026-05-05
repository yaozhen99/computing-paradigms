"""快速抢购脚本 - 绕过stdout缓冲问题"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys
import io

# 强制unbuffered输出
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import win32gui
import win32con
import win32api
import time
import datetime

# 配置
WINDOW_TITLE_KEYWORD = "智谱AI开放平台"
BUTTON_X = 929
BUTTON_Y = 1873
TARGET_HOUR = 10
TARGET_MIN = 0
TARGET_SEC = 0
SUCCESS_KEYWORDS = ["确认订单", "订单详情", "订单确认", "支付"]
SOLDOUT_KEYWORDS = ["售罄", "已抢完", "已售完", "已结束"]
MAX_RETRY_CLICKS = 30
RETRY_INTERVAL_SEC = 0.08

print("=== 快速抢购脚本启动 ===", flush=True)

# 找窗口
top_hwnd = None
render_hwnd = None

for attempt in range(30):
    top_hwnd = None
    def enum_top(hwnd, _):
        global top_hwnd
        if win32gui.IsWindowVisible(hwnd):
            title = win32gui.GetWindowText(hwnd)
            if WINDOW_TITLE_KEYWORD in title:
                top_hwnd = hwnd
                return False
        return True
    win32gui.EnumWindows(enum_top, None)
    if top_hwnd:
        break
    print(f"  等待窗口... ({attempt+1})", flush=True)
    time.sleep(0.5)

if not top_hwnd:
    print("!!! 未找到窗口，退出 !!!", flush=True)
    sys.exit(1)

title = win32gui.GetWindowText(top_hwnd)
print(f"找到窗口: hwnd={top_hwnd} title={title}", flush=True)

# 找渲染子窗口
render_hwnd = top_hwnd
def enum_child(hwnd, _):
    global render_hwnd
    if win32gui.IsWindowVisible(hwnd):
        cls = win32gui.GetClassName(hwnd)
        if cls == "Chrome_RenderWidgetHostHWND":
            render_hwnd = hwnd
            return False
    return True
win32gui.EnumChildWindows(top_hwnd, enum_child, None)
print(f"渲染窗口: hwnd={render_hwnd} class={win32gui.GetClassName(render_hwnd)}", flush=True)

# NTP校准
offset = 0.0
try:
    import ntplib
    client = ntplib.NTPClient()
    resp = client.request("ntp.aliyun.com", version=3)
    offset = time.time() - resp.tx_time
    print(f"NTP校准: 本地快 {offset:.3f} 秒", flush=True)
except Exception as e:
    print(f"NTP失败({e})，用本地时间", flush=True)

# 计算目标时间
now = datetime.datetime.now()
target = now.replace(hour=TARGET_HOUR, minute=TARGET_MIN, second=TARGET_SEC, microsecond=0)
if target <= now:
    target += datetime.timedelta(days=1)
adjusted_target = target + datetime.timedelta(seconds=offset)
print(f"目标时间: {target.strftime('%H:%M:%S')}", flush=True)
print(f"修正时间: {adjusted_target.strftime('%H:%M:%S.%f')}", flush=True)

# 前置窗口
def focus():
    try:
        if win32gui.IsIconic(top_hwnd):
            win32gui.ShowWindow(top_hwnd, win32con.SW_RESTORE)
        win32gui.SetForegroundWindow(top_hwnd)
        time.sleep(0.1)
    except:
        pass

# 点击
def click():
    lparam = win32api.MAKELONG(BUTTON_X, BUTTON_Y)
    win32api.SendMessage(render_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    time.sleep(0.005)
    win32api.SendMessage(render_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.005)
    win32api.SendMessage(render_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

# 检查标题
def check_title():
    title = win32gui.GetWindowText(top_hwnd)
    for kw in SUCCESS_KEYWORDS:
        if kw in title:
            return "success"
    for kw in SOLDOUT_KEYWORDS:
        if kw in title:
            return "soldout"
    return "unknown"

# 等到前5秒
pre_wake = adjusted_target - datetime.timedelta(seconds=5)
while datetime.datetime.now() < pre_wake:
    time.sleep(0.5)

print("窗口前置...", flush=True)
focus()

# 提前0.3秒忙等
pre_click = adjusted_target - datetime.timedelta(seconds=0.3)
while datetime.datetime.now() < pre_click:
    time.sleep(0.001)

# 高精度忙等
while datetime.datetime.now() < adjusted_target:
    pass

# 第一次点击
click()
click_time = datetime.datetime.now().strftime("%H:%M:%S.%f")
print(f"!!! 第一次点击 @ {click_time} !!!", flush=True)

# 补点循环
deadline = datetime.datetime.now() + datetime.timedelta(seconds=10)
click_count = 1

while datetime.datetime.now() < deadline and click_count < MAX_RETRY_CLICKS:
    state = check_title()
    if state == "success":
        print("!!! 抢购成功 !!!", flush=True)
        sys.exit(0)
    elif state == "soldout":
        print("!!! 已售罄 !!!", flush=True)
        sys.exit(1)
    
    time.sleep(RETRY_INTERVAL_SEC)
    click()
    click_count += 1
    print(f"补点 #{click_count}", flush=True)

print("补点结束，请手动检查", flush=True)
