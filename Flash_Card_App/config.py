from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent

DATA_DIR = BASE_DIR / "data" / "storage"
DECKS_DIR = DATA_DIR / "decks"
DB_FILE = DATA_DIR / "test.db"

DATA_DIR.mkdir(parents=True, exist_ok=True)
DECKS_DIR.mkdir(parents=True, exist_ok=True)