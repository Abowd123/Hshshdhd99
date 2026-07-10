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
Plugins/ranks/set_promote.py — مُقتطع من bmqa/Plugins/set_ranks.py (الجزء الأول)
مسؤول عن أوامر الرفع (group=7).

الأوامر:
  - تعطيل الرفع / تفعيل الرفع              (owner_pls)
  - رفع Dev  [reply | @user | ID]          (devp_pls)
  - رفع MY   [reply | @user | ID]          (dev2_pls)
  - رفع مالك اساسي [reply | @user | ID]    (gowner_pls)
  - رفع مالك       [reply | @user | ID]    (gowner_pls)
  - رفع مدير       [reply | @user | ID]    (owner_pls)
  - رفع ادمن       [reply | @user | ID]    (mod_pls)
  - رفع مميز       [reply | @user | ID]    (admin_pls)

التحويلات: sync→async، Thread→await، r.<op>→await rdb.<op>،
            c.get_chat→await c.get_chat، @register + @safe_handler.
resolve_target (helpers.ranks) يوحّد نمط حل @user/ID المكرر 14 مرة.
"""

import re
from pyrogram import Client, filters
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message, track_sent_message
from helpers.ranks import (
    admin_pls, mod_pls, owner_pls, gowner_pls,
    dev2_pls, devp_pls,
    get_rank, isLockCommand, resolve_target,
)


async def _common_guards(m, k) -> bool:
    """يعيد True إذا يجب إيقاف المعالجة (حارس مشترك لكلا الـhandler)."""
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return True
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return True
    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
        return True
    return False


async def _resolve_text(m):
    """يحسب النص بعد استبدال الأوامر المخصصة والتحقق من اسم البوت."""
    text = m.text
    name = await rdb.get(f'{Dev_Zaid}:BotName') or 'رعد'
    if text.startswith(f'{name} '):
        text = text.replace(f'{name} ', '')
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
    return text


async def _unmute_after_promote(m, uid: int):
    """يرفع الكتم العام والمحلي عن عضو تمت ترقيته."""
    if await rdb.get(f'{uid}:mute:{Dev_Zaid}'):
        await rdb.delete(f'{uid}:mute:{Dev_Zaid}')
        await rdb.srem(f'listMUTE:{Dev_Zaid}', uid)
    if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
        await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
        await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)


@register("set_promote")
@Client.on_message(filters.text & filters.group, group=7)
@safe_handler
async def ranksCommandsHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await _common_guards(m, k):
        return

    text = await _resolve_text(m)
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    cid = m.chat.id
    rank = await get_rank(m.from_user.id, cid)

    if text == 'تعطيل الرفع':
        if not await owner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.disable_ranks_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.disable_ranks_perm')
            return
        if await rdb.get(f'{cid}:disableRanks:{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.disable_ranks_already', botkey=k, mention=m.from_user.mention))
            await track_sent_message(cid, sent.id, 'promote.disable_ranks_already')
            return
        await rdb.set(f'{cid}:disableRanks:{Dev_Zaid}', 1)
        sent = await m.reply(await get_message('promote.disable_ranks_success', botkey=k, mention=m.from_user.mention))
        await track_sent_message(cid, sent.id, 'promote.disable_ranks_success')
        return

    if text == 'تفعيل الرفع':
        if not await owner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.enable_ranks_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.enable_ranks_perm')
            return
        if not await rdb.get(f'{cid}:disableRanks:{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.enable_ranks_already', botkey=k, mention=m.from_user.mention))
            await track_sent_message(cid, sent.id, 'promote.enable_ranks_already')
            return
        await rdb.delete(f'{cid}:disableRanks:{Dev_Zaid}')
        sent = await m.reply(await get_message('promote.enable_ranks_success', botkey=k, mention=m.from_user.mention))
        await track_sent_message(cid, sent.id, 'promote.enable_ranks_success')
        return

    if await rdb.get(f'{cid}:disableRanks:{Dev_Zaid}'):
        return

    # ─── رفع Dev ───────────────────────────────────────────────────────────
    if text.startswith('رفع Dev ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await devp_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.dev2_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.dev2_perm')
            return
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.dev2_self_user'))
            await track_sent_message(cid, sent.id, 'promote.dev2_self_user')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.dev2_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.dev2_self_devzaid')
            return
        if await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.dev2_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.dev2_already')
            return
        await rdb.set(f'{uid}:rankDEV2:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV2', uid)
        sent = await m.reply(await get_message('promote.dev2_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.dev2_success')
        return

    if text == 'رفع Dev' and m.reply_to_message and m.reply_to_message.from_user:
        if not await devp_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.dev2_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.dev2_perm')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.dev2_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.dev2_self_reply')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.dev2_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.dev2_self_devzaid')
            return
        if await rdb.get(f'{uid}:rankDEV2:{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.dev2_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.dev2_already')
            return
        await rdb.set(f'{uid}:rankDEV2:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV2', uid)
        sent = await m.reply(await get_message('promote.dev2_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.dev2_success')
        return

    # ─── رفع MY ────────────────────────────────────────────────────────────
    if text.startswith('رفع MY ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await dev2_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.dev_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.dev_perm')
            return
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.dev_self_user'))
            await track_sent_message(cid, sent.id, 'promote.dev_self_user')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.dev_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.dev_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.dev_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.dev_same_rank')
            return
        if await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.dev_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.dev_already')
            return
        await rdb.set(f'{uid}:rankDEV:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV', uid)
        sent = await m.reply(await get_message('promote.dev_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.dev_success')
        await _unmute_after_promote(m, uid)
        return

    if text == 'رفع MY' and m.reply_to_message and m.reply_to_message.from_user:
        if not await dev2_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.dev_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.dev_perm')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.dev_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.dev_self_reply')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.dev_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.dev_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.dev_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.dev_same_rank')
            return
        if await rdb.get(f'{uid}:rankDEV:{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.dev_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.dev_already')
            return
        await rdb.set(f'{uid}:rankDEV:{Dev_Zaid}', 1)
        await rdb.sadd(f'{Dev_Zaid}DEV', uid)
        sent = await m.reply(await get_message('promote.dev_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.dev_success')
        await _unmute_after_promote(m, uid)
        return

    # ─── رفع مالك اساسي ───────────────────────────────────────────────────
    if text.startswith('رفع مالك اساسي ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await gowner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.gowner_perm_user', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.gowner_perm_user')
            return
        result = await resolve_target(c, m, k, text, word_index=3)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.gowner_self_user'))
            await track_sent_message(cid, sent.id, 'promote.gowner_self_user')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.gowner_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.gowner_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.gowner_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.gowner_same_rank')
            return
        if await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.gowner_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.gowner_already')
            return
        await rdb.set(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.gowner_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.gowner_success')
        await _unmute_after_promote(m, uid)
        return

    if text == 'رفع مالك اساسي' and m.reply_to_message and m.reply_to_message.from_user:
        if not await gowner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.gowner_perm_reply', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.gowner_perm_reply')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.gowner_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.gowner_self_reply')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.gowner_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.gowner_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.gowner_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.gowner_same_rank')
            return
        if await rdb.get(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.gowner_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.gowner_already')
            return
        await rdb.set(f'{cid}:rankGOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listGOWNER:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.gowner_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.gowner_success')
        await _unmute_after_promote(m, uid)
        return

    # ─── رفع مالك ─────────────────────────────────────────────────────────
    if text.startswith('رفع مالك ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await gowner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.owner_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.owner_perm')
            return
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.owner_self_user'))
            await track_sent_message(cid, sent.id, 'promote.owner_self_user')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.owner_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.owner_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.owner_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.owner_same_rank')
            return
        if await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.owner_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.owner_already')
            return
        await rdb.set(f'{cid}:rankOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listOWNER:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.owner_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.owner_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع مالك' and m.reply_to_message and m.reply_to_message.from_user:
        if not await gowner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.owner_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.owner_perm')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.owner_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.owner_self_reply')
            return
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.owner_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.owner_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.owner_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.owner_same_rank')
            return
        if await rdb.get(f'{cid}:rankOWNER:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.owner_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.owner_already')
            return
        await rdb.set(f'{cid}:rankOWNER:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listOWNER:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.owner_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.owner_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    # ─── رفع مدير ─────────────────────────────────────────────────────────
    if text.startswith('رفع مدير ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await owner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.mod_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.mod_perm')
            return
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.mod_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.mod_self_devzaid')
            return
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.mod_self_user'))
            await track_sent_message(cid, sent.id, 'promote.mod_self_user')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.mod_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.mod_same_rank')
            return
        if await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.mod_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.mod_already')
            return
        await rdb.set(f'{cid}:rankMOD:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listMOD:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.mod_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.mod_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع مدير' and m.reply_to_message and m.reply_to_message.from_user:
        if not await owner_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.mod_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.mod_perm')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.mod_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.mod_self_devzaid')
            return
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.mod_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.mod_self_reply')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.mod_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.mod_same_rank')
            return
        if await rdb.get(f'{cid}:rankMOD:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.mod_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.mod_already')
            return
        await rdb.set(f'{cid}:rankMOD:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listMOD:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.mod_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.mod_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    # ─── رفع ادمن ─────────────────────────────────────────────────────────
    if text.startswith('رفع ادمن ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await mod_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.admin_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.admin_perm')
            return
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.admin_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.admin_self_devzaid')
            return
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.admin_self_user'))
            await track_sent_message(cid, sent.id, 'promote.admin_self_user')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.admin_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.admin_same_rank')
            return
        if await rdb.get(f'{cid}:rankADMIN:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.admin_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.admin_already')
            return
        await rdb.set(f'{cid}:rankADMIN:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listADMIN:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.admin_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.admin_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع ادمن' and m.reply_to_message and m.reply_to_message.from_user:
        if not await mod_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.admin_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.admin_perm')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.admin_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.admin_self_devzaid')
            return
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.admin_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.admin_self_reply')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.admin_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.admin_same_rank')
            return
        if await rdb.get(f'{cid}:rankADMIN:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.admin_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.admin_already')
            return
        await rdb.set(f'{cid}:rankADMIN:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listADMIN:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.admin_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.admin_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    # ─── رفع مميز ─────────────────────────────────────────────────────────
    if text.startswith('رفع مميز ') and ('@' in text or re.findall('[0-9]+', text)):
        if not await admin_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.pre_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.pre_perm')
            return
        result = await resolve_target(c, m, k, text, word_index=2)
        if result is None:
            return
        uid, mention = result
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.pre_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.pre_self_devzaid')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.pre_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.pre_same_rank')
            return
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.pre_self_user'))
            await track_sent_message(cid, sent.id, 'promote.pre_self_user')
            return
        if await rdb.get(f'{cid}:rankPRE:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.pre_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.pre_already')
            return
        await rdb.set(f'{cid}:rankPRE:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listPRE:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.pre_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.pre_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return

    if text == 'رفع مميز' and m.reply_to_message and m.reply_to_message.from_user:
        if not await admin_pls(m.from_user.id, cid):
            sent = await m.reply(await get_message('promote.pre_perm', botkey=k))
            await track_sent_message(cid, sent.id, 'promote.pre_perm')
            return
        uid = m.reply_to_message.from_user.id
        mention = m.reply_to_message.from_user.mention
        if uid == int(Dev_Zaid):
            sent = await m.reply(await get_message('promote.pre_self_devzaid'))
            await track_sent_message(cid, sent.id, 'promote.pre_self_devzaid')
            return
        if uid == m.from_user.id:
            sent = await m.reply(await get_message('promote.pre_self_reply'))
            await track_sent_message(cid, sent.id, 'promote.pre_self_reply')
            return
        if rank == await get_rank(uid, cid):
            sent = await m.reply(await get_message('promote.pre_same_rank'))
            await track_sent_message(cid, sent.id, 'promote.pre_same_rank')
            return
        if await rdb.get(f'{cid}:rankPRE:{uid}{Dev_Zaid}'):
            sent = await m.reply(await get_message('promote.pre_already', botkey=k, mention=mention))
            await track_sent_message(cid, sent.id, 'promote.pre_already')
            return
        await rdb.set(f'{cid}:rankPRE:{uid}{Dev_Zaid}', 1)
        await rdb.sadd(f'{cid}:listPRE:{Dev_Zaid}', uid)
        sent = await m.reply(await get_message('promote.pre_success', botkey=k, mention=mention))
        await track_sent_message(cid, sent.id, 'promote.pre_success')
        if await rdb.get(f'{uid}:mute:{m.chat.id}{Dev_Zaid}'):
            await rdb.delete(f'{uid}:mute:{m.chat.id}{Dev_Zaid}')
            await rdb.srem(f'{m.chat.id}:listMUTE:{Dev_Zaid}', uid)
        return
