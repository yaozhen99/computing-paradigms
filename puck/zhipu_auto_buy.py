"""
智谱Pro套餐定时抢购脚本 v2
- 针对Edge浏览器（已登录状态）
- NTP时间校准 + 忙等精准触发
- hwnd窗口消息点击（发给Chrome_RenderWidgetHostHWND渲染子窗口）
- 点击后循环检测窗口标题，智能补点
- 成功后清空键盘消息队列，干净退出
- 支持自动打开Edge到目标页面

使用前：
1. pip install pywin32 ntplib keyboard pyautogui
2. 确认Edge已登录智谱账号
3. 运行脚本，等待自动触发
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import win32gui
import win32con
import win32api
import ctypes
import time
import datetime
import subprocess
import sys

# ==================== 配置区 ====================
TARGET_URL = "https://bigmodel.cn/glm-coding"
EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"

# 窗口匹配关键字（Edge标签页标题）
WINDOW_TITLE_KEYWORD = "智谱AI开放平台"

# Pro套餐"特惠订阅"按钮的客户区坐标
# 需要用 get_coord.py 在Edge中测量，填入实际值
BUTTON_X = 929
BUTTON_Y = 1873

# 抢购时间
TARGET_HOUR = 10
TARGET_MIN = 0
TARGET_SEC = 0

# 成功/失败检测关键字
SUCCESS_KEYWORDS = ["确认订单", "订单详情", "订单确认", "支付"]
SOLDOUT_KEYWORDS = ["售罄", "已抢完", "已售完", "已结束"]

# 补点参数
MAX_RETRY_CLICKS = 20         # 最多补点次数
RETRY_INTERVAL_SEC = 0.10     # 补点间隔（秒）
MAX_RETRY_DURATION_SEC = 8    # 补点最长持续时间（秒）

# NTP
NTP_SERVER = "ntp.aliyun.com"
# ================================================


def open_edge_page():
    """用已登录的Edge打开目标页面"""
    # 用已有profile启动Edge，保留登录态
    cmd = [
        EDGE_PATH,
        "--new-window",
        TARGET_URL
    ]
    subprocess.Popen(cmd)
    print(f"🌐 已启动Edge打开 {TARGET_URL}")
    time.sleep(3)  # 等页面加载


class AutoBuyer:
    def __init__(self):
        self.top_hwnd = None
        self.render_hwnd = None
        self._find_windows()

    def _find_windows(self):
        """找到Edge顶级窗口和渲染子窗口"""
        print(f"🔍 搜索窗口标题含 '{WINDOW_TITLE_KEYWORD}' ...")

        # 最多重试10秒，等页面加载
        for attempt in range(20):
            self.top_hwnd = None
            self.render_hwnd = None

            def enum_top(hwnd, _):
                if win32gui.IsWindowVisible(hwnd):
                    title = win32gui.GetWindowText(hwnd)
                    if WINDOW_TITLE_KEYWORD in title:
                        self.top_hwnd = hwnd
                        return False
                return True
            win32gui.EnumWindows(enum_top, None)

            if self.top_hwnd:
                break

            print(f"  等待页面加载... ({attempt+1})")
            time.sleep(0.5)

        if not self.top_hwnd:
            raise Exception(f"未找到标题含 '{WINDOW_TITLE_KEYWORD}' 的窗口")

        # 找渲染子窗口
        self.render_hwnd = self.top_hwnd
        def enum_child(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                cls = win32gui.GetClassName(hwnd)
                if cls == "Chrome_RenderWidgetHostHWND":
                    self.render_hwnd = hwnd
                    return False
            return True
        win32gui.EnumChildWindows(self.top_hwnd, enum_child, None)

        top_title = win32gui.GetWindowText(self.top_hwnd)
        render_cls = win32gui.GetClassName(self.render_hwnd) if self.render_hwnd != self.top_hwnd else "顶级窗口(回退)"
        print(f"✅ 顶级窗口: [{top_title}] 句柄={self.top_hwnd}")
        print(f"✅ 渲染窗口: 类名={render_cls} 句柄={self.render_hwnd}")

    def _focus(self):
        """把Edge窗口带到前台"""
        try:
            if win32gui.IsIconic(self.top_hwnd):
                win32gui.ShowWindow(self.top_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.top_hwnd)
            time.sleep(0.15)
        except Exception:
            pass

    def _click_once(self):
        """向渲染窗口发送一次鼠标左键点击"""
        lparam = win32api.MAKELONG(BUTTON_X, BUTTON_Y)
        # 鼠标移动
        win32api.SendMessage(self.render_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(0.008)
        # 按下
        win32api.SendMessage(self.render_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.008)
        # 释放
        win32api.SendMessage(self.render_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def _check_title(self):
        """检查窗口标题判断状态: 'success' | 'soldout' | 'unknown'"""
        title = win32gui.GetWindowText(self.top_hwnd)
        for kw in SUCCESS_KEYWORDS:
            if kw in title:
                return "success"
        for kw in SOLDOUT_KEYWORDS:
            if kw in title:
                return "soldout"
        return "unknown"

    def _cleanup_and_exit(self):
        """彻底清空键盘状态和消息队列，然后退出"""
        print("🎯 抢购成功！正在清理键盘状态...")

        # 强制抬起修饰键
        for vk in [win32con.VK_CONTROL, win32con.VK_SHIFT, win32con.VK_MENU]:
            win32api.keybd_event(vk, 0, win32con.KEYEVENTF_KEYUP, 0)

        # 清空消息队列
        msg = ctypes.wintypes.MSG()
        for hwnd in [self.render_hwnd, self.top_hwnd]:
            if hwnd:
                while win32gui.PeekMessage(ctypes.byref(msg), hwnd, 0, 0, win32con.PM_REMOVE):
                    pass

        print("✅ 已清理，可以安全手动操作了。请尽快完成支付！")
        sys.exit(0)

    def start(self):
        """主流程"""
        # ---- NTP 校准 ----
        offset = 0.0
        try:
            import ntplib
            client = ntplib.NTPClient()
            resp = client.request(NTP_SERVER, version=3)
            offset = time.time() - resp.tx_time
            print(f"⏱ NTP校准: 本地比标准时间快 {offset:.3f} 秒")
        except Exception as e:
            print(f"⚠ NTP同步失败({e})，使用本地时间")

        # ---- 计算目标时间 ----
        now = datetime.datetime.now()
        target = now.replace(
            hour=TARGET_HOUR, minute=TARGET_MIN, second=TARGET_SEC, microsecond=0
        )
        # 如果今天的时间已过，说明是明天
        if target <= now:
            target += datetime.timedelta(days=1)
        adjusted_target = target + datetime.timedelta(seconds=offset)
        print(f"📅 目标时间: {target.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 修正后:   {adjusted_target.strftime('%Y-%m-%d %H:%M:%S.%f')}")

        # ---- 等待到抢购前5秒 ----
        pre_wake = adjusted_target - datetime.timedelta(seconds=5)
        while datetime.datetime.now() < pre_wake:
            time.sleep(0.5)

        # ---- 提前激活窗口 ----
        self._focus()
        print("🖥 窗口已前置，等待开抢...")

        # ---- 提前0.3秒进入忙等 ----
        pre_click = adjusted_target - datetime.timedelta(seconds=0.3)
        while datetime.datetime.now() < pre_click:
            time.sleep(0.001)

        # ---- 高精度忙等到点 ----
        while datetime.datetime.now() < adjusted_target:
            pass

        # ---- 第一次点击 ----
        self._click_once()
        click_time = datetime.datetime.now().strftime("%H:%M:%S.%f")
        print(f"🚀 第一次点击 @ {click_time}")

        # ---- 循环补点 + 状态检测 ----
        deadline = datetime.datetime.now() + datetime.timedelta(seconds=MAX_RETRY_DURATION_SEC)
        click_count = 1

        while datetime.datetime.now() < deadline and click_count < MAX_RETRY_CLICKS:
            state = self._check_title()
            if state == "success":
                self._cleanup_and_exit()
            elif state == "soldout":
                print("❌ 已售罄，停止抢购")
                return

            time.sleep(RETRY_INTERVAL_SEC)
            self._click_once()
            click_count += 1
            print(f"🔄 补点 #{click_count}")

        print("⏰ 补点结束，未检测到成功跳转，请手动检查页面。")


if __name__ == "__main__":
    print("=" * 50)
    print("智谱Pro套餐定时抢购脚本 v2")
    print("=" * 50)

    # 先尝试打开Edge页面
    open_edge_page()

    buyer = AutoBuyer()
    buyer.start()
