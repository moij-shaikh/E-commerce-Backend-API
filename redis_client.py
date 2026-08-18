import redis

redis_py=redis.Redis(
    host="localhost",
    port=6379,
    decode_responses=True
)