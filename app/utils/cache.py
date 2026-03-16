import hashlib
import json
import logging
from typing import Any, Callable
from app.services.redis import redis_client


logger = logging.getLogger(__name__)


def _normalize(value: Any):
    """
    Convert objects to JSON-serializable forms.
    """
    if value is None:
        return None

    if hasattr(value, "model_dump"):  # Pydantic model
        return value.model_dump()

    if isinstance(value, set):
        return sorted(list(value))

    if isinstance(value, (list, tuple)):
        return [_normalize(v) for v in value]

    if isinstance(value, dict):
        return {k: _normalize(v) for k, v in value.items()}

    return value


def build_cache_key(prefix: str, **kwargs) -> str:
    """
    Build a deterministic Redis cache key.

    Example:
        build_cache_key(
            "songs:usage_summary",
            filters=filter_query,
            activities=allowed_activity_ids
        )
    """
    if redis_client is None:
        return None

    normalized = {k: _normalize(v) for k, v in kwargs.items()}

    key_json = json.dumps(normalized, sort_keys=True, default=str)
    key_hash = hashlib.md5(key_json.encode()).hexdigest()

    logger.debug(f"BUILDING KEY --- {prefix}:{key_hash}")
    return f"{prefix}:{key_hash}"


def cache_get(key: str):
    if redis_client is None:
        return None

    value = redis_client.get(key)
    if value is None:
        return None
    return json.loads(value)


def cache_set(key: str, value, ttl: int = 300):
    if redis_client is None:
        return None

    value_json = json.dumps(value, default=str)
    redis_client.set(key, value_json, ex=ttl)


def cache_get_or_set(key: str, fn: Callable[[], Any], ttl: int = 3600):
    """Execute fn() and cache result. If Redis is disabled, simply executes fn()."""
    if redis_client is None:
        return fn()

    cached = cache_get(key)

    if cached is not None:
        logger.debug("Cache HIT %s", key)
        return cached

    logger.debug("Cache MISS %s", key)
    value = fn()

    cache_set(key, value, ttl)

    return value
