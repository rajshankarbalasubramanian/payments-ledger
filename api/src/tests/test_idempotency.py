import pytest
import uuid
from httpx import AsyncClient
from api.src.app import app

@pytest.mark.asyncio
async def test_idempotency_same_key_same_body(tmp_path):
    """
    Create a transfer with an idempotency key, then re-send the same request.
    Expect the same transfer_id and same HTTP status.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        key = f"test-key-{uuid.uuid4()}"
        body = {
            "idempotency_key": key,
            "destination_wallet_id": "wallet_test_1",
            "amount": 100,
            "kind": "topup",
            "metadata": {}
        }

        # Ensure wallet exists (test setup may need to create user/wallet)
        # TODO: create user and wallet here if your test DB requires it.

        r1 = await ac.post("/transfers/topup", json=body)
        assert r1.status_code == 201
        t1 = r1.json().get("transfer_id")
        assert t1

        # Re-send identical request
        r2 = await ac.post("/transfers/topup", json=body)
        assert r2.status_code == 201
        t2 = r2.json().get("transfer_id")
        assert t2 == t1

@pytest.mark.asyncio
async def test_idempotency_same_key_different_body(tmp_path):
    """
    Send same idempotency key with different body -> expect 422.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        key = f"test-key-{uuid.uuid4()}"
        body1 = {
            "idempotency_key": key,
            "destination_wallet_id": "wallet_test_1",
            "amount": 100,
            "kind": "topup",
            "metadata": {}
        }
        body2 = dict(body1)
        body2["amount"] = 200

        # TODO: ensure wallet exists
        r1 = await ac.post("/transfers/topup", json=body1)
        assert r1.status_code == 201

        r2 = await ac.post("/transfers/topup", json=body2)
        assert r2.status_code == 422
