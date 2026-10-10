import os, sqlite3, sys
ROOT = os.path.dirname(os.path.dirname(__file__))
DB_PATH = os.path.join(ROOT, "..", "..", "data", "dev.db")
MIGRATION = os.path.join(ROOT, "..", "..", "migrations", "0001_sqlite_init.sql")

os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
conn = sqlite3.connect(DB_PATH)
with open(MIGRATION, "r", encoding="utf-8") as f:
    sql = f.read()
conn.executescript(sql)
conn.commit()
conn.close()
print("migrations applied to", DB_PATH)
