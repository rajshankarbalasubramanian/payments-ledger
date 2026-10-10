# Isolation lab (two-session)

## Goal
Demonstrate concurrent transactions and isolation behavior.

## Session A
```sql
-- open transaction A
BEGIN;
SELECT COALESCE(SUM(amount),0) FROM entries WHERE wallet_id='wallet-1';
-- keep transaction open
