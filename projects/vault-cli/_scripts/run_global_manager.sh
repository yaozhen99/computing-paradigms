#!/bin/bash
# 全局 AI 启动脚本 — 循环拉起模式
# 每次拉起 AI 执行一轮感知，AI 自行退出后等待60秒再拉起
while true; do
  # 检测是否已完成
  if [ -f "_system/system_state.json" ]; then
    STATE=$(grep -o "MISSION_ACCOMPLISHED" "_system/system_state.json" 2>/dev/null)
    if [ -n "$STATE" ]; then
      echo "Mission accomplished. Exiting."
      break
    fi
  fi
  claude -p "Read and execute the instructions in _prompts_active/active_prompt_global_manager.md"
  sleep 60
done
