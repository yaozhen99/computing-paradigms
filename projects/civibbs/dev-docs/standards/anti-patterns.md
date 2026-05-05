# CiviBBS 插件开发反模式清单

> 来源：Claude Opus 代码评审 + Hermes 测试反馈
> 用途：嵌入开发岗 prompt + 测试岗 checklist
> 原则：绝对不能这么做 + 为什么

## 反模式 1：TOCTOU 竞态（Time-of-Check-to-Time-of-Use）

**❌ 错误做法：** 先 `exists()` 检查再操作
```python
if path.exists():
    path.unlink()  # 检查和操作之间有竞态窗口
```

**✅ 正确做法：** 直接操作，按异常类型分流
```python
try:
    path.unlink()
except FileNotFoundError:
    # 处理不存在
```

**为什么：** `exists()` 和后续操作之间，文件系统状态可能被其他进程改变。原子操作消除竞态窗口。

---

## 反模式 2：参数类型未校验

**❌ 错误做法：** 直接使用 bool 参数
```python
missing_ok = inputs.get("missing_ok", False)
# 传入 "false" 字符串会被当作 True
```

**✅ 正确做法：** 显式类型校验
```python
missing_ok = inputs.get("missing_ok", False)
if not isinstance(missing_ok, bool):
    return _fail(E_PARAM_TYPE, "missing_ok 必须为 bool 类型")
```

**为什么：** Python 中非空字符串是 truthy，`"false"` 会被当作 `True`。所有 bool 参数必须校验。

---

## 反模式 3：目录/文件混淆

**❌ 错误做法：** 假设路径一定指向预期类型
```python
path.unlink()  # 如果 path 是目录，Linux 抛 IsADirectoryError，Windows 抛 PermissionError
```

**✅ 正确做法：** 捕获目录相关异常，返回专门错误码
```python
except IsADirectoryError:
    return _fail(E_IS_DIRECTORY, "目标路径是目录")
except PermissionError as exc:
    if _is_directory_error(exc):  # Windows 特殊处理
        return _fail(E_IS_DIRECTORY, "目标路径是目录")
```

**为什么：** 用户误传目录路径是常见场景，必须区分"权限不足"和"这是目录"。Windows 上对目录 `unlink()` 抛的是 `PermissionError` 而非 `IsADirectoryError`。

---

## 反模式 4：符号链接语义不清

**❌ 错误做法：** 用 `exists()` 判断符号链接是否存在
```python
if not path.exists():  # 断开的符号链接 exists() 返回 False
    return E_NOT_FOUND  # 但 unlink() 可以删除它
```

**✅ 正确做法：** 原子操作天然处理符号链接
```python
try:
    path.unlink()  # 直接删除符号链接本身，不管目标是否存在
except FileNotFoundError:
    # 链接本身不存在
```

**为什么：** `exists()` 跟随链接，断开的链接返回 `False`。`unlink()` 删除链接本身。两者语义不同。

---

## 反模式 5：日志 f-string 提前求值

**❌ 错误做法：** f-string 格式化
```python
logger.debug(f"文件删除成功 {path}")  # 即使 DEBUG 未开启也会求值
```

**✅ 正确做法：** 惰性格式化
```python
logger.debug("文件删除成功 %s", path)  # 只在日志级别开启时才格式化
```

**为什么：** f-string 无论日志级别是否开启都会求值，高频调用时有性能浪费。惰性格式化只在需要时才格式化。

---

## 反模式 6：路径未校验空字节

**❌ 错误做法：** 只校验长度
```python
if len(path) > 1024:
    return E_PATH_INVALID
```

**✅ 正确做法：** 增加空字节检测
```python
if "\x00" in path:
    return _fail(E_PATH_INVALID, "路径包含非法空字节 (NUL)")
```

**为什么：** 空字节 `\x00` 在 C 语言中是字符串终止符，可能导致路径截断攻击。某些 OS 下会抛难以理解的 `ValueError`。

---

## 反模式 7：definition.yaml 的 logic.steps 过度规定实现

**❌ 错误做法：** 写伪代码步骤
```yaml
logic:
  steps:
    - 检查文件是否存在
    - 如不存在返回 E_NOT_FOUND
    - 删除文件
```

**✅ 正确做法：** 定义行为契约（输入→输出映射）
```yaml
logic:
  behavior:
    - 若文件存在且删除成功 → deleted=True, file_existed=True
    - 若文件不存在且 missing_ok=false → E_NOT_FOUND
    - 若路径指向目录 → E_IS_DIRECTORY
  implementation_note: 采用原子操作模式，避免TOCTOU竞态
```

**为什么：** 规范应定义"做什么"而非"怎么做"。过度规定实现会绑死开发者，导致"符合规范但有缺陷"的代码。

---

## 反模式 8：重复的错误构造代码

**❌ 错误做法：** 每个错误分支重复构造
```python
return DeleteFileResult(
    deleted=False, file_existed=False,
    error_code=ErrorCode.E_NOT_FOUND,
    error_message=error_msg,
).to_dict()
```

**✅ 正确做法：** 抽取 `_fail()` 工具函数
```python
def _fail(error_code, error_message, *, file_existed=False):
    logger.error(error_message)
    return DeleteFileResult(
        deleted=False, file_existed=file_existed,
        error_code=error_code, error_message=error_message,
    ).to_dict()
```

**为什么：** 减少重复代码，错误构造和日志绑定，改一处全局生效。

---

## 反模式 9：路径穿越未校验（安全漏洞）

**❌ 错误做法：** 直接使用用户输入的路径
```python
path = Path(user_input)  # 可能包含 ../../etc/passwd
path.mkdir()
```

**✅ 正确做法：** 校验路径穿越序列
```python
def _contains_traversal(path: str) -> bool:
    parts = Path(path).parts
    return ".." in parts

if _contains_traversal(base_path):
    return _fail(E_PATH_TRAVERSAL, "路径包含非法穿越序列")
```

**为什么：** 路径穿越攻击可让用户访问预期目录之外的文件系统位置，是 OWASP Top 10 之一。

---

## 反模式 10：路径长度未限制

**❌ 错误做法：** 不限制路径长度
```python
path = Path(user_input)  # 可能是超长路径
```

**✅ 正确做法：** 限制路径长度
```python
_MAX_PATH_LENGTH = 260  # Windows MAX_PATH

if len(path) > _MAX_PATH_LENGTH:
    return _fail(E_PATH_INVALID, "路径长度超过限制")
```

**为什么：** Windows MAX_PATH 为 260 字符，超长路径可能导致异常或缓冲区问题。

---

## 反模式 11：Windows 保留名未处理

**❌ 错误做法：** 不检测 Windows 保留名
```python
path = Path("CON")  # Windows 保留名，有特殊语义
```

**✅ 正确做法：** 检测 Windows 保留名
```python
_WINDOWS_RESERVED_NAMES = frozenset([
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{i}" for i in range(1, 10)),
    *(f"LPT{i}" for i in range(1, 10)),
])

def _is_windows_reserved_name(path: str) -> bool:
    name = Path(path).name.upper()
    base_name = name.split(".")[0] if "." in name else name
    return base_name in _WINDOWS_RESERVED_NAMES
```

**为什么：** Windows 保留名（CON, NUL, AUX 等）在 Windows 下有特殊语义，可能导致意外行为。

---

## 反模式 12：异常捕获过于宽泛

**❌ 错误做法：** 捕获所有异常
```python
try:
    path.mkdir()
except Exception as e:  # 吞掉所有异常，包括 KeyboardInterrupt
    return _fail(E_IO_ERROR, str(e))
```

**✅ 正确做法：** 只捕获预期异常
```python
try:
    path.mkdir()
except OSError as e:  # PermissionError 是 OSError 子类
    return _fail(E_IO_ERROR, str(e))
# 其他异常正常抛出，让上层处理
```

**为什么：** `except Exception` 会吞掉 `MemoryError`、`RecursionError` 等严重异常，掩盖真正的 bug。

---

## 反模式 13：返回结构不一致

**❌ 错误做法：** 成功和失败返回不同字段
```python
# 成功
return {"created": True}
# 失败
return {"created": False, "error_code": "E_XXX", "error_message": "..."}
```

**✅ 正确做法：** 统一返回结构
```python
def _success() -> dict:
    return {"created": True, "error_code": None, "error_message": None}

def _fail(code: str, msg: str) -> dict:
    return {"created": False, "error_code": code, "error_message": msg}
```

**为什么：** 结构一致便于调用方统一处理，避免 KeyError。

---

## 反模式 14：日志泄露敏感信息

**❌ 错误做法：** 日志包含完整路径
```python
logger.debug("创建目录成功: %s", full_path)  # 可能包含用户名、敏感路径
```

**✅ 正确做法：** 日志不包含敏感信息
```python
logger.debug("创建目录成功")  # 或只记录路径哈希/简名
```

**为什么：** 日志可能被收集到中央系统，完整路径可能泄露用户名、目录结构等敏感信息。

---

## 反模式 15：单次评审即定稿（流程缺陷）

**❌ 错误做法：** 代码写完只做一次评审就定稿
```python
# 开发 → 一次审核 → done
# 结果：幽灵错误码、测试假阳性、跨平台问题全部漏网
```

**✅ 正确做法：** 至少两轮迭代评审（自审 + 交叉审核）
```
开发+自审 → 交叉审核 → 收敛审核 → done
```

**为什么：** 建造者和评审者是两种认知模式，单次评审无法覆盖所有盲区。质量不取决于单个模型的能力上限，而取决于迭代+交叉审核的机制。详见 `iterative-review-methodology.md`。

---

## 更新机制

每次测试/评审发现新缺陷模式：
1. Hermes 反馈 → Atlas 追加到本清单
2. 更新开发岗 prompt 中的引用
3. 更新测试 checklist

---
*版本：1.1 | 创建：2026-04-22 | 更新：2026-04-24 | 维护：Atlas + Hermes*
