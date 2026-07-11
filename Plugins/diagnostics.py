"""
Plugins/diagnostics.py — bmqa-v2
أداة فحص شاملة "عند الطلب" — نسخة مدمجة من أداتين:
  1) الفحص الحي لهاندلرز Pyrogram (dispatcher.groups) + طابور arq الداخلي
     (كان سابقاً Plugins/diagnostics.py).
  2) فحص الخدمات الخارجية الحقيقية المستخدمة فعلاً في المشروع + تفصيل
     COMMAND_HANDLERS إلى أوامر قابلة للتوجيه مقابل تسميات مجموعات توثيقية
     (كان سابقاً Plugins/system_check.py).
تم دمجهما في ملف واحد لتفادي تسجيل أمرين منفصلين لنفس الغرض (وتعارض
محتمل لو سُجّل الملفان معاً بدون تنسيق).

التشغيل: ضع هذا الملف فقط داخل Plugins/ (لا تُضِف Plugins/system_check.py
بجانبه — تم استيعاب كل ما فيه هنا). أعد تشغيل البوت.

الأمر: أي من التالي (خاص فقط، SUDO_ID فقط):
  - "فحص الاوامر" أو "فحص_الاوامر"  (نص عربي)
  - /check أو /status                 (أمر سلاش)

يعتمد فقط على مكتبات/متغيرات موجودة بالفعل في المشروع (httpx عبر
helpers/utils.py، pytz). يحتاج فقط إضافة واحدة في config.py:
  groq_api_key = _optional("GROQ_API_KEY")   ← اختياري تماماً، لا يكسر شيء
  إن لم تُضِفها ستحصل على ImportError عند تحميل هذا الملف.

ما يفحصه التقرير:
  1. Redis (زمن استجابة PING الفعلي).
  2. طابور arq الداخلي (تحميلات downloader.py عبر core/worker.py) —
     عدد المهام العالقة فعلياً في Redis (تحذير لو worker متوقف).
  3. الخدمات الخارجية الحقيقية المستخدمة في الكود (طلب HTTP فعلي متوازٍ،
     مهلة قصيرة لكل خدمة حتى لا يتعلّق التقرير بسبب خدمة واحدة بطيئة):
       - الترجمة (hozory) — Plugins/all_features_toggle.py
       - تحويل نص لصوت (eduardo-tate) — Plugins/all_voice_and_blocklist.py
       - جسر gptzaid — Plugins/private_and_sudos.py
       - فحص تاريخ التسجيل (regdate) — helpers/get_create.py
       - Groq AI — فقط إن ضُبط GROQ_API_KEY (لا ميزة فعلية تستخدمه بعد،
         الفحص جاهز مسبقاً ليوم ما يُفعَّل).
     ⚠️ ملاحظة: ARQ_API_URL (arq.hamker.dev) غير مستخدم فعلياً في أي Plugin
     حالياً بالمشروع (تحقّقتُ: لا استيراد له خارج config.py) — لذا لم يُدرَج
     كخدمة مفحوصة هنا تفادياً لتقرير مضلّل عن اعتمادية غير حقيقية. إن كان
     له استخدام فعلي تنوي إضافته، أخبرني لأدرجه بدقة.
  4. عدد ملفات .py داخل Plugins/ على القرص مقابل عدد الملفات المحمَّلة
     فعلياً وقت التشغيل (اختلاف بينهما = ملف فشل تحميله، غالباً SyntaxError
     أو ImportError صامت في سجلات البوت).
  5. عدد الأوامر النصية القابلة للتوجيه المباشر عبر core.dispatcher مقابل
     تسميات المجموعات التوثيقية فقط، مع أمثلة.
  6. توزيع هاندلرز Pyrogram الحية حسب رقم group (من dispatcher.groups
     مباشرة، حيّ 100%، يشمل حتى الملفات غير المسجَّلة في COMMAND_HANDLERS).
  7. قائمة مرجعية ثابتة لأوامر "/" (eval/exec/ai/check...) — تحتاج تحديث
     يدوي عند إضافة أمر "/" جديد (موضّح كتعليق في SLASH_COMMANDS بالأسفل).
"""
from __future__ import annotations

import asyncio
import os
import sys
import time
from datetime import datetime

import pytz
from pyrogram import Client, filters

from config import arq_api_key, groq_api_key, sudo_id  # noqa: F401 (arq_api_key محفوظ للتوثيق فقط)
from core.dispatcher import COMMAND_HANDLERS
from core.errors import safe_handler
from helpers.utils import http

CHECK_TIMEOUT = 6  # ثوانٍ لكل خدمة خارجية
MAX_MSG = 3500  # هامش أمان تحت حد تيليجرام (4096) — تقسيم بدل اقتصاص

# قائمة مرجعية بأوامر "/" الثابتة غير المسجَّلة في core.dispatcher
# (حدّثها يدوياً عند إضافة أمر /command جديد لا يمرّ بالجدول المركزي)
SLASH_COMMANDS = [
    "/eval, /exec, /cmd, /print — تنفيذ كود (SUDO فقط)",
    "/sc, /webs, /ss — سكرين شوت لموقع (SUDO فقط)",
    "/check, /status — هذا التقرير (SUDO فقط)",
]


def _chunks(text: str, size: int = MAX_MSG):
    lines = text.split("\n")
    buf = ""
    for line in lines:
        if len(buf) + len(line) + 1 > size:
            yield buf
            buf = line
        else:
            buf = f"{buf}\n{line}" if buf else line
    if buf:
        yield buf


# ── فحص Redis + طابور arq الداخلي ────────────────────────────────────────

async def _redis_health() -> str:
    try:
        from core.db import redis_client
        t0 = time.perf_counter()
        await redis_client.ping()
        ms = (time.perf_counter() - t0) * 1000
        return f"✅ Redis — متصل ({ms:.1f}ms)"
    except Exception as e:
        return f"❌ Redis — {type(e).__name__}"


async def _arq_queue_health() -> str:
    """اسم الطابور الافتراضي لـ arq هو 'arq:queue' ما لم يُخصَّص queue_name صراحة
    في core/worker.py."""
    try:
        from core.db import redis_client
        pending = await redis_client.zcard("arq:queue")
        if pending == 0:
            return "✅ طابور arq الداخلي (تحميلات) — لا مهام عالقة"
        return f"⚠️ طابور arq الداخلي — {pending} مهمة عالقة (تحقّق أن الـ worker يعمل)"
    except Exception as e:
        return f"❔ طابور arq الداخلي — تعذّر الفحص ({type(e).__name__})"


# ── فحص الخدمات الخارجية الحقيقية ────────────────────────────────────────

async def _check_service(name: str, url: str, headers: dict | None = None) -> str:
    start = time.monotonic()
    try:
        resp = await http.get(url, headers=headers or {}, timeout=CHECK_TIMEOUT)
        ms = int((time.monotonic() - start) * 1000)
        if resp.status_code < 500:
            return f"✅ {name} — {resp.status_code} ({ms}ms)"
        return f"⚠️ {name} — خطأ سيرفر {resp.status_code} ({ms}ms)"
    except Exception as e:
        ms = int((time.monotonic() - start) * 1000)
        return f"❌ {name} — لا يستجيب ({type(e).__name__}, {ms}ms)"


async def _regdate_check() -> str:
    """يعيد استخدام الدالة الحقيقية helpers.get_create.get_creation_date على
    آيدي المطوّر نفسه (SUDO_ID) بدل تخمين رابط عام — هذا فحص دقيق فعلي
    للمسار/الطريقة/الهيدرز الصحيحة المستخدمة فعلاً في الكود، لا تخمين."""
    start = time.monotonic()
    try:
        from helpers.get_create import get_creation_date
        date = await asyncio.wait_for(get_creation_date(sudo_id), timeout=CHECK_TIMEOUT)
        ms = int((time.monotonic() - start) * 1000)
        return f"✅ فحص تاريخ التسجيل (regdate) — نجح ({ms}ms, تاريخك: {date})"
    except Exception as e:
        ms = int((time.monotonic() - start) * 1000)
        return f"❌ فحص تاريخ التسجيل (regdate) — {type(e).__name__} ({ms}ms)"


async def _external_services_report() -> list[str]:
    # المسارات هنا مطابقة تماماً لما تستدعيه الأكواد الفعلية (وليست تخميناً
    # على الدومين العام فقط) — الأولى كانت تعطي 404 خاطئ على regdate لأنها
    # كانت تطلب الدومين المجرّد بدل المسار/الطريقة الصحيحة.
    checks = [
        _check_service("الترجمة (hozory)", "https://hozory.com/translate/?target=en&text=test"),
        _check_service("تحويل نص لصوت (eduardo-tate)", "https://eduardo-tate.com/AI/voice.php?text=test"),
        _check_service("جسر gptzaid", "https://gptzaid.zaidbot.repl.co/1/text=test"),
        _regdate_check(),
    ]
    if groq_api_key:
        checks.append(_check_service(
            "Groq AI",
            "https://api.groq.com/openai/v1/models",
            headers={"Authorization": f"Bearer {groq_api_key}"},
        ))
    else:
        checks.append(asyncio.sleep(0, result="⚪ Groq AI — غير مُفعّل (لا يوجد GROQ_API_KEY، ولا ميزة تستخدمه بعد)"))

    results = await asyncio.gather(*checks, return_exceptions=True)
    return [
        r if isinstance(r, str) else f"❌ خطأ غير متوقع أثناء الفحص ({type(r).__name__})"
        for r in results
    ]


# ── فحص الأوامر والملفات ─────────────────────────────────────────────────

def _count_plugin_files_on_disk() -> int:
    plugins_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "Plugins")
    count = 0
    for root, _, files in os.walk(plugins_dir):
        count += sum(1 for f in files if f.endswith(".py") and not f.startswith("__"))
    return count


def _count_plugin_modules_loaded() -> int:
    return sum(
        1 for name in sys.modules
        if name.startswith("Plugins.") and "." not in name[len("Plugins."):]
    )


def _dispatcher_summary() -> tuple[int, int, list[str]]:
    """تمييز حسب توثيق core/dispatcher.py: مفاتيح بلا '_' = أوامر نصية حقيقية
    قابلة للتوجيه المباشر، مفاتيح فيها '_' = تسميات مجموعات توثيقية فقط."""
    real_commands = sorted(k.strip() for k in COMMAND_HANDLERS if "_" not in k)
    labels_only = [k for k in COMMAND_HANDLERS if "_" in k]
    return len(real_commands), len(labels_only), real_commands


def _handler_report(c: Client) -> tuple[int, str]:
    """يقرأ c.dispatcher.groups الحي وقت التشغيل — يشمل حتى الهاندلرز التي لا
    تمر عبر COMMAND_HANDLERS إطلاقاً (مثل group=17 وgroup=32 وغيرها)."""
    groups = getattr(getattr(c, "dispatcher", None), "groups", None)
    if not groups:
        return 0, "⚠️ لم أستطع قراءة dispatcher.groups من العميل الحالي."

    total = 0
    lines = []
    for gid in sorted(groups.keys()):
        handlers = groups[gid]
        total += len(handlers)
        names = [getattr(getattr(h, "callback", None), "__name__", "?") for h in handlers]
        names_str = "، ".join(names[:6]) + (" …" if len(names) > 6 else "")
        lines.append(f"  group={gid:<6} ({len(handlers)}): {names_str}")

    return total, "\n".join(lines)


# ── الهاندلر الرئيسي ─────────────────────────────────────────────────────

@Client.on_message(
    (
        filters.command(["check", "status"])
        | (filters.text & filters.regex(r"^فحص[_ ]الاوامر$"))
    )
    & filters.private
    & filters.user(sudo_id),
    group=999,
)
@safe_handler
async def systemCheckHandler(c: Client, m) -> None:
    status_msg = await m.reply("⏳ جاري فحص كل الأوامر والخدمات...", quote=True)

    # 1) Redis + طابور arq الداخلي (متوازي مع فحص الخدمات الخارجية)
    redis_task = _redis_health()
    arq_task = _arq_queue_health()
    services_task = _external_services_report()
    redis_status, arq_status, service_lines = await asyncio.gather(
        redis_task, arq_task, services_task
    )

    # 2) ملخّص الأوامر
    real_count, labels_count, real_commands = _dispatcher_summary()
    disk_count = _count_plugin_files_on_disk()
    loaded_count = _count_plugin_modules_loaded()
    total_handlers, handler_breakdown = _handler_report(c)

    commands_preview = "، ".join(real_commands[:25])
    if len(real_commands) > 25:
        commands_preview += f" ... (+{len(real_commands) - 25} أخرى)"

    plugins_line = f"• ملفات .py على القرص: {disk_count} — المحمَّلة فعلياً: {loaded_count}"
    if disk_count != loaded_count:
        plugins_line += f" ⚠️ فرق {abs(disk_count - loaded_count)} (تحقّق من سجلات البوت)"

    now = datetime.now(pytz.timezone("Asia/Riyadh")).strftime("%Y-%m-%d %I:%M %p")

    report = (
        f"📋 تقرير فحص البوت الشامل — {now}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🗄️ {redis_status}\n"
        f"📥 {arq_status}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🔌 الخدمات الخارجية المستخدمة فعلياً بالمشروع:\n"
        + "\n".join(service_lines) + "\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"🧩 الأوامر والملفات:\n"
        f"{plugins_line}\n"
        f"• أوامر نصية موجّهة مباشرة عبر dispatcher: {real_count}\n"
        f"• تسميات مجموعات توثيقية فقط: {labels_count}\n"
        f"• إجمالي هاندلرز Pyrogram الحية (dispatcher.groups): {total_handlers}\n"
        f"• أمثلة على الأوامر الموجَّهة: {commands_preview or '—'}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"📁 توزيع الهاندلرز حسب group:\n{handler_breakdown}\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⌨️ أوامر \"/\" ثابتة (مرجع يدوي):\n"
        + "\n".join(f"• {line}" for line in SLASH_COMMANDS)
    )

    parts = list(_chunks(report))
    await status_msg.edit(parts[0])
    for extra in parts[1:]:
        await m.reply(extra)
