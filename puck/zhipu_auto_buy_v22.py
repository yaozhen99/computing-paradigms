"""
智谱Pro套餐定时抢购脚本 v2.2 - 紧急修正版
直接指定hwnd，跳过搜索
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

# ==================== 配置区 ====================
BUTTON_X = 929
BUTTON_Y = 1873
TARGET_HOUR = 10
TARGET_MIN = 0
TARGET_SEC = 0
SUCCESS_KEYWORDS = ["确认订单", "订单详情", "订单确认", "支付"]
SOLDOUT_KEYWORDS = ["售罄", "已抢完", "已售完", "已结束"]
MAX_RETRY_CLICKS = 20
RETRY_INTERVAL_SEC = 0.10
MAX_RETRY_DURATION_SEC = 8
NTP_SERVER = "ntp.aliyun.com"
# ================================================

# 直接用最大化窗口的hwnd
TOP_HWND = 3148052

class AutoBuyer:
    def __init__(self):
        self.top_hwnd = TOP_HWND
        self.render_hwnd = self.top_hwnd
        
        # 找渲染子窗口
        def enum_child(hwnd, _):
            if win32gui.IsWindowVisible(hwnd):
                cls = win32gui.GetClassName(hwnd)
                if cls == "Chrome_RenderWidgetHostHWND":
                    self.render_hwnd = hwnd
                    return False
            return True
        win32gui.EnumChildWindows(self.top_hwnd, enum_child, None)
        
        title = win32gui.GetWindowText(self.top_hwnd)
        render_cls = win32gui.GetClassName(self.render_hwnd) if self.render_hwnd != self.top_hwnd else "顶级窗口(回退)"
        print(f"✅ 顶级窗口: [{title[:60]}] 句柄={self.top_hwnd}")
        print(f"✅ 渲染窗口: 类名={render_cls} 句柄={self.render_hwnd}")

    def _focus(self):
        try:
            if win32gui.IsIconic(self.top_hwnd):
                win32gui.ShowWindow(self.top_hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(self.top_hwnd)
            time.sleep(0.15)
        except Exception:
            pass

    def _click_once(self):
        lparam = win32api.MAKELONG(BUTTON_X, BUTTON_Y)
        win32api.SendMessage(self.render_hwnd, win32con.WM_MOUSEMOVE, 0, lparam)
        time.sleep(0.008)
        win32api.SendMessage(self.render_hwnd, win32con.WM_LBUTTONDOWN, win32con.MK_LBUTTON, lparam)
        time.sleep(0.008)
        win32api.SendMessage(self.render_hwnd, win32con.WM_LBUTTONUP, 0, lparam)

    def _check_title(self):
        title = win32gui.GetWindowText(self.top_hwnd)
        for kw in SUCCESS_KEYWORDS:
            if kw in title:
                return "success"
        for kw in SOLDOUT_KEYWORDS:
            if kw in title:
                return "soldout"
        return "unknown"

    def start(self):
        offset = 0.0
        try:
            import ntplib
            client = ntplib.NTPClient()
            resp = client.request(NTP_SERVER, version=3)
            offset = time.time() - resp.tx_time
            print(f"⏱ NTP校准: 本地比标准时间快 {offset:.3f} 秒")
        except Exception as e:
            print(f"⚠ NTP同步失败({e})，使用本地时间")

        now = datetime.datetime.now()
        target = now.replace(hour=TARGET_HOUR, minute=TARGET_MIN, second=TARGET_SEC, microsecond=0)
        if target <= now:
            target += datetime.timedelta(days=1)
        adjusted_target = target + datetime.timedelta(seconds=offset)
        print(f"📅 目标时间: {target.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"📅 修正后:   {adjusted_target.strftime('%Y-%m-%d %H:%M:%S.%f')}")

        # 等待到抢购前5秒
        pre_wake = adjusted_target - datetime.timedelta(seconds=5)
        while datetime.datetime.now() < pre_wake:
            time.sleep(0.5)

        self._focus()
        print("🖥 窗口已前置，等待开抢...")

        pre_click = adjusted_target - datetime.timedelta(seconds=0.3)
        while datetime.datetime.now() < pre_click:
            time.sleep(0.001)

        while datetime.datetime.now() < adjusted_target:
            pass

        self._click_once()
        click_time = datetime.datetime.now().strftime("%H:%M:%S.%f")
        print(f"🚀 第一次点击 @ {click_time}")

        deadline = datetime.datetime.now() + datetime.timedelta(seconds=MAX_RETRY_DURATION_SEC)
        click_count = 1

        while datetime.datetime.now() < deadline and click_count < MAX_RETRY_CLICKS:
            state = self._check_title()
            if state == "success":
                print("🎯 抢购成功！")
                return "success"
            elif state == "soldout":
                print("❌ 已售罄，停止抢购")
                return "soldout"

            time.sleep(RETRY_INTERVAL_SEC)
            self._click_once()
            click_count += 1
            print(f"🔄 补点 #{click_count}")

        print("⏰ 补点结束，未检测到成功跳转")
        return "timeout"

if __name__ == "__main__":
    print("=" * 50)
    print("智谱Pro套餐定时抢购脚本 v2.2 (紧急修正)")
    print("=" * 50)

    buyer = AutoBuyer()
    result = buyer.start()
    print(f"\n最终结果: {result}")
