import os
import redis
import logging

logger = logging.getLogger(__name__)

CACHE_ENABLED = os.getenv("CACHE_ENABLED", "false").lower() == "true"
redis_client = None

if CACHE_ENABLED:
    redis_url = os.getenv("UPSTASH_REDIS_URL")

    if redis_url:
        logger.info("Using PRODUCTION Redis")
        redis_client = redis.Redis.from_url(
            redis_url,
            decode_responses=True,
            socket_timeout=5,
        )
    else:
        logger.info("Using LOCAL Redis")
        redis_client = redis.Redis(
            host=os.getenv("LOCAL_REDIS_HOST", "localhost"),
            port=int(os.getenv("LOCAL_REDIS_PORT", 6379)),
            decode_responses=True,
            socket_timeout=5,
        )
else:
    logger.info("Caching is not enabled")
