@echo off
cd /d "C:\tower-of-babel\projects\vault-cli"
:loop
if exist "_system\system_state.json" (
  findstr /C:"MISSION_ACCOMPLISHED" "_system\system_state.json" >nul 2>&1
  if %errorlevel%==0 (
    echo Mission accomplished. Exiting.
    goto :end
  )
)
claude -p "Read and execute the instructions in _prompts_active/active_prompt_global_manager.md"
timeout /t 60 /nobreak >nul
goto loop
:end
