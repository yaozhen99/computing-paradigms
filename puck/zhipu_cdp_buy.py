"""持续刷新抢购脚本 - 通过浏览器控制台注入"""
import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys, io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace', line_buffering=True)

import time
from datetime import datetime

# 通过CDP直接操作浏览器
import json
import urllib.request

CDP_PORT = 18800

def get_tabs():
    """获取所有标签页"""
    req = urllib.request.Request(f'http://127.0.0.1:{CDP_PORT}/json')
    with urllib.request.urlopen(req, timeout=3) as resp:
        return json.loads(resp.read())

def find_zhipu_tab():
    """找到智谱页面标签"""
    tabs = get_tabs()
    for tab in tabs:
        if 'bigmodel.cn' in tab.get('url', ''):
            return tab
    return None

def send_cdp(ws_url, method, params=None):
    """通过WebSocket发送CDP命令"""
    import websocket
    ws = websocket.create_connection(ws_url, timeout=10)
    msg = {'id': 1, 'method': method}
    if params:
        msg['params'] = params
    ws.send(json.dumps(msg))
    result = json.loads(ws.recv())
    ws.close()
    return result

def evaluate_js(tab, js_code):
    """在标签页执行JS"""
    ws_url = tab['webSocketDebuggerUrl']
    import websocket
    ws = websocket.create_connection(ws_url, timeout=10)
    
    # 发送执行命令
    msg = {'id': 1, 'method': 'Runtime.evaluate', 'params': {'expression': js_code, 'returnByValue': True}}
    ws.send(json.dumps(msg))
    result = json.loads(ws.recv())
    ws.close()
    return result

print("=== CDP持续刷新抢购脚本 ===", flush=True)

# 先安装websocket-client
try:
    import websocket
except ImportError:
    print("安装websocket-client...", flush=True)
    import subprocess
    subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'websocket-client', '-q'])
    import websocket

attempts = 0
max_attempts = 100

while attempts < max_attempts:
    attempts += 1
    now = datetime.now().strftime('%H:%M:%S')
    
    try:
        tab = find_zhipu_tab()
        if not tab:
            print(f"[{now}] 未找到智谱页面标签", flush=True)
            time.sleep(2)
            continue
        
        # 检查按钮状态
        js_check = """
        (function() {
            const buttons = document.querySelectorAll('button');
            for (const btn of buttons) {
                const text = btn.textContent || '';
                // Pro按钮在第二个位置（Lite之后）
                if (text.includes('特惠订阅') || text.includes('立即订阅')) {
                    return {text: text.trim(), disabled: btn.disabled, clicked: false};
                }
            }
            // 检查所有按钮文字
            const allTexts = Array.from(buttons).map(b => b.textContent.trim()).filter(t => t.includes('售罄') || t.includes('抢购') || t.includes('订阅'));
            return {text: allTexts.join(' | '), disabled: true, clicked: false};
        })()
        """
        
        result = evaluate_js(tab, js_check)
        value = result.get('result', {}).get('result', {}).get('value', {})
        btn_text = value.get('text', 'unknown')[:60] if isinstance(value, dict) else str(value)[:60]
        btn_disabled = value.get('disabled', True) if isinstance(value, dict) else True
        
        print(f"[{now}] #{attempts} 按钮: {btn_text} disabled={btn_disabled}", flush=True)
        
        if not btn_disabled:
            # 按钮可点击！点击Pro按钮
            js_click = """
            (function() {
                const buttons = document.querySelectorAll('button');
                for (const btn of buttons) {
                    const text = btn.textContent || '';
                    if ((text.includes('特惠订阅') || text.includes('立即订阅')) && !btn.disabled) {
                        btn.click();
                        return 'CLICKED: ' + text.trim();
                    }
                }
                return 'No clickable button found';
            })()
            """
            click_result = evaluate_js(tab, js_click)
            click_value = click_result.get('result', {}).get('result', {}).get('value', '')
            print(f"!!! {click_value} !!!", flush=True)
            
            if 'CLICKED' in str(click_value):
                print("!!! 抢购按钮已点击，等待页面跳转 !!!", flush=True)
                time.sleep(3)
                # 检查是否跳转到订单页
                tab2 = find_zhipu_tab()
                if tab2:
                    check_result = evaluate_js(tab2, "document.title")
                    title = check_result.get('result', {}).get('result', {}).get('value', '')
                    print(f"页面标题: {title}", flush=True)
                    if '确认订单' in title or '支付' in title or '订单' in title:
                        print("!!! 抢购成功 !!!", flush=True)
                        break
                print("未检测到成功跳转，继续尝试...", flush=True)
        
        # 刷新页面
        if btn_disabled and attempts < max_attempts:
            evaluate_js(tab, "location.reload()")
            time.sleep(1.5)
        
    except Exception as e:
        print(f"[{now}] 错误: {e}", flush=True)
        time.sleep(2)

print("脚本结束", flush=True)
