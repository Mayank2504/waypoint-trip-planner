from waypoint.rate_limit import RateLimiter


def test_rate_limiter_sleeps_for_remaining_interval(monkeypatch):
    times = iter([10.0, 10.0, 10.25, 11.0])
    sleeps = []
    monkeypatch.setattr("waypoint.rate_limit.time.monotonic", lambda: next(times))
    monkeypatch.setattr("waypoint.rate_limit.time.sleep", sleeps.append)
    limiter = RateLimiter(1.0)
    limiter.wait()
    limiter.wait()
    assert sleeps == [0.75]
