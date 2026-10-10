import asyncio
import pytest
import uuid
from httpx import AsyncClient
from api.src.app import app

@pytest.mark.asyncio
async def test_stampede_single_transfer(tmp_path):
    """
    Fire multiple concurrent requests with the same idempotency key.
    Assert that only one unique transfer_id is returned across responses
    or that subsequent requests return the cached response.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        key = f"stampede-{uuid.uuid4()}"
        body = {
            "idempotency_key": key,
            "destination_wallet_id": "wallet_test_1",
            "amount": 50,
            "kind": "transfer",
            "metadata": {}
        }

        # TODO: ensure wallet(s) exist and source has sufficient balance if needed

        async def send():
            r = await ac.post("/transfers", json=body)
            return r.status_code, r.json()

        tasks = [asyncio.create_task(send()) for _ in range(10)]
        results = await asyncio.gather(*tasks)

        # collect transfer_ids from successful responses
        transfer_ids = {res[1].get("transfer_id") for res in results if isinstance(res[1], dict) and res[1].get("transfer_id")}
        # There should be at most one unique transfer id for the same idempotency key
        assert len(transfer_ids) <= 1
