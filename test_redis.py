import redis
from dotenv import load_dotenv
import os

load_dotenv()

redis_url = os.getenv("REDIS_URL", "redis://127.0.0.1:6379/0")
print("Используемый URL:", redis_url)

r = redis.from_url(redis_url, socket_timeout=5, socket_connect_timeout=5)
try:
    ok = r.ping()
    print("PING:", ok)  # должно быть True
except Exception as e:
    print("Ошибка:", e)