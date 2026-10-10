# Payments Ledger — Demo Project

**Goal**: single repository a reviewer can clone, run one command, and see tests pass.  
This repo implements a small payments ledger with idempotency, stampede protection, reconciliation, and a background worker.

---

## Quick start (one command)
```bash
# from repo root
make ci-run

Starts services with docker compose up -d (Postgres, API, worker).

Runs migrations.

Seeds a small dataset for CI.

Runs the test suite (pytest).

Tears down services.
