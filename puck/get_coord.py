"""
坐标采集工具
把鼠标放在购买按钮上，按 Ctrl+Shift+P 打印客户区坐标
按 Ctrl+Shift+Q 退出
"""

import pyautogui
import keyboard
import win32gui
import time

print("把鼠标放在购买按钮上，按 Ctrl+Shift+P 打印客户区坐标")
print("按 Ctrl+Shift+Q 退出")
print("-" * 40)

while True:
    if keyboard.is_pressed('ctrl+shift+p'):
        hwnd = win32gui.GetForegroundWindow()
        sx, sy = pyautogui.position()
        cx, cy = win32gui.ScreenToClient(hwnd, (sx, sy))
        title = win32gui.GetWindowText(hwnd)
        class_name = win32gui.GetClassName(hwnd)
        print(f"窗口: [{title}] 类名={class_name}")
        print(f"  屏幕坐标: ({sx}, {sy})")
        print(f"  客户区坐标: ({cx}, {cy})  ← 填入 BUTTON_X, BUTTON_Y")
        print("-" * 40)
        time.sleep(0.5)
    if keyboard.is_pressed('ctrl+shift+q'):
        print("退出")
        break
    time.sleep(0.1)
