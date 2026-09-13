"""Apply pending migrations to DATABASE_URL. Back up before upgrading."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from app.db import engine
from app.migrations import upgrade

if __name__ == "__main__":
    print("Database at revision " + upgrade(engine))
