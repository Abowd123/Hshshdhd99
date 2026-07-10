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
مُنقول من bmqa/Plugins/customRank.py، محوَّل بالكامل إلى async:
  - r.<op>(...) -> await rdb.<op>(...)  (core/db.py)
  - Thread(target=customRankFunc, ...).start() -> await customRankFunc(...)
  - كل دوال helpers.ranks (admin_pls, mod_pls, isLockCommand, ...) أصبحت
    async فأصبحت تُستدعى بـ await.
  - نداءات Pyrogram المتزامنة ظاهرياً في الأصل (m.reply, ...) هي أصلاً
    coroutines في Pyrogram/kurigram؛ أُضيف لها await لتعمل صحيحاً بدون
    الاعتماد على "وضع sync" الذي كان يوفره تشغيلها داخل Thread منفصل.
  - الرسائل الثابتة مُرحَّلة لـ get_message()؛ قائمة الرتب الديناميكية تبقى كما هي.
"""

import random, re, time
from pyrogram import *
from pyrogram.enums import *
from pyrogram.types import *
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.messages import get_message, track_sent_message
from helpers.ranks import *
from helpers.ranks import isLockCommand


@Client.on_message(filters.text & filters.group, group=35)
@safe_handler
async def customrankHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    channel = await rdb.get(f'{Dev_Zaid}:BotChannel') if await rdb.get(f'{Dev_Zaid}:BotChannel') else 'yqyqy66'
    await customRankFunc(c, m, k, channel)
    
async def customRankFunc(c, m, k, channel):
   if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):  return
   if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):  return 
   if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):  return 
   if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):  return
   if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') or await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):  return 
   if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id,m.chat.id):  return  
   if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):  return 
   text = m.text
   name = await rdb.get(f'{Dev_Zaid}:BotName') if await rdb.get(f'{Dev_Zaid}:BotName') else 'رعد'
   if text.startswith(f'{name} '):
      text = text.replace(f'{name} ','')
   if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}'):
       text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={text}')
   if await rdb.get(f'Custom:{Dev_Zaid}&text={text}'):
       text = await rdb.get(f'Custom:{Dev_Zaid}&text={text}')
   if await isLockCommand(m.from_user.id, m.chat.id, text): return

   cid = m.chat.id

   if text == 'الغاء':
     if await rdb.get(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}') or await rdb.get(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}') or await rdb.get(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}'):
        sent = await m.reply(await get_message('custom_rank.cancel_success', botkey=k))
        await track_sent_message(cid, sent.id, 'custom_rank.cancel_success')
        await rdb.delete(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}')
        await rdb.delete(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}')
        await rdb.delete(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')
   
   if await rdb.get(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}') and await mod_pls(m.from_user.id,m.chat.id) and len(m.text) <= 20:
     rank = await rdb.get(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')
     await rdb.delete(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}')
     if rank == 'مالك اساسي':
       if await rdb.get(f'{m.chat.id}:RankGowner:{Dev_Zaid}'):
         rrr = await rdb.get(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
         await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rrr}')
         await rdb.delete(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
       await rdb.set(f'{m.chat.id}:RankGowner:{Dev_Zaid}',m.text)
     if rank == 'مالك':
       if await rdb.get(f'{m.chat.id}:RankOwner:{Dev_Zaid}'):
         rrr = await rdb.get(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
         await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rrr}')
         await rdb.delete(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
       await rdb.set(f'{m.chat.id}:RankOwner:{Dev_Zaid}',m.text)
     if rank == 'مدير':
       if await rdb.get(f'{m.chat.id}:RankMod:{Dev_Zaid}'):
         rrr = await rdb.get(f'{m.chat.id}:RankMod:{Dev_Zaid}')
         await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rrr}')
         await rdb.delete(f'{m.chat.id}:RankMod:{Dev_Zaid}')     
       await rdb.set(f'{m.chat.id}:RankMod:{Dev_Zaid}',m.text)
     if rank == 'ادمن':
       if await rdb.get(f'{m.chat.id}:RankAdm:{Dev_Zaid}'):
         rrr = await rdb.get(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
         await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rrr}')
         await rdb.delete(f'{m.chat.id}:RankAdm:{Dev_Zaid}')     
       await rdb.set(f'{m.chat.id}:RankAdm:{Dev_Zaid}',m.text)
     if rank == 'مميز':
       if await rdb.get(f'{m.chat.id}:RankPre:{Dev_Zaid}'):
         rrr = await rdb.get(f'{m.chat.id}:RankPre:{Dev_Zaid}')
         await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rrr}')
         await rdb.delete(f'{m.chat.id}:RankPre:{Dev_Zaid}')     
       await rdb.set(f'{m.chat.id}:RankPre:{Dev_Zaid}',m.text)
     if rank == 'عضو':
       if await rdb.get(f'{m.chat.id}:RankMem:{Dev_Zaid}'):
         rrr = await rdb.get(f'{m.chat.id}:RankMem:{Dev_Zaid}')
         await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rrr}')
         await rdb.delete(f'{m.chat.id}:RankMem:{Dev_Zaid}')     
       await rdb.set(f'{m.chat.id}:RankMem:{Dev_Zaid}',m.text)
     await rdb.sadd(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={m.text}')
     sent = await m.reply(await get_message('custom_rank.set_new_rank_success', botkey=k, new_rank=m.text))
     await track_sent_message(cid, sent.id, 'custom_rank.set_new_rank_success')
     return
       
   if await rdb.get(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}') and await mod_pls(m.from_user.id,m.chat.id):
     await rdb.delete(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}')
     if not m.text in ['مالك اساسي','مالك','مدير','ادمن','مميز','عضو']:
       sent = await m.reply(await get_message('custom_rank.invalid_rank', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.invalid_rank')
       return
     else:
       await rdb.set(f'{m.from_user.id}:addRank2:{m.chat.id}{Dev_Zaid}',m.text,ex=600)
       sent = await m.reply(await get_message('custom_rank.ask_new_rank', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.ask_new_rank')
       return
   
   if await rdb.get(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}') and await mod_pls(m.from_user.id,m.chat.id):
     await rdb.delete(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}')
     if not m.text in ['مالك اساسي','مالك','مدير','ادمن','مميز','عضو']:
       sent = await m.reply(await get_message('custom_rank.del_invalid_rank', botkey=k, input_text=m.text[:20]))
       await track_sent_message(cid, sent.id, 'custom_rank.del_invalid_rank')
       return
     else:
       rank = m.text
       if rank == 'مالك اساسي':
         rank2 = await rdb.get(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
       if rank == 'مالك':
         rank2 = await rdb.get(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
       if rank == 'مدير':
         rank2 = await rdb.get(f'{m.chat.id}:RankMod:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankMod:{Dev_Zaid}')
       if rank == 'ادمن':
         rank2 = await rdb.get(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
       if rank == 'مميز':
         rank2 = await rdb.get(f'{m.chat.id}:RankPre:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankPre:{Dev_Zaid}')
       if rank == 'عضو':
         rank2 = await rdb.get(f'{m.chat.id}:RankMem:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankMem:{Dev_Zaid}')
       await rdb.srem(f'{m.chat.id}:ranklist:{Dev_Zaid}',f'{rank}&&newr={rank2}')
       sent = await m.reply(await get_message('custom_rank.del_success', botkey=k, rank_name=rank2))
       await track_sent_message(cid, sent.id, 'custom_rank.del_success')
       return
   
   if text == 'مسح الرتب':
     if not await mod_pls(m.from_user.id,m.chat.id):
       sent = await m.reply(await get_message('custom_rank.clear_ranks_perm', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.clear_ranks_perm')
       return
     else:
       if not await rdb.smembers(f'{m.chat.id}:ranklist:{Dev_Zaid}'):
         sent = await m.reply(await get_message('custom_rank.clear_ranks_empty', botkey=k))
         await track_sent_message(cid, sent.id, 'custom_rank.clear_ranks_empty')
         return
       else:
         sent = await m.reply(await get_message('custom_rank.clear_ranks_success', botkey=k))
         await track_sent_message(cid, sent.id, 'custom_rank.clear_ranks_success')
         await rdb.delete(f'{m.chat.id}:RankGowner:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankOwner:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankMod:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankAdm:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankPre:{Dev_Zaid}')
         await rdb.delete(f'{m.chat.id}:RankMem:{Dev_Zaid}')
         return await rdb.delete(f'{m.chat.id}:ranklist:{Dev_Zaid}')
   
   if text == 'قائمه الرتب' or text == 'قائمة الرتب':
     if not await mod_pls(m.from_user.id,m.chat.id):
       sent = await m.reply(await get_message('custom_rank.list_ranks_perm', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.list_ranks_perm')
       return
     else:
       if not await rdb.smembers(f'{m.chat.id}:ranklist:{Dev_Zaid}'):
         sent = await m.reply(await get_message('custom_rank.list_ranks_empty', botkey=k))
         await track_sent_message(cid, sent.id, 'custom_rank.list_ranks_empty')
         return
       else:
         # قائمة الرتب ديناميكية — تبقى كما هي ولا تُرحَّل
         txt = 'قائمة الرتب:\n'
         count = 1
         for rrr in await rdb.smembers(f'{m.chat.id}:ranklist:{Dev_Zaid}'):
            rank = rrr.split('&&newr=')
            txt += f'{count}) {rank[0]} ~ ( {rank[1]} )\n'
            count += 1
         txt += '\n☆'
         return await m.reply(txt, disable_web_page_preview=True)

   if text == 'مسح رتبه' or text == 'مسح رتبة':
     if not await mod_pls(m.from_user.id,m.chat.id):
       sent = await m.reply(await get_message('custom_rank.del_rank_perm', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.del_rank_perm')
       return
     else:
       await rdb.set(f'{m.from_user.id}:delRank:{m.chat.id}{Dev_Zaid}',1,ex=600)
       sent = await m.reply(await get_message('custom_rank.ask_rank_to_del', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.ask_rank_to_del')
       return
   
   if text == 'تغيير رتبه' or text == 'تغيير رتبة':
     if not await mod_pls(m.from_user.id,m.chat.id):
       sent = await m.reply(await get_message('custom_rank.change_rank_perm', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.change_rank_perm')
       return
     else:
       await rdb.set(f'{m.from_user.id}:addRank:{m.chat.id}{Dev_Zaid}',1,ex=600)
       sent = await m.reply(await get_message('custom_rank.ask_rank_to_change', botkey=k))
       await track_sent_message(cid, sent.id, 'custom_rank.ask_rank_to_change')
       return
