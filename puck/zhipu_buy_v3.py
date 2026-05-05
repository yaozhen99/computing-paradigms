"""智谱Pro抢购脚本 - 简化版 v3
直接用win32api点击Edge渲染窗口
"""
import win32gui, win32con, win32api, time, datetime, ctypes

# 配置
BUTTON_X = 929
BUTTON_Y = 1873
TARGET_HOUR = 10
TARGET_MIN = 0
TARGET_SEC = 0
NTP_SERVER = "ntp.aliyun.com"
SUCCESS_KEYWORDS = ["确认订单", "订单详情", "订单确认", "支付"]
SOLDOUT_KEYWORDS = ["售罄", "已抢完", "已售完", "已结束"]

print("=" * 50)
print("智谱Pro抢购脚本 v3 (简化版)")
print("=" * 50)

# 找窗口
print("搜索Edge窗口...")
top_hwnd = None
render_hwnd = None

def enum_top(hwnd, _):
    global top_hwnd
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if '智谱AI开放平台' in title and 'DeepSeek' not in title:
            # Check for render child
            rh = None
            def enum_child(ch, _):
                nonlocal rh
                cls = win32gui.GetClassName(ch)
                if cls == 'Chrome_RenderWidgetHostHWND':
                    rh = ch
                return True
            win32gui.EnumChildWindows(hwnd, enum_child, None)
            if rh:
                top_hwnd = hwnd
                return False
    return True

win32gui.EnumWindows(enum_top, None)

if not top_hwnd:
    print("ERROR: 未找到智谱Edge窗口！")
    input("按回车退出...")
    exit(1)

# 找渲染子窗口
def enum_child(hwnd, _):
    global render_hwnd
    if win32gui.IsWindowVisible(hwnd):
        cls = win32gui.GetClassName(hwnd)
        if cls == 'Chrome_RenderWidgetHostHWND':
            render_hwnd = hwnd
            return False
    return True
win32gui.EnumChildWindows(top_hwnd, enum_child, None)

title = win32gui.GetWindowText(top_hwnd)
print(f"顶级窗口: [{title}] hwnd={top_hwnd}")
print(f"渲染窗口: hwnd={render_hwnd}")

# NTP校准
offset = 0.0
try:
    import ntplib
    client = ntplib.NTPClient()
    resp = client.request(NTP_SERVER, version=3)
    offset = time.time() - resp.tx_time
    print(f"NTP校准: 本地比标准时间快 {offset:.3f} 秒")
except Exception as e:
    print(f"NTP同步失败({e})，使用本地时间")

# 计算目标时间
now = datetime.datetime.now()
target = now.replace(hour=TARGET_HOUR, minute=TARGET_MIN, second=TARGET_SEC, microsecond=0)
if target <= now:
    target += datetime.timedelta(days=1)
adjusted = target + datetime.timedelta(seconds=offset)
print(f"目标时间: {target.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"修正后:   {adjusted.strftime('%Y-%m-%d %H:%M:%S.%f')}")

# 前置窗口
if win32gui.IsIconic(top_hwnd):
    win32gui.ShowWindow(top_hwnd, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(top_hwnd)
time.sleep(0.3)
print("窗口已前置")

# 等待到抢购前5秒
pre_wake = adjusted - datetime.timedelta(seconds=5)
while datetime.datetime.now() < pre_wake:
    time.sleep(0.5)
print("还剩5秒！")

# 提前0.3秒进入忙等
pre_click = adjusted - datetime.timedelta(seconds=0.3)
while datetime.datetime.now() < pre_click:
    time.sleep(0.001)

# 高精度忙等
while datetime.datetime.now() < adjusted:
    pass

# 点击！
lparam = win32api.MAKELONG(BUTTON_X, BUTTON_Y)
win32api.SendMessage(render_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
time.sleep(0.008)
win32api.SendMessage(render_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
time.sleep(0.008)
win32api.SendMessage(render_hwnd, win32con.WM_LBUTTONUP, 0, lparam)
click_time = datetime.datetime.now().strftime("%H:%M:%S.%f")
print(f"第一次点击 @ {click_time}")

# 补点循环
deadline = datetime.datetime.now() + datetime.timedelta(seconds=8)
click_count = 1
while datetime.datetime.now() < deadline and click_count < 20:
    title = win32gui.GetWindowText(top_hwnd)
    for kw in SUCCESS_KEYWORDS:
        if kw in title:
            print(f"SUCCESS! 窗口标题: {title}")
            print("请尽快完成支付！")
            input("按回车退出...")
            exit(0)
    for kw in SOLDOUT_KEYWORDS:
        if kw in title:
            print(f"SOLD OUT! 窗口标题: {title}")
            input("按回车退出...")
            exit(1)
    time.sleep(0.10)
    win32api.SendMessage(render_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
    time.sleep(0.008)
    win32api.SendMessage(render_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
    time.sleep(0.008)
    win32api.SendMessage(render_hwnd, win32con.WM_LBUTTONUP, 0, lparam)
    click_count += 1
    print(f"补点 #{click_count}")

print("补点结束，未检测到成功跳转，请手动检查页面。")
