import os
import logging
from redis import Redis, RedisError
from redis.retry import Retry
from redis.backoff import ExponentialBackoff
from redis.exceptions import ConnectionError, TimeoutError, ReadOnlyError


logger = logging.getLogger(__name__)

retry = Retry(ExponentialBackoff(), 2, (ConnectionError, TimeoutError, ReadOnlyError))


CACHE_ENABLED = os.getenv("CACHE_ENABLED", "false").lower() == "true"
redis_client = None

if CACHE_ENABLED:
    redis_url = os.getenv("UPSTASH_REDIS_URL")

    if redis_url:
        logger.info("Using PRODUCTION Redis")
        redis_client = Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=0.5,
            retry=retry,
        )
    else:
        logger.info("Using LOCAL Redis")
        redis_client = Redis(
            host=os.getenv("LOCAL_REDIS_HOST", "localhost"),
            port=int(os.getenv("LOCAL_REDIS_PORT", 6379)),
            decode_responses=True,
            socket_timeout=2,
            socket_connect_timeout=0.5,
            retry=retry,
        )

    # Startup connectivity check
    try:
        redis_client.ping()
        logger.info("Redis connection successful")

    except RedisError as e:
        logger.warning("Redis not reachable at startup: %s. Caching disabled.", e)
        redis_client = None
else:
    logger.info("Caching is not enabled")
