"""
all_callback_settings.py — bmqa-v2
═══════════════════════════════════════════════════════════════════════════════
قائمة أزرار (Inline Buttons) لأمر "الاعدادات" — بديل لعرض النص الجامد
القديم في Plugins/all_settings.py.

الفكرة:
  - "الاعدادات" (من all_settings.py) يرسل القائمة الرئيسية: 4 تصنيفات.
  - الضغط على تصنيف → cfgcat:<key>   → يعرض أزرار القفل/الفتح لهذا التصنيف.
  - الضغط على أي قفل → cfgtoggle:<cat>:<lockKey> → يبدّل الحالة ويعيد رسم نفس
    التصنيف بالحالة الجديدة.
  - رجوع → cfgmain   |   إغلاق → cfgclose

كل قفل مخزَّن في Redis بنفس المفاتيح المستخدمة أصلاً في باقي المشروع:
    {chat_id}:{lockKey}:{Dev_Zaid}
موجود = مقفول ⇠ غائب = مفتوح (نفس منطق all_settings.py سطر 109-134).
"""

from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.callback_dispatcher import register_callback
from helpers.ranks import mod_pls

# ─── تعريف الأقفال لكل تصنيف: (مفتاح_الردis, التسمية_العربية) ──────────────

LOCK_CATEGORIES: dict[str, list[tuple[str, str]]] = {
    "media": [
        ("lockAudios", "الملفات الصوتية"),
        ("lockVideo", "الفيديو"),
        ("lockVoice", "الفويس"),
        ("lockPhoto", "الصور"),
        ("lockFiles", "الملفات"),
        ("lockAnimations", "المتحركات"),
        ("lockStickers", "الستيكرات"),
        ("lockEditM", "تعديل الميديا"),
    ],
    "content": [
        ("mute", "الدردشة"),
        ("lockInline", "الانلاين"),
        ("lockForward", "التوجيه"),
        ("lockHashtags", "الهشتاق"),
        ("lockEdit", "التعديل"),
        ("lockUrls", "الروابط"),
        ("lockBots", "البوتات"),
        ("lockTags", "اليوزرات"),
        ("lockMessages", "الكلام الكثير"),
        ("lockSHTM", "السب"),
        ("lockSpam", "التكرار"),
        ("lockChannels", "القنوات"),
    ],
    "security": [
        ("lockJoin", "الدخول"),
        ("lockPersian", "الفارسية"),
        ("lockJoinPersian", "دخول الإيراني"),
        ("lockNSFW", "الإباحي"),
    ],
    "other": [
        ("lockNot", "الاشعارات"),
        ("lockaddContacts", "الاضافة"),
    ],
}

CATEGORY_TITLES: dict[str, str] = {
    "media": "الوسائط",
    "content": "المحتوى",
    "security": "الدخول والحماية",
    "other": "أخرى",
}

_DENY_MSG = "هذا الزر يخص ( المدير وفوق ) بس"


# ─── بناء اللوحات ────────────────────────────────────────────────────────

def build_main_menu() -> InlineKeyboardMarkup:
    """القائمة الرئيسية: زر لكل تصنيف + إغلاق."""
    rows = []
    keys = list(CATEGORY_TITLES.items())
    for i in range(0, len(keys), 2):
        row = [
            InlineKeyboardButton(title, callback_data=f"cfgcat:{key}")
            for key, title in keys[i:i + 2]
        ]
        rows.append(row)
    rows.append([InlineKeyboardButton("✖️ إغلاق", callback_data="cfgclose")])
    return InlineKeyboardMarkup(rows)


async def build_category_menu(cid: int, cat: str) -> InlineKeyboardMarkup:
    """أزرار القفل/الفتح لتصنيف معيّن، بحسب حالتها الحالية في Redis."""
    rows = []
    locks = LOCK_CATEGORIES[cat]
    for i in range(0, len(locks), 2):
        row = []
        for lock_key, label in locks[i:i + 2]:
            locked = bool(await rdb.get(f"{cid}:{lock_key}:{Dev_Zaid}"))
            icon = "❌" if locked else "✅"
            row.append(
                InlineKeyboardButton(
                    f"{icon} {label}",
                    callback_data=f"cfgtoggle:{cat}:{lock_key}",
                )
            )
        rows.append(row)
    rows.append([InlineKeyboardButton("‹ رجوع", callback_data="cfgmain")])
    return InlineKeyboardMarkup(rows)


MAIN_MENU_TEXT = "اعدادات المجموعة :\n\nاختر تصنيف الإعدادات اللي تبي تتحكم فيه 👇"


def category_text(cat: str) -> str:
    return f"إعدادات ( {CATEGORY_TITLES[cat]} ) :\n\n✅ = مفتوح   ⁄   ❌ = مقفول\nاضغط على أي زر عشان تبدّل حالته."


# ─── المعالجات ───────────────────────────────────────────────────────────

@register_callback("cfgmain")
@safe_handler
async def _cfg_main(c, m) -> None:
    if not await mod_pls(m.from_user.id, m.message.chat.id):
        return await m.answer(_DENY_MSG, show_alert=True)
    await m.edit_message_text(MAIN_MENU_TEXT, reply_markup=build_main_menu())


@register_callback("cfgcat:")
@safe_handler
async def _cfg_cat(c, m) -> None:
    if not await mod_pls(m.from_user.id, m.message.chat.id):
        return await m.answer(_DENY_MSG, show_alert=True)
    cat = m.data.split(":", 1)[1]
    if cat not in LOCK_CATEGORIES:
        return
    cid = m.message.chat.id
    await m.edit_message_text(category_text(cat), reply_markup=await build_category_menu(cid, cat))


@register_callback("cfgtoggle:")
@safe_handler
async def _cfg_toggle(c, m) -> None:
    if not await mod_pls(m.from_user.id, m.message.chat.id):
        return await m.answer(_DENY_MSG, show_alert=True)

    _, cat, lock_key = m.data.split(":", 2)
    if cat not in LOCK_CATEGORIES:
        return

    cid = m.message.chat.id
    redis_key = f"{cid}:{lock_key}:{Dev_Zaid}"
    currently_locked = bool(await rdb.get(redis_key))

    if currently_locked:
        await rdb.delete(redis_key)
        toast = "تم الفتح ✅"
    else:
        await rdb.set(redis_key, 1)
        toast = "تم القفل ❌"

    await m.edit_message_text(category_text(cat), reply_markup=await build_category_menu(cid, cat))
    await m.answer(toast)


@register_callback("cfgclose")
@safe_handler
async def _cfg_close(c, m) -> None:
    if not await mod_pls(m.from_user.id, m.message.chat.id):
        return await m.answer(_DENY_MSG, show_alert=True)
    await m.edit_message_text("تم إغلاق قائمة الإعدادات ✅")
