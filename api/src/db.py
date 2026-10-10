# api/src/db.py
import os
from databases import Database

# Use SQLite file in repo for local dev
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./data/dev.db")
# For sqlite, databases library needs a query string with three slashes
db = Database(DATABASE_URL, force_rollback=False)
