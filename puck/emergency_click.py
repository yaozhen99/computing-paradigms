"""
紧急补救：用pyautogui直接点击
策略：滚动到页面底部，点击可能的按钮位置
"""
import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pyautogui
import win32gui
import win32con
import time
import datetime

# 把窗口带到前台
hwnd = 3148052
if win32gui.IsIconic(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.3)

# 先检查当前标题
title = win32gui.GetWindowText(hwnd)
print(f"当前标题: {title}")

# 如果标题已经包含成功关键字，直接退出
for kw in ["确认订单", "支付", "订单详情"]:
    if kw in title:
        print(f"🎯 已经成功！标题含'{kw}'")
        sys.exit(0)

# 如果标题含售罄
for kw in ["售罄", "已抢完"]:
    if kw in title:
        print(f"❌ 已售罄")
        sys.exit(1)

print(f"当前时间: {datetime.datetime.now().strftime('%H:%M:%S')}")
print("尝试用pyautogui点击...")

# 用pyautogui点击屏幕坐标 (930, 1873)
# pyautogui用的是屏幕坐标
pyautogui.click(930, 1873)
print(f"点击 (930, 1873)")

time.sleep(1)

# 检查标题变化
title = win32gui.GetWindowText(hwnd)
print(f"点击后标题: {title}")

for kw in ["确认订单", "支付", "订单详情"]:
    if kw in title:
        print(f"🎯 成功！标题含'{kw}'")
        break
else:
    # 尝试其他位置 - 可能按钮在页面不同位置
    # 滚动到页面顶部先
    print("第一次点击未成功，尝试滚动后重新点击...")
    
    # 按Home键回到顶部
    import keyboard
    keyboard.press_and_release('home')
    time.sleep(0.5)
    
    # 滚动到Pro套餐区域 - 用PageDown多次
    for i in range(5):
        keyboard.press_and_release('pagedown')
        time.sleep(0.3)
    
    time.sleep(0.5)
    
    # 尝试多个可能的按钮位置
    positions = [
        (930, 1873),
        (960, 1800),
        (960, 1700),
        (960, 1600),
        (960, 1500),
        (960, 1400),
        (960, 1300),
        (960, 1200),
        (960, 1100),
        (960, 1000),
        (960, 900),
        (960, 800),
    ]
    
    for x, y in positions:
        pyautogui.click(x, y)
        print(f"  点击 ({x}, {y})")
        time.sleep(0.5)
        title = win32gui.GetWindowText(hwnd)
        for kw in ["确认订单", "支付", "订单详情", "售罄"]:
            if kw in title:
                print(f"  检测到: {kw}")
                print(f"  最终标题: {title}")
                sys.exit(0)
    
    title = win32gui.GetWindowText(hwnd)
    print(f"最终标题: {title}")
    print("⚠ 所有点击均未触发跳转，可能需要手动操作")
