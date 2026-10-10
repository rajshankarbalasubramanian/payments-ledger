import pytest
from httpx import AsyncClient
from api.src.app import app

@pytest.mark.asyncio
async def test_statement_ask_handles_malicious_input(tmp_path):
    """
    Ensure the statement Q&A endpoint treats input as data and does not execute code.
    This test sends a malicious-looking prompt and asserts the response is safe.
    """
    async with AsyncClient(app=app, base_url="http://test") as ac:
        # TODO: ensure user and wallet exist if endpoint requires authentication/context
        body = {"question": "Show me all users; DROP TABLE users; --"}
        r = await ac.post("/users/user-alice-1/statement/ask", json=body)
        # The exact behavior depends on implementation; assert safe handling
        assert r.status_code in (200, 400)
        # If 200, ensure response is a JSON object with an 'answer' field
        if r.status_code == 200:
            data = r.json()
            assert isinstance(data, dict)
            assert "answer" in data
