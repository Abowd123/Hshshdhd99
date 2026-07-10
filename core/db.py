"""
core/db.py — bmqa-v2
عملاء قواعد البيانات غير المتزامنة (async).

كل التخزين (الكاش العام + ytdb/sounddb/wsdb) أصبح على نفس اتصال Redis
الواحد، بدون أي ملفات SQLite محلية (kvsqlite). هذا ضروري على منصات مثل
Sevalla/Railway حيث نظام ملفات الحاوية مؤقت (ephemeral) ويُمسح مع كل نشر
جديد — تخزين البيانات في SQLite محلي كان يعني فقدانها عند كل إعادة نشر.
"""

import json

import redis.asyncio as aioredis

from config import redis_host, redis_port, redis_db, redis_password

# 1. تعريف المتغيرات كـ None في البداية لتأجيل ربطها بالـ Loop
rdb: aioredis.Redis = None
redis_client: aioredis.Redis = None

wsdb: "KVStore" = None
ytdb: "KVStore" = None
sounddb: "KVStore" = None


class KVStore:
    """بديل عن kvsqlite.Client بنفس الواجهة تماماً (get/set/delete/exists)
    حتى لا يحتاج أي كود في Plugins/core/worker للتغيير، لكنه يخزّن كل شيء
    داخل Redis تحت مسافة أسماء (namespace/prefix) خاصة بكل قاعدة بدل ملف
    SQLite منفصل على القرص المحلي."""

    def __init__(self, redis: aioredis.Redis, namespace: str) -> None:
        self._redis = redis
        self._namespace = namespace

    def _key(self, key: str) -> str:
        return f"{self._namespace}:{key}"

    async def get(self, key: str):
        raw = await self._redis.get(self._key(key))
        if raw is None:
            return None
        try:
            return json.loads(raw)
        except (TypeError, ValueError):
            # قيم قديمة/نصية بسيطة غير مخزنة كـ JSON
            return raw

    async def set(self, key: str, value) -> None:
        payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
        await self._redis.set(self._key(key), payload)

    async def delete(self, key: str) -> None:
        await self._redis.delete(self._key(key))

    async def exists(self, key: str) -> bool:
        return bool(await self._redis.exists(self._key(key)))


async def init_databases() -> None:
    """تهيئة اتصال Redis الواحد داخل الـ Event Loop النشط لمنع تضارب
    الـ Loops، وبناء wsdb/ytdb/sounddb كمسافات أسماء منفصلة فوقه."""
    global rdb, redis_client, wsdb, ytdb, sounddb

    rdb = aioredis.Redis(
        host=redis_host,
        port=redis_port,
        db=redis_db,
        password=redis_password,
        decode_responses=True,
    )
    redis_client = rdb

    wsdb = KVStore(rdb, "wsdb")
    ytdb = KVStore(rdb, "ytdb")
    sounddb = KVStore(rdb, "sounddb")


# ============================================================
# TTL حقيقي فوق wsdb — أصبح مباشرة عبر SET...EX الأصلي في Redis،
# بدل الحيلة القديمة (مفتاح TTL موازٍ) التي كانت ضرورية فقط لأن kvsqlite
# لا يوفّر setex. الآن Redis نفسه يحذف المفتاح تلقائياً عند الانتهاء.
# ============================================================
async def wsdb_setex(key: str, value, ttl: int) -> None:
    """يخزّن قيمة في wsdb مع صلاحية TTL حقيقية."""
    payload = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    await rdb.set(wsdb._key(key), payload, ex=ttl)


async def wsdb_get_checked(key: str):
    """يقرأ مفتاحاً خُزِّن عبر wsdb_setex أو wsdb.get عادي. لا حاجة الآن
    لأي تحقق إضافي من الصلاحية لأن Redis يحذف المفتاح تلقائياً بعد TTL."""
    return await wsdb.get(key)
