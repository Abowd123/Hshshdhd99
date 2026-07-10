'''


██████╗░██████╗░██████╗░
██╔══██╗╚════██╗██╔══██╗
██████╔╝░█████╔╝██║░░██║
██╔══██╗░╚═══██╗██║░░██║
██║░░██║██████╔╝██████╔╝
╚═╝░░╚═╝╚═════╝░╚═════╝░


[ = This plugin is a part from R3D Source code = ]
{"Developer":"https://t.me/yqyqy66"}

'''

"""
مُنقول من bmqa/Plugins/customFilter.py → bmqa-v2/Plugins/custom_filter.py

═══════════════════════════════════════════════════════════════════
الهاندلرز (3):

group=21 — addCustomReplyDone  (filters.group)
  يستقبل الردّ الفعلي (نص/صورة/فيديو/…) لفلتر محلي جارٍ إضافته.
  يُشغّل عند وجود حالة {cid}:addFilter2:{uid}{Dev_Zaid} في Redis.
  ← pipeline: set×3 + sadd + delete في رحلة شبكة واحدة.

group=22 — addCustomReply  (filters.text & filters.group)
  إدارة الفلاتر المحلية وردود الأعضاء:
    • اضف رد / مسح رد / الرد [كلمة]
    • تعطيل الردود / تفعيل الردود
    • تعطيل ردود الاعضاء / تفعيل ردود الاعضاء
    • الردود / مسح الردود
    • ردود الاعضاء / مسح ردود الاعضاء
    • اضف ردي / مسح ردي

group=23 — addCustomReplyRandom  (filters.group & filters.text)
  فلاتر الردود المتعددة المحلية:
    • اضف رد مميز / مسح رد مميز
    • الردود المميزه / مسح الردود المميزه

═══════════════════════════════════════════════════════════════════
تحليل التداخل/التعارض مع global_filters.py:

✅ لا تعارض في أسماء الأوامر:
  local        ↔  global
  ─────────────────────────────────────────────
  اضف رد      ↔  اضف رد عام
  مسح رد      ↔  مسح رد عام
  الردود       ↔  الردود العامه
  اضف رد مميز ↔  اضف رد متعدد عام
  مسح رد مميز ↔  مسح رد متعدد عام
  الردود المميزه ↔ الردود المتعدده العامه

✅ لا تصادم في مفاتيح Redis:
  local:  {text}:filter:{Dev_Zaid}{cid}       (cid مُضمَّن بالنهاية)
  global: {text}:filter:{Dev_Zaid}            (بدون cid)
  → سلاسل مختلفة، لا تداخل.

⚠ مفاتيح حالة (state) متشابهة الشكل لكن بلاحقات مختلفة:
  local:  addFilter / addFilter2 / delFilter / addFilterR / addFilterR2 / delFilterR
  global: addFilterG / addFilter2GG / delFilterG / addFilterRG / addFilterRG2 / delFilterRG
  → بلاحقات مميزة، لا تصادم.

═══════════════════════════════════════════════════════════════════
التحويلات:
  - Thread → await مباشر
  - r.<op> → await rdb.<op>
  - c.get_users (sync) → await c.get_users
  - حفظ الفلتر (5 عمليات متتالية) → async with rdb.pipeline()
  - helpers.Ranks → helpers.ranks (حروف صغيرة)
  - @register + @safe_handler مُضافان
  - import محدّد بدل wildcard
"""

import logging
import pytz
from datetime import datetime
from pyrogram import Client, filters
from pyrogram.enums import ParseMode
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message, track_sent_message
from helpers.ranks import admin_pls, mod_pls, isLockCommand


# ─── دالة مساعدة مشتركة ────────────────────────────────────────────────────

async def _resolve_text(m):
    """يحوّل نص الرسالة بعد استبدال اسم البوت والأوامر المخصصة."""
    text = m.text or ''
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    return text


def _now_ksa() -> str:
    """التاريخ والوقت الحالي بتوقيت الرياض."""
    tz = pytz.timezone('Asia/Riyadh')
    return datetime.now(tz).strftime('%d/%m/%Y %I:%M:%S %p')


async def _save_local_filter(text: str, cid: int, payload: str, ftype: str, by: int, date: str, uid: int):
    """يحفظ فلتراً محلياً في Redis بـ pipeline واحدة (5 عمليات)."""
    state_key = f'{cid}:addFilter2:{uid}{Dev_Zaid}'
    async with rdb.pipeline(transaction=False) as pipe:
        pipe.set(f'{text}:filter:{Dev_Zaid}{cid}', payload)
        pipe.set(f'{text}:filtertype:{cid}{Dev_Zaid}', ftype)
        pipe.set(f'{text}:filterInfo:{cid}{Dev_Zaid}', f'by={by}&date={date}')
        pipe.sadd(f'{cid}:FiltersList:{Dev_Zaid}', text)
        pipe.delete(state_key)
        await pipe.execute()


# ═══════════════════════════════════════════════════════════════════════════
# group=21 — يستقبل الردّ الفعلي (نص/وسائط) لفلتر محلي جارٍ إضافته
# ═══════════════════════════════════════════════════════════════════════════

@register("custom_filter_receive")
@Client.on_message(filters.group, group=21)
@safe_handler
async def addCustomReplyDone(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return

    uid = m.from_user.id
    cid = m.chat.id
    state_key = f'{cid}:addFilter2:{uid}{Dev_Zaid}'
    date = _now_ksa()

    # ─── إلغاء عبر نص ──────────────────────────────────────────────────────
    if m.text:
        if m.text == 'الغاء' and await rdb.get(state_key):
            await rdb.delete(state_key)
            sent = await m.reply(await get_message('custom_filter.cancel_add_reply', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.cancel_add_reply')
            return

        if await rdb.get(state_key) and await mod_pls(uid, cid):
            text = await rdb.get(state_key)
            payload = f'type=text&text={m.text.html}'
            await _save_local_filter(text, cid, payload, 'نص', uid, date, uid)
            sent = await m.reply(
                await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
                parse_mode=ParseMode.HTML,
            )
            await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
            return

    # ─── صورة ──────────────────────────────────────────────────────────────
    if m.photo and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=photo&photo={m.photo.file_id}&caption={caption}'
        await _save_local_filter(text, cid, payload, 'صوره', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
        return

    # ─── فيديو ─────────────────────────────────────────────────────────────
    if m.video and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=video&video={m.video.file_id}&caption={caption}'
        await _save_local_filter(text, cid, payload, 'فيديو', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
        return

    # ─── متحركة ────────────────────────────────────────────────────────────
    if m.animation and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=animation&animation={m.animation.file_id}&caption={caption}'
        await _save_local_filter(text, cid, payload, 'متحركه', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
        return

    # ─── صوت (audio) ───────────────────────────────────────────────────────
    if m.audio and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=audio&audio={m.audio.file_id}&caption={caption}'
        await _save_local_filter(text, cid, payload, 'صوت', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
        return

    # ─── بصمة (voice) ──────────────────────────────────────────────────────
    if m.voice and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=voice&voice={m.voice.file_id}&caption={caption}'
        await _save_local_filter(text, cid, payload, 'بصمه', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
        return

    # ─── ملف (document) ────────────────────────────────────────────────────
    if m.document and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        caption = m.caption.html if m.caption else 'None'
        payload = f'type=doc&doc={m.document.file_id}&caption={caption}'
        await _save_local_filter(text, cid, payload, 'ملف', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')
        return

    # ─── ستيكر ─────────────────────────────────────────────────────────────
    if m.sticker and await rdb.get(state_key) and await mod_pls(uid, cid):
        text = await rdb.get(state_key)
        payload = f'type=sticker&sticker={m.sticker.file_id}'
        await _save_local_filter(text, cid, payload, 'ستيكر', uid, date, uid)
        sent = await m.reply(
            await get_message('custom_filter.reply_added', botkey=k, filter_name=text),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_added')


# ═══════════════════════════════════════════════════════════════════════════
# group=22 — إدارة الفلاتر المحلية وردود الأعضاء
# ═══════════════════════════════════════════════════════════════════════════

@register("custom_filter_manage")
@Client.on_message(filters.text & filters.group, group=22)
@safe_handler
async def addCustomReply(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return

    text = await _resolve_text(m)
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    uid = m.from_user.id
    cid = m.chat.id

    # ─── إلغاء حالات الإضافة/الحذف الجارية ────────────────────────────────
    if await rdb.get(f'{cid}:addFilter:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:addFilter:{uid}{Dev_Zaid}')
        sent = await m.reply(await get_message('custom_filter.cancel_add_reply', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.cancel_add_reply')
        return

    if await rdb.get(f'{cid}:delFilter:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:delFilter:{uid}{Dev_Zaid}')
        sent = await m.reply(await get_message('custom_filter.cancel_del_reply', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.cancel_del_reply')
        return

    # ─── تنفيذ حذف فلتر (بعد إرسال اسمه) ─────────────────────────────────
    if await rdb.get(f'{cid}:delFilter:{uid}{Dev_Zaid}') and await mod_pls(uid, cid):
        if not await rdb.get(f'{m.text}:filterInfo:{cid}{Dev_Zaid}'):
            await rdb.delete(f'{cid}:delFilter:{uid}{Dev_Zaid}')
            sent = await m.reply(await get_message('custom_filter.not_in_list', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.not_in_list')
            return
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{m.text}:filter:{Dev_Zaid}{cid}')
            pipe.delete(f'{m.text}:filtertype:{cid}{Dev_Zaid}')
            pipe.delete(f'{m.text}:filterInfo:{cid}{Dev_Zaid}')
            pipe.srem(f'{cid}:FiltersList:{Dev_Zaid}', m.text)
            pipe.delete(f'{cid}:delFilter:{uid}{Dev_Zaid}')
            await pipe.execute()
        sent = await m.reply(await get_message('custom_filter.reply_deleted', botkey=k, filter_name=m.text))
        await track_sent_message(cid, sent.id, 'custom_filter.reply_deleted')
        return

    # ─── تنفيذ انتقال: أرسل كلمة الفلتر → انتظر ردّ الوسائط (group=21) ───
    if await rdb.get(f'{cid}:addFilter:{uid}{Dev_Zaid}') and await mod_pls(uid, cid):
        await rdb.set(f'{cid}:addFilter2:{uid}{Dev_Zaid}', m.text)
        await rdb.delete(f'{cid}:addFilter:{uid}{Dev_Zaid}')
        sent = await m.reply(
            await get_message('custom_filter.prompt_reply_content', botkey=k),
            parse_mode=ParseMode.MARKDOWN,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.prompt_reply_content')
        return

    # ─── الرد [كلمة] — عرض معلومات فلتر محدد ──────────────────────────────
    if text.startswith('الرد ') and len(m.text.split()) > 1 and await mod_pls(uid, cid):
        reply = m.text.split(None, 1)[1]
        info = await rdb.get(f'{reply}:filterInfo:{cid}{Dev_Zaid}')
        if not info:
            sent = await m.reply(await get_message('custom_filter.not_in_list', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.not_in_list')
            return
        by = info.split('by=')[1].split('&date=')[0]
        date = info.split('&date=')[1]
        ftype = await rdb.get(f'{reply}:filtertype:{cid}{Dev_Zaid}')
        sent = await m.reply(
            await get_message(
                'custom_filter.reply_info',
                botkey=k,
                filter_name=reply,
                by_id=by,
                date=date,
                filter_type=ftype,
            )
        )
        await track_sent_message(cid, sent.id, 'custom_filter.reply_info')
        return

    # ─── تعطيل/تفعيل الردود المحلية ────────────────────────────────────────
    if text == 'تعطيل الردود':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        if await rdb.get(f'{cid}:lock_filter:{Dev_Zaid}'):
            sent = await m.reply(
                await get_message('custom_filter.replies_disabled_already', botkey=k, mention=m.from_user.mention),
                parse_mode=ParseMode.HTML,
            )
            await track_sent_message(cid, sent.id, 'custom_filter.replies_disabled_already')
            return
        await rdb.set(f'{cid}:lock_filter:{Dev_Zaid}', 1)
        sent = await m.reply(
            await get_message('custom_filter.replies_disabled_success', botkey=k, mention=m.from_user.mention),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.replies_disabled_success')
        return

    if text == 'تفعيل الردود':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        if not await rdb.get(f'{cid}:lock_filter:{Dev_Zaid}'):
            sent = await m.reply(
                await get_message('custom_filter.replies_enabled_already', botkey=k, mention=m.from_user.mention),
                parse_mode=ParseMode.HTML,
            )
            await track_sent_message(cid, sent.id, 'custom_filter.replies_enabled_already')
            return
        await rdb.delete(f'{cid}:lock_filter:{Dev_Zaid}')
        sent = await m.reply(
            await get_message('custom_filter.replies_enabled_success', botkey=k, mention=m.from_user.mention),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.replies_enabled_success')
        return

    # ─── تعطيل/تفعيل ردود الأعضاء ─────────────────────────────────────────
    if text == 'تعطيل ردود الاعضاء':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        if await rdb.get(f'{cid}:lock_filterMEM:{Dev_Zaid}'):
            sent = await m.reply(
                await get_message('custom_filter.member_replies_disabled_already', botkey=k, mention=m.from_user.mention),
                parse_mode=ParseMode.HTML,
            )
            await track_sent_message(cid, sent.id, 'custom_filter.member_replies_disabled_already')
            return
        await rdb.set(f'{cid}:lock_filterMEM:{Dev_Zaid}', 1)
        sent = await m.reply(
            await get_message('custom_filter.member_replies_disabled_success', botkey=k, mention=m.from_user.mention),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.member_replies_disabled_success')
        return

    if text == 'تفعيل ردود الاعضاء':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        if not await rdb.get(f'{cid}:lock_filterMEM:{Dev_Zaid}'):
            sent = await m.reply(
                await get_message('custom_filter.member_replies_enabled_already', botkey=k, mention=m.from_user.mention),
                parse_mode=ParseMode.HTML,
            )
            await track_sent_message(cid, sent.id, 'custom_filter.member_replies_enabled_already')
            return
        await rdb.delete(f'{cid}:lock_filterMEM:{Dev_Zaid}')
        sent = await m.reply(
            await get_message('custom_filter.member_replies_enabled_success', botkey=k, mention=m.from_user.mention),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.member_replies_enabled_success')
        return

    # ─── ردود الاعضاء — قائمة ──────────────────────────────────────────────
    if text == 'ردود الاعضاء':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        members = await rdb.smembers(f'{cid}:FiltersListMEM:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('custom_filter.no_member_replies', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_member_replies')
            return
        lines = 'ردود الاعضاء:\n'
        count = 1
        for entry in members:
            rep = entry.split('&&&&')[0]
            owner_id = entry.split('&&&&')[1]
            try:
                user = await c.get_users(int(owner_id))
                mention = user.mention
            except Exception as e:
                logging.exception(e)
                mention = f'<a href="tg://user?id={owner_id}">{owner_id}</a>'
            lines += f'\n{count} - ( {rep} ) ࿓ ( {mention} )'
            count += 1
        lines += '\n☆'
        return await m.reply(lines, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

    # ─── مسح ردود الاعضاء ──────────────────────────────────────────────────
    if text == 'مسح ردود الاعضاء':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        members = await rdb.smembers(f'{cid}:FiltersListMEM:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('custom_filter.no_member_replies', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_member_replies')
            return
        total = 0
        for entry in list(members):
            owner_id = entry.split('&&&&')[1]
            await rdb.delete(f'{entry}:filterMEM:{Dev_Zaid}{cid}')
            await rdb.srem(f'{cid}:FiltersListMEM:{Dev_Zaid}', entry)
            await rdb.delete(f'{owner_id}:FILT:{cid}{Dev_Zaid}')
            total += 1
        sent = await m.reply(await get_message('custom_filter.clear_member_replies_success', botkey=k, count=total))
        await track_sent_message(cid, sent.id, 'custom_filter.clear_member_replies_success')
        return

    # ─── الردود — قائمة الفلاتر المحلية ───────────────────────────────────
    if text == 'الردود':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        filters_list = await rdb.smembers(f'{cid}:FiltersList:{Dev_Zaid}')
        if not filters_list:
            sent = await m.reply(await get_message('custom_filter.no_replies', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_replies')
            return
        lines = 'ردود المجموعه:\n'
        count = 1
        for rep in filters_list:
            ftype = await rdb.get(f'{rep}:filtertype:{cid}{Dev_Zaid}')
            lines += f'\n{count} - ( {rep} ) ࿓ ( {ftype} )'
            count += 1
        lines += '\n☆'
        return await m.reply(lines, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

    # ─── مسح الردود — حذف كل الفلاتر المحلية ──────────────────────────────
    if text == 'مسح الردود':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        filters_list = await rdb.smembers(f'{cid}:FiltersList:{Dev_Zaid}')
        if not filters_list:
            sent = await m.reply(await get_message('custom_filter.no_replies', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_replies')
            return
        total = 0
        for rep in list(filters_list):
            async with rdb.pipeline(transaction=False) as pipe:
                pipe.delete(f'{rep}:filter:{Dev_Zaid}{cid}')
                pipe.delete(f'{rep}:filtertype:{cid}{Dev_Zaid}')
                pipe.delete(f'{rep}:filterInfo:{cid}{Dev_Zaid}')
                pipe.srem(f'{cid}:FiltersList:{Dev_Zaid}', rep)
                await pipe.execute()
            total += 1
        sent = await m.reply(await get_message('custom_filter.clear_replies_success', botkey=k, count=total))
        await track_sent_message(cid, sent.id, 'custom_filter.clear_replies_success')
        return

    # ─── اضف ردي — عضو يضيف ردّه الخاص ────────────────────────────────────
    if text == 'اضف ردي':
        if await rdb.get(f'{cid}:lock_filterMEM:{Dev_Zaid}'):
            sent = await m.reply(await get_message('custom_filter.member_reply_disabled_error', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.member_reply_disabled_error')
            return
        existing = await rdb.get(f'{uid}:FILT:{cid}{Dev_Zaid}')
        if existing:
            sent = await m.reply(await get_message('custom_filter.member_reply_already_added', botkey=k, filter_name=existing))
            await track_sent_message(cid, sent.id, 'custom_filter.member_reply_already_added')
            return
        await rdb.set(f'{cid}:addFilterMM:{uid}{Dev_Zaid}', 1, ex=600)
        sent = await m.reply(await get_message('custom_filter.prompt_member_name', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.prompt_member_name')
        return

    if await rdb.get(f'{cid}:addFilterMM:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:addFilterMM:{uid}{Dev_Zaid}')
        sent = await m.reply(await get_message('custom_filter.cancel_member_add', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.cancel_member_add')
        return

    if await rdb.get(f'{cid}:addFilterMM:{uid}{Dev_Zaid}') and len(m.text) <= 50:
        name_val = m.text
        if await rdb.sismember(f'{cid}:FiltersListMEM:{Dev_Zaid}', name_val):
            sent = await m.reply(await get_message('custom_filter.name_reserved', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.name_reserved')
            return
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.sadd(f'{cid}:FiltersListMEM:{Dev_Zaid}', f'{name_val}&&&&{uid}')
            pipe.sadd(f'{cid}:FiltersListMEMM:{Dev_Zaid}', uid)
            pipe.set(f'{name_val}:filterMEM:{Dev_Zaid}{cid}', uid)
            pipe.set(f'{uid}:FILT:{cid}{Dev_Zaid}', name_val)
            pipe.delete(f'{cid}:addFilterMM:{uid}{Dev_Zaid}')
            await pipe.execute()
        sent = await m.reply(await get_message('custom_filter.member_reply_added', botkey=k, filter_name=name_val))
        await track_sent_message(cid, sent.id, 'custom_filter.member_reply_added')
        return

    # ─── مسح ردي ───────────────────────────────────────────────────────────
    if text == 'مسح ردي':
        rep = await rdb.get(f'{uid}:FILT:{cid}{Dev_Zaid}')
        if not rep:
            sent = await m.reply(await get_message('custom_filter.no_own_reply', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_own_reply')
            return
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{rep}:filterMEM:{Dev_Zaid}{cid}')
            pipe.srem(f'{cid}:FiltersListMEM:{Dev_Zaid}', f'{rep}&&&&{uid}')
            pipe.delete(f'{uid}:FILT:{cid}{Dev_Zaid}')
            await pipe.execute()
        sent = await m.reply(await get_message('custom_filter.own_reply_deleted', botkey=k, filter_name=rep))
        await track_sent_message(cid, sent.id, 'custom_filter.own_reply_deleted')
        return

    # ─── اضف رد (يبدأ جلسة الإضافة) ───────────────────────────────────────
    if text == 'اضف رد':
        if not await rdb.get(f'{cid}:addFilter:{uid}{Dev_Zaid}'):
            if not await mod_pls(uid, cid):
                sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
                await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
                return
            await rdb.set(f'{cid}:addFilter:{uid}{Dev_Zaid}', 1)
            sent = await m.reply(await get_message('custom_filter.prompt_add_reply_word', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.prompt_add_reply_word')
            return

    # ─── مسح رد (يبدأ جلسة الحذف) ─────────────────────────────────────────
    if text == 'مسح رد':
        if not await rdb.get(f'{cid}:delFilter:{uid}{Dev_Zaid}'):
            if not await mod_pls(uid, cid):
                sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
                await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
                return
            await rdb.set(f'{cid}:delFilter:{uid}{Dev_Zaid}', 1)
            sent = await m.reply(
                await get_message('custom_filter.prompt_del_reply', botkey=k),
                parse_mode=ParseMode.MARKDOWN,
            )
            await track_sent_message(cid, sent.id, 'custom_filter.prompt_del_reply')
            return


# ═══════════════════════════════════════════════════════════════════════════
# group=23 — فلاتر الردود المتعددة (عشوائية) المحلية
# ═══════════════════════════════════════════════════════════════════════════

@register("custom_filter_random")
@Client.on_message(filters.group & filters.text, group=23)
@safe_handler
async def addCustomReplyRandom(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return

    text = await _resolve_text(m)
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    uid = m.from_user.id
    cid = m.chat.id

    # ─── إلغاء جلسات الردود المتعددة ───────────────────────────────────────
    if await rdb.get(f'{cid}:addFilterR:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:addFilterR:{uid}{Dev_Zaid}')
        sent = await m.reply(await get_message('custom_filter.cancel_add_random', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.cancel_add_random')
        return

    if await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}') and text == 'الغاء':
        rep = await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}')
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{cid}:addFilterR2:{uid}{Dev_Zaid}')
            pipe.delete(f'{rep}:randomfilter:{cid}{Dev_Zaid}')
            await pipe.execute()
        sent = await m.reply(await get_message('custom_filter.cancel_add_random_step2', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.cancel_add_random_step2')
        return

    if await rdb.get(f'{cid}:delFilterR:{uid}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{cid}:delFilterR:{uid}{Dev_Zaid}')
        sent = await m.reply(await get_message('custom_filter.cancel_del_random', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.cancel_del_random')
        return

    # ─── تم — حفظ الرد المتعدد وإنهاء التجميع ─────────────────────────────
    if await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}') and text == 'تم':
        filter_name = await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}')
        count = len(await rdb.smembers(f'{filter_name}:randomfilter:{cid}{Dev_Zaid}'))
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.set(f'{filter_name}:randomFilter:{cid}{Dev_Zaid}', 1)
            pipe.sadd(f'{cid}:RFiltersList:{Dev_Zaid}', filter_name)
            pipe.delete(f'{cid}:addFilterR2:{uid}{Dev_Zaid}')
            await pipe.execute()
        sent = await m.reply(
            await get_message('custom_filter.random_reply_added', botkey=k, filter_name=filter_name, count=count),
            parse_mode=ParseMode.HTML,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.random_reply_added')
        return

    # ─── حذف رد مميز (بعد إرسال اسمه) ────────────────────────────────────
    if await rdb.get(f'{cid}:delFilterR:{uid}{Dev_Zaid}') and await mod_pls(uid, cid):
        if not await rdb.get(f'{m.text}:randomFilter:{cid}{Dev_Zaid}'):
            await rdb.delete(f'{cid}:delFilterR:{uid}{Dev_Zaid}')
            sent = await m.reply(await get_message('custom_filter.random_not_in_list', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.random_not_in_list')
            return
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{m.text}:randomFilter:{cid}{Dev_Zaid}')
            pipe.delete(f'{m.text}:randomfilter:{cid}{Dev_Zaid}')
            pipe.delete(f'{cid}:delFilterR:{uid}{Dev_Zaid}')
            pipe.srem(f'{cid}:RFiltersList:{Dev_Zaid}', m.text)
            await pipe.execute()
        sent = await m.reply(await get_message('custom_filter.random_reply_deleted', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.random_reply_deleted')
        return

    # ─── انتقال: أرسل اسم الفلتر → ابدأ تجميع الأجوبة ────────────────────
    if await rdb.get(f'{cid}:addFilterR:{uid}{Dev_Zaid}') and await mod_pls(uid, cid):
        async with rdb.pipeline(transaction=False) as pipe:
            pipe.delete(f'{cid}:addFilterR:{uid}{Dev_Zaid}')
            pipe.set(f'{cid}:addFilterR2:{uid}{Dev_Zaid}', m.text)
            await pipe.execute()
        sent = await m.reply(
            await get_message('custom_filter.prompt_random_answers', botkey=k),
            parse_mode=ParseMode.MARKDOWN,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.prompt_random_answers')
        return

    # ─── تجميع الأجوبة (كل رسالة = جواب واحد) ─────────────────────────────
    if await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}') and await mod_pls(uid, cid):
        filter_name = await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}')
        await rdb.sadd(f'{filter_name}:randomfilter:{cid}{Dev_Zaid}', m.text.html)
        sent = await m.reply(
            await get_message('custom_filter.random_answer_added', botkey=k),
            parse_mode=ParseMode.MARKDOWN,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.random_answer_added')
        return

    # ─── الردود المميزه — قائمة ────────────────────────────────────────────
    if text == 'الردود المميزه':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        rfilters = await rdb.smembers(f'{cid}:RFiltersList:{Dev_Zaid}')
        if not rfilters:
            sent = await m.reply(await get_message('custom_filter.no_random_replies', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_random_replies')
            return
        lines = 'الردود المميزه:\n'
        count = 1
        for rep in rfilters:
            ttt = len(await rdb.smembers(f'{rep}:randomfilter:{cid}{Dev_Zaid}'))
            lines += f'\n{count} - ( {rep} ) ☆ ( {ttt} )'
            count += 1
        lines += '\n☆'
        return await m.reply(lines, disable_web_page_preview=True, parse_mode=ParseMode.HTML)

    # ─── مسح الردود المميزه ────────────────────────────────────────────────
    if text == 'مسح الردود المميزه':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        rfilters = await rdb.smembers(f'{cid}:RFiltersList:{Dev_Zaid}')
        if not rfilters:
            sent = await m.reply(await get_message('custom_filter.no_random_replies', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.no_random_replies')
            return
        count = 0
        for rep in list(rfilters):
            async with rdb.pipeline(transaction=False) as pipe:
                pipe.delete(f'{rep}:randomfilter:{cid}{Dev_Zaid}')
                pipe.srem(f'{cid}:RFiltersList:{Dev_Zaid}', rep)
                pipe.delete(f'{rep}:randomFilter:{cid}{Dev_Zaid}')
                await pipe.execute()
            count += 1
        sent = await m.reply(await get_message('custom_filter.clear_random_success', botkey=k, count=count))
        await track_sent_message(cid, sent.id, 'custom_filter.clear_random_success')
        return

    # ─── اضف رد مميز (يبدأ جلسة الإضافة) ─────────────────────────────────
    if (text == 'اضف رد مميز'
            and not await rdb.get(f'{cid}:addFilterR:{uid}{Dev_Zaid}')
            and not await rdb.get(f'{cid}:addFilterR2:{uid}{Dev_Zaid}')):
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        await rdb.set(f'{cid}:addFilterR:{uid}{Dev_Zaid}', 1)
        sent = await m.reply(await get_message('custom_filter.prompt_add_random_word', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_filter.prompt_add_random_word')
        return

    # ─── مسح رد مميز (يبدأ جلسة الحذف) ───────────────────────────────────
    if text == 'مسح رد مميز' and not await rdb.get(f'{cid}:delFilterR:{uid}{Dev_Zaid}'):
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('custom_filter.perm_mod', botkey=k))
            await track_sent_message(cid, sent.id, 'custom_filter.perm_mod')
            return
        await rdb.set(f'{cid}:delFilterR:{uid}{Dev_Zaid}', 1)
        sent = await m.reply(
            await get_message('custom_filter.prompt_del_reply', botkey=k),
            parse_mode=ParseMode.MARKDOWN,
        )
        await track_sent_message(cid, sent.id, 'custom_filter.prompt_del_reply')
        return
