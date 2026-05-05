"""pytest 配置文件：共享 fixture 和路径配置。"""

import sys
from pathlib import Path

# 确保可导入 vault_cli（即使未 pip install -e 也可用）
BACKEND_SRC = Path(__file__).resolve().parent.parent.parent / "03_source" / "backend" / "src"
if str(BACKEND_SRC) not in sys.path:
    sys.path.insert(0, str(BACKEND_SRC))
