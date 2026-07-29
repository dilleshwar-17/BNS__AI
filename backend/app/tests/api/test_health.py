class TestHealthDetailed:
    async def test_health_detailed_returns_200(self, client):
        resp = await client.get("/api/v1/health/detailed")
        assert resp.status_code == 200

    async def test_health_detailed_has_services(self, client):
        resp = await client.get("/api/v1/health/detailed")
        data = resp.json()
        assert "services" in data
        assert "database" in data["services"]

    async def test_liveness(self, client):
        resp = await client.get("/api/v1/health/liveness")
        assert resp.status_code == 200
        assert resp.json()["status"] == "alive"

    async def test_readiness(self, client):
        resp = await client.get("/api/v1/health/readiness")
        assert resp.status_code == 200
        data = resp.json()
        assert "status" in data


class TestMetrics:
    async def test_prometheus_metrics_endpoint(self, client):
        resp = await client.get("/metrics")
        assert resp.status_code == 200

    async def test_llm_metrics_endpoint(self, client):
        resp = await client.get("/api/v1/metrics")
        assert resp.status_code == 200
