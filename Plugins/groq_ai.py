"""
Plugins/groq_ai.py — bmqa-v2
تكامل Groq API (استدلال سريع لنماذج اللغة عبر endpoint متوافق مع OpenAI).

الأوامر:
  - ذكاء <سؤال>                  (نص عربي، يعمل داخل القروبات — group=41)
  - /ai <سؤال>  أو  /so2al <سؤال>  (يعمل في الخاص والقروبات، ويدعم الرد على
    رسالة نصية بدل كتابة السؤال مباشرة)
  - تفعيل الذكاء / تعطيل الذكاء   (المدير وفوق فقط، تفعيل/تعطيل لكل قروب)

المتطلبات:
  - متغير بيئة GROQ_API_KEY (احصل عليه من https://console.groq.com/keys).
    لو غير مضبوط، الأمر يرد برسالة توضيحية بدل الفشل الصامت.
  - GROQ_MODEL اختياري (افتراضياً "openai/gpt-oss-20b").

التنفيذ يعتمد على helpers.utils.http (عميل httpx المشترك في المشروع، بدل
إنشاء عميل HTTP جديد) + core.rate_limit.rate_limited لمنع إغراق الحساب
بطلبات متكررة من نفس المستخدم.
"""

import logging

from pyrogram import Client, filters
from pyrogram.enums import ChatAction, ChatType

from config import Dev_Zaid, groq_api_key, groq_model
from core.db import rdb, redis_client
from core.errors import safe_handler
from core.dispatcher import register
from core.rate_limit import is_allowed, rate_limited
from helpers.ranks import admin_pls, isLockCommand
from helpers.utils import http

logger = logging.getLogger(__name__)

GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"
MAX_REPLY_LEN = 4000  # حد تيليجرام الفعلي 4096 حرف، نترك هامش أمان

SYSTEM_PROMPT = (
    "أنت مساعد ذكاء اصطناعي داخل بوت تيليجرام. رد بالعربية بشكل واضح ومباشر "
    "ومفيد، وحافظ على إجابات مركّزة وقصيرة نسبياً ما لم يطلب المستخدم التفصيل."
)


async def _resolve_text(m) -> str:
    """يطبّع نص الرسالة (يزيل اسم البوت من البداية) بنفس أسلوب باقي الملفات."""
    text = m.text or ""
    name = await rdb.get(f"{Dev_Zaid}:BotName") or "ليو"
    if text.startswith(f"{name} "):
        text = text.replace(f"{name} ", "", 1)
    return text


async def _ask_groq(prompt: str) -> str:
    """يرسل السؤال إلى Groq ويرجع نص الإجابة، أو رسالة خطأ عربية واضحة."""
    if not groq_api_key:
        return (
            "❌ لم يتم ضبط GROQ_API_KEY بعد.\n"
            "راجع مالك البوت لإضافة المفتاح من https://console.groq.com/keys"
        )

    prompt = (prompt or "").strip()
    if not prompt:
        return "❌ اكتب سؤالك بعد الأمر، مثال:\nذكاء ما هي عاصمة السعودية؟"

    payload = {
        "model": groq_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.6,
        "max_completion_tokens": 1024,
    }
    headers = {
        "Authorization": f"Bearer {groq_api_key}",
        "Content-Type": "application/json",
    }

    try:
        resp = await http.post(GROQ_URL, headers=headers, json=payload)
    except Exception:
        logger.exception("Groq API: فشل الاتصال")
        return "❌ تعذر الاتصال بخدمة الذكاء الاصطناعي، حاول بعد قليل."

    if resp.status_code == 401:
        logger.error("Groq API: مفتاح غير صحيح (401)")
        return "❌ مفتاح GROQ_API_KEY غير صحيح، راجع مالك البوت."
    if resp.status_code == 429:
        return "⏳ تم تجاوز الحد المسموح من طلبات Groq حالياً، حاول بعد قليل."
    if resp.status_code >= 400:
        logger.error("Groq API error %s: %s", resp.status_code, resp.text[:500])
        return "❌ حدث خطأ من خدمة الذكاء الاصطناعي، حاول لاحقاً."

    try:
        data = resp.json()
        answer = data["choices"][0]["message"]["content"].strip()
    except Exception:
        logger.exception("Groq API: شكل رد غير متوقع")
        return "❌ رد غير متوقع من خدمة الذكاء الاصطناعي."

    if not answer:
        return "❌ لم ترجع خدمة الذكاء الاصطناعي أي رد."
    if len(answer) > MAX_REPLY_LEN:
        answer = answer[:MAX_REPLY_LEN] + "…"
    return answer


async def _handle_ai_request(c, m, prompt: str) -> None:
    """منطق مشترك: يستخدم نص الرسالة المرفوع عليها الرد لو لم يُكتب سؤال،
    يعرض حالة "يكتب..." أثناء الانتظار، ثم يرسل جواب Groq."""
    if not prompt and m.reply_to_message and m.reply_to_message.text:
        prompt = m.reply_to_message.text

    try:
        await m.reply_chat_action(ChatAction.TYPING)
    except Exception:
        pass

    answer = await _ask_groq(prompt)
    await m.reply(answer, quote=True)


# ══════════════════════════════════════════════════════════════════════════
# /ai و /so2al — يعمل في الخاص والقروبات (لا يمر بالجدول المركزي)
# ══════════════════════════════════════════════════════════════════════════
@register("groq_ai_commands")
@Client.on_message(filters.command(["ai", "so2al"]))
@safe_handler
@rate_limited(redis_client, "groq_ai", max_commands=6, window_seconds=60)
async def aiCommandHandler(c, m) -> None:
    if m.chat and m.chat.type in (ChatType.GROUP, ChatType.SUPERGROUP):
        if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
            return
        if await rdb.get(f"{m.chat.id}:disableAI:{Dev_Zaid}"):
            return await m.reply("❌ أمر الذكاء الاصطناعي معطل في هذا القروب.")

    prompt = " ".join(m.command[1:]) if len(m.command) > 1 else ""
    await _handle_ai_request(c, m, prompt)


# ══════════════════════════════════════════════════════════════════════════
# ذكاء <سؤال> + تفعيل/تعطيل الذكاء — نص عربي داخل القروبات فقط (group=41،
# رقم غير مستخدم في أي ملف آخر من الـ Plugins حالياً)
# ══════════════════════════════════════════════════════════════════════════
@Client.on_message(filters.text & filters.group, group=41)
@safe_handler
async def aiGroupTextHandler(c, m) -> None:
    if not await rdb.get(f"{m.chat.id}:enable:{Dev_Zaid}"):
        return

    text = await _resolve_text(m)
    uid, cid = m.from_user.id, m.chat.id
    k = await rdb.get(f"{Dev_Zaid}:botkey")
    mention = m.from_user.mention

    # ── تفعيل/تعطيل الميزة لهذا القروب (المدير وفوق) ───────────────────
    if text == "تعطيل الذكاء":
        if not await admin_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if await rdb.get(f"{cid}:disableAI:{Dev_Zaid}"):
            return await m.reply(f"{k} من「 {mention} 」\n{k} أمر الذكاء معطل من قبل\n☆")
        await rdb.set(f"{cid}:disableAI:{Dev_Zaid}", 1)
        return await m.reply(f"{k} من「 {mention} 」\n{k} ابشر عطلت أمر الذكاء\n☆")

    if text == "تفعيل الذكاء":
        if not await admin_pls(uid, cid):
            return await m.reply(f"{k} هذا الامر يخص ( المدير وفوق ) بس")
        if not await rdb.get(f"{cid}:disableAI:{Dev_Zaid}"):
            return await m.reply(f"{k} من「 {mention} 」\n{k} أمر الذكاء مفعل من قبل\n☆")
        await rdb.delete(f"{cid}:disableAI:{Dev_Zaid}")
        return await m.reply(f"{k} من「 {mention} 」\n{k} ابشر فعلت أمر الذكاء\n☆")

    # ── السؤال نفسه: "ذكاء ..." أو "ذكاء" فقط (رد على رسالة) ───────────
    if text == "ذكاء" or text.startswith("ذكاء "):
        if await rdb.get(f"{cid}:disableAI:{Dev_Zaid}"):
            return await m.reply(f"{k} أمر الذكاء معطل في هذا القروب")
        if await isLockCommand(uid, cid, text):
            return
        # فحص معدل الاستخدام هنا فقط (وليس عبر ديكوريتر على كامل الهاندلر)
        # لأن هذا الهاندلر يستقبل كل رسائل القروب النصية، فلو طُبِّق الديكوريتر
        # على كامل الدالة لكان يستهلك حصة المستخدم من رسائله العادية أيضاً.
        if not await is_allowed(redis_client, uid, "groq_ai_text", max_commands=6, window_seconds=60):
            return await m.reply(f"{k} استخدمت أمر الذكاء كثيراً، حاول بعد دقيقة")
        prompt = text[len("ذكاء"):].strip()
        return await _handle_ai_request(c, m, prompt)
