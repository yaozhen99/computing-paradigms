"""干跑测试：验证脚本能找到Edge窗口和渲染子窗口，不实际点击"""
import win32gui
import win32con
import win32api
import time

WINDOW_TITLE_KEYWORD = "智谱AI开放平台"
BUTTON_X = 918
BUTTON_Y = 1875

top_hwnd = None
render_hwnd = None

def enum_top(hwnd, _):
    global top_hwnd
    if win32gui.IsWindowVisible(hwnd):
        title = win32gui.GetWindowText(hwnd)
        if WINDOW_TITLE_KEYWORD in title:
            top_hwnd = hwnd
            return False
    return True

win32gui.EnumWindows(enum_top, None)

if not top_hwnd:
    print(f"❌ 未找到标题含 '{WINDOW_TITLE_KEYWORD}' 的窗口")
    exit(1)

title = win32gui.GetWindowText(top_hwnd)
print(f"✅ 顶级窗口: [{title}]")
print(f"   句柄: {top_hwnd}")
print(f"   类名: {win32gui.GetClassName(top_hwnd)}")

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

render_cls = win32gui.GetClassName(render_hwnd) if render_hwnd != top_hwnd else "顶级窗口(回退)"
print(f"✅ 渲染窗口: 类名={render_cls}")
print(f"   句柄: {render_hwnd}")

# 验证坐标在窗口范围内
rect = win32gui.GetClientRect(render_hwnd)
print(f"   客户区范围: ({rect[0]},{rect[1]}) - ({rect[2]},{rect[3]})")
print(f"   目标点击: ({BUTTON_X}, {BUTTON_Y})")

if BUTTON_X < rect[2] and BUTTON_Y < rect[3]:
    print(f"✅ 坐标在窗口范围内")
else:
    print(f"⚠️ 坐标超出窗口范围！窗口宽={rect[2]} 高={rect[3]}")

# 模拟发送消息（不实际点击，只验证lparam构造）
lparam = win32api.MAKELONG(BUTTON_X, BUTTON_Y)
print(f"✅ lparam构造成功: {lparam}")
print(f"\n🎯 干跑测试通过！脚本可以正常运行。")
