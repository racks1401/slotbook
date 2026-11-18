import os
from pathlib import Path

# Load environment variables from .env file if present
for env_path in [Path(".env"), Path("../.env"), Path(__file__).resolve().parent.parent / ".env"]:
    if env_path.is_file():
        with open(env_path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    os.environ.setdefault(key.strip(), val.strip().strip('"').strip("'"))
        break

# Settings with local defaults as defined in spec
SECRET_KEY = os.getenv("SECRET_KEY", "slotbook-secret-key-change-in-production")
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./slotbook.db")
TOKEN_MINUTES = int(os.getenv("TOKEN_MINUTES", "60"))
cors_origins_raw = os.getenv("CORS_ORIGINS", "http://localhost:5173,http://127.0.0.1:5173")
CORS_ORIGINS = [origin.strip() for origin in cors_origins_raw.split(",") if origin.strip()]
