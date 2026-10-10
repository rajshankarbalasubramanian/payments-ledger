# Schema and ER

## Noun list
- **User**: id, name, email
- **Wallet**: id, user_id, currency
- **Transfer**: id, kind, source_wallet_id, destination_wallet_id, amount, status, idempotency_key
- **Entry**: id, wallet_id, transfer_id, amount, balance_after
- **IdempotencyKey**: key, request_hash, state, response_status, response_body
- **ReconciliationRun**: id, started_at, finished_at, summary

## Cardinality
- **User 1..* Wallets**
- **Wallet 1..* Entries**
- **Transfer 1..* Entries** (a transfer produces one or more entries)
- **IdempotencyKey 1..1 Transfer** (key maps to a transfer attempt)

## ER diagram (ASCII)
