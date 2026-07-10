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
مُعاد تسميته: customCommad.py → custom_command.py
مُنقول من bmqa/Plugins/customCommad.py → bmqa-v2/Plugins/custom_command.py

الأوامر/المعالجات:

  [1] customCummandHandler (group=999، text & group) — أوامر الأوامر المخصصة للمجموعة:
      - الاوامر المضافه | الاوامر المضافة : عرض الأوامر المضافة في المجموعة
      - اضف امر | تغيير امر               : إضافة/تغيير أمر مخصص (خطوتان)
      - الغاء                             : إلغاء الخطوة الجارية

  [2] delCustomCommandHandler (group=1000، text & group) — حذف الأوامر المخصصة:
      - مسح الاوامر | مسح الاوامر المضافة : مسح كل الأوامر المخصصة
      - مسح امر                           : مسح أمر مخصص واحد (بالاسم)
      - الغاء                             : إلغاء الخطوة الجارية

  [3] customCummandGlobalHandler (group=1001، text جميع المحادثات) — الأوامر العامة:
      - الاوامر العامه | الاوامر المضافه العامه : عرض الأوامر العامة
      - اضف امر عام | تغيير امر عام            : إضافة/تغيير أمر عام (خطوتان)
      - الغاء                                  : إلغاء الخطوة الجارية

  [4] delCustomCommandGHandler (group=1002، text جميع المحادثات) — حذف الأوامر العامة + قفل الأوامر:
      - مسح الاوامر العامه                      : مسح كل الأوامر العامة
      - مسح امر عام                            : مسح أمر عام واحد
      - قفل امر <نص>                           : قفل أمر لرتبة معينة (يفتح InlineKeyboard لاختيار الرتبة)
      - فتح امر <نص>                           : فتح أمر مقفول
      - الاوامر المقفوله                         : عرض الأوامر المقفولة مع رتبها
      - مسح الاوامر المقفوله                     : مسح كل الأوامر المقفولة
      - الغاء                                  : إلغاء الخطوة الجارية

التحويلات: sync→async، Thread→await مباشر، r.<op>→await rdb.<op>
"""

import re
from pyrogram import Client, filters
from pyrogram.enums import *
from pyrogram.types import *
from config import Dev_Zaid
from core.db import rdb
from core.errors import safe_handler
from core.dispatcher import register
from core.messages import get_message, track_sent_message
from helpers.ranks import admin_pls, owner_pls, mod_pls, dev_pls, devp_pls, gowner_pls
from helpers.ranks import isLockCommand


@register("custom_command_add")
@Client.on_message(filters.text & filters.group, group=999)
@safe_handler
async def customCummandHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
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

    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}')
        sent = await m.reply(quote=True, text=await get_message('custom_command.cancel_add', botkey=k))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.cancel_add')
        return

    if await rdb.get(f'{m.chat.id}:addCustom2:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:addCustom2:{m.from_user.id}{Dev_Zaid}')
        sent = await m.reply(quote=True, text=await get_message('custom_command.cancel_add', botkey=k))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.cancel_add')
        return

    if text == 'الاوامر المضافه' or text == 'الاوامر المضافة':
        if not await owner_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command.perm_owner', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command.perm_owner')
            return
        else:
            members = await rdb.smembers(f'{m.chat.id}:listCustom:{m.chat.id}{Dev_Zaid}')
            if not members:
                sent = await m.reply(quote=True, text=await get_message('custom_command.no_commands', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.no_commands')
                return
            else:
                txt = 'الاوامر المضافة:\n'
                count = 0
                for cmnd in members:
                    count += 1
                    command = cmnd
                    cc = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={command}')
                    old_c = cc
                    txt += f'{count}) {command} ~ ( {old_c} )\n'
                txt += '\n༄'
                return await m.reply(quote=True, text=txt)

    if text == 'اضف امر' or text == 'تغيير امر':
        if not await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}'):
            if not await owner_pls(m.from_user.id, m.chat.id):
                sent = await m.reply(quote=True, text=await get_message('custom_command.perm_owner', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.perm_owner')
                return
            else:
                await rdb.set(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}', 1)
                sent = await m.reply(quote=True, text=await get_message('custom_command.prompt_old_command', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.prompt_old_command')
                return

    if await rdb.get(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}') and await admin_pls(m.from_user.id, m.chat.id) and len(m.text) < 50:
        await rdb.delete(f'{m.chat.id}:addCustom:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{m.chat.id}:addCustom2:{m.from_user.id}{Dev_Zaid}', m.text)
        sent = await m.reply(quote=True, text=await get_message('custom_command.confirm_old_command', botkey=k, command=m.text))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.confirm_old_command')
        return

    if await rdb.get(f'{m.chat.id}:addCustom2:{m.from_user.id}{Dev_Zaid}') and await admin_pls(m.from_user.id, m.chat.id) and len(m.text) < 50:
        command_o = await rdb.get(f'{m.chat.id}:addCustom2:{m.from_user.id}{Dev_Zaid}')
        command_n = m.text
        await rdb.delete(f'{m.chat.id}:addCustom2:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={command_n}', command_o)
        await rdb.sadd(f'{m.chat.id}:listCustom:{m.chat.id}{Dev_Zaid}', command_n)
        sent = await m.reply(quote=True, text=await get_message('custom_command.success_changed', botkey=k, command_old=command_o, command_new=command_n))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.success_changed')
        return


@register("custom_command_del")
@Client.on_message(filters.text & filters.group, group=1000)
@safe_handler
async def delCustomCommandHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if not await rdb.get(f'{m.chat.id}:enable:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
        return
    text = m.text
    if await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={m.text}'):
        text = await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={m.text}')
    if await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}')
    if await isLockCommand(m.from_user.id, m.chat.id, text):
        return

    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}')
        sent = await m.reply(quote=True, text=await get_message('custom_command.cancel_del', botkey=k))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.cancel_del')
        return

    if text == 'مسح الاوامر' or text == 'مسح الاوامر المضافة':
        if not await mod_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command.perm_mod', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command.perm_mod')
            return
        else:
            members = await rdb.smembers(f'{m.chat.id}:listCustom:{m.chat.id}{Dev_Zaid}')
            if not members:
                sent = await m.reply(quote=True, text=await get_message('custom_command.no_commands', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.no_commands')
                return
            else:
                count = 0
                for cmnd in members:
                    command = cmnd
                    await rdb.delete(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={command}')
                    await rdb.srem(f'{m.chat.id}:listCustom:{m.chat.id}{Dev_Zaid}', command)
                    count += 1
                sent = await m.reply(quote=True, text=await get_message(
                    'custom_command.success_clear_all',
                    botkey=k,
                    mention=m.from_user.mention,
                    count=count,
                ))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.success_clear_all')
                return

    if text == 'مسح امر':
        if not await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}'):
            if not await mod_pls(m.from_user.id, m.chat.id):
                sent = await m.reply(quote=True, text=await get_message('custom_command.perm_mod', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.perm_mod')
                return
            else:
                await rdb.set(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}', 1)
                sent = await m.reply(quote=True, text=await get_message('custom_command.prompt_del', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.prompt_del')
                return

    if await rdb.get(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}') and await admin_pls(m.from_user.id, m.chat.id) and len(m.text) < 50:
        await rdb.delete(f'{m.chat.id}:delCustom:{m.from_user.id}{Dev_Zaid}')
        if not await rdb.get(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={m.text}'):
            sent = await m.reply(quote=True, text=await get_message('custom_command.not_added', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command.not_added')
            return
        await rdb.srem(f'{m.chat.id}:listCustom:{m.chat.id}{Dev_Zaid}', m.text)
        await rdb.delete(f'{m.chat.id}:Custom:{m.chat.id}{Dev_Zaid}&text={m.text}')
        sent = await m.reply(quote=True, text=await get_message(
            'custom_command.success_del',
            botkey=k,
            mention=m.from_user.mention,
        ))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.success_del')
        return


@register("custom_command_global_add")
@Client.on_message(filters.text, group=1001)
@safe_handler
async def customCummandGlobalHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    text = m.text
    if await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}')

    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}')
        sent = await m.reply(quote=True, text=await get_message('custom_command_global.cancel_add', botkey=k))
        await track_sent_message(m.chat.id, sent.id, 'custom_command_global.cancel_add')
        return

    if await rdb.get(f'{m.chat.id}:addCustom2G:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:addCustom2G:{m.from_user.id}{Dev_Zaid}')
        sent = await m.reply(quote=True, text=await get_message('custom_command_global.cancel_add', botkey=k))
        await track_sent_message(m.chat.id, sent.id, 'custom_command_global.cancel_add')
        return

    if text == 'الاوامر العامه' or text == 'الاوامر المضافه العامه' and not m.chat.type == ChatType.PRIVATE:
        if not await dev_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_dev', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_dev')
            return
        else:
            members = await rdb.smembers(f'listCustom:{Dev_Zaid}')
            if not members:
                sent = await m.reply(quote=True, text=await get_message('custom_command_global.no_commands', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.no_commands')
                return
            else:
                txt = 'الاوامر العامه:\n'
                count = 0
                for cmnd in members:
                    count += 1
                    command = cmnd
                    cc = await rdb.get(f'Custom:{Dev_Zaid}&text={command}')
                    old_c = cc
                    txt += f'{count}) {command} ~ ( {old_c} )\n'
                txt += '\n☆'
                return await m.reply(quote=True, text=txt)

    if text == 'اضف امر عام' or text == 'تغيير امر عام':
        if not await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}'):
            if not await dev_pls(m.from_user.id, m.chat.id):
                sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_dev', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_dev')
                return
            else:
                await rdb.set(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}', 1)
                sent = await m.reply(quote=True, text=await get_message('custom_command.prompt_old_command', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.prompt_old_command')
                return

    if await rdb.get(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}') and await dev_pls(m.from_user.id, m.chat.id) and len(m.text) < 50:
        await rdb.delete(f'{m.chat.id}addCustomG:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'{m.chat.id}:addCustom2G:{m.from_user.id}{Dev_Zaid}', m.text)
        sent = await m.reply(quote=True, text=await get_message('custom_command.confirm_old_command', botkey=k, command=m.text))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.confirm_old_command')
        return

    if await rdb.get(f'{m.chat.id}:addCustom2G:{m.from_user.id}{Dev_Zaid}') and await dev_pls(m.from_user.id, m.chat.id) and len(m.text) < 50:
        command_o = await rdb.get(f'{m.chat.id}:addCustom2G:{m.from_user.id}{Dev_Zaid}')
        command_n = m.text
        await rdb.delete(f'{m.chat.id}:addCustom2G:{m.from_user.id}{Dev_Zaid}')
        await rdb.set(f'Custom:{Dev_Zaid}&text={command_n}', command_o)
        await rdb.sadd(f'listCustom:{Dev_Zaid}', command_n)
        sent = await m.reply(quote=True, text=await get_message('custom_command.success_changed', botkey=k, command_old=command_o, command_new=command_n))
        await track_sent_message(m.chat.id, sent.id, 'custom_command.success_changed')
        return


@register("custom_command_global_del")
@Client.on_message(filters.text, group=1002)
@safe_handler
async def delCustomCommandGHandler(c, m):
    k = await rdb.get(f'{Dev_Zaid}:botkey')
    if await rdb.get(f'{m.from_user.id}:mute:{m.chat.id}{Dev_Zaid}'):
        return
    if await rdb.get(f'{m.chat.id}:mute:{Dev_Zaid}') and not await admin_pls(m.from_user.id, m.chat.id):
        return
    if await rdb.get(f'{m.from_user.id}:mute:{Dev_Zaid}'):
        return
    text = m.text
    if await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}'):
        text = await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}')

    if await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}') and text == 'الغاء':
        await rdb.delete(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}')
        sent = await m.reply(quote=True, text=await get_message('custom_command_global.cancel_del', botkey=k))
        await track_sent_message(m.chat.id, sent.id, 'custom_command_global.cancel_del')
        return

    if text == 'مسح الاوامر العامه':
        if not await dev_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_dev', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_dev')
            return
        else:
            members = await rdb.smembers(f'listCustom:{Dev_Zaid}')
            if not members:
                sent = await m.reply(quote=True, text=await get_message('custom_command_global.no_commands', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.no_commands')
                return
            else:
                count = 0
                for cmnd in members:
                    command = cmnd
                    await rdb.delete(f'Custom:{Dev_Zaid}&text={command}')
                    await rdb.srem(f'listCustom:{Dev_Zaid}', command)
                    count += 1
                sent = await m.reply(quote=True, text=await get_message(
                    'custom_command_global.success_clear_all',
                    botkey=k,
                    mention=m.from_user.mention,
                    count=count,
                ))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.success_clear_all')
                return

    if text == 'مسح امر عام':
        if not await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}'):
            if not await dev_pls(m.from_user.id, m.chat.id):
                sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_dev', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_dev')
                return
            else:
                await rdb.set(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}', 1)
                sent = await m.reply(quote=True, text=await get_message('custom_command.prompt_del', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command.prompt_del')
                return

    if text == "الاوامر المقفوله":
        if not await gowner_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_gowner', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_gowner')
            return
        else:
            commands = await rdb.hgetall(Dev_Zaid + f"locks-{m.chat.id}")
            if not commands:
                sent = await m.reply(await get_message('custom_command_global.no_locked_commands', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.no_locked_commands')
                return
            else:
                txt = "الاوامر المقفوله:\n\n"
                count = 1
                for command in commands:
                    cc = int(commands[command])
                    if cc == 0:
                        rank = "مالك اساسي"
                    elif cc == 1:
                        rank = "مالك وفوق"
                    elif cc == 2:
                        rank = "مدير و فوق"
                    elif cc == 3:
                        rank = "ادمن وفوق"
                    elif cc == 4:
                        rank = "مميز و فوق"
                    else:
                        rank = str(cc)
                    txt += f"{count} ) {command} - ( {rank} )\n"
                    count += 1
                return await m.reply(txt, disable_web_page_preview=True)

    if text == "مسح الاوامر المقفوله":
        if not await gowner_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_gowner', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_gowner')
            return
        else:
            commands = await rdb.hgetall(Dev_Zaid + f"locks-{m.chat.id}")
            if not commands:
                sent = await m.reply(await get_message('custom_command_global.no_locked_commands', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.no_locked_commands')
                return
            else:
                count = len(list(commands.keys()))
                await rdb.delete(Dev_Zaid + f"locks-{m.chat.id}")
                sent = await m.reply(await get_message('custom_command_global.success_clear_locked', botkey=k, count=count))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.success_clear_locked')
                return

    if re.match("^فتح امر ", text):
        if not await gowner_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_gowner', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_gowner')
            return
        else:
            txt = text.split(None, 2)[2]
            if not await rdb.hget(Dev_Zaid + f"locks-{m.chat.id}", txt):
                sent = await m.reply(await get_message('custom_command_global.not_locked', botkey=k))
                await track_sent_message(m.chat.id, sent.id, 'custom_command_global.not_locked')
                return
            await rdb.hdel(Dev_Zaid + f"locks-{m.chat.id}", txt)
            sent = await m.reply(await get_message('custom_command_global.success_unlock', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.success_unlock')
            return

    if re.match("^قفل امر ", text):
        if not await gowner_pls(m.from_user.id, m.chat.id):
            sent = await m.reply(quote=True, text=await get_message('custom_command_global.perm_gowner', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.perm_gowner')
            return
        else:
            txt = text.split(None, 2)[2]
            sent = await m.reply(
                await get_message('custom_command_global.lock_prompt', botkey=k, command=txt),
                reply_markup=InlineKeyboardMarkup(
                    [
                        [InlineKeyboardButton("مالك اساسي", callback_data=f"gowner+{m.from_user.id}")],
                        [InlineKeyboardButton("مالك", callback_data=f"owner+{m.from_user.id}")],
                        [InlineKeyboardButton("مدير", callback_data=f"mod+{m.from_user.id}")],
                        [InlineKeyboardButton("ادمن", callback_data=f"admin+{m.from_user.id}")],
                        [InlineKeyboardButton("مميز", callback_data=f"pre+{m.from_user.id}")],
                    ]
                )
            )
            await track_sent_message(m.chat.id, sent.id, 'custom_command_global.lock_prompt')
            return

    if await rdb.get(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}') and await dev_pls(m.from_user.id, m.chat.id) and len(m.text) < 50:
        await rdb.delete(f'{m.chat.id}:delCustomG:{m.from_user.id}{Dev_Zaid}')
        if not await rdb.get(f'Custom:{Dev_Zaid}&text={m.text}'):
            sent = await m.reply(quote=True, text=await get_message('custom_command.not_added', botkey=k))
            await track_sent_message(m.chat.id, sent.id, 'custom_command.not_added')
            return
        await rdb.srem(f'listCustom:{Dev_Zaid}', m.text)
        await rdb.delete(f'Custom:{Dev_Zaid}&text={m.text}')
        sent = await m.reply(quote=True, text=await get_message(
            'custom_command_global.success_del',
            botkey=k,
            mention=m.from_user.mention,
        ))
        await track_sent_message(m.chat.id, sent.id, 'custom_command_global.success_del')
        return
