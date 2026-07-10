"""


██████╗░██████╗░██████╗░
██╔══██╗╚════██╗██╔══██╗
██████╔╝░█████╔╝██║░░██║
██╔══██╗░╚═══██╗██║░░██║
██║░░██║██████╔╝██████╔╝
╚═╝░░╚═╝╚═════╝░╚═════╝░


[ = This plugin is a part from R3D Source code = ]
{"Developer":"https://t.me/yqyqy66"}

"""

"""
مُنقول من bmqa/Plugins/welcome_and_rules.py → bmqa-v2/Plugins/welcome_and_rules.py

الأوامر/المعالجات:

  [1] setWelcomeHandler (group=29، text & group) — أوامر إدارة الترحيب والقوانين:
      - وضع الترحيب | ضع الترحيب  : وضع رسالة ترحيب مخصصة (يتبعها الرسالة التالية)
      - مسح الترحيب                : مسح رسالة الترحيب المخصصة
      - الترحيب                   : عرض رسالة الترحيب الحالية
      - وضع قوانين                 : وضع قوانين مخصصة للمجموعة (يتبعها الرسالة التالية)
      - مسح القوانين               : مسح القوانين المخصصة
      - الغاء                     : إلغاء وضع الترحيب أو وضع القوانين

  [2] welcomeRespons (group=4، new_chat_members) — معالج مستقل لانضمام الأعضاء الجدد:
      يُرسل رسالة ترحيب مع صورة العضو (إن وُجدت) عند انضمام أي عضو جديد.
      يدعم متغيرات: {الاسم} {اليوزر} {المجموعه} {التاريخ} {الوقت} {القوانين}

التحويلات: sync→async، Thread→await مباشر، r.<op>→await rdb.<op>،
            c.get_chat_photos → async for، isLockCommand → await
ملاحظة: جميع نصوص الترحيب والقوانين الافتراضية محفوظة بالضبط كما هي في الأصل.
"""

import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import *
from pyrogram.types import *
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from helpers.ranks import admin_pls, mod_pls, pre_pls
from helpers.ranks import isLockCommand
from core.messages import get_message, track_sent_message

default_welcome = """لا تُسِئ اللفظ وإن ضَاق عليك الرَّد

ɴᴀᴍᴇ ⌯ {الاسم}
ᴜѕᴇʀɴᴀᴍᴇ ⌯ {اليوزر}
𝖣𝖺𝗍𝖾 ⌯ {التاريخ}"""


@register("welcome_settings")
@Client.on_message(filters.group & filters.text, group=29)
@safe_handler
async def setWelcomeHandler(c, m):
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    if await rdb.get(f"{m.chat.id}:mute:{Dev_Zaid}") and not await admin_pls(m.from_user.id, m.chat.id):
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

    text = m.text
    name = await rdb.get(f"{Dev_Zaid}:BotName") or "رعد"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "")
    if await rdb.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}"):
        text = await rdb.get(f"{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}")
    if await rdb.get(f"Custom:{Dev_Zaid}&text={text}"):
        text = await rdb.get(f"Custom:{Dev_Zaid}&text={text}")
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    if text == "الغاء" and await rdb.get(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}"):
        await rdb.delete(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}")
        sent = await m.reply(await get_message("welcome_and_rules.cancel_welcome_mode", botkey=k))
        await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.cancel_welcome_mode")
        return sent

    if text == "الغاء" and await rdb.get(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}"):
        await rdb.delete(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}")
        sent = await m.reply(await get_message("welcome_and_rules.cancel_rules_mode", botkey=k))
        await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.cancel_rules_mode")
        return sent

    if await rdb.get(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}") and await mod_pls(m.from_user.id, m.chat.id):
        await rdb.set(f"{m.chat.id}:CustomRules:{Dev_Zaid}", m.text.html)
        await rdb.delete(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}")
        sent = await m.reply(await get_message("welcome_and_rules.rules_set_success", botkey=k))
        await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.rules_set_success")
        return sent

    if await rdb.get(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}") and await mod_pls(m.from_user.id, m.chat.id):
        await rdb.set(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}", m.text.html)
        await rdb.delete(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}")
        sent = await m.reply(await get_message("welcome_and_rules.welcome_set_success", botkey=k))
        await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.welcome_set_success")
        return sent

    if text == "مسح القوانين":
        if not await mod_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(await get_message("welcome_and_rules.perm_mod", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.perm_mod")
            return sent
        else:
            await rdb.delete(f"{m.chat.id}:CustomRules:{Dev_Zaid}")
            sent = await m.reply(await get_message("welcome_and_rules.rules_cleared", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.rules_cleared")
            return sent

    if text == "وضع قوانين":
        if not await mod_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(await get_message("welcome_and_rules.perm_mod", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.perm_mod")
            return sent
        else:
            await rdb.set(f"{m.chat.id}:setRules:{m.from_user.id}{Dev_Zaid}", 1)
            sent = await m.reply(await get_message("welcome_and_rules.rules_prompt", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.rules_prompt")
            return sent

    if text == "الترحيب":
        if not await mod_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(await get_message("welcome_and_rules.perm_mod", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.perm_mod")
            return sent
        else:
            # ⚠️ default_welcome / نص الترحيب المخصص للجروب لم يُنقلا لنظام
            # core/messages.py عمداً (تعارض نطاق/ملكية — راجع core/messages.py).
            # يُعرَض النص الخام دون تنسيق كما في الأصل تماماً.
            if not await rdb.get(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}"):
                return await m.reply(f"`{default_welcome}`")
            else:
                welcome = await rdb.get(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}")
                return await m.reply(f"`{welcome}`")

    if text == "مسح الترحيب":
        if not await mod_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(await get_message("welcome_and_rules.perm_mod", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.perm_mod")
            return sent
        else:
            await rdb.delete(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}")
            sent = await m.reply(await get_message("welcome_and_rules.welcome_cleared", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.welcome_cleared")
            return sent

    if text == "وضع الترحيب" or text == "ضع الترحيب":
        if not await mod_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(await get_message("welcome_and_rules.perm_mod", botkey=k))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.perm_mod")
            return sent
        else:
            await rdb.set(f"{m.chat.id}:setWelcome:{m.from_user.id}{Dev_Zaid}", 1)
            sent = await m.reply(await get_message("welcome_and_rules.welcome_set_prompt"))
            await track_sent_message(m.chat.id, sent.id, "welcome_and_rules.welcome_set_prompt")
            return sent


@register("welcome_new_member")
@Client.on_message(filters.new_chat_members, group=4)
@safe_handler
async def welcomeRespons(c: Client, m: Message):
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    channel = await rdb.get(f"{Dev_Zaid}:BotChannel") or "eFFb0t"

    if not await rdb.get(f"{m.chat.id}:disableWelcome:{Dev_Zaid}") and m.new_chat_members:
        if not await rdb.get(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}"):
            welcome = default_welcome
        else:
            welcome = await rdb.get(f"{m.chat.id}:CustomWelcome:{Dev_Zaid}")
        for me in m.new_chat_members:
            if not me.id == int(Dev_Zaid):
                if await rdb.get(f"{m.chat.id}:enableVerify:{Dev_Zaid}") and not await pre_pls(me.id, m.chat.id):
                    return
                photo = None
                if not await rdb.get(f"{m.chat.id}:disableWelcomep:{Dev_Zaid}") and me.photo:
                    async for p in c.get_chat_photos(me.id, limit=1):
                        photo = p.file_id
                        break
                title = m.chat.title
                name = me.first_name
                if me.username:
                    username = f"@{me.username}"
                else:
                    username = f"@{channel}"
                TIME_ZONE = "Asia/Riyadh"
                ZONE = pytz.timezone(TIME_ZONE)
                TIME = datetime.now(ZONE)
                clock = TIME.strftime("%I:%M %p")
                date = TIME.strftime("%d/%m/%Y")
                if await rdb.get(f"{m.chat.id}:CustomRules:{Dev_Zaid}"):
                    rules = await rdb.get(f"{m.chat.id}:CustomRules:{Dev_Zaid}")
                else:
                    rules = """{k} ممنوع نشر الروابط 
{k} ممنوع التكلم او نشر صور اباحيه 
{k} ممنوع اعاده توجيه 
{k} ممنوع العنصرية بكل انواعها 
{k} الرجاء احترام المدراء والادمنيه"""
                w = (
                    welcome.replace("{القوانين}", rules)
                    .replace("{الاسم}", name)
                    .replace("{المجموعه}", title)
                    .replace("{الوقت}", clock)
                    .replace("{التاريخ}", date)
                    .replace("{اليوزر}", username)
                )
                if not photo:
                    return await m.reply(w, disable_web_page_preview=True)
                else:
                    return await m.reply_photo(photo, caption=w)
