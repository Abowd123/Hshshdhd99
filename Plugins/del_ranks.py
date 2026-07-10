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
مُنقول من bmqa/Plugins/del_ranks.py → bmqa-v2/Plugins/del_ranks.py

الأوامر (handler واحد، group=13، text & group):
  - مسح قائمه Dev       — مسح كل Dev²🎖️             (devp_pls)
  - مسح قائمه MY        — مسح كل Myth🎖️              (dev2_pls)
  - مسح المالكين الاساسيين — مسح كل gowner القروب    (dev_pls)
  - مسح المالكين          — مسح كل owner القروب      (gowner_pls)
  - مسح المدراء           — مسح كل mod القروب        (owner_pls)
  - مسح الادمنيه | مسح الادمن — مسح كل admin القروب  (mod_pls)
  - مسح المميزين          — مسح كل pre القروب        (mod_pls)
  - مسح المكتومين         — مسح كل muted القروب      (mod_pls)
  - مسح المكتومين عام     — مسح كل muted عام         (dev_pls)
  - مسح المحظورين عام     — مسح كل gban عام          (dev_pls)

التحويلات:
  - Thread → await مباشر
  - r.<op> → await rdb.<op>
  - get_rank → await get_rank
  - @register + @safe_handler مُضافان
  - _DEMOTED_TPL مُزال وحلّت محله استدعاءات get_message()
"""

import logging
from pyrogram import Client, filters
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message, track_sent_message
from helpers.ranks import (
    admin_pls, mod_pls, get_rank,
    dev_pls, dev2_pls, devp_pls, gowner_pls, owner_pls,
    isLockCommand,
)


@register("del_ranks")
@Client.on_message(filters.text & filters.group, group=13)
@safe_handler
async def delRanksHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')

    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
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

    uid = m.from_user.id
    cid = m.chat.id

    if text == 'مسح قائمه Dev':
        if not await devp_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.dev2_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.dev2_perm')
            return
        members = await rdb.smembers(f'{Dev_Zaid}DEV2')
        if not members:
            sent = await m.reply(await get_message('del_ranks.dev2_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.dev2_empty')
            return
        count = 0
        for dev2 in list(members):
            await rdb.srem(f'{Dev_Zaid}DEV2', int(dev2))
            await rdb.delete(f'{int(dev2)}:rankDEV2:{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.dev2_success', botkey=k, caller_rank=caller_rank, count=count, list_name='قائمة Dev'))
        await track_sent_message(cid, sent.id, 'del_ranks.dev2_success')

    if text == 'مسح قائمه MY':
        if not await dev2_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.dev_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.dev_perm')
            return
        members = await rdb.smembers(f'{Dev_Zaid}DEV')
        if not members:
            sent = await m.reply(await get_message('del_ranks.dev_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.dev_empty')
            return
        count = 0
        for dev in list(members):
            await rdb.srem(f'{Dev_Zaid}DEV', int(dev))
            await rdb.delete(f'{int(dev)}:rankDEV:{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.dev_success', botkey=k, caller_rank=caller_rank, count=count, list_name='قائمة MY'))
        await track_sent_message(cid, sent.id, 'del_ranks.dev_success')

    if text == 'مسح المالكين الاساسيين':
        if not await dev_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.gowner_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.gowner_perm')
            return
        members = await rdb.smembers(f'{cid}:listGOWNER:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.gowner_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.gowner_empty')
            return
        count = 0
        for gowner in list(members):
            await rdb.srem(f'{cid}:listGOWNER:{Dev_Zaid}', int(gowner))
            await rdb.delete(f'{cid}:rankGOWNER:{int(gowner)}{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.gowner_success', botkey=k, caller_rank=caller_rank, count=count, list_name='المالكين الاساسيين'))
        await track_sent_message(cid, sent.id, 'del_ranks.gowner_success')

    if text == 'مسح المالكين':
        if not await gowner_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.owner_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.owner_perm')
            return
        members = await rdb.smembers(f'{cid}:listOWNER:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.owner_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.owner_empty')
            return
        count = 0
        for owner in list(members):
            await rdb.srem(f'{cid}:listOWNER:{Dev_Zaid}', int(owner))
            await rdb.delete(f'{cid}:rankOWNER:{int(owner)}{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.owner_success', botkey=k, caller_rank=caller_rank, count=count, list_name='المالكين'))
        await track_sent_message(cid, sent.id, 'del_ranks.owner_success')

    if text == 'مسح المدراء':
        if not await owner_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.mod_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.mod_perm')
            return
        members = await rdb.smembers(f'{cid}:listMOD:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.mod_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.mod_empty')
            return
        count = 0
        for MOD in list(members):
            await rdb.srem(f'{cid}:listMOD:{Dev_Zaid}', int(MOD))
            await rdb.delete(f'{cid}:rankMOD:{int(MOD)}{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.mod_success', botkey=k, caller_rank=caller_rank, count=count, list_name='المدراء'))
        await track_sent_message(cid, sent.id, 'del_ranks.mod_success')

    if text == 'مسح الادمنيه' or text == 'مسح الادمن':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.admin_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.admin_perm')
            return
        members = await rdb.smembers(f'{cid}:listADMIN:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.admin_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.admin_empty')
            return
        count = 0
        for ADM in list(members):
            await rdb.srem(f'{cid}:listADMIN:{Dev_Zaid}', int(ADM))
            await rdb.delete(f'{cid}:rankADMIN:{int(ADM)}{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.admin_success', botkey=k, caller_rank=caller_rank, count=count, list_name='الادمن'))
        await track_sent_message(cid, sent.id, 'del_ranks.admin_success')

    if text == 'مسح المميزين':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.pre_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.pre_perm')
            return
        members = await rdb.smembers(f'{cid}:listPRE:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.pre_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.pre_empty')
            return
        count = 0
        for PRE in list(members):
            await rdb.srem(f'{cid}:listPRE:{Dev_Zaid}', int(PRE))
            await rdb.delete(f'{cid}:rankPRE:{int(PRE)}{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.pre_success', botkey=k, caller_rank=caller_rank, count=count, list_name='المميزين'))
        await track_sent_message(cid, sent.id, 'del_ranks.pre_success')

    if text == 'مسح المكتومين':
        if not await mod_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.mute_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.mute_perm')
            return
        members = await rdb.smembers(f'{cid}:listMUTE:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.mute_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.mute_empty')
            return
        count = 0
        for MOD in list(members):
            try:
                mod = int(MOD)
            except Exception as e:
                logging.exception(e)
                mod = MOD
            await rdb.srem(f'{cid}:listMUTE:{Dev_Zaid}', mod)
            await rdb.delete(f'{mod}:mute:{cid}{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.mute_success', botkey=k, caller_rank=caller_rank, count=count, list_name='المكتومين'))
        await track_sent_message(cid, sent.id, 'del_ranks.mute_success')

    if text == 'مسح المكتومين عام':
        if not await dev_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.gmute_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.gmute_perm')
            return
        members = await rdb.smembers(f'listMUTE:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.gmute_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.gmute_empty')
            return
        count = 0
        for MOD in list(members):
            await rdb.srem(f'listMUTE:{Dev_Zaid}', int(MOD))
            await rdb.delete(f'{int(MOD)}:mute:{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.gmute_success', botkey=k, caller_rank=caller_rank, count=count, list_name='المكتومين عام'))
        await track_sent_message(cid, sent.id, 'del_ranks.gmute_success')

    if text == 'مسح المحظورين عام':
        if not await dev_pls(uid, cid):
            sent = await m.reply(await get_message('del_ranks.gban_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.gban_perm')
            return
        members = await rdb.smembers(f'listGBAN:{Dev_Zaid}')
        if not members:
            sent = await m.reply(await get_message('del_ranks.gban_empty', botkey=k))
            await track_sent_message(cid, sent.id, 'del_ranks.gban_empty')
            return
        count = 0
        for MOD in list(members):
            await rdb.srem(f'listGBAN:{Dev_Zaid}', int(MOD))
            await rdb.delete(f'{int(MOD)}:gban:{Dev_Zaid}')
            count += 1
        caller_rank = await get_rank(uid, cid)
        sent = await m.reply(await get_message('del_ranks.gban_success', botkey=k, caller_rank=caller_rank, count=count, list_name='الحمير المحظورين عام'))
        await track_sent_message(cid, sent.id, 'del_ranks.gban_success')
