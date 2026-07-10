"""
all_locks_2.py
منقول من bmqa/Plugins/all.py (guardCommands — سطر 2408 → 2648)
الفئة: الأقفال التفصيلية — دفعة 2 (11 زوج قفل/فتح = 22 أمر)

تستورد _lock_toggle من all_locks_1.py — دالة واحدة تخدم كلا الملفين.

ملاحظة هامة:
  قفل الكفر / قفل الشيعه / قفل الشيعة (سطر 2408-2427) داخل triple-quoted
  string (معطَّل بالكامل في الأصل) — لم يُنقَل ولم يُفعَّل. [A1]

التحويلات:
  r.get/set/delete → await rdb.*
  m.reply(...)     → await m.reply(...)
  return False     → return
"""

from pyrogram import Client, ContinuePropagation, filters

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message, track_sent_message
from helpers.ranks import admin_pls, mod_pls, owner_pls, isLockCommand
from Plugins.all_locks_1 import _lock_toggle, _resolve_text


# ══════════════════════════════════════════════════════════════════════════════
# جدول الأقفال — دفعة 2 (سطر 2429-2648)
#
# الحقول: (texts_lock, texts_unlock, redis_key, display, gender, rank_fn, perm_msg_id)
#   ⚠️ قفل الإباحي: rank_fn = owner_pls (ليس mod_pls!) [A2]
#   ⚠️ فتح الإباحي: رسالة "مفتوح من قبل" بخطأ إملائي أصلي — معالَج خارج الجدول [A3]
# ══════════════════════════════════════════════════════════════════════════════

_LOCK_TABLE_2 = [
    # ── زوج 1: الإباحي (سطر 2429-2447) — owner_pls — مذكر ───────────────
    # ⚠️ فتح الإباحي معالَج خارج الجدول أدناه بسبب الخطأ الإملائي [A3]
    (
        ("قفل الإباحي", "قفل الاباحي"),
        ("فتح الإباحي", "فتح الاباحي"),
        "lockNSFW", "الإباحي", "m", owner_pls, "locks.perm_owner",
    ),
    # ── زوج 2: الكلام الكثير/الكلايش (سطر 2449-2467) — مذكر ─────────────
    (
        ("قفل الكلام الكثير", "قفل الكلايش"),
        ("فتح الكلام الكثير", "فتح الكلايش"),
        "lockMessages", "الكلام الكثير", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 3: التكرار (سطر 2469-2487) — مذكر ───────────────────────────
    (
        ("قفل التكرار",),
        ("فتح التكرار",),
        "lockSpam", "التكرار", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 4: التوجيه (سطر 2489-2507) — مذكر ───────────────────────────
    (
        ("قفل التوجيه",),
        ("فتح التوجيه",),
        "lockForward", "التوجيه", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 5: الانلاين (سطر 2509-2527) — مذكر ──────────────────────────
    (
        ("قفل الانلاين",),
        ("فتح الانلاين",),
        "lockInline", "الانلاين", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 6: السب (سطر 2529-2547) — مذكر ──────────────────────────────
    (
        ("قفل السب",),
        ("فتح السب",),
        "lockSHTM", "السب", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 7: الاضافه/الجهات (سطر 2549-2567) — مؤنث ────────────────────
    (
        ("قفل الاضافه", "قفل الاضافة", "قفل الجهات"),
        ("فتح الاضافه", "فتح الاضافة", "فتح الجهات"),
        "lockaddContacts", "الاضافه", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 8: دخول البوتات/الوهمي/الايراني (سطر 2569-2587) — مؤنث ───────
    (
        ("قفل دخول البوتات", "قفل الوهمي", "قفل الايراني"),
        ("فتح دخول البوتات", "فتح الوهمي", "فتح الايراني"),
        "lockJoinPersian", "دخول البوتات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 9: الصوت (سطر 2589-2607) — مذكر ─────────────────────────────
    (
        ("قفل الصوت",),
        ("فتح الصوت",),
        "lockAudios", "الصوت", "m", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 10: القنوات (سطر 2609-2627) — مؤنث ──────────────────────────
    (
        ("قفل القنوات",),
        ("فتح القنوات",),
        "lockChannels", "القنوات", "f", mod_pls, "locks.perm_mod",
    ),
    # ── زوج 11: الدخول (سطر 2629-2647) — مذكر ───────────────────────────
    (
        ("قفل الدخول",),
        ("فتح الدخول",),
        "lockJoin", "الدخول", "m", mod_pls, "locks.perm_mod",
    ),
]

# فهرس سريع: text → (entry, is_locking)
_TEXT_MAP_2: dict = {}
for _entry in _LOCK_TABLE_2:
    _ltexts, _utexts, _key, _disp, _g, _rank, _perm = _entry
    for _t in _ltexts:
        _TEXT_MAP_2[_t] = (_entry, True)
    for _t in _utexts:
        _TEXT_MAP_2[_t] = (_entry, False)

# ── معالجة خاصة لخطأ "فتح الإباحي" الإملائي [A3] ──────────────────────────
# الأصل (سطر 2444): Openn.format(k, mention, k, "aalإباحي") — ألف مكررة
# محفوظ عبر locks.nsfw_already_unlocked في core/messages.py
# (الخطأ مُدمَج داخل القالب — لا تُصحَّح هذه الكلمة)
_NSFW_OPEN_TYPO_MSG_ID = "locks.nsfw_already_unlocked"


# ══════════════════════════════════════════════════════════════════════════════
# الهاندلر الرئيسي — group=28
# ══════════════════════════════════════════════════════════════════════════════

@register("locks_2_commands")
@Client.on_message(filters.group & filters.text, group=28)
@safe_handler
async def locks2Handler(c, m) -> None:
    """
    يعالج 22 أمر قفل/فتح (دفعة 2) عبر جدول _LOCK_TABLE_2.
    يستورد _lock_toggle من all_locks_1.
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

    k       = await rdb.get(f"{Dev_Zaid}:botkey")
    cid     = m.chat.id
    mention = m.from_user.mention

    # ── حالة خاصة: فتح الإباحي — رسالة "مفتوح من قبل" بها خطأ إملائي [A3]
    # هذه الحالة تُعالَج خارج _lock_toggle لأن الخطأ الإملائي في "من قبل" مُدمَج
    # في قالب locks.nsfw_already_unlocked ولا يمكن تمريره كـ feature للـ _lock_toggle.
    if text in ("فتح الإباحي", "فتح الاباحي"):
        if not await owner_pls(m.from_user.id, cid):
            perm_text = await get_message("locks.nsfw_open_perm", botkey=k)
            sent = await m.reply(perm_text)
            await track_sent_message(cid, sent.id, "locks.nsfw_open_perm")
            return
        state = await rdb.get(f"{cid}:lockNSFW:{Dev_Zaid}")
        if not state:
            # الأصل سطر 2444: "aalإباحي" — ألف إضافية (محفوظ في القالب)
            already_text = await get_message(
                _NSFW_OPEN_TYPO_MSG_ID, botkey=k, mention=mention
            )
            sent = await m.reply(already_text)
            await track_sent_message(cid, sent.id, _NSFW_OPEN_TYPO_MSG_ID)
            return
        await rdb.delete(f"{cid}:lockNSFW:{Dev_Zaid}")
        open_text = await get_message("locks.nsfw_unlocked", botkey=k, mention=mention)
        sent = await m.reply(open_text)
        await track_sent_message(cid, sent.id, "locks.nsfw_unlocked")
        return

    # ── البحث في جدول الأقفال (كل الأوامر الأخرى) ──────────────────────
    match = _TEXT_MAP_2.get(text)
    if match:
        entry, is_locking = match
        _, _, redis_key, display, gender, rank_fn, perm_msg_id = entry
        # قفل الإباحي (is_locking=True) يمر من هنا — _lock_toggle يتعامل معه
        return await _lock_toggle(
            m, k, redis_key, display, rank_fn,
            perm_msg_id, gender, is_locking
        )

    # لا يوجد أمر مطابق ضمن جدول هذا الملف (_LOCK_TABLE_2 ولا حالة الإباحي
    # الخاصة أعلاه) — لم يُرسَل أي رد فعلي للمستخدم في هذا المسار، لذا
    # نُمرِّر المعالجة لبقية handlers group=28 (راجع [C4] في all_moderation_2.py).
    raise ContinuePropagation()


# ══════════════════════════════════════════════════════════════════════════════
# AMBIGUOUS — سلوكيات غامضة
# ══════════════════════════════════════════════════════════════════════════════
#
# [A1] قفل الكفر / قفل الشيعه / قفل الشيعة (سطر 2408-2427):
#      الكود داخل triple-quoted string `"""..."""` في الأصل — معطَّل تماماً.
#      المفتاح: lockKFR، الصلاحية: admin_pls (وليس mod_pls).
#      لم يُنقَل لأنه ليس كوداً فعلياً في الأصل.
#      إن أردت تفعيله:
#        entry = (("قفل الكفر","قفل الشيعه","قفل الشيعة"),
#                 ("فتح الكفر","فتح الشيعه","فتح الشيعة"),
#                 "lockKFR","الكفر","f", admin_pls, "locks.perm_mod")
#        أضفه لـ _LOCK_TABLE_2.
#
# [A2] قفل الإباحي — صلاحية owner_pls (المالك):
#      الأصل سطر 2430-2441 يستخدم owner_pls وليس mod_pls.
#      هذا الوحيد في الدفعتين الذي يتطلب مالك المجموعة.
#
# [A3] فتح الإباحي — خطأ إملائي في رسالة "مفتوح من قبل":
#      الأصل سطر 2444: Openn.format(k, mention, k, "aalإباحي")
#      النص الظاهر للمستخدم: "{k} ا الإباحي مفتوح من قبل" ← ألف مكررة.
#      محفوظ في locks.nsfw_already_unlocked (core/messages.py) بالنص الأصلي.
#      إن أردت التصحيح: غيّر القالب في core/messages.py — لا تعديل هنا.
#
# [A4] قفل الاضافه / قفل الجهات — المفتاح "lockaddContacts":
#      اسم المفتاح به camelCase غير منتظم (lowercase "add").
#      محفوظ لمطابقة الأصل وعدم كسر بيانات Redis الموجودة.
#
# [A5] قفل دخول البوتات / قفل الايراني — المفتاح "lockJoinPersian":
#      مختلف عن "lockPersian" (قفل الفارسيه) — مفتاحان منفصلان لهدفين مختلفين:
#      - lockPersian: يمنع النصوص الفارسية
#      - lockJoinPersian: يمنع دخول حسابات إيرانية/وهمية
