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
مُنقول من bmqa/Plugins/get_ranks.py → bmqa-v2/Plugins/get_ranks.py

الأوامر (handler واحد، group=12، text & group):
  - قائمه Dev          — قائمة Dev²🎖️ العامة       (devp_pls)
  - قائمه MY           — قائمة Myth🎖️ العامة        (dev2_pls)
  - المالكين الاساسيين  — قائمة gowner في القروب    (dev_pls)
  - المالكين            — قائمة owner في القروب     (gowner_pls)
  - المدراء             — قائمة mod في القروب       (owner_pls)
  - الادمنيه            — قائمة admin في القروب     (mod_pls)
  - المشرفين            — أدمنية تيليجرام الفعلية  (owner_pls) ← core/cache.py
  - المميزين            — قائمة pre في القروب       (admin_pls)
  - المكتومين           — قائمة muted في القروب     (mod_pls)

التحويلات:
  - Thread → await مباشر
  - r.<op> → await rdb.<op>
  - c.get_users (sync داخل Thread) → await c.get_users
  - m.chat.get_members (sync) → members_cache.get_admins (async، core/cache.py)
  - @register + @safe_handler مُضافان
  - build_member_list (helpers.ranks) يوحّد نمط بناء قائمة الأعضاء المكرر 8 مرات
  - رسائل perm/empty مُرحَّلة لـ get_message()؛ الردود الديناميكية (txt) تبقى كما هي
"""

from pyrogram import Client, filters
from pyrogram.enums import ChatMembersFilter
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.cache import members_cache
from core.messages import get_message, track_sent_message
from helpers.ranks import (
    admin_pls, mod_pls, owner_pls, gowner_pls,
    dev_pls, dev2_pls, devp_pls,
    isLockCommand, build_member_list,
)


@register("get_ranks")
@Client.on_message(filters.text & filters.group, group=12)
@safe_handler
async def getRanksHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') or 'yqyqy66'

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return

    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    cid = m.chat.id

    if text == 'قائمه Dev':
        if not await devp_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.dev2_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.dev2_perm')
            return
        members = await rdb.smembers(f'{Dev_Zaid}DEV2')
        if not members:
            sent = await m.reply(await get_message('get_ranks.dev2_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.dev2_empty')
            return
        txt = await build_member_list(c, channel, members, '- قائمة  Dev²🎖:')
        return await m.reply(txt)

    if text == 'قائمه MY':
        if not await dev2_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.dev_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.dev_perm')
            return
        members = await rdb.smembers(f'{Dev_Zaid}DEV')
        if not members:
            sent = await m.reply(await get_message('get_ranks.dev_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.dev_empty')
            return
        txt = await build_member_list(c, channel, members, '- قائمة Myth🎖️:')
        return await m.reply(txt)

    if text == 'المالكين الاساسيين':
        if not await dev_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.gowner_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.gowner_perm')
            return
        members = await rdb.smembers(f'{cid}:listGOWNER:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('get_ranks.gowner_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.gowner_empty')
            return
        txt = await build_member_list(c, channel, members, '- المالكين الاساسيين:')
        return await m.reply(txt)

    if text == 'المالكين':
        if not await gowner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.owner_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.owner_perm')
            return
        members = await rdb.smembers(f'{cid}:listOWNER:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('get_ranks.owner_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.owner_empty')
            return
        txt = await build_member_list(c, channel, members, '- المالكيين:')
        return await m.reply(txt)

    if text == 'المدراء':
        if not await owner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.mod_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.mod_perm')
            return
        members = await rdb.smembers(f'{cid}:listMOD:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('get_ranks.mod_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.mod_empty')
            return
        txt = await build_member_list(c, channel, members, '- المدراء:')
        return await m.reply(txt)

    if text == 'الادمنيه':
        if not await mod_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.admin_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.admin_perm')
            return
        members = await rdb.smembers(f'{cid}:listADMIN:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('get_ranks.admin_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.admin_empty')
            return
        txt = await build_member_list(c, channel, members, '- الادمنيه:')
        return await m.reply(txt)

    if text == 'المشرفين':
        if not await owner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.tg_admins_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.tg_admins_perm')
            return
        admins = await members_cache.get_admins(c, cid, ChatMembersFilter.ADMINISTRATORS)
        txt = '- المشرفين:\n\n'
        count = 1
        for mm in admins:
            if count == 101:
                break
            if not mm.user.is_deleted and not mm.user.is_bot:
                uid = mm.user.id
                uname = mm.user.username
                if uname:
                    txt += f'{count} ➣ @{uname} ࿓ ( `{uid}` )\n'
                else:
                    txt += f'{count} ➣ [@{channel}](tg://user?id={uid}) ࿓ ( `{uid}` )\n'
                count += 1
        txt += '\n☆'
        return await m.reply(txt)

    if text == 'المميزين':
        if not await admin_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.pre_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.pre_perm')
            return
        members = await rdb.smembers(f'{cid}:listPRE:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('get_ranks.pre_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.pre_empty')
            return
        txt = await build_member_list(c, channel, members, '- المميزين:')
        return await m.reply(txt)

    if text == 'المكتومين':
        if not await mod_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('get_ranks.mute_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.mute_perm')
            return
        members = await rdb.smembers(f'{cid}:listMUTE:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('get_ranks.mute_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'get_ranks.mute_empty')
            return
        txt = await build_member_list(c, channel, members, '- المكتومين:')
        return await m.reply(txt)
