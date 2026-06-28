import sys
from pathlib import Path

# 將專案根目錄加入 sys.path，以便正常導入 app 模組
sys.path.append(str(Path(__file__).parent.parent))

# 導入 FastAPI 主應用程式實例
from app import app
