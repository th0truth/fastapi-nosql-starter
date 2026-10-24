import json


class RedisCache:
    @staticmethod
    async def get(redis, key: str) -> dict | list | str | None:
        data = await redis.get(key)

        if data:
            try:
                return json.loads(data)
            except json.JSONDecodeError:
                pass

        return None
