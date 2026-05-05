import subprocess, re

cmd = 'wsl -d Alpine-WSL1 -e sh -c "source ~/hermes-venv/bin/activate && hermes chat -q ping -Q"'
proc = subprocess.run(cmd, shell=True, capture_output=True, text=True, timeout=60)
print('STDOUT:', repr(proc.stdout[:300]) if proc.stdout else 'EMPTY')
print('STDERR:', repr(proc.stderr[:300]) if proc.stderr else 'EMPTY')
print('RC:', proc.returncode)

# Try cleaning
raw = (proc.stdout or "") + (proc.stderr or "")
clean = re.sub(r'\x1b\[[0-9;]*m', '', raw)
lines = [l.strip() for l in clean.split('\n') if l.strip() and not l.strip().startswith('session_id:')]
output = '\n'.join(lines).strip()
print('CLEANED:', output)
