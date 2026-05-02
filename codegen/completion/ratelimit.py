"""Simple IP-based rate limiter for API protection."""

import time
import threading
from collections import defaultdict
from functools import wraps
from django.conf import settings
from django.http import JsonResponse


def _client_ip(request):
    xff = request.META.get("HTTP_X_FORWARDED_FOR")
    if xff:
        return xff.split(",")[0].strip()
    return request.META.get("REMOTE_ADDR", "127.0.0.1")


class SlidingWindowLimiter:
    """In-memory sliding window rate limiter. Suitable for single-server deployments."""

    def __init__(self, max_requests: int = 60, window_seconds: int = 60):
        self.max = max_requests
        self.window = window_seconds
        self._buckets: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()

    def is_allowed(self, key: str) -> bool:
        now = time.time()
        cutoff = now - self.window
        with self._lock:
            bucket = self._buckets[key]
            # prune expired entries
            while bucket and bucket[0] < cutoff:
                bucket.pop(0)
            if len(bucket) >= self.max:
                return False
            bucket.append(now)
            return True


_limiter = None


def _get_limiter() -> SlidingWindowLimiter:
    global _limiter
    if _limiter is None:
        _limiter = SlidingWindowLimiter(
            max_requests=getattr(settings, "RATE_LIMIT_REQUESTS", 60),
            window_seconds=getattr(settings, "RATE_LIMIT_WINDOW", 60),
        )
    return _limiter


def rate_limit(view_func):
    """Decorator: apply IP-based rate limiting to a view."""

    @wraps(view_func)
    def wrapped(request, *args, **kwargs):
        limiter = _get_limiter()
        ip = _client_ip(request)
        if not limiter.is_allowed(ip):
            return JsonResponse(
                {"success": False, "error_code": "RATE_LIMITED", "error": "请求过于频繁，请稍后重试"},
                status=429,
            )
        return view_func(request, *args, **kwargs)

    return wrapped
