# 智谱套餐购买流程 — 底层API逆向分析

> 分析日期：2026-04-30
> 分析人：Puck（副手，仅分析记录，不写代码）
> 页面：https://bigmodel.cn/glm-coding
> 前端框架：Vue 2 + Element UI + Webpack

---

## 一、购买流程总览

```
用户点击"特惠订阅"按钮
  → 检查登录状态（未登录→跳转登录页）
  → 检查老用户弹窗（isOldUser + oldUserTipDontShowAgain）
  → 打开PayComponent弹窗（payDialogVisible = true）
  → 触发腾讯验证码（TencentCaptcha, appId: 196026326）
  → 验证成功后调用 payPreviewFn()
  → 根据用户状态选择不同API：
    ├─ 新购/升级 → POST /biz/pay/preview
    └─ 老版续订 → POST /biz/product/createPreOrder
  → 返回支付预览数据（含bizId、金额、售罄状态）
  → 如果售罄 → 关闭弹窗提示"套餐已达今日售卖上限"
  → 如果未售罄 → 渲染支付二维码 + 轮询支付状态
  → 用户扫码支付
  → 轮询 GET /biz/pay/check?bizId=xxx 检测支付结果
  → 支付成功 → 弹出成功对话框
```

---

## 二、核心API清单

### 2.1 支付预览（关键！抢购的入口）

| API | 方法 | 用途 | 请求参数 |
|-----|------|------|----------|
| `/biz/pay/preview` | POST | 新购/升级预览 | `{productId, invitationCode, ticket, randstr}` |
| `/biz/product/createPreOrder` | POST | 老版续订预览 | `{productId, invitationCode, ticket, randstr}` |

**请求参数说明**：
- `productId`: 套餐产品ID（从cardData获取）
- `invitationCode`: 邀请码（URL参数 `?ic=xxx`）
- `ticket`: 腾讯验证码ticket
- `randstr`: 腾讯验证码随机字符串

**响应数据**：
- `code: 200` → 成功
- `data.soldOut: true` → 售罄
- `data.bizId` → 业务ID（后续轮询用）
- `data.thirdPartyAmount` → 支付金额
- `data.lastSubscriptionSummary` → 上次订阅信息

### 2.2 支付签约

| API | 方法 | 用途 | 请求参数 |
|-----|------|------|----------|
| `/biz/pay/create-sign` | POST | 新购签约 | `{payType, productId, customerId, bizId, invitationCode}` |
| `/biz/pay/product/update/sign` | POST | 续订签约 | `{payType, oldProductId, newProductId, customerId, agreementNo, bizId}` |

**payType映射**：
- `"ALI"` → 支付宝
- `"WE_CHAT"` → 微信

**响应数据**：
- `data.sign` → 支付签约URL（跳转即支付）
- `data.orderId` → 订单ID

### 2.3 支付状态轮询

| API | 方法 | 用途 |
|-----|------|------|
| `/biz/pay/check?bizId={bizId}` | GET | 检查支付状态 |

**响应**：
- `"SUCCESS"` → 支付成功
- `"EXPIRE"` → 支付过期
- 其他 → 未支付（继续轮询）

### 2.4 限购与产品信息

| API | 方法 | 用途 |
|-----|------|------|
| `/biz/product/isLimitBuy` | GET | 检查是否限购 |
| `/biz/product/info` | GET | 获取产品信息 |
| `/biz/product/query-order/{payOrderNo}` | GET | 查询订单状态 |
| `/biz/pay/status?key={key}` | GET | 查询支付状态 |
| `/biz/subscription/list` | GET | 获取订阅列表 |

### 2.5 其他辅助API

| API | 方法 | 用途 |
|-----|------|------|
| `/biz/riskClassify/displayType` | GET | 风控分类展示类型 |
| `/biz/pay/batch-preview` | POST | 批量支付预览 |
| `/biz/pay/unsubscribe` | POST | 取消订阅 |
| `/biz/pay/comeback/check` | GET | 回归用户检查 |
| `/biz/pay/comeback/preview` | POST | 回归用户预览 |
| `/biz/partner/bind` | POST | 绑定邀请关系 |
| `/biz/campaign/lottery/{code}/draw` | GET | 活动抽奖 |
| `/biz/campaign/lottery/{code}/status` | GET | 活动抽奖状态 |
| `/biz/trial-cards/claim` | - | 领取体验卡 |
| `/biz/fission/invite-code/` | - | 邀请码 |

---

## 三、风控机制分析

### 3.1 腾讯验证码（TencentCaptcha）

- **AppId**: `196026326`
- **类型**: bind模式（手动触发），popup样式
- **脚本URL**: `https://turing.captcha.qcloud.com/TJCaptcha.js`
- **触发时机**: PayComponent弹窗打开时自动触发
- **验证结果**: 返回 `{ticket, randstr}`
- **验证结果传递**: ticket和randstr作为参数传给payPreviewFn → 发送到后端

**绕过可能性分析**：
- 验证码是服务端校验的，ticket必须由腾讯服务器签发
- 不能伪造ticket，因为后端会向腾讯验证
- **唯一绕过方式**：在浏览器内自动完成验证码（需要图像识别或手动过一次）

### 3.2 腾讯设备指纹（TDID）

- **脚本URL**: `https://cdn.bigmodel.cn/static/platform/js/TENCENT-TDID.js`
- **用途**: 设备指纹采集，反作弊
- **风险**: 多次请求同一设备可能被标记

### 3.3 限购机制

- `isLimitBuy` API返回是否限购
- 前端按钮状态逻辑：
  - `cardData.isLimitBuy = true` → 按钮显示"抢购人数过多，请刷新再试"
  - `cardData.soldOut = true` → 按钮显示"暂时售罄 ｜ {refreshTime} 10:00 补货"
  - `cardData.forbidden = true` → 按钮显示"特惠订阅"但不可点击

### 3.4 售罄检测

- `payPreviewFn` 返回 `data.soldOut = true` 时关闭弹窗
- 前端不控制售罄，由后端API返回

---

## 四、绕过按钮的可能性分析

### 4.1 方案A：直接调API（绕过按钮点击）

**可行性**：⭐⭐⭐⭐（高）

直接调用 `/biz/pay/preview` API，跳过前端按钮点击。

**优势**：
- 不需要找按钮坐标
- 不受页面布局变化影响
- 速度更快（直接HTTP请求 vs 窗口消息→DOM事件→JS处理→HTTP请求）

**需要解决的问题**：
1. **认证**：需要登录态（Cookie/Token）
2. **验证码**：需要有效的ticket和randstr
3. **设备指纹**：TDID可能参与风控

**流程**：
```
1. 提前获取登录Cookie
2. 提前完成验证码获取ticket（或自动过验证码）
3. 在开抢时刻直接POST /biz/pay/preview
4. 获取bizId后调 /biz/pay/create-sign
5. 获取sign URL后人工扫码支付
```

### 4.2 方案B：CDP协议直接操作DOM

**可行性**：⭐⭐⭐（中）

通过CDP协议在浏览器内执行JS，直接触发购买流程。

**优势**：
- 复用浏览器登录态
- 验证码可在浏览器内完成
- 不需要单独处理认证

**劣势**：
- 仍需等待页面加载
- CDP操作有延迟
- 需要浏览器开启远程调试

### 4.3 方案C：hwnd窗口消息（当前方案）

**可行性**：⭐⭐（低，对于限量抢购）

**劣势**：
- 仍需等待前端JS处理链路（按钮→验证码→API请求）
- 验证码环节无法自动化
- 坐标依赖页面布局

### 4.4 方案D：预获取验证码 + API直调（最优）

**可行性**：⭐⭐⭐⭐⭐（最高）

**核心思路**：验证码和API请求解耦

1. **提前过验证码**：在开抢前完成腾讯验证码，获取ticket+randstr
2. **ticket有效期**：需要测试ticket的有效期（通常5-10分钟）
3. **开抢时直接POST**：用预获取的ticket直接调 `/biz/pay/preview`
4. **跳过所有前端逻辑**：不需要打开页面、不需要点按钮

**关键问题**：
- ticket有效期多长？如果只有几分钟，需要在开抢前几分钟获取
- 后端是否校验ticket的时间戳与请求时间的间隔？
- 是否需要TDID设备指纹？

---

## 五、按钮状态逻辑（前端）

```javascript
btnText() {
  if (subscribeLoding) return "订阅中..."
  if (cardData.isLimitBuy) return "抢购人数过多，请刷新再试"
  if (cardData.soldOut) return "暂时售罄 ｜ {refreshTime} 10:00 补货"
  if (!loginStatus || (loginStatus && !isSubscribe) || cardData.forbidden) return "特惠订阅"
  if (cardData.canRepurchase) return "开启自动续订"
  if (cardData.lastValid && !cardData.inCurrentPeriod) return "已订阅"
  if (cardData.lastValid && cardData.inCurrentPeriod) return "我的订阅"
  if (cardData.delay) return "特惠订阅"
  return "订阅升级"
}
```

---

## 六、PayComponent完整流程（源码级）

```
1. payDialogVisible = true（watch触发）
   → 埋点：WebExposure "支付弹窗"
   → openVerifyCaptcha()
   → 设置 isSubscribeLocal, isRenewLocal

2. openVerifyCaptcha()
   → captchaVerified = false
   → $refs.captchaComponent.openVerification()
   → 腾讯验证码弹出

3. handleCaptchaSuccess({ticket, randstr})
   → 保存 captchaTicket, captchaRandstr
   → captchaVerified = true
   → payPreviewFn()

4. payPreviewFn()
   → 构造参数: {productId, invitationCode, ticket, randstr}
   → 判断用户状态:
     ├─ 老版续订(ACTIVE_V1/MISTAKEN_UPGRADE/EXPIRED_V1)
     │   → productId = checkData.targetProductId
     │   → POST /biz/product/createPreOrder
     └─ 新购/升级
         → POST /biz/pay/preview
   → 处理响应:
     ├─ code=200 && soldOut=true → 关闭弹窗，提示售罄
     ├─ code=200 && !soldOut → 设置priceData，开始轮询支付状态
     └─ code≠200 → isServerBusy=true

5. getPayStatusFn()
   → setInterval 1秒
   → GET /biz/pay/check?bizId={bizId}
   → "SUCCESS" → 支付成功，弹成功对话框
   → "EXPIRE" → 停止轮询

6. renderQrCode()（PC端）
   → 构造支付参数JSON
   → AES加密（KEY: "zhiPuAi123456789", ECB, PKCS7）
   → 生成二维码URL: {origin}/pay-middle-page?info={encrypted}

7. getAppPaySignFn()（移动端）
   → POST /biz/pay/create-sign（新购）
   → POST /biz/pay/product/update/sign（续订）
   → 返回 sign URL → window.location.href = signUrl

8. confirmPayFn()
   → 移动端跳转支付URL
```

---

## 七、AES加密细节

- **密钥**: `zhiPuAi123456789`（16字节，AES-128）
- **模式**: ECB
- **填充**: PKCS7
- **加密内容**: 支付参数JSON字符串
- **用途**: 生成支付中间页URL参数

**加密的JSON结构**：
```json
{
  "productId": "xxx",
  "productName": "xxx",
  "amount": 402.3,
  "customerId": "xxx",
  "customerName": "xxx",
  "oldProductId": "",
  "agreementNo": "",
  "isSubscribe": false,
  "bizId": "xxx",
  "payType": "alipay",
  "userState": null
}
```

---

## 八、认证机制（已确认）

### 8.1 Token存储

- **存储方式**：Cookie（js-cookie库）
- **Cookie名**：`c["TokenKey"]`（常量模块 `22a6` 中定义）
- **域名**：`.bigmodel.cn`
- **属性**：`secure=true, sameSite=None`

### 8.2 请求头

API请求通过axios拦截器自动添加以下Header：

```
Authorization: {token值}
Bigmodel-Organization: {组织ID，从localStorage的OrgIdKey获取}
Bigmodel-Project: {项目ID，从localStorage的ProjectIdKey获取}
Set-Language: zh/en
Accept-Language: zh/en
```

### 8.3 Token获取函数

```javascript
// 模块5f87导出
getToken()       // u["e"]() → Cookie中读取TokenKey
setToken(val, exp) // u["p"]() → 设置Cookie
removeToken()    // u["i"]() → 删除Cookie
hasToken()       // u["g"]() → 检查Token是否存在
getUserInfo()    // u["f"]() → localStorage读取UserInfoKey
getOrgId()       // u["b"]() → localStorage读取OrgIdKey
getProjectId()   // u["c"]() → localStorage读取ProjectIdKey
```

### 8.4 withToken选项

- API请求默认 `withToken: true`（需要认证）
- 登录接口 `withToken: false`（不需要认证）
- 无Token时清除所有缓存

### 8.5 Token过期处理

- 响应拦截器检测特定code（`d["c"]`数组中的code）
- Token过期 → 提示"登录失效" → 500ms后跳转登录页

---

## 九、产品ID（已确认）

| 套餐 | productId | 类型 | 周期 | 售价 | 原价 |
|------|-----------|------|------|------|------|
| Lite | `product-b8ea38` | lite | quarter(包季) | ¥132.3 | ¥147 |
| Pro | `product-fef82f` | pro | quarter(包季) | ¥402.3 | ¥447 |
| Max | `product-5d3a03` | max | quarter(包季) | ¥1266.3 | ¥1407 |

> 注意：当前页面默认显示的是"连续包季"，包月/包年可能有不同productId

---

## 十、待验证事项

- [x] ~~登录Token的获取方式~~ → Cookie存储，Authorization Header
- [x] ~~productId的具体值~~ → 见第九节
- [ ] ticket有效期测试（开抢前多久获取合适？）
- [ ] TDID设备指纹是否为必须参数
- [ ] `/biz/pay/preview` 是否校验Referer
- [ ] 连续包月/包季/包年是否不同productId
- [ ] API请求频率限制
- [ ] 同一ticket能否多次使用
- [ ] 验证码是否每次购买都必须（还是只在特定条件下）

---

## 十一、风险提示

1. **封号风险**：代抢脚本可能违反平台用户协议
2. **风控触发**：高频API请求可能触发风控
3. **法律风险**：自动化抢购可能涉及法律问题
4. **技术风险**：前端代码更新可能导致API变化

---

## 十二、结论与建议

### 最优方案：预获取验证码 + API直调

**理由**：
1. 绕过按钮点击，速度最快
2. 不依赖页面布局和坐标
3. 可以在毫秒级完成请求
4. 验证码提前处理，不占用抢购时间窗口

**实施步骤**（需Claude Code开发）：
1. 在已登录浏览器中获取Cookie/Token
2. 开抢前5分钟完成腾讯验证码，保存ticket+randstr
3. NTP校准时间
4. 开抢时刻直接POST `/biz/pay/preview`
5. 获取bizId后调 `/biz/pay/create-sign`
6. 获取sign URL后人工扫码支付

**相比hwnd方案的优势**：
- hwnd方案：点击按钮 → 前端JS处理 → 验证码 → API请求（串行，3-5秒）
- API直调：直接发HTTP请求（并行，<100ms）

---

## 附录：Webpack模块映射

| 模块ID | 用途 |
|--------|------|
| `8f7b` | 支付API（payPreview, createSign, payCheck等） |
| `e832` | 产品API（createPreOrder, queryOrder, isLimitBuy等） |
| `e8bd` | PayComponent组件 |
| `5f87` | 认证工具（getToken, setToken, getUserInfo等） |
| `22a6` | 常量定义（TokenKey, UserInfoKey等） |
| `2c17` | 外部脚本URL（TENCENT_TDID_URL, TJ_CAPTCHA_URL） |
| `b775` | axios请求封装（所有API的基础） |
