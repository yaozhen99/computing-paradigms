"""
Hermes Bridge MCP Server
让 Claude Code 原生集成 Hermes Bridge，实现双向通信。
"""
import json
import httpx
from mcp.server.fastmcp import FastMCP

BRIDGE_URL = "http://localhost:8898"

mcp = FastMCP("hermes-bridge")


@mcp.tool()
def hermes_submit_task(query: str, task_id: str = "", source: str = "claude-code") -> str:
    """向 Hermes 提交任务。query 是任务内容，task_id 可选，source 标识来源。"""
    payload = {"query": query, "from": source}
    if task_id:
        payload["task_id"] = task_id
    r = httpx.post(f"{BRIDGE_URL}/task", json=payload, timeout=10)
    return r.text


@mcp.tool()
def hermes_get_result(task_id: str) -> str:
    """查询 Hermes 任务结果。task_id 是提交任务时返回的 ID。"""
    r = httpx.get(f"{BRIDGE_URL}/result/{task_id}", timeout=10)
    return r.text


@mcp.tool()
def hermes_list_results() -> str:
    """列出 Hermes 所有任务结果。"""
    r = httpx.get(f"{BRIDGE_URL}/result", timeout=10)
    return r.text


@mcp.tool()
def hermes_check_inbox() -> str:
    """检查 Hermes 发来的消息（收件箱）。"""
    r = httpx.get(f"{BRIDGE_URL}/inbox", timeout=10)
    return r.text


@mcp.tool()
def hermes_read_message(msg_id: str) -> str:
    """读取收件箱中的单条消息。msg_id 是消息 ID。"""
    r = httpx.get(f"{BRIDGE_URL}/inbox/{msg_id}", timeout=10)
    return r.text


@mcp.tool()
def hermes_delete_message(msg_id: str) -> str:
    """删除收件箱中的消息。msg_id 是消息 ID。"""
    r = httpx.delete(f"{BRIDGE_URL}/inbox/{msg_id}", timeout=10)
    return r.text


@mcp.tool()
def hermes_bridge_status() -> str:
    """查询 Hermes Bridge 服务状态。"""
    r = httpx.get(f"{BRIDGE_URL}/status", timeout=10)
    return r.text


if __name__ == "__main__":
    mcp.run()
