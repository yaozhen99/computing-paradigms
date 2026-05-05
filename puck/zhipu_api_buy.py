"""
智谱Pro套餐 API直调抢购脚本 v1
=================================

核心思路：跳过前端，直接调API，速度<100ms。
相比hwnd窗口消息方案（串行3-5秒），API直调方案直接发HTTP请求。

流程：
1. 从已登录浏览器Cookie中提取Token（Authorization header）
2. 开抢前5分钟，在浏览器中完成腾讯验证码，获取ticket+randstr
3. NTP校准时间
4. 开抢时刻直接POST /biz/pay/preview（参数：productId, invitationCode, ticket, randstr）
5. 获取bizId后调 /biz/pay/create-sign（参数：payType, productId, customerId, bizId）
6. 获取sign URL后输出，人工扫码支付
7. 轮询 /biz/pay/check?bizId=xxx 检测支付结果

使用前：
1. pip install requests ntplib pycryptodome
2. 确保Edge已登录智谱账号（bigmodel.cn）
3. 运行脚本，按提示操作

命令行参数：
  --product-id     产品ID（默认: product-fef82f 即Pro包季）
  --time           抢购时间，格式 HH:MM:SS（默认: 10:00:00）
  --pay-type       支付方式 ALI=支付宝 WE_CHAT=微信（默认: ALI）
  --token          手动提供Token（不提供则自动从浏览器Cookie获取）
  --ticket         手动提供验证码ticket（不提供则自动触发验证码）
  --randstr        手动提供验证码randstr
  --ntp-server     NTP服务器（默认: ntp.aliyun.com）
  --no-ntp         禁用NTP校准
  --preview-only   只执行preview，不执行支付（调试用）
  --retry-interval 补点重试间隔ms（默认: 100）
  --max-retries    最大重试次数（默认: 50）
  --cdp-port       CDP调试端口（默认: 18800）
  --invitation-code 邀请码（可选）

示例：
  python zhipu_api_buy.py
  python zhipu_api_buy.py --product-id product-fef82f --time 10:00:00 --pay-type ALI
  python zhipu_api_buy.py --token "your_token" --ticket "your_ticket" --randstr "your_randstr"
"""

import os
os.environ['PYTHONIOENCODING'] = 'utf-8'
import sys
import io
sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

import argparse
import json
import time
import datetime
import base64
import hashlib
import sqlite3
import shutil
import tempfile
import subprocess
import re

import requests
import ntplib

# ==================== 常量 ====================
API_BASE = "https://bigmodel.cn"
CAPTCHA_APP_ID = "196026326"
AES_KEY = "zhiPuAi123456789"  # 16 bytes, AES-128

# API路径
PATH_PREVIEW = "/biz/pay/preview"
PATH_CREATE_SIGN = "/biz/pay/create-sign"
PATH_PAY_CHECK = "/biz/pay/check"
PATH_IS_LIMIT_BUY = "/biz/product/isLimitBuy"
PATH_SUBSCRIPTION_LIST = "/biz/subscription/list"

# 默认配置
DEFAULT_PRODUCT_ID = "product-fef82f"  # Pro包季
DEFAULT_PAY_TYPE = "ALI"
DEFAULT_NTP_SERVER = "ntp.aliyun.com"
DEFAULT_CDP_PORT = 18800
DEFAULT_RETRY_INTERVAL_MS = 100
DEFAULT_MAX_RETRIES = 50
DEFAULT_TARGET_TIME = "10:00:00"

# Edge Cookie数据库路径（Win10/11默认）
EDGE_COOKIE_PATHS = [
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Default\Cookies"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Profile 1\Cookies"),
    os.path.expandvars(r"%LOCALAPPDATA%\Microsoft\Edge\User Data\Profile 2\Cookies"),
]

# Cookie域名匹配
COOKIE_DOMAIN = ".bigmodel.cn"
TOKEN_COOKIE_NAME = None  # 需要动态探测，可能是 "TokenKey" 或其他


# ==================== AES加密（支付中间页） ====================
def aes_encrypt(data_dict):
    """
    AES-ECB-PKCS7加密，用于生成支付中间页URL参数
    密钥: zhiPuAi123456789 (16 bytes)
    """
    try:
        from Crypto.Cipher import AES
        from Crypto.Util.Padding import pad
    except ImportError:
        # 尝试 pycryptodome 的另一个导入路径
        from Cryptodome.Cipher import AES
        from Cryptodome.Util.Padding import pad

    key = AES_KEY.encode('utf-8')
    cipher = AES.new(key, AES.MODE_ECB)
    plaintext = json.dumps(data_dict, ensure_ascii=False).encode('utf-8')
    padded = pad(plaintext, AES.block_size)
    encrypted = cipher.encrypt(padded)
    return base64.b64encode(encrypted).decode('utf-8')


# ==================== Token获取 ====================
def get_token_from_cdp(cdp_port=DEFAULT_CDP_PORT):
    """
    方案1（优先）：通过CDP协议从已登录浏览器中读取Cookie中的Token
    """
    try:
        import websocket
    except ImportError:
        print("⚠ 需要安装 websocket-client: pip install websocket-client")
        return None

    cdp_url = f"http://127.0.0.1:{cdp_port}"

    try:
        # 获取标签页列表
        resp = requests.get(f"{cdp_url}/json", timeout=5)
        tabs = resp.json()

        # 找bigmodel.cn的标签页
        target_ws_url = None
        for tab in tabs:
            if 'bigmodel.cn' in tab.get('url', ''):
                target_ws_url = tab.get('webSocketDebuggerUrl')
                break

        if not target_ws_url:
            # 没有bigmodel标签页，用任意page标签页
            for tab in tabs:
                if tab.get('type') == 'page':
                    target_ws_url = tab.get('webSocketDebuggerUrl')
                    break

        if not target_ws_url:
            print("⚠ CDP: 未找到可用的标签页")
            return None

        # 连接并读取Cookie
        ws = websocket.create_connection(target_ws_url, timeout=10)

        # 获取bigmodel.cn的所有Cookie
        msg_id = 1
        msg = {
            "id": msg_id,
            "method": "Network.getCookies",
            "params": {"urls": ["https://bigmodel.cn"]}
        }
        ws.send(json.dumps(msg))
        result = json.loads(ws.recv())

        cookies = result.get('result', {}).get('cookies', [])
        ws.close()

        # 查找Token Cookie
        # Token可能存储在各种名字下，优先找Authorization相关的
        token = None
        for cookie in cookies:
            name = cookie.get('name', '')
            domain = cookie.get('domain', '')
            if COOKIE_DOMAIN in domain or 'bigmodel' in domain:
                # 常见Token Cookie名
                if name in ('token', 'Token', 'TokenKey', 'Authorization',
                           'access_token', 'accessToken', 'auth_token',
                           'jwt', 'sid', 'session_id'):
                    token = cookie.get('value', '')
                    print(f"✅ CDP: 从Cookie '{name}' 获取到Token")
                    break

        # 如果没找到明确的Token名，尝试找最长的Cookie值（通常是JWT token）
        if not token and cookies:
            bigmodel_cookies = [c for c in cookies
                              if COOKIE_DOMAIN in c.get('domain', '') or 'bigmodel' in c.get('domain', '')]
            if bigmodel_cookies:
                # 按值长度排序，最长的可能是token
                bigmodel_cookies.sort(key=lambda c: len(c.get('value', '')), reverse=True)
                for c in bigmodel_cookies:
                    val = c.get('value', '')
                    # JWT token通常是 eyJ 开头
                    if val.startswith('eyJ') or len(val) > 50:
                        token = val
                        print(f"✅ CDP: 从Cookie '{c['name']}' 获取到Token (长度={len(val)})")
                        break

        if not token:
            print(f"⚠ CDP: 在 {len(cookies)} 个Cookie中未找到Token")
            # 打印所有bigmodel.cn的cookie名帮助调试
            for c in cookies:
                if 'bigmodel' in c.get('domain', ''):
                    print(f"  Cookie: {c['name']} = {c.get('value', '')[:20]}...")

        return token

    except requests.exceptions.ConnectionError:
        print("⚠ CDP: 无法连接到浏览器调试端口，请确保Edge以 --remote-debugging-port 启动")
        return None
    except Exception as e:
        print(f"⚠ CDP获取Token失败: {e}")
        return None


def get_token_from_cookie_db():
    """
    方案2：从Edge Cookie SQLite数据库中读取Token
    需要Edge关闭或数据库可读
    """
    for cookie_path in EDGE_COOKIE_PATHS:
        if not os.path.exists(cookie_path):
            continue

        try:
            # 复制数据库到临时文件（避免锁定问题）
            tmp_dir = tempfile.mkdtemp()
            tmp_db = os.path.join(tmp_dir, "Cookies")
            shutil.copy2(cookie_path, tmp_db)

            conn = sqlite3.connect(tmp_db)
            cursor = conn.cursor()

            # 查询bigmodel.cn的Cookie
            cursor.execute(
                "SELECT name, encrypted_value, value FROM cookies "
                "WHERE host_key LIKE '%bigmodel%'"
            )
            rows = cursor.fetchall()
            conn.close()
            shutil.rmtree(tmp_dir, ignore_errors=True)

            if not rows:
                continue

            # 尝试找Token
            for name, encrypted_value, value in rows:
                if value:
                    # 明文Cookie
                    if name in ('token', 'Token', 'TokenKey', 'Authorization',
                               'access_token', 'accessToken') or value.startswith('eyJ'):
                        print(f"✅ CookieDB: 从 '{name}' 获取到Token")
                        return value

                # 尝试解密加密Cookie（Windows DPAPI）
                if encrypted_value and not value:
                    try:
                        decrypted = _decrypt_windows_cookie(encrypted_value)
                        if decrypted and (name in ('token', 'Token', 'TokenKey',
                                                    'Authorization', 'access_token',
                                                    'accessToken') or decrypted.startswith('eyJ')):
                            print(f"✅ CookieDB: 从 '{name}' (解密) 获取到Token")
                            return decrypted
                    except Exception:
                        pass

            # 如果没找到明确的Token名，打印所有Cookie名帮助调试
            print(f"⚠ CookieDB: 在 {cookie_path} 中找到 {len(rows)} 个Cookie，但未识别Token")
            for name, _, value in rows:
                v = value if value else "(加密)"
                print(f"  Cookie: {name} = {v[:30]}...")

        except Exception as e:
            print(f"⚠ CookieDB: 读取 {cookie_path} 失败: {e}")

    return None


def _decrypt_windows_cookie(encrypted_value):
    """解密Windows Chrome/Edge Cookie（DPAPI）"""
    try:
        import win32crypt

        # Chrome v80+ 使用AES-GCM加密
        if encrypted_value[:3] == b'v10' or encrypted_value[:3] == b'v20':
            # 需要获取Chrome的加密密钥，这比较复杂
            # 这里先尝试DPAPI解密旧格式
            pass

        # 尝试DPAPI解密
        decrypted = win32crypt.CryptUnprotectData(encrypted_value, None, None, None, 0)
        return decrypted[1].decode('utf-8', errors='replace')
    except Exception:
        return None


def get_token_manual():
    """方案3：手动输入Token"""
    print("\n📋 请从浏览器中获取Token：")
    print("  1. 打开 https://bigmodel.cn 并登录")
    print("  2. 按F12打开开发者工具 → Application → Cookies")
    print("  3. 找到 .bigmodel.cn 域名下的Token Cookie")
    print("  4. 复制其值")
    token = input("请粘贴Token: ").strip()
    return token if token else None


# ==================== 验证码获取 ====================
def get_captcha_via_cdp(cdp_port=DEFAULT_CDP_PORT):
    """
    方案1（优先）：通过CDP在浏览器中自动触发腾讯验证码，获取ticket+randstr
    """
    try:
        import websocket
    except ImportError:
        print("⚠ 需要安装 websocket-client: pip install websocket-client")
        return None, None

    cdp_url = f"http://127.0.0.1:{cdp_port}"

    try:
        resp = requests.get(f"{cdp_url}/json", timeout=5)
        tabs = resp.json()

        target_ws_url = None
        for tab in tabs:
            if 'bigmodel.cn' in tab.get('url', ''):
                target_ws_url = tab.get('webSocketDebuggerUrl')
                break

        if not target_ws_url:
            for tab in tabs:
                if tab.get('type') == 'page':
                    target_ws_url = tab.get('webSocketDebuggerUrl')
                    break

        if not target_ws_url:
            print("⚠ CDP: 未找到可用的标签页")
            return None, None

        ws = websocket.create_connection(target_ws_url, timeout=30)

        # 注入腾讯验证码脚本并触发
        js_code = f"""
        (() => {{
            return new Promise((resolve, reject) => {{
                // 检查是否已有TencentCaptcha
                if (typeof TencentCaptcha === 'undefined') {{
                    // 动态加载验证码脚本
                    const script = document.createElement('script');
                    script.src = 'https://turing.captcha.qcloud.com/TJCaptcha.js';
                    script.onload = () => {{
                        triggerCaptcha(resolve);
                    }};
                    script.onerror = () => reject('验证码脚本加载失败');
                    document.head.appendChild(script);
                }} else {{
                    triggerCaptcha(resolve);
                }}

                function triggerCaptcha(resolve) {{
                    try {{
                        const captcha = new TencentCaptcha('{CAPTCHA_APP_ID}', (res) => {{
                            if (res.ret === 0) {{
                                resolve(JSON.stringify({{
                                    ticket: res.ticket,
                                    randstr: res.randstr
                                }}));
                            }} else {{
                                resolve(JSON.stringify({{
                                    error: '验证码未通过',
                                    ret: res.ret
                                }}));
                            }}
                        }}, {{ bizState: 'zhipu_buy' }});
                        captcha.show();
                    }} catch(e) {{
                        reject('验证码初始化失败: ' + e.message);
                    }}
                }}
            }});
        })()
        """

        msg_id = 1
        msg = {
            "id": msg_id,
            "method": "Runtime.evaluate",
            "params": {
                "expression": js_code,
                "returnByValue": True,
                "awaitPromise": True
            }
        }
        ws.send(json.dumps(msg))

        print("🔐 验证码已触发，请在浏览器中完成验证...")

        # 等待验证码完成（最长60秒）
        ws.settimeout(60)
        result = json.loads(ws.recv())
        ws.close()

        value = result.get('result', {}).get('result', {}).get('value', '')
        if value:
            data = json.loads(value)
            if 'error' in data:
                print(f"⚠ 验证码失败: {data['error']}")
                return None, None
            ticket = data.get('ticket', '')
            randstr = data.get('randstr', '')
            if ticket:
                print(f"✅ 验证码获取成功！ticket={ticket[:20]}... randstr={randstr}")
                return ticket, randstr

        print("⚠ 验证码未返回有效数据")
        return None, None

    except Exception as e:
        print(f"⚠ CDP验证码获取失败: {e}")
        return None, None


def get_captcha_via_playwright():
    """
    方案2：通过Playwright自动化触发验证码
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print("⚠ 需要安装 playwright: pip install playwright && playwright install chromium")
        return None, None

    print("🎭 启动Playwright获取验证码...")
    ticket, randstr = None, None

    with sync_playwright() as p:
        # 连接到已运行的浏览器或启动新的
        try:
            browser = p.chromium.connect_over_cdp(f"http://127.0.0.1:{DEFAULT_CDP_PORT}")
            context = browser.contexts[0] if browser.contexts else browser.new_context()
        except Exception:
            browser = p.chromium.launch(headless=False)
            context = browser.new_context()

        page = context.pages[0] if context.pages else context.new_page()

        # 导航到智谱页面
        if 'bigmodel.cn' not in page.url:
            page.goto("https://bigmodel.cn/glm-coding", wait_until="networkidle")

        # 注入验证码
        result = page.evaluate(f"""() => {{
            return new Promise((resolve, reject) => {{
                const checkAndTrigger = () => {{
                    if (typeof TencentCaptcha === 'undefined') {{
                        const script = document.createElement('script');
                        script.src = 'https://turing.captcha.qcloud.com/TJCaptcha.js';
                        script.onload = triggerCaptcha;
                        document.head.appendChild(script);
                    }} else {{
                        triggerCaptcha();
                    }}
                }};

                function triggerCaptcha() {{
                    try {{
                        const captcha = new TencentCaptcha('{CAPTCHA_APP_ID}', (res) => {{
                            if (res.ret === 0) {{
                                resolve(JSON.stringify({{ ticket: res.ticket, randstr: res.randstr }}));
                            }} else {{
                                resolve(JSON.stringify({{ error: 'ret=' + res.ret }}));
                            }}
                        }}, {{ bizState: 'zhipu_buy' }});
                        captcha.show();
                    }} catch(e) {{
                        reject(e.message);
                    }}
                }}

                checkAndTrigger();
            }});
        }}""")

        if result:
            data = json.loads(result)
            if 'ticket' in data:
                ticket = data['ticket']
                randstr = data.get('randstr', '')
                print(f"✅ Playwright验证码获取成功！ticket={ticket[:20]}...")

        browser.close()

    return ticket, randstr


def get_captcha_manual():
    """方案3：手动输入验证码ticket和randstr"""
    print("\n📋 请手动完成验证码：")
    print("  1. 在浏览器中打开 https://bigmodel.cn/glm-coding")
    print("  2. 点击特惠订阅按钮触发验证码")
    print("  3. 完成验证码后，在F12控制台执行以下代码获取ticket+randstr：")
    print(f"     new TencentCaptcha('{CAPTCHA_APP_ID}', r=>console.log(JSON.stringify(r))).show()")
    print("  4. 复制ticket和randstr")
    ticket = input("请粘贴ticket: ").strip()
    randstr = input("请粘贴randstr: ").strip()
    return ticket if ticket else None, randstr if randstr else None


# ==================== NTP校准 ====================
def ntp_offset(server=DEFAULT_NTP_SERVER):
    """获取NTP时间偏移（本地时间 - 标准时间）"""
    try:
        client = ntplib.NTPClient()
        resp = client.request(server, version=3)
        offset = time.time() - resp.tx_time
        print(f"⏱ NTP校准: 本地比标准时间快 {offset:.4f} 秒")
        return offset
    except Exception as e:
        print(f"⚠ NTP同步失败({e})，使用本地时间")
        return 0.0


# ==================== API调用 ====================
class ZhipuBuyer:
    """智谱套餐API直调抢购"""

    def __init__(self, token, product_id=DEFAULT_PRODUCT_ID,
                 pay_type=DEFAULT_PAY_TYPE, invitation_code="",
                 retry_interval_ms=DEFAULT_RETRY_INTERVAL_MS,
                 max_retries=DEFAULT_MAX_RETRIES):
        self.token = token
        self.product_id = product_id
        self.pay_type = pay_type
        self.invitation_code = invitation_code
        self.retry_interval_ms = retry_interval_ms
        self.max_retries = max_retries

        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": token,
            "Content-Type": "application/json",
            "Accept": "application/json, text/plain, */*",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0",
            "Origin": "https://bigmodel.cn",
            "Referer": "https://bigmodel.cn/glm-coding",
            "Set-Language": "zh",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        })

    def _url(self, path):
        return f"{API_BASE}{path}"

    def check_limit_buy(self):
        """检查是否限购"""
        try:
            resp = self.session.get(
                self._url(PATH_IS_LIMIT_BUY),
                params={"productId": self.product_id},
                timeout=10
            )
            data = resp.json()
            print(f"📊 限购检查: {json.dumps(data, ensure_ascii=False)}")
            return data
        except Exception as e:
            print(f"⚠ 限购检查失败: {e}")
            return None

    def get_subscription_list(self):
        """获取当前订阅列表"""
        try:
            resp = self.session.get(
                self._url(PATH_SUBSCRIPTION_LIST),
                timeout=10
            )
            data = resp.json()
            print(f"📊 当前订阅: {json.dumps(data, ensure_ascii=False)[:200]}")
            return data
        except Exception as e:
            print(f"⚠ 获取订阅失败: {e}")
            return None

    def pay_preview(self, ticket, randstr):
        """
        核心API：支付预览
        返回: (status, data)
          status: "success" | "soldout" | "busy" | "error"
        """
        payload = {
            "productId": self.product_id,
            "invitationCode": self.invitation_code,
            "ticket": ticket,
            "randstr": randstr,
        }

        try:
            resp = self.session.post(
                self._url(PATH_PREVIEW),
                json=payload,
                timeout=10
            )
            data = resp.json()

            code = data.get('code')
            resp_data = data.get('data', {})

            if code == 200:
                if resp_data.get('soldOut'):
                    return "soldout", data
                else:
                    return "success", data
            else:
                return "busy", data

        except requests.exceptions.Timeout:
            return "error", {"msg": "请求超时"}
        except Exception as e:
            return "error", {"msg": str(e)}

    def create_sign(self, customer_id, biz_id):
        """创建支付签约，获取支付URL"""
        payload = {
            "payType": self.pay_type,
            "productId": self.product_id,
            "customerId": customer_id,
            "bizId": biz_id,
            "invitationCode": self.invitation_code,
        }

        try:
            resp = self.session.post(
                self._url(PATH_CREATE_SIGN),
                json=payload,
                timeout=10
            )
            data = resp.json()
            return data
        except Exception as e:
            print(f"⚠ 创建签约失败: {e}")
            return None

    def check_pay_status(self, biz_id):
        """轮询支付状态"""
        try:
            resp = self.session.get(
                self._url(PATH_PAY_CHECK),
                params={"bizId": biz_id},
                timeout=10
            )
            data = resp.json()
            status = data.get('data', '')
            return status  # "SUCCESS" | "EXPIRE" | 其他
        except Exception as e:
            return None

    def generate_pay_middle_url(self, pay_data):
        """
        生成支付中间页URL（AES加密）
        pay_data应包含: productId, productName, amount, customerId,
                        customerName, oldProductId, agreementNo,
                        isSubscribe, bizId, payType, userState
        """
        encrypted = aes_encrypt(pay_data)
        return f"{API_BASE}/pay-middle-page?info={encrypted}"

    def buy(self, ticket, randstr, target_time=None, ntp_offset_val=0.0):
        """
        主抢购流程

        Args:
            ticket: 腾讯验证码ticket
            randstr: 腾讯验证码randstr
            target_time: 目标时间 datetime，None则立即执行
            ntp_offset_val: NTP偏移量
        """
        # ---- 等待到开抢时刻 ----
        if target_time:
            adjusted_target = target_time + datetime.timedelta(seconds=ntp_offset_val)
            print(f"\n📅 目标时间: {target_time.strftime('%Y-%m-%d %H:%M:%S')}")
            print(f"📅 修正后:   {adjusted_target.strftime('%Y-%m-%d %H:%M:%S.%f')}")

            # 等到开抢前5秒
            pre_wake = adjusted_target - datetime.timedelta(seconds=5)
            while datetime.datetime.now() < pre_wake:
                time.sleep(0.5)

            print("⏳ 即将开抢，进入忙等...")

            # 提前0.1秒进入忙等
            pre_click = adjusted_target - datetime.timedelta(seconds=0.1)
            while datetime.datetime.now() < pre_click:
                time.sleep(0.001)

            # 高精度忙等到点
            while datetime.datetime.now() < adjusted_target:
                pass

            fire_time = datetime.datetime.now().strftime("%H:%M:%S.%f")
            print(f"🚀 开抢！@ {fire_time}")
        else:
            print("\n🚀 立即执行抢购...")

        # ---- 执行preview ----
        attempt = 0
        preview_data = None
        biz_id = None
        customer_id = None

        while attempt < self.max_retries:
            attempt += 1
            status, data = self.pay_preview(ticket, randstr)

            if status == "success":
                preview_data = data.get('data', data)
                biz_id = preview_data.get('bizId')
                # customer_id可能在preview响应中
                customer_id = preview_data.get('customerId')
                amount = preview_data.get('thirdPartyAmount', '?')
                print(f"✅ Preview成功！bizId={biz_id}, 金额=¥{amount}")
                break

            elif status == "soldout":
                print(f"❌ 售罄！(尝试 {attempt}/{self.max_retries})")
                # 售罄也重试，可能刚补货
                if attempt < self.max_retries:
                    time.sleep(self.retry_interval_ms / 1000.0)
                    continue
                else:
                    print("❌ 最终售罄，停止抢购")
                    return False

            elif status == "busy":
                msg = data.get('msg', data.get('message', ''))
                code = data.get('code', '')
                print(f"⚠ 服务器繁忙 code={code} msg={msg} (尝试 {attempt}/{self.max_retries})")
                time.sleep(self.retry_interval_ms / 1000.0)
                continue

            else:  # error
                msg = data.get('msg', str(data))
                print(f"⚠ 请求错误: {msg} (尝试 {attempt}/{self.max_retries})")
                time.sleep(self.retry_interval_ms / 1000.0)
                continue

        if not biz_id:
            print("❌ 未能获取bizId，抢购失败")
            return False

        # ---- 创建支付签约 ----
        print(f"\n💳 创建支付签约 (payType={self.pay_type})...")

        # 如果preview没返回customerId，尝试从订阅列表获取
        if not customer_id:
            sub_data = self.get_subscription_list()
            if sub_data and sub_data.get('data'):
                # 从订阅数据中提取customerId
                sub_list = sub_data.get('data', [])
                if isinstance(sub_list, list) and sub_list:
                    customer_id = sub_list[0].get('customerId')
                elif isinstance(sub_list, dict):
                    customer_id = sub_list.get('customerId')

        if not customer_id:
            print("⚠ 未获取到customerId，尝试不传customerId创建签约...")
            customer_id = ""

        sign_result = self.create_sign(customer_id, biz_id)
        if not sign_result:
            print("❌ 创建签约失败")
            return False

        sign_code = sign_result.get('code')
        if sign_code != 200:
            print(f"❌ 签约失败: {json.dumps(sign_result, ensure_ascii=False)}")
            return False

        sign_data = sign_result.get('data', {})
        sign_url = sign_data.get('sign')
        order_id = sign_data.get('orderId')

        if sign_url:
            print(f"✅ 支付链接获取成功！")
            print(f"📋 订单ID: {order_id}")
            print(f"🔗 支付URL: {sign_url}")

            # 尝试生成支付中间页URL（备用）
            try:
                pay_middle_data = {
                    "productId": self.product_id,
                    "productName": "智谱Pro套餐",
                    "amount": preview_data.get('thirdPartyAmount', 0),
                    "customerId": customer_id,
                    "customerName": "",
                    "oldProductId": "",
                    "agreementNo": "",
                    "isSubscribe": False,
                    "bizId": biz_id,
                    "payType": "alipay" if self.pay_type == "ALI" else "wxpay",
                    "userState": None,
                }
                middle_url = self.generate_pay_middle_url(pay_middle_data)
                print(f"🔗 支付中间页(备用): {middle_url}")
            except Exception as e:
                print(f"⚠ 生成支付中间页失败: {e}")

            # 自动打开支付链接
            try:
                subprocess.Popen(['cmd', '/c', 'start', sign_url])
                print("🌐 已自动打开支付链接")
            except Exception:
                print("⚠ 无法自动打开，请手动复制链接到浏览器")

        # ---- 轮询支付状态 ----
        print(f"\n⏳ 轮询支付状态 (bizId={biz_id})...")
        poll_count = 0
        max_polls = 300  # 5分钟（每秒1次）

        while poll_count < max_polls:
            poll_count += 1
            status = self.check_pay_status(biz_id)

            if status == "SUCCESS":
                print(f"\n🎉🎉🎉 支付成功！订单完成！")
                return True
            elif status == "EXPIRE":
                print(f"\n⏰ 支付已过期，请重新抢购")
                return False
            else:
                if poll_count % 10 == 0:
                    print(f"  等待支付... ({poll_count}s) 状态={status}")
                time.sleep(1)

        print("⏰ 轮询超时，请手动检查支付状态")
        return False


# ==================== 主程序 ====================
def main():
    parser = argparse.ArgumentParser(
        description="智谱Pro套餐 API直调抢购脚本",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__
    )
    parser.add_argument("--product-id", default=DEFAULT_PRODUCT_ID,
                       help=f"产品ID (默认: {DEFAULT_PRODUCT_ID})")
    parser.add_argument("--time", default=DEFAULT_TARGET_TIME,
                       help=f"抢购时间 HH:MM:SS (默认: {DEFAULT_TARGET_TIME})")
    parser.add_argument("--pay-type", default=DEFAULT_PAY_TYPE,
                       choices=["ALI", "WE_CHAT"],
                       help=f"支付方式 (默认: {DEFAULT_PAY_TYPE})")
    parser.add_argument("--token", default=None,
                       help="手动提供Token")
    parser.add_argument("--ticket", default=None,
                       help="手动提供验证码ticket")
    parser.add_argument("--randstr", default=None,
                       help="手动提供验证码randstr")
    parser.add_argument("--ntp-server", default=DEFAULT_NTP_SERVER,
                       help=f"NTP服务器 (默认: {DEFAULT_NTP_SERVER})")
    parser.add_argument("--no-ntp", action="store_true",
                       help="禁用NTP校准")
    parser.add_argument("--preview-only", action="store_true",
                       help="只执行preview，不执行支付（调试用）")
    parser.add_argument("--retry-interval", type=int, default=DEFAULT_RETRY_INTERVAL_MS,
                       help=f"重试间隔ms (默认: {DEFAULT_RETRY_INTERVAL_MS})")
    parser.add_argument("--max-retries", type=int, default=DEFAULT_MAX_RETRIES,
                       help=f"最大重试次数 (默认: {DEFAULT_MAX_RETRIES})")
    parser.add_argument("--cdp-port", type=int, default=DEFAULT_CDP_PORT,
                       help=f"CDP调试端口 (默认: {DEFAULT_CDP_PORT})")
    parser.add_argument("--invitation-code", default="",
                       help="邀请码 (可选)")
    parser.add_argument("--now", action="store_true",
                       help="立即执行，不等待定时")

    args = parser.parse_args()

    print("=" * 60)
    print("  智谱Pro套餐 API直调抢购脚本 v1")
    print("=" * 60)
    print(f"  产品ID: {args.product_id}")
    print(f"  支付方式: {'支付宝' if args.pay_type == 'ALI' else '微信'}")
    print(f"  抢购时间: {'立即' if args.now else args.time}")
    print(f"  NTP校准: {'禁用' if args.no_ntp else args.ntp_server}")
    print("=" * 60)

    # ---- Step 1: 获取Token ----
    print("\n📌 Step 1: 获取Token")
    token = args.token

    if not token:
        print("尝试从CDP获取Token...")
        token = get_token_from_cdp(args.cdp_port)

    if not token:
        print("尝试从Cookie数据库获取Token...")
        token = get_token_from_cookie_db()

    if not token:
        print("自动获取失败，请手动提供Token")
        token = get_token_manual()

    if not token:
        print("❌ 无法获取Token，退出")
        return

    print(f"✅ Token: {token[:20]}... (长度={len(token)})")

    # ---- Step 2: 获取验证码 ----
    print("\n📌 Step 2: 获取验证码 (ticket + randstr)")
    ticket = args.ticket
    randstr = args.randstr

    if not ticket:
        # 计算开抢时间
        target_dt = None
        if not args.now:
            try:
                parts = args.time.split(':')
                h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
                now = datetime.datetime.now()
                target_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
                if target_dt <= now:
                    target_dt += datetime.timedelta(days=1)
            except Exception:
                print(f"⚠ 时间格式错误: {args.time}，使用默认 {DEFAULT_TARGET_TIME}")
                target_dt = None

        # 在开抢前5分钟获取验证码
        if target_dt:
            captcha_time = target_dt - datetime.timedelta(minutes=5)
            now = datetime.datetime.now()
            if captcha_time > now:
                wait_sec = (captcha_time - now).total_seconds()
                print(f"⏳ 等待到开抢前5分钟获取验证码... (还需等待 {wait_sec:.0f} 秒)")
                while datetime.datetime.now() < captcha_time:
                    time.sleep(1)
            elif now > target_dt:
                print("⚠ 已过开抢时间，立即获取验证码")

        print("尝试通过CDP获取验证码...")
        ticket, randstr = get_captcha_via_cdp(args.cdp_port)

    if not ticket:
        print("尝试通过Playwright获取验证码...")
        ticket, randstr = get_captcha_via_playwright()

    if not ticket:
        print("自动获取失败，请手动提供验证码")
        ticket, randstr = get_captcha_manual()

    if not ticket:
        print("❌ 无法获取验证码ticket，退出")
        return

    print(f"✅ ticket: {ticket[:20]}... randstr: {randstr}")

    # ---- Step 3: NTP校准 ----
    print("\n📌 Step 3: NTP时间校准")
    offset = 0.0
    if not args.no_ntp:
        offset = ntp_offset(args.ntp_server)

    # ---- Step 4: 预检查 ----
    print("\n📌 Step 4: 预检查")
    buyer = ZhipuBuyer(
        token=token,
        product_id=args.product_id,
        pay_type=args.pay_type,
        invitation_code=args.invitation_code,
        retry_interval_ms=args.retry_interval,
        max_retries=args.max_retries,
    )

    # 检查限购
    buyer.check_limit_buy()

    # ---- Step 5: 执行抢购 ----
    print("\n📌 Step 5: 执行抢购")

    target_dt = None
    if not args.now:
        try:
            parts = args.time.split(':')
            h, m, s = int(parts[0]), int(parts[1]), int(parts[2])
            now = datetime.datetime.now()
            target_dt = now.replace(hour=h, minute=m, second=s, microsecond=0)
            if target_dt <= now:
                target_dt += datetime.timedelta(days=1)
        except Exception:
            target_dt = None

    if args.preview_only:
        print("🔍 调试模式：只执行preview")
        status, data = buyer.pay_preview(ticket, randstr)
        print(f"Preview结果: status={status}")
        print(f"Preview数据: {json.dumps(data, ensure_ascii=False, indent=2)}")
        return

    success = buyer.buy(
        ticket=ticket,
        randstr=randstr,
        target_time=target_dt,
        ntp_offset_val=offset,
    )

    if success:
        print("\n🎊🎊🎊 抢购成功！🎊🎊🎊")
    else:
        print("\n😢 抢购未成功，请检查日志")


if __name__ == "__main__":
    main()
