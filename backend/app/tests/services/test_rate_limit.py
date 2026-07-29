class TestInMemoryRateLimiter:
    def test_basic_rate_limiting(self):
        from app.middleware.rate_limit import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()
        key = "test:127.0.0.1"

        async def run():
            assert await limiter.check(key, 3, 60) is True
            assert await limiter.check(key, 3, 60) is True
            assert await limiter.check(key, 3, 60) is True
            assert await limiter.check(key, 3, 60) is False
            return True

        import asyncio

        assert asyncio.run(run())

    def test_different_keys_independent(self):
        from app.middleware.rate_limit import InMemoryRateLimiter

        limiter = InMemoryRateLimiter()

        async def run():
            assert await limiter.check("key1", 1, 60) is True
            assert await limiter.check("key2", 1, 60) is True
            assert await limiter.check("key1", 1, 60) is False
            assert await limiter.check("key2", 1, 60) is False
            return True

        import asyncio

        assert asyncio.run(run())


class TestRateLimitCircuitBreaker:
    def test_initial_state_closed(self):
        from app.middleware.rate_limit import RateLimitCircuitBreaker

        cb = RateLimitCircuitBreaker()
        assert cb.state == "closed"
        assert cb.is_available() is True

    def test_opens_after_max_failures(self):
        from app.middleware.rate_limit import RateLimitCircuitBreaker

        cb = RateLimitCircuitBreaker()
        cb.max_failures = 2
        cb.record_failure()
        assert cb.state == "closed"
        cb.record_failure()
        assert cb.state == "open"
        assert cb.is_available() is False

    def test_records_success(self):
        from app.middleware.rate_limit import RateLimitCircuitBreaker

        cb = RateLimitCircuitBreaker()
        cb.max_failures = 1
        cb.record_failure()
        assert cb.state == "open"
        cb.record_success()
        assert cb.state == "closed"


class TestEndpointLimits:
    def test_endpoint_limits_structure(self):
        from app.middleware.rate_limit import ENDPOINT_LIMITS, GLOBAL_LIMIT

        assert isinstance(ENDPOINT_LIMITS, dict)
        assert len(ENDPOINT_LIMITS) >= 5
        for path, (limit, window) in ENDPOINT_LIMITS.items():
            assert path.startswith("/")
            assert isinstance(limit, int) and limit > 0
            assert isinstance(window, int) and window > 0
        assert len(GLOBAL_LIMIT) == 2
        assert GLOBAL_LIMIT[0] > 0 and GLOBAL_LIMIT[1] > 0
