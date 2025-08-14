from telegram import InlineKeyboardMarkup, InlineKeyboardButton
from storage import get_admins, add_admin, delete_admin
from config import ADMINS as ENV_ADMINS


def _to_int_set(values) -> set[int]:
    s: set[int] = set()
    if not values:
        return s
    for v in values:
        try:
            s.add(int(v))
        except Exception:
            continue
    return s


def is_admin(user_id: int) -> bool:
    """
    .env dagi ADMINS va DB dagi adminlar roʻyxatini birlashtirib tekshiradi.
    Shunday qilib, admin panel orqali qoʻshilgan yangi admin ham zudlik bilan tan olinadi.
    """
    # .env dagi (config.ADMINS) — odatda [int, int, ...]
    env_admins: set[int] = _to_int_set(ENV_ADMINS)

    # DB dagi adminlar
    try:
        db_admins: set[int] = {int(r["id"]) for r in get_admins()}
    except Exception:
        db_admins = set()

    return int(user_id) in env_admins or int(user_id) in db_admins


def load_admins() -> dict:
    """
    admin_manage.py mosligi uchun: DB dagi adminlarni
    { "123": {"id":123, "name":"..."} } ko‘rinishida qaytaradi.
    """
    data = get_admins()  # [{'id':..., 'name':...}]
    return {str(r["id"]): {"id": int(r["id"]), "name": r.get("name") or ""} for r in data}


def save_admins(admins: dict):
    """
    admin_manage.py mosligi uchun: berilgan dict ni DB bilan sinxronlashtiradi.
    Minimal diff bilan ishlaydi: yangilarni qo‘shadi, mavjuddan yo‘q bo‘lganlarini o‘chiradi.
    """
    existing = load_admins()
    # qo'shilganlar
    for k, v in admins.items():
        if k not in existing:
            add_admin(int(v["id"]), v.get("name") or "")
    # o'chirilganlar
    for k in list(existing.keys()):
        if k not in admins:
            delete_admin(int(k))


# Orqaga/Asosiy klaviatura (admin bo'limlarida)
BACK_HOME_KB = InlineKeyboardMarkup([
    [
        InlineKeyboardButton("🔙 Ortga", callback_data="admin_panel"),
        InlineKeyboardButton("🏠 Asosiy menyu", callback_data="home")
    ]
])
