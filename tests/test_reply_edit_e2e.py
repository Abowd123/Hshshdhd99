"""
tests/test_reply_edit_e2e.py
════════════════════════════════════════════════════════════════════════════════
سيناريو طرف-لطرف (End-to-End) لآلية تعديل الردود عبر Reply.

الهدف:
  التحقق أن التدفق التالي يعمل من أوله لآخره دون تعديلات إضافية:
    1. تنفيذ أمر قفل حقيقي → يرسل البوت رداً مُتتبَّعاً.
    2. المطوّر يرسل "تعديل" كـ Reply على ذلك الرد.
    3. المطوّر يرسل النص الجديد بصيغة [الاسم].
    4. تنفيذ أمر القفل مجدداً → الرد الجديد يظهر فعلياً.

الاختبارات المُتضمَّنة:
  A. وحدة (unit) — تختبر منطق Redis مباشرةً بدون Telegram.
  B. توثيقي (doctest-style) — خطوات السيناريو الكامل لتشغيل يدوي.

كيفية التشغيل:
  pytest tests/test_reply_edit_e2e.py -v
  python tests/test_reply_edit_e2e.py          # تشغيل يدوي مباشر

المتطلبات:
  - Redis يعمل + متغيّرات .env مُضبَطة (DATABASE_URL, DEV_ZAID, ...).
  - pytest-asyncio مثبَّت (pip install pytest-asyncio).
════════════════════════════════════════════════════════════════════════════════
"""

from __future__ import annotations

import asyncio
import pytest

from core.db import rdb
from core.keys import message_override_key, sent_message_key
from core.messages import (
    DEFAULT_MESSAGES,
    get_message,
    get_tracked_message_id,
    reset_message,
    set_message_override,
    track_sent_message,
)

# ── ثوابت الاختبار ──────────────────────────────────────────────────────────
CHAT_ID     = -1009999999999   # شات وهمي
BOT_MSG_ID  = 12345            # معرّف رسالة Telegram وهمي (سيُنشئه البوت)
MESSAGE_KEY = "locks.chat_locked"

# ════════════════════════════════════════════════════════════════════════════
# A. اختبارات الوحدة (unit tests) — منطق Redis فقط، بدون Telegram
# ════════════════════════════════════════════════════════════════════════════

@pytest.fixture(autouse=True)
async def cleanup_redis():
    """يُنظّف مفاتيح الاختبار في Redis قبل وبعد كل اختبار."""
    keys_to_clean = [
        sent_message_key(CHAT_ID, BOT_MSG_ID),
        message_override_key(MESSAGE_KEY),
    ]
    for k in keys_to_clean:
        await rdb.delete(k)
    yield
    for k in keys_to_clean:
        await rdb.delete(k)


# ── A1: التتبّع → الاسترجاع ──────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a1_track_then_retrieve():
    """
    محاكاة: البوت يرسل رسالة → يتتبّعها → المطوّر يستعلم عنها.
    الخطوات:
      1. البوت يرسل الرد (محاكاة: BOT_MSG_ID = 12345)
      2. يُستدعى track_sent_message مع (chat_id, bot_msg_id, message_key)
      3. المطوّر يرسل "تعديل" كـ Reply → يستدعي get_tracked_message_id
      4. يجب أن يرجع نفس message_key
    """
    # الخطوة 2: تتبّع الرسالة (يُنفَّذ في all_locks_1._lock_toggle)
    await track_sent_message(CHAT_ID, BOT_MSG_ID, MESSAGE_KEY)

    # الخطوة 3: استرجاع المعرّف (يُنفَّذ في replyEditHandler)
    mid = await get_tracked_message_id(CHAT_ID, BOT_MSG_ID)

    assert mid == MESSAGE_KEY, f"توقّع {MESSAGE_KEY!r}، استُرجع {mid!r}"


# ── A2: معاينة Override → تستخدم النص الجديد ───────────────────────────────

@pytest.mark.asyncio
async def test_a2_override_affects_get_message():
    """
    محاكاة: بعد حفظ Override، get_message يستخدمه تلقائياً.
    الخطوات:
      1. النص الافتراضي يُعرض بصيغة {botkey}/{mention}/{feature}
      2. تُحفظ نص جديد عبر set_message_override
      3. استدعاء get_message يجب أن يرجع النص الجديد
    """
    dummy = {"botkey": "🤖", "mention": "أحمد", "feature": "الشات"}

    # قبل Override: يجب أن يُرجع النص الافتراضي
    default_rendered = await get_message(MESSAGE_KEY, **dummy)
    assert "ابشر قفلت" in default_rendered

    # حفظ Override
    new_template = "{botkey} — تم القفل بواسطة {mention} — الميزة: {feature} 🔒"
    await set_message_override(MESSAGE_KEY, new_template)

    # بعد Override: يجب أن يُرجع النص الجديد
    new_rendered = await get_message(MESSAGE_KEY, **dummy)
    assert "تم القفل بواسطة أحمد" in new_rendered, f"لم يُطبَّق Override: {new_rendered!r}"
    assert "ابشر قفلت" not in new_rendered, "الرد الافتراضي لا يزال ظاهراً رغم Override"


# ── A3: reset_message يُعيد النص الافتراضي ───────────────────────────────────

@pytest.mark.asyncio
async def test_a3_reset_restores_default():
    """
    بعد reset_message، get_message يعود للنص الافتراضي.
    """
    dummy = {"botkey": "🤖", "mention": "أحمد", "feature": "الشات"}

    await set_message_override(MESSAGE_KEY, "{botkey} override test {mention} {feature}")
    await reset_message(MESSAGE_KEY)

    rendered = await get_message(MESSAGE_KEY, **dummy)
    assert "ابشر قفلت" in rendered, f"النص الافتراضي لم يُستعَد: {rendered!r}"


# ════════════════════════════════════════════════════════════════════════════
# B. السيناريو الكامل (موثَّق للتشغيل اليدوي في بيئة Telegram حقيقية)
# ════════════════════════════════════════════════════════════════════════════

MANUAL_SCENARIO = """
════════════════════════════════════════════════════════════════════════════════
سيناريو طرف-لطرف: تعديل رد البوت عبر Reply
════════════════════════════════════════════════════════════════════════════════

المتطلبات:
  • مجموعة Telegram نشطة مع البوت مضافاً وممكَّناً (rdb: {chat_id}:enable:{Dev_Zaid} = 1)
  • حساب مطوّر (dev_pls أو devp_pls = True)
  • Redis يعمل

──────────────────────────────────────────────────────────────────────────────
الخطوة 1 — تنفيذ أمر قفل حقيقي
──────────────────────────────────────────────────────────────────────────────
  المستخدم (مدير): يرسل "قفل الشات" في المجموعة.
  المتوقَّع:
    ✅ البوت يرد برسالة مثل:
         🧚‍♀️ من 「 @admin_username 」
         🧚‍♀️ ابشر قفلت الشات
         ☆
    ✅ في Redis:
         sentmsg:{chat_id}:{bot_reply_msg_id}{Dev_Zaid} = "locks.chat_locked"
  التحقق اليدوي:
    redis-cli GET "sentmsg:{chat_id}:{bot_msg_id}{Dev_Zaid}"
    # يجب أن يُرجع: "locks.chat_locked"

──────────────────────────────────────────────────────────────────────────────
الخطوة 2 — المطوّر يرد على رسالة البوت بـ "تعديل"
──────────────────────────────────────────────────────────────────────────────
  المطوّر: يضغط Reply على رسالة البوت ثم يكتب: تعديل
  المتوقَّع:
    ✅ البوت يرد برسالة تعديل تفاعلية تحتوي على:
         ✏️ تعديل الرد: locks.chat_locked
         النص الحالي:
         [اسم_البوت] من 「 [الشخص] 」
         [اسم_البوت] ابشر قفلت [الميزة]
         ☆
         الأسماء المتاحة لهذا الرد:
         • [اسم_البوت]
         • [الشخص]
         • [الميزة]
         أرسل الآن النص الجديد ... خلال 5 دقائق.
    ✅ في Redis:
         msgedit_pending:{dev_uid}:{chat_id}{Dev_Zaid} = "locks.chat_locked"  (TTL=300s)
  التحقق اليدوي:
    redis-cli GET "msgedit_pending:{dev_uid}:{chat_id}{Dev_Zaid}"
    # يجب أن يُرجع: "locks.chat_locked"

──────────────────────────────────────────────────────────────────────────────
الخطوة 3 — المطوّر يرسل النص الجديد
──────────────────────────────────────────────────────────────────────────────
  المطوّر: يرسل (خلال 5 دقائق):
         [اسم_البوت] 🔒 تم قفل [الميزة] من طرف [الشخص]

  المتوقَّع:
    ✅ البوت يرد برسالة تأكيد تحتوي على:
         ✅ تم حفظ الرد الجديد: locks.chat_locked
         📄 معاينة (ببيانات وهمية: mention="أحمد"):
         ────────────────
         🧚‍♀️ 🔒 تم قفل الميزة التجريبية من طرف أحمد
         ────────────────
         ⚡️ الردود الحقيقية القادمة في الشات ستستخدم هذا النص تلقائياً ...
    ✅ في Redis:
         msgoverride:locks.chat_locked{Dev_Zaid} = "{botkey} 🔒 تم قفل {feature} من طرف {mention}"
         msgedit_pending: محذوف (TTL أُلغي)
  التحقق اليدوي:
    redis-cli GET "msgoverride:locks.chat_locked{Dev_Zaid}"
    redis-cli EXISTS "msgedit_pending:{dev_uid}:{chat_id}{Dev_Zaid}"  # يجب: 0

──────────────────────────────────────────────────────────────────────────────
الخطوة 4 — تنفيذ أمر القفل مجدداً للتأكيد
──────────────────────────────────────────────────────────────────────────────
  تحضير: أرسل "فتح الشات" أولاً لإلغاء القفل الأول.
  ثم: أرسل "قفل الشات" مرةً ثانيةً.
  المتوقَّع:
    ✅ البوت يرد بالنص الجديد فعلياً:
         🧚‍♀️ 🔒 تم قفل الشات من طرف @admin_username
    ❌ لا يجب أن يظهر: "ابشر قفلت"  (النص الافتراضي القديم)

──────────────────────────────────────────────────────────────────────────────
تنظيف بعد الاختبار (اختياري)
──────────────────────────────────────────────────────────────────────────────
  redis-cli DEL "msgoverride:locks.chat_locked{Dev_Zaid}"
  # أو من داخل المجموعة (بصلاحية مطوّر):
  # استرجاع_رد locks.chat_locked  ← ثم اضغط "✅ نعم، استرجاع"

════════════════════════════════════════════════════════════════════════════════
"""


# ════════════════════════════════════════════════════════════════════════════
# C. قائمة Edge Cases — موثَّقة، غير مُصلَحة (للمرحلة القادمة)
# ════════════════════════════════════════════════════════════════════════════

EDGE_CASES = """
════════════════════════════════════════════════════════════════════════════════
Edge Cases — لاحظتها، مؤجَّلة للمرحلة القادمة
════════════════════════════════════════════════════════════════════════════════

[EC-1] "تعديل" أثناء حالة pending نشطة
─────────────────────────────────────────
  السيناريو: المطوّر في حالة تعديل مُعلَّقة (pending نشط)، ثم يرسل "تعديل"
             كـ Reply على رسالة أخرى.
  ما يحدث: pendingEditGateHandler (group=17) يلتقطها قبل replyEditHandler
             (group=1500). نص "تعديل" لا يحتوي أسماء [...]، فـ
             _translate_and_validate يُرجع ("تعديل", []) بلا أخطاء.
             النتيجة: تُحفظ كلمة "تعديل" حرفياً كـ override للرسالة قيد التعديل.
  الأثر: الرد المُخزَّن يصبح "تعديل" فارغاً من أي placeholders — الرد الفعلي
         في الشات سيظهر كـ "تعديل" دون أي استبدال.
  الحل المقترح (لاحقاً): في pendingEditGateHandler، تحقّق إذا كان النص
             يُطابق أوامر التدفق المعروفة ("تعديل"، وربما أوامر أخرى) قبل
             معالجته كنص جديد.

[EC-2] انتهاء TTL على الرسالة المُتتبَّعة (أسبوع)
───────────────────────────────────────────────────
  السيناريو: المطوّر يريد تعديل رسالة قفل أُرسلت منذ أكثر من 7 أيام.
  ما يحدث: get_tracked_message_id يرجع None → رسالة "غير مسجّلة في نظام
             التتبّع" رغم وجود الرسالة في الشات تاريخياً.
  الأثر: المطوّر يضطر للاستخدام اليدوي (تعديل_رد locks.chat_locked).
  الحل المقترح (لاحقاً): رسالة "غير مسجّلة" تُوضّح أن السبب قد يكون انتهاء
             المهلة، مع ذكر اسم message_id المحتمل للتتبّع اليدوي.

[EC-3] انتهاء TTL على حالة pending (5 دقائق) بدون إشعار
──────────────────────────────────────────────────────────
  السيناريو: المطوّر بدأ تدفق التعديل ثم تأخر أكثر من 5 دقائق.
  ما يحدث: الرسالة التالية التي يرسلها تُمرَّر بـ ContinuePropagation بدون
             أي رد — المطوّر لا يعلم أن المهلة انتهت.
  الأثر: المطوّر يُرسل نص التعديل في المجموعة فيظهر كرسالة عادية للأعضاء.
  الحل المقترح (لاحقاً): حفظ timestamp بدء التعديل، والتحقق منه في
             pendingEditGateHandler لإرسال رسالة "انتهت مهلة التعديل (5 دقائق)".

[EC-4] رسالة البوت أُرسلت بـ send_message() لا بـ m.reply()
──────────────────────────────────────────────────────────────
  السيناريو: أي مكان مستقبلي في الكود يرسل رسالة عبر get_message() لكن يستخدم
             c.send_message() أو m.reply_document() بدلاً من m.reply() البسيطة.
  ما يحدث: track_sent_message لا يُستدعى → "تعديل" عليها يُرجع None.
  الأثر: المطوّر يرى "غير مسجّلة" رغم أن الرسالة مُدارة فعلاً بـ get_message().
  الحل المقترح (لاحقاً): وثّق اتفاقية: "أي استدعاء لـ get_message() يجب أن
             يُعقَّب بـ track_sent_message بعد الإرسال"، مع إضافة linter rule
             أو تعليق WARNING في core/messages.py.

[EC-5] تعديلان متزامنان من مطوّرَين على نفس message_id
────────────────────────────────────────────────────────
  السيناريو: مطوّران يفتحان تدفق تعديل لـ locks.chat_locked في نفس الوقت
             من شاتَّين مختلفَين.
  ما يحدث: _pending_key مستقل لكل (uid, cid) — لا تعارض هناك. لكن
             set_message_override يكتب على نفس مفتاح Redis الواحد. الكاتب
             الأخير يفوز بدون أي تحذير للأول.
  الأثر: أحد التعديلين يُفقَد بصمت.
  الحل المقترح (لاحقاً): ETag/version في مفتاح override، أو قفل Redis
             (SETNX) حول فترة التعديل.

[EC-6] الأمر "تعديل" بدون filters.group / filters.private
────────────────────────────────────────────────────────────
  السيناريو: مطوّر يرسل "تعديل" كـ Reply في محادثة خاصة مع البوت.
  ما يحدث: replyEditHandler لا يقيّد filters.group، فيعمل في الخاصّي أيضاً.
             في الخاصّي cid == uid، لذا _pending_key يُميّز بشكل فريد. هذا
             قد يكون مقصوداً (مطوّر يختبر بمفرده) أو غير مقصود.
  الأثر: لا خطأ فعلي، لكن الردود تُتتبَّع بـ chat_id = uid (الخاصّي). إذا
             أُرسلت نفس الرسالة لاحقاً في مجموعة، لن تجد تتبّعاً هناك.
  الحل المقترح (لاحقاً): قرار صريح بإضافة أو عدم إضافة filters.group.

════════════════════════════════════════════════════════════════════════════════
"""


# ════════════════════════════════════════════════════════════════════════════
# تشغيل يدوي مباشر (بدون pytest)
# ════════════════════════════════════════════════════════════════════════════

async def _run_unit_tests():
    """يشغّل اختبارات A يدوياً ويطبع النتائج."""

    print("════════ اختبارات الوحدة (Unit Tests) ════════")

    # تنظيف مبدئي
    await rdb.delete(sent_message_key(CHAT_ID, BOT_MSG_ID))
    await rdb.delete(message_override_key(MESSAGE_KEY))

    # A1
    await track_sent_message(CHAT_ID, BOT_MSG_ID, MESSAGE_KEY)
    mid = await get_tracked_message_id(CHAT_ID, BOT_MSG_ID)
    assert mid == MESSAGE_KEY, f"A1 فشل: {mid!r}"
    print("  ✓ A1: track_sent_message → get_tracked_message_id")

    # A2
    dummy = {"botkey": "🤖", "mention": "أحمد", "feature": "الشات"}
    new_tpl = "{botkey} 🔒 تم قفل {feature} من طرف {mention}"
    await set_message_override(MESSAGE_KEY, new_tpl)
    rendered = await get_message(MESSAGE_KEY, **dummy)
    assert "تم قفل الشات من طرف أحمد" in rendered, f"A2 فشل: {rendered!r}"
    print("  ✓ A2: set_message_override → get_message يستخدم النص الجديد")

    # A3
    await reset_message(MESSAGE_KEY)
    rendered2 = await get_message(MESSAGE_KEY, **dummy)
    assert "ابشر قفلت" in rendered2, f"A3 فشل: {rendered2!r}"
    print("  ✓ A3: reset_message → get_message يعود للنص الافتراضي")

    # تنظيف
    await rdb.delete(sent_message_key(CHAT_ID, BOT_MSG_ID))
    await rdb.delete(message_override_key(MESSAGE_KEY))

    print("\n✅ جميع اختبارات الوحدة نجحت")
    print("\n" + MANUAL_SCENARIO)
    print(EDGE_CASES)


if __name__ == "__main__":
    asyncio.run(_run_unit_tests())
