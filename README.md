# bmqa-v2 — أرضية نظيفة أمنياً

هذا المجلد هو نقطة انطلاق جديدة بنفس بنية مجلدات `bmqa` الأصلي (`Plugins/`,
`helpers/`) لكن **بدون أي قيمة سرية مكتوبة داخل الكود**. لم يُلمس مجلد `bmqa`
الأصلي إطلاقاً.

## الملفات الجاهزة في هذه النسخة

- `.env.example` — كل أسماء المتغيرات الحساسة (توكن، API_ID/HASH، إلخ) بدون قيمها.
- `config.py` — يقرأ كل شيء من `os.environ` عبر `python-dotenv`، بدون أي قيمة مكتوبة صراحة.
- `.gitignore` — يستثني `.env`, ملفات `*.session`, `__pycache__/`, وقواعد sqlite.
- `SECURITY_AUDIT_REPORT.md` — **اقرأ هذا الملف أولاً**: يسرد كل قيمة سرية كانت
  مكتوبة صراحة في الكود القديم (config.py, information.py, main.py, Plugins/all.py)
  حتى تراجعها وتدوّرها يدوياً قبل أي تشغيل فعلي.
- `Plugins/`, `helpers/` — مجلدات فارغة بنفس بنية المشروع الأصلي، جاهزة لنقل
  الكود إليها تدريجياً بعد تنظيفه من أي قيمة مكتوبة صراحة (استبدلها بقراءة من
  `config.py` بدلاً من ذلك).

## خطوات الإعداد

```bash
cp .env.example .env
# عدّل .env وضع القيم الجديدة (بعد تدويرها حسب SECURITY_AUDIT_REPORT.md)
pip install -r requirements.txt
```

## تشغيل الطابور الخلفي (arq worker) — لتحميلات downloader.py

`Plugins/downloader.py` لا يعد يحمّل يوتيوب/تيك توك/ساوند كلاود أو يشغّل
ffmpeg داخل عملية البوت نفسها. كل عملية ثقيلة تُرسَل فوراً إلى طابور Redis
(عبر `arq`، انظر `core/worker.py`)، والبوت يرد فوراً بـ"⏳ جاري التنفيذ..."
ثم عملية **worker منفصلة** هي من تُنفّذ التحميل/التحويل الفعلي وتُرسل
النتيجة/تُحدّث رسالة الحالة عند الانتهاء.

**لهذا يجب تشغيل عمليتين منفصلتين دائماً معاً**: البوت (`main.py`) والـ
worker (`arq core.worker.WorkerSettings`). لو شغّلت البوت فقط بدون worker،
ستبقى كل أوامر التحميل عالقة عند "⏳ جاري التنفيذ..." للأبد (المهمة تنتظر في
الطابور بلا من ينفّذها).

### متطلبات إضافية على مستوى النظام

```bash
# ffmpeg مطلوب فعلياً على السيرفر (وليس فقط كحزمة بايثون):
sudo apt update && sudo apt install -y ffmpeg
```

### أوامر التشغيل المحلي (Terminal 1 + Terminal 2)

```bash
# 0) مرة واحدة فقط: البيئة + الاعتماديات
cp .env.example .env   # ثم عدّل القيم داخل .env
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# تأكد أن Redis يعمل محلياً (أو عدّل REDIS_HOST/REDIS_PORT في .env
# ليشيرا لسيرفر Redis خارجي):
redis-server --daemonize yes

# Terminal 1: البوت نفسه
source .venv/bin/activate
python3 main.py

# Terminal 2: الـ worker (نفس البيئة الافتراضية، بنفس متغيرات .env)
source .venv/bin/activate
arq core.worker.WorkerSettings
```

- شغّل الأمرين في نافذتي طرفية منفصلتين (أو عبر `tmux`/`screen`/`supervisor`
  في الإنتاج) — كلاهما ضروري لعمل أوامر التحميل.
- ملفات التحميل المؤقتة تُحفظ في `downloads/` (قابل للتغيير عبر متغير بيئة
  `DOWNLOAD_DIR`) وتُحذف تلقائياً بعد إرسال النتيجة أو عند فشل المهمة.

## ما لم يُنقل بعد

لم يتم نسخ محتوى `Plugins/*.py` و `helpers/*.py` و `main.py` من المشروع
الأصلي تلقائياً، لأن أغلبها يستورد أسرار من `config.py`/`information.py`
مباشرة (`from config import token`, إلخ) وبحاجة لمراجعة قبل النقل. الخطوة
التالية المقترحة: انسخ كل ملف على حدة، وتأكد أن أي استيراد لقيمة سرية يمر عبر
`config.py` الجديد (مثل `from config import token, api_id, api_hash`) وليس
عبر قيمة مكتوبة مباشرة.
