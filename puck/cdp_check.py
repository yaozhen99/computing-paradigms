"""
通过Chrome DevTools Protocol (CDP) 连接Edge，执行JS获取页面内容
"""
import os, sys, io
os.environ['PYTHONIOENCODING'] = 'utf-8'
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')

import subprocess
import json
import time

# 先确保Edge开启了远程调试端口
# 检查是否已有带调试端口的Edge
result = subprocess.run(
    ['powershell', '-Command', 
     "Get-Process msedge -ErrorAction SilentlyContinue | Select-Object Id | Format-Table -HideTableHeaders"],
    capture_output=True, text=True
)
print("Edge进程:", result.stdout.strip()[:200])

# 尝试用CDP连接 - Edge默认调试端口9222
import urllib.request
try:
    resp = urllib.request.urlopen('http://localhost:9222/json', timeout=3)
    tabs = json.loads(resp.read())
    print(f"\n找到 {len(tabs)} 个标签页:")
    for tab in tabs:
        print(f"  {tab.get('title', '?')[:60]} - {tab.get('url', '?')[:80]}")
        if 'bigmodel' in tab.get('url', '').lower() or 'coding' in tab.get('url', '').lower():
            print(f"    ^^^ 目标页面！webSocketDebuggerUrl: {tab.get('webSocketDebuggerUrl', '?')[:80]}")
except Exception as e:
    print(f"CDP连接失败: {e}")
    print("Edge可能没有开启远程调试端口")
    print("需要用 --remote-debugging-port=9222 启动Edge")
