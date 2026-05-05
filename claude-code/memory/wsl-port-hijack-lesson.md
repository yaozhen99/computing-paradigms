---
name: wsl-port-hijack-lesson
description: WSL wslrelay 会劫持 Windows 同端口请求，导致服务收不到流量
type: feedback
---

WSL 的 wslrelay.exe 会自动将 WSL 内监听的端口转发到 Windows 同端口，导致 Windows 上的同名服务收不到请求。

**Why:** Hermes Bridge 在 Windows (PID 25144) 和 WSL (PID 36401) 都监听 8899，wslrelay 把 Windows 8899 流量转发到 WSL 旧进程，Windows bridge 完全收不到请求。表现为：API 返回 202 但文件不创建、日志不更新。

**How to apply:** 部署 Windows 服务时，先检查 WSL 内是否有进程监听同端口（`wsl -d Ubuntu -- bash -c "ss -tlnp | grep <port>"`），如有则先杀掉 WSL 内的进程。同理，netstat -ano 看到多个 PID 监听同一端口时，要排查是否有 wslrelay 在中间。
