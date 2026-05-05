import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import pyautogui
import datetime

# 截图保存
screenshot = pyautogui.screenshot()
ts = datetime.datetime.now().strftime('%H%M%S')
path = f'C:\\tower-of-babel\\puck\\screenshot_{ts}.png'
screenshot.save(path)
print(f"截图已保存: {path}")
print(f"分辨率: {screenshot.size}")
