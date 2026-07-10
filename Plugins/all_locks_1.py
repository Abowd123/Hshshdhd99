"""
all_locks_1.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 2107 → 2406)
الفئة: الأقفال التفصيلية — دفعة 1 (15 زوج قفل/فتح = 30 أمر)

النمط الموحّد:
  - كل زوج (قفل X / فتح X) يُمرَّر لـ _lock_toggle(...)
  - الهاندلر مُوجَّه بجدول _LOCK_TABLE_1 (لا تكرار منطق)
  - _lock_toggle مُصدَّرة لـ all_locks_2.py

التحويلات المطبّقة:
  - r.get/set/delete → await rdb.*
  - m.reply(...)     → await m.reply(...)
  - return False     → return

السلوكيات الغامضة موثّقة في قسم AMBIGUOUS.
"""

from pyrogram import Client, ContinuePropagation, filters

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message, track_sent_message
from helpers.ranks import admin_pls, mod_pls, owner_pls, isLockCommand


# ══════════════════════════════════════════════════════════════════════════════
# Templates — محفوظة للتوافق مع all_locks_2.py الذي يستوردها مباشرة.
#
# ⚠️ هذه القوالب لم تعد تُستخدَم داخل _lock_toggle() بعد ترحيل الرسائل إلى
# core/messages.py. بقيت معرَّفة لأن all_locks_2.py يستوردها لاستخدامها في
# حالة "فتح الإباحي" الخاصة (Open, Openn). لا تحذف هذه القوالب قبل التحقق
# من أن all_locks_2.py لا يستوردها بعد الترحيل الكامل.
# ══════════════════════════════════════════════════════════════════════════════

Open = """
{} من 「 {} 」
{} ابشر فتحت {}
☆
"""

Openn = """
{} من 「 {} 」
{} {} مفتوح من قبل
☆
"""

Openn2 = """
{} من 「 {} 」
{} {} مفتوحه من قبل
☆
"""

lock = """
{} من 「 {} 」
{} ابشر قفلت {}
☆
"""

lockn = """
{} من 「 {} 」
{} {} مقفل من قبل
☆
"""

locknn = """
{} من 「 {} 」
{} {} مقفله من قبل
☆
"""


# ══════════════════════════════════════════════════════════════════════════════
# الدالة العامة (Generic Toggle Handler)
# مُصدَّرة → تُستورَد في all_locks_2.py
#
# المعاملات:
#   m             — كائن الرسالة
#   k             — مفتاح البوت (botkey)
#   redis_key     — اسم المفتاح في Redis بدون cid أو Dev_Zaid
#   display       — النص الذي يظهر في الرسالة ("الشات"، "الفيديو"...)
#   rank_fn       — دالة التحقق من الصلاحية (mod_pls / owner_pls)
#   perm_msg_id   — message_id لرسالة رفض الصلاحية (مثال: "locks.perm_mod")
#   gender        — "m" مذكر → already_locked_m/already_unlocked_m
#                   "f" مؤنث → already_locked_f/already_unlocked_f
#   is_locking    — True=قفل، False=فتح
# ══════════════════════════════════════════════════════════════════════════════

async def _lock_toggle(
    m,
    k: str,
    redis_key: str,
    display: str,
    rank_fn,
    perm_msg_id: str,
    gender: str,
    is_locking: bool,
) -> None:
    # ── cid/mention يُعرَّفان هنا لاستخدامهما في التتبّع حتى عند رفض الصلاحية ─
    cid     = m.chat.id
    mention = m.from_user.mention

    if not await rank_fn(m.from_user.id, cid):
        perm_text = await get_message(perm_msg_id, botkey=k)
        sent = await m.reply(perm_text)
        await track_sent_message(cid, sent.id, perm_msg_id)
        return

    state = await rdb.get(f"{cid}:{redis_key}:{Dev_Zaid}")

    if is_locking:
        if state:
            mid = "locks.already_locked_f" if gender == "f" else "locks.already_locked_m"
            text = await get_message(mid, botkey=k, mention=mention, feature=display)
            sent = await m.reply(text)
            await track_sent_message(cid, sent.id, mid)
            return
        await rdb.set(f"{cid}:{redis_key}:{Dev_Zaid}", 1)
        text = await get_message("locks.chat_locked", botkey=k, mention=mention, feature=display)
        sent = await m.reply(text)
        await track_sent_message(cid, sent.id, "locks.chat_locked")
        return
    else:
        if not state:
            mid = "locks.already_unlocked_f" if gender == "f" else "locks.already_unlocked_m"
            text = await get_message(mid, botkey=k, mention=mention, feature=display)
            sent = await m.reply(text)
            await track_sent_message(cid, sent.id, mid)
            return
        await rdb.delete(f"{cid}:{redis_key}:{Dev_Zaid}")
        text = await get_message("locks.chat_opened", botkey=k, mention=mention, feature=display)
        sent = await m.reply(text)
        await track_sent_message(cid, sent.id, "locks.chat_opened")
        return


# ══════════════════════════════════════════════════════════════════════════════
# جدول الأقفال — دفعة 1 (سطر 2107-2406)
#
# الحقول: (texts_lock, texts_unlock, redis_key, display, gender, rank_fn, perm_msg_id)
#   gender:      "m"=مذكر (already_locked_m/already_unlocked_m)
#                "f"=مؤنث (already_locked_f/already_unlocked_f)
#   perm_msg_id: معرّف رسالة رفض الصلاحية في core/messages.py
# ══════════════════════════════════════════════════════════════════════════════

_LOCK_TABLE_1 = [
    # ── زوج 1: الدردشة (سطر 2107-2125) ──────────────────────────────────
    (
        ("قفل الدردشة", "قفل الدردشه", "قفل الشات"),
        ("فتح الدردشة", "فتح الدردشه", "فتح الشات"),
        "mute", "الشات", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 2: التعديل (سطر 2127-2145) ──────────────────────────────────
    (
        ("قفل التعديل",),
        ("فتح التعديل",),
        "lockEdit", "التعديل", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 3: تعديل الميديا (سطر 2147-2165) ────────────────────────────
    (
        ("قفل تعديل الميديا",),
        ("فتح تعديل الميديا",),
        "lockEditM", "تعديل الميديا", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 4: الفويسات/البصمات (سطر 2167-2185) ─────────────────────────
    (
        ("قفل الفويسات", "قفل البصمات"),
        ("فتح الفويسات", "فتح البصمات"),
        "lockVoice", "الفويس", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 5: الفيديو (سطر 2187-2205) ──────────────────────────────────
    (
        ("قفل الفيديو", "قفل الفيديوهات"),
        ("فتح الفيديو", "فتح الفيديوهات"),
        "lockVideo", "الفيديو", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 6: الاشعارات (سطر 2207-2225) — مؤنث ─────────────────────────
    (
        ("قفل الاشعارات",),
        ("فتح الاشعارات",),
        "lockNot", "الاشعارات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 7: الصور (سطر 2227-2245) — مؤنث ─────────────────────────────
    (
        ("قفل الصور",),
        ("فتح الصور",),
        "lockPhoto", "الصور", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 8: الملصقات (سطر 2247-2265) — مؤنث ──────────────────────────
    (
        ("قفل الملصقات",),
        ("فتح الملصقات",),
        "lockStickers", "الملصقات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 9: الفارسيه (سطر 2267-2285) — مؤنث ──────────────────────────
    (
        ("قفل الفارسيه",),
        ("فتح الفارسيه",),
        "lockPersian", "الفارسيه", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 10: الملفات (سطر 2287-2305) — مؤنث ──────────────────────────
    (
        ("قفل الملفات",),
        ("فتح الملفات",),
        "lockFiles", "الملفات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 11: المتحركات (سطر 2307-2325) — مؤنث ────────────────────────
    (
        ("قفل المتحركات", "قفل المتحركه"),
        ("فتح المتحركات", "فتح المتحركه"),
        "lockAnimations", "المتحركات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 12: الروابط (سطر 2327-2345) — مؤنث ──────────────────────────
    (
        ("قفل الروابط",),
        ("فتح الروابط",),
        "lockUrls", "الروابط", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 13: الهشتاق (سطر 2347-2365) — مذكر ──────────────────────────
    (
        ("قفل الهشتاق", "قفل الهاشتاق"),
        ("فتح الهشتاق", "فتح الهاشتاق"),
        "lockHashtags", "الهاشتاق", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 14: البوتات (سطر 2367-2385) — مؤنث ──────────────────────────
    (
        ("قفل البوتات",),
        ("فتح البوتات",),
        "lockBots", "البوتات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 15: اليوزرات/المنشن (سطر 2387-2405) — مؤنث ──────────────────
    (
        ("قفل اليوزرات", "قفل المنشن"),
        ("فتح اليوزرات", "فتح المنشن"),
        "lockTags", "اليوزرات", "f", mod_pls, "locks.perm_mod",
    ),
]

# فهرس سريع: text → (entry_index, is_locking)
_TEXT_MAP_1: dict = {}
for _entry in _LOCK_TABLE_1:
    _ltexts, _utexts, _key, _disp, _g, _rank, _perm = _entry
    for _t in _ltexts:
        _TEXT_MAP_1[_t] = (_entry, True)
    for _t in _utexts:
        _TEXT_MAP_1[_t] = (_entry, False)


# ══════════════════════════════════════════════════════════════════════════════
# دالة مساعدة: بناء نص الأمر
# ══════════════════════════════════════════════════════════════════════════════

async def _resolve_text(m) -> str:
    text = m.text or ""
    name = await rdb.get(f"{Dev_Zaid}:BotName") or "ليو"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "", 1)
    custom = await rdb.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if custom:
        text = custom
    global_custom = await rdb.get(f"Custom:{Dev_Zaid}&text={text}")
    if global_custom:
        text = global_custom
    return text


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28
# ══════════════════════════════════════════════════════════════════════════════

@register("locks_1_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def locks1Handler(c, m) -> None:
    """
    يعالج 30 أمر قفل/فتح (دفعة 1) عبر جدول _LOCK_TABLE_1.
    """

    # ── فحوصات الأهلية ──────────────────────────────────────────────────
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not await admin_pls(
        m.from_user.id, m.chat.id
    ):
        return
    if await rdb.get(f"{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.from_user.id}:mute:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}") or await rdb.get(
        f"{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}"
    ):
        return

    text = await _resolve_text(m)

    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    k = await rdb.get(f"{Dev_Zaid}:botkey")

    # ── البحث في جدول الأقفال ───────────────────────────────────────────
    match = _TEXT_MAP_1.get(text)
    if match:
        entry, is_locking = match
        _, _, redis_key, display, gender, rank_fn, perm_msg_id = entry
        return await _lock_toggle(
            m, k, redis_key, display, rank_fn,
            perm_msg_id, gender, is_locking
        )

    # لا يوجد أمر مطابق ضمن جدول هذا الملف (_LOCK_TABLE_1) — لم يُرسَل أي رد
    # فعلي للمستخدم في هذا المسار، لذا نُمرِّر المعالجة لبقية handlers
    # group=28 (راجع [C4] في all_moderation_2.py لشرح المشكلة الأصلية).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] قفل الدردشة → redis_key = "mute" (نفس مفتاح الصمت الكلي للمجموعة)
#      أي أن "قفل الدردشة" و"كتم" يتشاركان المفتاح ذاته.
#      إذا كان هناك هاندلر كتم منفصل يستخدم نفس المفتاح، فهذا تداخل مقصود.
#
# [A2] قفل التعديل (lockEdit) ≠ قفل تعديل الميديا (lockEditM):
#      مفتاحان منفصلان رغم التشابه في الاسم. lockEditM يُفعَّل أيضاً
#      في "تفعيل الحماية" لكن "تعطيل الحماية" لا يُلغيه.
#      انظر AMBIGUOUS [A3] في all_protection.py.
#
# [A3] gender="m" للفويسات/البصمات:
#      النص في الرسالة "الفويس" (مذكر) وليس "الفويسات" (جمع مؤنث).
#      هذا اختيار مقصود في الأصل — محفوظ.
#
# [A4] فتح الاشعارات → already_unlocked_f (مؤنث): "مفتوحه"
#      لكن قفل الاشعارات → chat_locked (بدون جنس): "ابشر قفلت"
#      ثم رسالة "مقفله" (already_locked_f) — مؤنث. متسق.
