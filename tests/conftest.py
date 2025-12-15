import os
import sys
from pathlib import Path

os.environ.setdefault("APP_PASSWORD_PEPPER", "test-pepper")
os.environ.setdefault("APP_ADMIN_PASSWORD", "password123")
os.environ.setdefault("APP_USER1_PASSWORD", "secret456")
os.environ.setdefault("APP_ADMIN_RESET_PASSWORD", "password123")

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
