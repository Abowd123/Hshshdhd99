"""
core/keys.py — bmqa-v2
مركزيّة بناء مفاتيح Redis الموحّدة عبر المشروع.
"""

from config import Dev_Zaid


def message_override_key(message_id: str) -> str:
    """يبني مفتاح Redis الموحّد لتخزين نص رسالة مُخصَّص (override) لمعرّف رسالة معيّن."""
    return f"msgoverride:{message_id}{Dev_Zaid}"


def sent_message_key(chat_id: int, telegram_message_id: int) -> str:
    """
    يبني مفتاح Redis الموحّد لتتبّع الرسائل المُرسَلة.
    الصيغة: sentmsg:{chat_id}:{telegram_message_id}{Dev_Zaid}
    مثال:   sentmsg:-1001234567890:99112{Dev_Zaid}
    """
    return f"sentmsg:{chat_id}:{telegram_message_id}{Dev_Zaid}"
