import json
import os
from functools import lru_cache

try:
    from redis import Redis
    from redis.exceptions import RedisError
except ImportError:  # pragma: no cover - fallback for environments before dependency install
    Redis = None

    class RedisError(Exception):
        pass


@lru_cache(maxsize=1)
def get_redis_client():
    redis_url = os.getenv("REDIS_URL") or os.getenv("CACHE_REDIS_URL")
    if not redis_url or Redis is None:
        return None
    try:
        return Redis.from_url(redis_url, decode_responses=True)
    except RedisError:
        return None


def get_json(key):
    client = get_redis_client()
    if not client:
        return None
    try:
        value = client.get(key)
    except RedisError:
        return None
    if not value:
        return None
    try:
        return json.loads(value)
    except json.JSONDecodeError:
        return None


def set_json(key, value, ex=60):
    client = get_redis_client()
    if not client:
        return False
    try:
        client.set(key, json.dumps(value), ex=ex)
        return True
    except (RedisError, TypeError, ValueError):
        return False


def get_int(key, default=0):
    client = get_redis_client()
    if not client:
        return default
    try:
        value = client.get(key)
        return int(value) if value is not None else default
    except (RedisError, TypeError, ValueError):
        return default


def incr(key):
    client = get_redis_client()
    if not client:
        return None
    try:
        return client.incr(key)
    except RedisError:
        return None


def set_if_absent(key, value, ex):
    client = get_redis_client()
    if not client:
        return False
    try:
        return bool(client.set(key, value, ex=ex, nx=True))
    except RedisError:
        return False


def delete(key):
    client = get_redis_client()
    if not client:
        return 0
    try:
        return int(client.delete(key))
    except RedisError:
        return 0
