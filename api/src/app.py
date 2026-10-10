# api/src/app.py
import uuid
import json
import uvicorn
from typing import Optional
from pydantic import BaseModel, EmailStr
from fastapi import FastAPI, HTTPException, Request, Path, Body
from fastapi.responses import JSONResponse
from .db import db
from .utils import hash_body

class InsufficientFunds(Exception):
    pass

app = FastAPI(title="Payments Ledger API")

# -------------------------
# Pydantic models
# -------------------------
class UserIn(BaseModel):
    id: str
    name: str
    email: EmailStr
    metadata: Optional[dict] = {}

class WalletIn(BaseModel):
    id: str
    currency: Optional[str] = "INR"
    metadata: Optional[dict] = {}

class CreateTransfer(BaseModel):
    idempotency_key: str
    source_wallet_id: Optional[str] = None
    destination_wallet_id: Optional[str] = None
    amount: int
    kind: str
    metadata: Optional[dict] = {}

# -------------------------
# Startup / Shutdown
# -------------------------
@app.on_event("startup")
async def startup():
    await db.connect()

@app.on_event("shutdown")
async def shutdown():
    await db.disconnect()

# -------------------------
# Health route (debug)
# -------------------------
@app.get("/__health")
async def _health():
    return {"ok": True}

# -------------------------
# POST /users
# -------------------------
@app.post("/users", status_code=201)
async def create_user(user: UserIn):
    try:
        await db.execute(
            "INSERT OR IGNORE INTO users (id, name, email, created_at) VALUES (:id, :name, :email, datetime('now'))",
            {"id": user.id, "name": user.name, "email": user.email}
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
    return {"id": user.id, "name": user.name, "email": user.email}

# -------------------------
# POST /users/{user_id}/wallets
# -------------------------
@app.post("/users/{user_id}/wallets", status_code=201)
async def open_wallet(user_id: str = Path(..., description="User id"), wallet: Optional[WalletIn] = None):
    if wallet is None:
        raise HTTPException(status_code=422, detail="Missing wallet body")
    try:
        row = await db.fetch_one("SELECT id FROM users WHERE id = :id", {"id": user_id})
        if not row:
            raise HTTPException(status_code=404, detail="User not found")
        await db.execute(
            "INSERT OR IGNORE INTO wallets (id, user_id, currency, created_at) VALUES (:id, :user_id, :currency, datetime('now'))",
            {"id": wallet.id, "user_id": user_id, "currency": wallet.currency}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"DB error: {str(e)}")
    return {"id": wallet.id, "user_id": user_id, "currency": wallet.currency}

# -------------------------
# POST /transfers/topup  (new)
# -------------------------
from fastapi import Body

@app.post("/transfers/topup")
async def topup_transfer(body: dict = Body(...)):
    key = body.get("idempotency_key")
    dst = body.get("destination_wallet_id")
    try:
        amount = int(body.get("amount", 0))
    except Exception:
        return JSONResponse(status_code=422, content={"error": "amount must be an integer"})

    if not key or not dst or amount <= 0:
        return JSONResponse(status_code=422, content={"error": "idempotency_key, destination_wallet_id and positive amount required"})

    req_hash = hash_body(body)

    # PART A: idempotency - use safe transaction context
    try:
        await db.execute("BEGIN IMMEDIATE")
        await db.execute(
            "INSERT OR IGNORE INTO idempotency_keys (key, request_hash, state) VALUES (:key, :hash, 'running')",
            {"key": key, "hash": req_hash}
        )
        row = await db.fetch_one(
            "SELECT request_hash, state, response_status, response_body FROM idempotency_keys WHERE key = :key",
            {"key": key}
        )
        if row is None:
            await db.execute("ROLLBACK")
            return JSONResponse(status_code=500, content={"error": "Failed to persist idempotency key"})
        if row["request_hash"] != req_hash:
            await db.execute("ROLLBACK")
            return JSONResponse(status_code=422, content={"error": "Idempotency key used with different body"})
        if row["state"] == "running" and row["response_status"] is None:
            await db.execute("ROLLBACK")
            return JSONResponse(status_code=409, content={"error": "Request is still running; retry shortly"})
        if row["state"] == "completed":
            await db.execute("ROLLBACK")
            return JSONResponse(status_code=row["response_status"], content=json.loads(row["response_body"]))
        await db.execute("COMMIT")
    except Exception:
        # ensure we do not call ROLLBACK twice; if BEGIN failed, skip ROLLBACK
        try:
            await db.execute("ROLLBACK")
        except Exception:
            pass
        raise

    # PART B: core topup - use safe transaction and cleanup on error
    try:
        await db.execute("BEGIN IMMEDIATE")

        w = await db.fetch_one("SELECT id FROM wallets WHERE id = :w", {"w": dst})
        if not w:
            await db.execute("ROLLBACK")
            # remove the running idempotency key so client can retry
            await db.execute("DELETE FROM idempotency_keys WHERE key = :key AND state = 'running'", {"key": key})
            return JSONResponse(status_code=404, content={"error": "Destination wallet not found"})

        transfer_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO transfers (id, kind, source_wallet_id, destination_wallet_id, amount, status, idempotency_key, created_at) VALUES (:id, :kind, NULL, :dst, :amt, 'completed', :key, datetime('now'))",
            {"id": transfer_id, "kind": "topup", "dst": dst, "amt": amount, "key": key}
        )

        dst_bal_row = await db.fetch_one("SELECT COALESCE(SUM(amount),0) as bal FROM entries WHERE wallet_id = :w", {"w": dst})
        dst_bal = dst_bal_row["bal"] if dst_bal_row else 0
        await db.execute(
            "INSERT INTO entries (id, wallet_id, transfer_id, amount, balance_after, created_at) VALUES (:id, :w, :t, :amt, :bal, datetime('now'))",
            {"id": str(uuid.uuid4()), "w": dst, "t": transfer_id, "amt": amount, "bal": dst_bal + amount}
        )

        response_body = {"transfer_id": transfer_id, "status": "completed"}
        await db.execute(
            "UPDATE idempotency_keys SET state='completed', response_status=201, response_body=:body WHERE key=:key",
            {"body": json.dumps(response_body), "key": key}
        )

        await db.execute("COMMIT")
        return JSONResponse(status_code=201, content=response_body)

    except Exception as e:
        # rollback if possible, then remove running idempotency key so client can retry
        try:
            await db.execute("ROLLBACK")
        except Exception:
            pass
        try:
            await db.execute("DELETE FROM idempotency_keys WHERE key = :key AND state = 'running'", {"key": key})
        except Exception:
            pass
        return JSONResponse(status_code=400, content={"error": str(e)})


# -------------------------
# POST /transfers  (existing)
# -------------------------
@app.post("/transfers")
async def create_transfer(request: Request):
    body = await request.json()
    if "idempotency_key" not in body:
        return JSONResponse(status_code=400, content={"error": "Missing idempotency_key"})
    status_code, response_data = await handle_transfer_request(body)
    return JSONResponse(status_code=status_code, content=response_data)

async def handle_transfer_request(body: dict):
    key = body.get("idempotency_key")
    req_hash = hash_body(body)

    # PART A: Idempotency
    await db.execute("BEGIN IMMEDIATE")
    try:
        await db.execute(
            "INSERT OR IGNORE INTO idempotency_keys (key, request_hash, state) VALUES (:key, :hash, 'running')",
            {"key": key, "hash": req_hash}
        )
        row = await db.fetch_one(
            "SELECT request_hash, state, response_status, response_body FROM idempotency_keys WHERE key = :key",
            {"key": key}
        )
        if row is None:
            await db.execute("ROLLBACK")
            return 500, {"error": "Failed to persist idempotency key"}
        if row["request_hash"] != req_hash:
            await db.execute("ROLLBACK")
            return 422, {"error": "Idempotency key used with different body"}
        if row["state"] == "running" and row["response_status"] is None:
            await db.execute("ROLLBACK")
            return 409, {"error": "Request is still running; retry shortly"}
        if row["state"] == "completed":
            await db.execute("ROLLBACK")
            cached_body = row["response_body"]
            if cached_body is None:
                return 500, {"error": "Completed transfer is missing a cached response"}
            return row["response_status"], json.loads(cached_body)
        await db.execute("COMMIT")
    except Exception:
        await db.execute("ROLLBACK")
        raise

    # PART B: Ledger execution
    await db.execute("BEGIN IMMEDIATE")
    try:
        src = body.get("source_wallet_id")
        dst = body.get("destination_wallet_id")
        amount = int(body.get("amount", 0))
        if amount <= 0:
            raise Exception("Amount must be positive")
        if src:
            bal_row = await db.fetch_one("SELECT COALESCE(SUM(amount), 0) as bal FROM entries WHERE wallet_id = :w", {"w": src})
            if not bal_row or bal_row["bal"] < amount:
                raise InsufficientFunds("Insufficient balance available")
        transfer_id = str(uuid.uuid4())
        await db.execute(
            "INSERT INTO transfers (id, kind, source_wallet_id, destination_wallet_id, amount, status, idempotency_key, created_at) VALUES (:id, :kind, :src, :dst, :amt, :status, :key, datetime('now'))",
            {"id": transfer_id, "kind": body.get("kind", "payment"), "src": src, "dst": dst, "amt": amount, "status": "completed", "key": key}
        )
        if src:
            src_bal_row = await db.fetch_one("SELECT COALESCE(SUM(amount), 0) as bal FROM entries WHERE wallet_id = :w", {"w": src})
            src_bal = src_bal_row["bal"] if src_bal_row else 0
            await db.execute(
                "INSERT INTO entries (id, wallet_id, transfer_id, amount, balance_after, created_at) VALUES (:id, :w, :t, :amt, :bal, datetime('now'))",
                {"id": str(uuid.uuid4()), "w": src, "t": transfer_id, "amt": -amount, "bal": src_bal - amount}
            )
        if dst:
            dst_bal_row = await db.fetch_one("SELECT COALESCE(SUM(amount), 0) as bal FROM entries WHERE wallet_id = :w", {"w": dst})
            dst_bal = dst_bal_row["bal"] if dst_bal_row else 0
            await db.execute(
                "INSERT INTO entries (id, wallet_id, transfer_id, amount, balance_after, created_at) VALUES (:id, :w, :t, :amt, :bal, datetime('now'))",
                {"id": str(uuid.uuid4()), "w": dst, "t": transfer_id, "amt": amount, "bal": dst_bal + amount}
            )
        response_body = {"transfer_id": transfer_id, "status": "completed"}
        await db.execute(
            "UPDATE idempotency_keys SET state='completed', response_status=201, response_body=:body WHERE key=:key",
            {"body": json.dumps(response_body), "key": key}
        )
        await db.execute("COMMIT")
        return 201, response_body
    except InsufficientFunds as e:
        await db.execute("ROLLBACK")
        await db.execute("DELETE FROM idempotency_keys WHERE key = :key AND state = 'running'", {"key": key})
        return 400, {"error": str(e)}
    except Exception as e:
        await db.execute("ROLLBACK")
        await db.execute("DELETE FROM idempotency_keys WHERE key = :key AND state = 'running'", {"key": key})
        return 400, {"error": str(e)}

# -------------------------
# Boot loader
# -------------------------
if __name__ == "__main__":
    uvicorn.run("api.src.app:app", host="127.0.0.1", port=8000, reload=True)
