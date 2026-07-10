"""
tests/test_track_sent_message.py
اختبار يدوي/توثيقي لآلية تتبّع الرسائل المُرسَلة.

كيفية التشغيل (مع Redis حيّ):
    python -m pytest tests/test_track_sent_message.py -v
    # أو
    python tests/test_track_sent_message.py

المتطلبات:
    - Redis يعمل على المنفذ الافتراضي (أو REDIS_URL مضبوط في .env)
    - المتغيّر Dev_Zaid مضبوط في config.py
"""

import asyncio
import pytest

# ── المساعد: تنظيف المفتاح بعد كل اختبار ────────────────────────────────────
from core.db import rdb
from core.keys import sent_message_key
from core.messages import get_tracked_message_id, track_sent_message

CHAT_ID = -1001111111111   # معرّف مجموعة وهمية للاختبار
MSG_ID  = 99999            # معرّف رسالة تيليغرام وهمية


@pytest.fixture(autouse=True)
async def cleanup():
    """يحذف المفتاح قبل وبعد كل اختبار لضمان العزل."""
    await rdb.delete(sent_message_key(CHAT_ID, MSG_ID))
    yield
    await rdb.delete(sent_message_key(CHAT_ID, MSG_ID))


# ── الاختبار 1: تخزين معرّف الرسالة واسترجاعه ──────────────────────────────

@pytest.mark.asyncio
async def test_track_and_retrieve():
    """
    بعد track_sent_message يجب أن يرجع get_tracked_message_id
    نفس message_id المُخزَّن.
    """
    await track_sent_message(CHAT_ID, MSG_ID, "locks.chat_locked")
    result = await get_tracked_message_id(CHAT_ID, MSG_ID)
    assert result == "locks.chat_locked", f"expected 'locks.chat_locked', got {result!r}"


# ── الاختبار 2: مفتاح غير موجود يرجع None ───────────────────────────────────

@pytest.mark.asyncio
async def test_missing_key_returns_none():
    """
    get_tracked_message_id يجب أن يرجع None لرسالة لم تُتتبَّع.
    """
    result = await get_tracked_message_id(CHAT_ID, MSG_ID)
    assert result is None, f"expected None for untracked message, got {result!r}"


# ── الاختبار 3: TTL قصير → انتهاء المهلة ────────────────────────────────────

@pytest.mark.asyncio
async def test_ttl_expiry():
    """
    بعد انتهاء TTL (ثانية واحدة للاختبار) يجب أن يرجع None.
    """
    await track_sent_message(CHAT_ID, MSG_ID, "locks.chat_opened", ttl=1)
    await asyncio.sleep(1.2)
    result = await get_tracked_message_id(CHAT_ID, MSG_ID)
    assert result is None, f"expected None after TTL expiry, got {result!r}"


# ── الاختبار 4: استبدال القيمة ───────────────────────────────────────────────

@pytest.mark.asyncio
async def test_overwrite():
    """
    استدعاء track_sent_message مرتين بنفس المفاتيح يجب أن يحتفظ بالقيمة الأحدث.
    """
    await track_sent_message(CHAT_ID, MSG_ID, "locks.chat_locked")
    await track_sent_message(CHAT_ID, MSG_ID, "locks.chat_opened")
    result = await get_tracked_message_id(CHAT_ID, MSG_ID)
    assert result == "locks.chat_opened", f"expected 'locks.chat_opened', got {result!r}"


# ══════════════════════════════════════════════════════════════════════════════
# تشغيل يدوي مباشر (بدون pytest)
# ══════════════════════════════════════════════════════════════════════════════

async def _manual_demo():
    print("── تخزين الرسالة ──")
    await track_sent_message(CHAT_ID, MSG_ID, "locks.chat_locked")
    print(f"  track_sent_message({CHAT_ID}, {MSG_ID}, 'locks.chat_locked') → تم")

    print("── استرجاع المعرّف ──")
    mid = await get_tracked_message_id(CHAT_ID, MSG_ID)
    print(f"  get_tracked_message_id({CHAT_ID}, {MSG_ID}) → {mid!r}")
    assert mid == "locks.chat_locked"

    print("── تنظيف ──")
    await rdb.delete(sent_message_key(CHAT_ID, MSG_ID))
    mid2 = await get_tracked_message_id(CHAT_ID, MSG_ID)
    print(f"  بعد الحذف → {mid2!r}  (يجب أن يكون None)")
    assert mid2 is None

    print("✓ جميع الفحوصات اليدوية نجحت")


if __name__ == "__main__":
    asyncio.run(_manual_demo())
