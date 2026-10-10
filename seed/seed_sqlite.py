#!/usr/bin/env python3
import sqlite3, uuid, random, argparse, os
ROOT = os.path.dirname(os.path.dirname(__file__))
DB = os.path.join(ROOT, "data", "dev.db")
os.makedirs(os.path.dirname(DB), exist_ok=True)

parser = argparse.ArgumentParser()
parser.add_argument("--small", action="store_true", help="small seed for CI")
args = parser.parse_args()

users = 100 if args.small else 1000
wallets_per_user = 2
transfers = 10000 if args.small else 100000

conn = sqlite3.connect(DB)
cur = conn.cursor()

# create users
for i in range(users):
    uid = f"user-{i+1}"
    cur.execute("INSERT OR IGNORE INTO users (id,name,email,created_at) VALUES (?,?,?,datetime('now'))",
                (uid, f"User {i+1}", f"user{i+1}@example.com"))
# create wallets
wallets = []
for i in range(users):
    uid = f"user-{i+1}"
    for j in range(wallets_per_user):
        wid = f"wallet-{i+1}-{j+1}"
        wallets.append(wid)
        cur.execute("INSERT OR IGNORE INTO wallets (id,user_id,currency,created_at) VALUES (?,?,?,datetime('now'))",
                    (wid, uid, "INR"))
conn.commit()

# create random topups
for t in range(transfers):
    wid = random.choice(wallets)
    tid = str(uuid.uuid4())
    amt = random.randint(1, 10000)
    cur.execute("INSERT INTO transfers (id,kind,source_wallet_id,destination_wallet_id,amount,status,idempotency_key,created_at) VALUES (?,?,?,?,?,?,?,datetime('now'))",
                (tid, "topup", None, wid, amt, "completed", f"seed-{t}"))
    cur.execute("INSERT INTO entries (id,wallet_id,transfer_id,amount,balance_after,created_at) VALUES (?,?,?,?,?,datetime('now'))",
                (str(uuid.uuid4()), wid, tid, amt, amt))
    if t % 1000 == 0:
        conn.commit()
conn.commit()
conn.close()
print("seed complete")
