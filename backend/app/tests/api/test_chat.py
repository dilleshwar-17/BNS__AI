class TestChatEndpoint:
    async def test_chat_requires_auth(self, client):
        resp = await client.post("/api/v1/chat", json={"message": "hello"})
        assert resp.status_code in (401, 403, 307)

    async def test_chat_history_requires_auth(self, client):
        resp = await client.get("/api/v1/chat/history")
        assert resp.status_code in (401, 403, 307)

    async def test_chat_invalid_body(self, client):
        resp = await client.post("/api/v1/chat", json={})
        assert resp.status_code in (401, 403, 307, 422)
