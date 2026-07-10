"""
helpers/get_create.py — bmqa-v2

مُنقول من bmqa/helpers/get_create.py (النسخة الفعّالة فقط؛ الكتلة الأولى في
الأصل كانت docstring معطَّلة/كود قديم غير مستخدم فعلياً، فلم تُنقل).

التغييرات عن الأصل:
  - `requests.post` (متزامن) -> `httpx.AsyncClient().post` (async)،
    تماشياً مع قاعدة المشروع (لا "requests"، راجع requirements.txt).
  - `from config import r` + نداءات `r.get(...)` / `r.set(...)` المتزامنة
    -> `from core.db import rdb` + `await rdb.get(...)` / `await rdb.set(...)`
    (نفس أسماء العمليات تماماً، فقط بإضافة await، كما هو موضّح في core/db.py).
  - الدالة نفسها أصبحت `async def` بالكامل، وبالتالي أي مكان يستدعيها الآن
    يحتاج `await get_creation_date(id)`.
"""

import httpx

from core.db import rdb

REGDATE_URL = "https://restore-access.indream.app/regdate"


async def get_creation_date(id: int) -> str:
    cached = await rdb.get(f"{id}:CreateDate")
    if cached:
        return cached

    headers = {
        "accept": "*/*",
        "content-type": "application/x-www-form-urlencoded",
        "user-agent": "Nicegram/92 CFNetwork/1390 Darwin/22.0.0",
        "x-api-key": "e758fb28-79be-4d1c-af6b-066633ded128",
        "accept-language": "en-US,en;q=0.9",
    }
    data = {"telegramId": id}

    async with httpx.AsyncClient() as client:
        res = await client.post(REGDATE_URL, headers=headers, json=data)

    date = res.json()["data"]["date"].replace("-", "/")
    await rdb.set(f"{id}:CreateDate", date)
    return date
