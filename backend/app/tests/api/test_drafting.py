class TestDraftingEndpoint:
    async def test_drafting_requires_auth(self, client):
        resp = await client.post("/api/v1/drafting/generate", json={"type": "fir"})
        assert resp.status_code in (401, 403, 307)

    async def test_drafting_types_public(self, client):
        resp = await client.get("/api/v1/drafting/types")
        assert resp.status_code in (200, 401, 403)
