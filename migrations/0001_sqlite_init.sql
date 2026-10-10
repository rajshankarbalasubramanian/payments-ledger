BEGIN;
CREATE TABLE users (
  id TEXT PRIMARY KEY,
  name TEXT NOT NULL,
  email TEXT NOT NULL,
  created_at TEXT
);

CREATE TABLE wallets (
  id TEXT PRIMARY KEY,
  user_id TEXT NOT NULL,
  currency TEXT,
  created_at TEXT,
  FOREIGN KEY(user_id) REFERENCES users(id)
);

CREATE TABLE transfers (
  id TEXT PRIMARY KEY,
  kind TEXT,
  source_wallet_id TEXT,
  destination_wallet_id TEXT,
  amount INTEGER,
  status TEXT,
  idempotency_key TEXT,
  created_at TEXT
);

CREATE TABLE entries (
  id TEXT PRIMARY KEY,
  wallet_id TEXT,
  transfer_id TEXT,
  amount INTEGER,
  balance_after INTEGER,
  created_at TEXT
);

CREATE TABLE idempotency_keys (
  key TEXT PRIMARY KEY,
  request_hash TEXT,
  state TEXT,
  response_status INTEGER,
  response_body TEXT
);

CREATE TABLE reconciliation_runs (
  id TEXT PRIMARY KEY,
  started_at TEXT,
  finished_at TEXT,
  summary TEXT
);
COMMIT;
