"""
用OCR或像素分析找到"特惠订阅"按钮位置
"""
import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pyautogui
import datetime

# 截图
screenshot = pyautogui.screenshot()
ts = datetime.datetime.now().strftime('%H%M%S')
path = f'C:\\tower-of-babel\\puck\\screenshot_{ts}.png'
screenshot.save(path)
print(f"截图已保存: {path}")

# 尝试用pyautogui找按钮 - 搜索特定颜色区域
# 先试试直接用pyautogui点击 - 搜索"特惠订阅"文字
# pyautogui没有OCR，但可以搜索图片模板

# 让我换一种方式：用win32api直接在最大化窗口上点击多个可能的位置
# 窗口hwnd=3148052是全屏的，所以屏幕坐标≈客户区坐标

# 先把窗口带到前台
import win32gui
import win32con
import win32api
import time

hwnd = 3148052
if win32gui.IsIconic(hwnd):
    win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
win32gui.SetForegroundWindow(hwnd)
time.sleep(0.3)

# 获取窗口位置
rect = win32gui.GetWindowRect(hwnd)
print(f"窗口位置: {rect}")
print(f"窗口大小: {rect[2]-rect[0]} x {rect[3]-rect[1]}")

# 获取客户区位置
client_rect = win32gui.GetClientRect(hwnd)
print(f"客户区大小: {client_rect[2]} x {client_rect[3]}")

# 计算客户区到屏幕坐标的偏移
# 左上角
point = win32gui.ClientToScreen(hwnd, (0, 0))
print(f"客户区屏幕起点: {point}")

# 按钮客户区坐标 (929, 1873) 转屏幕坐标
btn_screen = win32gui.ClientToScreen(hwnd, (929, 1873))
print(f"按钮屏幕坐标(929,1873): {btn_screen}")

# 也检查一下当前时间
now = datetime.datetime.now()
print(f"当前时间: {now.strftime('%H:%M:%S')}")
