"""
💰 FinanceBot v3 — Telegram-бот для учёта финансов
- 3 языка: Русский, English, Deutsch
- Месячный учёт доходов и расходов
- Категории трат (подписки = обычная категория)
- Удаление и редактирование записей
- Итоги по категориям и общий
- История месяцев
"""

import os
import logging
import sqlite3
from datetime import datetime
from pathlib import Path

from telegram import (
    Update, InlineKeyboardButton, InlineKeyboardMarkup
)
from telegram.ext import (
    Application, CommandHandler, CallbackQueryHandler,
    MessageHandler, ContextTypes, filters
)

# ─── Настройки ───────────────────────────────────────────────
BOT_TOKEN = os.getenv("BOT_TOKEN", "YOUR_BOT_TOKEN_HERE")
DB_PATH = Path(__file__).parent / "finance.db"

logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

# ─── Категории ───────────────────────────────────────────────
CATEGORIES = {
    "food":    {"ru": "🍔 Еда",               "en": "🍔 Food",            "de": "🍔 Essen"},
    "fuel":    {"ru": "⛽ Бензин",             "en": "⛽ Fuel",            "de": "⛽ Benzin"},
    "invest":  {"ru": "📈 Инвестирование",     "en": "📈 Investments",     "de": "📈 Investitionen"},
    "clothes": {"ru": "👕 Одежда",             "en": "👕 Clothes",         "de": "👕 Kleidung"},
    "health":  {"ru": "💊 Здоровье",           "en": "💊 Health",          "de": "💊 Gesundheit"},
    "forced":  {"ru": "⚠️ Вынужденные траты",  "en": "⚠️ Forced expenses", "de": "⚠️ Pflichtausgaben"},
    "subs":    {"ru": "🔄 Подписки",           "en": "🔄 Subscriptions",   "de": "🔄 Abonnements"},
    "other":   {"ru": "📦 Прочее",             "en": "📦 Other",           "de": "📦 Sonstiges"},
}
CATEGORY_KEYS = list(CATEGORIES.keys())

# ─── Переводы интерфейса ─────────────────────────────────────
T = {
    "welcome": {
        "ru": (
            "💰 *FinanceBot* — учёт финансов\n\n"
            "Я помогу отслеживать доходы и расходы по месяцам.\n\n"
            "📌 *Как пользоваться:*\n"
            "1️⃣ Начни новый месяц\n"
            "2️⃣ Вноси доходы и расходы\n"
            "3️⃣ Подводи итоги\n"
            "4️⃣ Завершай месяц и начинай новый\n\n"
            "Нажми /menu чтобы начать!"
        ),
        "en": (
            "💰 *FinanceBot* — finance tracker\n\n"
            "I'll help you track income and expenses monthly.\n\n"
            "📌 *How to use:*\n"
            "1️⃣ Start a new month\n"
            "2️⃣ Add income and expenses\n"
            "3️⃣ Check summaries\n"
            "4️⃣ Close month and start a new one\n\n"
            "Press /menu to begin!"
        ),
        "de": (
            "💰 *FinanceBot* — Finanzverwaltung\n\n"
            "Ich helfe dir, Einnahmen und Ausgaben monatlich zu verfolgen.\n\n"
            "📌 *So funktioniert's:*\n"
            "1️⃣ Starte einen neuen Monat\n"
            "2️⃣ Trage Einnahmen und Ausgaben ein\n"
            "3️⃣ Sieh dir die Zusammenfassung an\n"
            "4️⃣ Schließe den Monat ab und starte neu\n\n"
            "Drücke /menu um zu beginnen!"
        ),
    },
    "choose_lang": {
        "ru": "🌍 Выбери язык:",
        "en": "🌍 Choose language:",
        "de": "🌍 Sprache wählen:",
    },
    "lang_set": {
        "ru": "✅ Язык: Русский\n\nНажми /menu",
        "en": "✅ Language: English\n\nPress /menu",
        "de": "✅ Sprache: Deutsch\n\nDrücke /menu",
    },
    "no_month": {
        "ru": "💰 *FinanceBot*\n\nУ тебя нет активного месяца.\nНачни новый чтобы вести учёт!",
        "en": "💰 *FinanceBot*\n\nYou have no active month.\nStart a new one to begin tracking!",
        "de": "💰 *FinanceBot*\n\nDu hast keinen aktiven Monat.\nStarte einen neuen!",
    },
    "current_month": {
        "ru": "📅 *Текущий месяц: {}*\n\n💵 Доходы: {}\n💸 Расходы: {}\n{} Баланс: {}\n",
        "en": "📅 *Current month: {}*\n\n💵 Income: {}\n💸 Expenses: {}\n{} Balance: {}\n",
        "de": "📅 *Aktueller Monat: {}*\n\n💵 Einnahmen: {}\n💸 Ausgaben: {}\n{} Saldo: {}\n",
    },
    "btn_expense":    {"ru": "💸 Расход",        "en": "💸 Expense",        "de": "💸 Ausgabe"},
    "btn_income":     {"ru": "💵 Доход",         "en": "💵 Income",         "de": "💵 Einnahme"},
    "btn_summary":    {"ru": "📊 Итоги месяца",  "en": "📊 Monthly summary","de": "📊 Monatsübersicht"},
    "btn_all":        {"ru": "📋 Все записи",    "en": "📋 All entries",    "de": "📋 Alle Einträge"},
    "btn_close":      {"ru": "🏁 Завершить месяц","en": "🏁 Close month",   "de": "🏁 Monat abschließen"},
    "btn_history":    {"ru": "📚 История месяцев","en": "📚 Month history",  "de": "📚 Monatshistorie"},
    "btn_new_month":  {"ru": "🆕 Начать новый месяц","en": "🆕 Start new month","de": "🆕 Neuen Monat starten"},
    "btn_lang":       {"ru": "🌍 Язык",         "en": "🌍 Language",       "de": "🌍 Sprache"},
    "btn_menu":       {"ru": "◀️ Меню",          "en": "◀️ Menu",           "de": "◀️ Menü"},
    "btn_more_exp":   {"ru": "💸 Ещё расход",    "en": "💸 More expense",   "de": "💸 Weitere Ausgabe"},
    "btn_more_inc":   {"ru": "💵 Ещё доход",     "en": "💵 More income",    "de": "💵 Weitere Einnahme"},
    "new_month_ask": {
        "ru": "🆕 *Новый месяц*\n\nНапиши название (например: Март 2026):",
        "en": "🆕 *New month*\n\nEnter name (e.g. March 2026):",
        "de": "🆕 *Neuer Monat*\n\nName eingeben (z.B. März 2026):",
    },
    "month_created": {
        "ru": "✅ Месяц *{}* создан!\n\nТеперь можешь вносить доходы и расходы.",
        "en": "✅ Month *{}* created!\n\nYou can now add income and expenses.",
        "de": "✅ Monat *{}* erstellt!\n\nDu kannst jetzt Einnahmen und Ausgaben eintragen.",
    },
    "new_expense": {
        "ru": "💸 *Новый расход*\n\nНапиши название траты:",
        "en": "💸 *New expense*\n\nEnter expense name:",
        "de": "💸 *Neue Ausgabe*\n\nName der Ausgabe:",
    },
    "new_income": {
        "ru": "💵 *Новый доход*\n\nНапиши название (например: Зарплата):",
        "en": "💵 *New income*\n\nEnter name (e.g. Salary):",
        "de": "💵 *Neue Einnahme*\n\nName eingeben (z.B. Gehalt):",
    },
    "enter_amount": {
        "ru": "💰 Введи сумму:",
        "en": "💰 Enter amount:",
        "de": "💰 Betrag eingeben:",
    },
    "choose_cat": {
        "ru": "📂 Выбери категорию:",
        "en": "📂 Choose category:",
        "de": "📂 Kategorie wählen:",
    },
    "enter_date": {
        "ru": "📅 Напиши дату (число дня, например: 15) или `сегодня`:",
        "en": "📅 Enter date (day number, e.g. 15) or `today`:",
        "de": "📅 Datum eingeben (Tag, z.B. 15) oder `heute`:",
    },
    "saved": {
        "ru": "✅ Записано!",
        "en": "✅ Saved!",
        "de": "✅ Gespeichert!",
    },
    "bad_number": {
        "ru": "❌ Введи положительное число:",
        "en": "❌ Enter a positive number:",
        "de": "❌ Positive Zahl eingeben:",
    },
    "bad_date": {
        "ru": "❌ Введи число дня или дату (например: 15 или 15.03):",
        "en": "❌ Enter day number or date (e.g. 15 or 15.03):",
        "de": "❌ Tag oder Datum eingeben (z.B. 15 oder 15.03):",
    },
    "no_active": {
        "ru": "❌ Нет активного месяца. Начни новый!",
        "en": "❌ No active month. Start a new one!",
        "de": "❌ Kein aktiver Monat. Starte einen neuen!",
    },
    "summary_title": {
        "ru": "📊 *Итоги: {}*\n",
        "en": "📊 *Summary: {}*\n",
        "de": "📊 *Zusammenfassung: {}*\n",
    },
    "total_income": {
        "ru": "💵 *Доходы:* {}",
        "en": "💵 *Income:* {}",
        "de": "💵 *Einnahmen:* {}",
    },
    "expenses_by_cat": {
        "ru": "💸 *Расходы по категориям:*",
        "en": "💸 *Expenses by category:*",
        "de": "💸 *Ausgaben nach Kategorie:*",
    },
    "total_expenses": {
        "ru": "💸 *Всего расходов:* {}",
        "en": "💸 *Total expenses:* {}",
        "de": "💸 *Gesamtausgaben:* {}",
    },
    "balance_pos": {
        "ru": "🟢 *Баланс: +{}*",
        "en": "🟢 *Balance: +{}*",
        "de": "🟢 *Saldo: +{}*",
    },
    "balance_neg": {
        "ru": "🔴 *Баланс: {}*",
        "en": "🔴 *Balance: {}*",
        "de": "🔴 *Saldo: {}*",
    },
    "saved_pct": {
        "ru": "💡 Сохранено {}% от дохода",
        "en": "💡 Saved {}% of income",
        "de": "💡 {}% des Einkommens gespart",
    },
    "over_budget": {
        "ru": "⚠️ Расходы превысили доходы!",
        "en": "⚠️ Expenses exceeded income!",
        "de": "⚠️ Ausgaben übersteigen Einnahmen!",
    },
    "all_entries_title": {
        "ru": "📋 *Все записи: {}*\n",
        "en": "📋 *All entries: {}*\n",
        "de": "📋 *Alle Einträge: {}*\n",
    },
    "incomes_header": {
        "ru": "💵 *Доходы:*",
        "en": "💵 *Income:*",
        "de": "💵 *Einnahmen:*",
    },
    "expenses_header": {
        "ru": "💸 *Расходы:*",
        "en": "💸 *Expenses:*",
        "de": "💸 *Ausgaben:*",
    },
    "empty": {
        "ru": "Пока пусто!",
        "en": "Nothing yet!",
        "de": "Noch nichts!",
    },
    "close_confirm": {
        "ru": "🏁 Завершить месяц *{}*?\n\nПосле завершения добавлять записи будет нельзя.",
        "en": "🏁 Close month *{}*?\n\nYou won't be able to add entries after closing.",
        "de": "🏁 Monat *{}* abschließen?\n\nNach dem Abschluss können keine Einträge mehr hinzugefügt werden.",
    },
    "btn_yes": {"ru": "✅ Да, завершить", "en": "✅ Yes, close", "de": "✅ Ja, abschließen"},
    "btn_cancel": {"ru": "❌ Отмена", "en": "❌ Cancel", "de": "❌ Abbrechen"},
    "month_closed": {
        "ru": "✅ Месяц *{}* завершён!",
        "en": "✅ Month *{}* closed!",
        "de": "✅ Monat *{}* abgeschlossen!",
    },
    "cancelled": {
        "ru": "Отменено. Нажми /menu",
        "en": "Cancelled. Press /menu",
        "de": "Abgebrochen. Drücke /menu",
    },
    "history_empty": {
        "ru": "📚 История пуста — ни одного завершённого месяца.",
        "en": "📚 No closed months yet.",
        "de": "📚 Keine abgeschlossenen Monate.",
    },
    "history_title": {
        "ru": "📚 *История месяцев*\n\nНажми чтобы посмотреть итоги:",
        "en": "📚 *Month history*\n\nTap to view summary:",
        "de": "📚 *Monatshistorie*\n\nTippe um Zusammenfassung zu sehen:",
    },
    "deleted_exp": {
        "ru": "🗑 Расход удалён!\n\nНажми /menu",
        "en": "🗑 Expense deleted!\n\nPress /menu",
        "de": "🗑 Ausgabe gelöscht!\n\nDrücke /menu",
    },
    "deleted_inc": {
        "ru": "🗑 Доход удалён!\n\nНажми /menu",
        "en": "🗑 Income deleted!\n\nPress /menu",
        "de": "🗑 Einnahme gelöscht!\n\nDrücke /menu",
    },
    "edit_expense": {
        "ru": "✏️ *Редактирование расхода*\n\nСейчас: *{}* — {} [{}] {}\n\nНапиши новое название\n(или `-` чтобы оставить):",
        "en": "✏️ *Edit expense*\n\nCurrent: *{}* — {} [{}] {}\n\nEnter new name\n(or `-` to keep):",
        "de": "✏️ *Ausgabe bearbeiten*\n\nAktuell: *{}* — {} [{}] {}\n\nNeuen Namen eingeben\n(oder `-` zum Beibehalten):",
    },
    "edit_income": {
        "ru": "✏️ *Редактирование дохода*\n\nСейчас: *{}* — {} {}\n\nНапиши новое название\n(или `-` чтобы оставить):",
        "en": "✏️ *Edit income*\n\nCurrent: *{}* — {} {}\n\nEnter new name\n(or `-` to keep):",
        "de": "✏️ *Einnahme bearbeiten*\n\nAktuell: *{}* — {} {}\n\nNeuen Namen eingeben\n(oder `-` zum Beibehalten):",
    },
    "new_amount": {
        "ru": "💰 Новая сумма (или `-` чтобы оставить):",
        "en": "💰 New amount (or `-` to keep):",
        "de": "💰 Neuer Betrag (oder `-` zum Beibehalten):",
    },
    "new_date": {
        "ru": "📅 Новая дата (или `-` чтобы оставить):",
        "en": "📅 New date (or `-` to keep):",
        "de": "📅 Neues Datum (oder `-` zum Beibehalten):",
    },
    "new_cat": {
        "ru": "📂 Выбери новую категорию:",
        "en": "📂 Choose new category:",
        "de": "📂 Neue Kategorie wählen:",
    },
    "keep_cat": {
        "ru": "Оставить: {}",
        "en": "Keep: {}",
        "de": "Beibehalten: {}",
    },
    "updated_exp": {
        "ru": "✅ Расход обновлён!\n\nНажми /menu",
        "en": "✅ Expense updated!\n\nPress /menu",
        "de": "✅ Ausgabe aktualisiert!\n\nDrücke /menu",
    },
    "updated_inc": {
        "ru": "✅ Доход обновлён: *{}* — {} ({})\n\nНажми /menu",
        "en": "✅ Income updated: *{}* — {} ({})\n\nPress /menu",
        "de": "✅ Einnahme aktualisiert: *{}* — {} ({})\n\nDrücke /menu",
    },
    "press_menu": {
        "ru": "Нажми /menu чтобы открыть меню 💰",
        "en": "Press /menu to open menu 💰",
        "de": "Drücke /menu um das Menü zu öffnen 💰",
    },
    "not_found": {
        "ru": "❌ Запись не найдена.",
        "en": "❌ Entry not found.",
        "de": "❌ Eintrag nicht gefunden.",
    },
    "bad_input": {
        "ru": "❌ Введи число или `-`:",
        "en": "❌ Enter a number or `-`:",
        "de": "❌ Zahl oder `-` eingeben:",
    },
    "help": {
        "ru": (
            "💰 *FinanceBot — Команды*\n\n"
            "/start — приветствие\n"
            "/menu — главное меню\n"
            "/lang — сменить язык\n"
            "/help — эта справка"
        ),
        "en": (
            "💰 *FinanceBot — Commands*\n\n"
            "/start — welcome\n"
            "/menu — main menu\n"
            "/lang — change language\n"
            "/help — this help"
        ),
        "de": (
            "💰 *FinanceBot — Befehle*\n\n"
            "/start — Begrüßung\n"
            "/menu — Hauptmenü\n"
            "/lang — Sprache ändern\n"
            "/help — diese Hilfe"
        ),
    },
}

TODAY_WORDS = {"сегодня", "today", "heute", "."}


# ─── База данных ─────────────────────────────────────────────

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            user_id  INTEGER PRIMARY KEY,
            lang     TEXT DEFAULT 'ru'
        );
        CREATE TABLE IF NOT EXISTS months (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL,
            name     TEXT NOT NULL,
            status   TEXT DEFAULT 'active',
            created_at TEXT DEFAULT (datetime('now')),
            closed_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS income (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL,
            month_id INTEGER NOT NULL,
            name     TEXT NOT NULL,
            amount   REAL NOT NULL,
            date     TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS expenses (
            id       INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id  INTEGER NOT NULL,
            month_id INTEGER NOT NULL,
            name     TEXT NOT NULL,
            amount   REAL NOT NULL,
            category TEXT NOT NULL,
            date     TEXT NOT NULL,
            created_at TEXT DEFAULT (datetime('now'))
        );
    """)
    conn.commit()
    conn.close()


# ── Язык пользователя ──

def get_lang(user_id: int) -> str:
    conn = sqlite3.connect(DB_PATH)
    row = conn.execute("SELECT lang FROM users WHERE user_id = ?", (user_id,)).fetchone()
    conn.close()
    return row[0] if row else "ru"


def set_lang(user_id: int, lang: str):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "INSERT INTO users (user_id, lang) VALUES (?, ?) ON CONFLICT(user_id) DO UPDATE SET lang = ?",
        (user_id, lang, lang),
    )
    conn.commit()
    conn.close()


def t(key: str, user_id: int) -> str:
    lang = get_lang(user_id)
    return T[key].get(lang, T[key]["en"])


def cat_name(key: str, user_id: int) -> str:
    lang = get_lang(user_id)
    return CATEGORIES[key].get(lang, CATEGORIES[key]["en"])


# ── Месяцы ──

def get_active_month(user_id: int) -> dict | None:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM months WHERE user_id = ? AND status = 'active' ORDER BY id DESC LIMIT 1",
        (user_id,),
    ).fetchone()
    conn.close()
    return dict(row) if row else None


def create_month(user_id: int, name: str) -> int:
    conn = sqlite3.connect(DB_PATH)
    cur = conn.execute("INSERT INTO months (user_id, name) VALUES (?, ?)", (user_id, name))
    mid = cur.lastrowid
    conn.commit()
    conn.close()
    return mid


def close_month(month_id: int):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        "UPDATE months SET status = 'closed', closed_at = datetime('now') WHERE id = ?",
        (month_id,),
    )
    conn.commit()
    conn.close()


def get_closed_months(user_id: int) -> list:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        "SELECT * FROM months WHERE user_id = ? AND status = 'closed' ORDER BY id DESC",
        (user_id,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


# ── Доходы ──

def add_income(uid, mid, name, amount, date):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO income (user_id, month_id, name, amount, date) VALUES (?,?,?,?,?)",
                 (uid, mid, name, amount, date))
    conn.commit(); conn.close()

def get_all_income(uid, mid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM income WHERE user_id=? AND month_id=? ORDER BY date, id", (uid, mid)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_total_income(uid, mid):
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute("SELECT COALESCE(SUM(amount),0) FROM income WHERE user_id=? AND month_id=?", (uid, mid)).fetchone()
    conn.close(); return r[0]

def delete_income_entry(iid):
    conn = sqlite3.connect(DB_PATH); conn.execute("DELETE FROM income WHERE id=?", (iid,)); conn.commit(); conn.close()

def get_income_by_id(iid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM income WHERE id=?", (iid,)).fetchone()
    conn.close(); return dict(r) if r else None

def update_income(iid, name, amount, date):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE income SET name=?, amount=?, date=? WHERE id=?", (name, amount, date, iid))
    conn.commit(); conn.close()


# ── Расходы ──

def add_expense(uid, mid, name, amount, category, date):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("INSERT INTO expenses (user_id, month_id, name, amount, category, date) VALUES (?,?,?,?,?,?)",
                 (uid, mid, name, amount, category, date))
    conn.commit(); conn.close()

def get_all_expenses(uid, mid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    rows = conn.execute("SELECT * FROM expenses WHERE user_id=? AND month_id=? ORDER BY date, id", (uid, mid)).fetchall()
    conn.close(); return [dict(r) for r in rows]

def get_total_expenses(uid, mid):
    conn = sqlite3.connect(DB_PATH)
    r = conn.execute("SELECT COALESCE(SUM(amount),0) FROM expenses WHERE user_id=? AND month_id=?", (uid, mid)).fetchone()
    conn.close(); return r[0]

def get_expenses_by_category(uid, mid):
    conn = sqlite3.connect(DB_PATH)
    rows = conn.execute("SELECT category, SUM(amount) FROM expenses WHERE user_id=? AND month_id=? GROUP BY category", (uid, mid)).fetchall()
    conn.close(); return {r[0]: r[1] for r in rows}

def delete_expense(eid):
    conn = sqlite3.connect(DB_PATH); conn.execute("DELETE FROM expenses WHERE id=?", (eid,)); conn.commit(); conn.close()

def get_expense_by_id(eid):
    conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
    r = conn.execute("SELECT * FROM expenses WHERE id=?", (eid,)).fetchone()
    conn.close(); return dict(r) if r else None

def update_expense(eid, name, amount, category, date):
    conn = sqlite3.connect(DB_PATH)
    conn.execute("UPDATE expenses SET name=?, amount=?, category=?, date=? WHERE id=?", (name, amount, category, date, eid))
    conn.commit(); conn.close()


# ─── Утилиты ─────────────────────────────────────────────────

def fmt(amount: float) -> str:
    if amount == int(amount):
        return f"{int(amount):,}".replace(",", " ")
    return f"{amount:,.2f}".replace(",", " ")


def parse_date(text: str) -> str | None:
    text = text.strip().lower()
    if text in TODAY_WORDS:
        return datetime.now().strftime("%d.%m")
    try:
        if "." in text:
            return text
        day = int(text)
        if 1 <= day <= 31:
            return f"{day:02d}.{datetime.now().month:02d}"
    except ValueError:
        pass
    return None


def cat_buttons(uid: int, prefix: str = "cat_") -> list:
    buttons = []
    row = []
    for key in CATEGORY_KEYS:
        row.append(InlineKeyboardButton(cat_name(key, uid), callback_data=f"{prefix}{key}"))
        if len(row) == 2:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)
    return buttons


# ─── Команды ─────────────────────────────────────────────────

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")],
    ])
    await update.message.reply_text(
        "🌍 Выбери язык / Choose language / Sprache wählen:",
        reply_markup=keyboard,
    )


async def menu(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    month = get_active_month(uid)

    if month:
        ti = get_total_income(uid, month["id"])
        te = get_total_expenses(uid, month["id"])
        bal = ti - te
        icon = "🟢" if bal >= 0 else "🔴"

        text = t("current_month", uid).format(month["name"], fmt(ti), fmt(te), icon, fmt(bal))

        buttons = [
            [
                InlineKeyboardButton(t("btn_expense", uid), callback_data="add_expense"),
                InlineKeyboardButton(t("btn_income", uid), callback_data="add_income"),
            ],
            [InlineKeyboardButton(t("btn_summary", uid), callback_data="summary")],
            [InlineKeyboardButton(t("btn_all", uid), callback_data="all_entries")],
            [InlineKeyboardButton(t("btn_close", uid), callback_data="close_month")],
            [InlineKeyboardButton(t("btn_history", uid), callback_data="history")],
            [InlineKeyboardButton(t("btn_lang", uid), callback_data="change_lang")],
        ]
    else:
        text = t("no_month", uid)
        buttons = [
            [InlineKeyboardButton(t("btn_new_month", uid), callback_data="new_month")],
            [InlineKeyboardButton(t("btn_history", uid), callback_data="history")],
            [InlineKeyboardButton(t("btn_lang", uid), callback_data="change_lang")],
        ]

    await update.message.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


async def help_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(t("help", update.effective_user.id), parse_mode="Markdown")


async def lang_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = InlineKeyboardMarkup([
        [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
        [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
        [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")],
    ])
    await update.message.reply_text(
        t("choose_lang", update.effective_user.id),
        reply_markup=keyboard,
    )


# ─── Итоги ───────────────────────────────────────────────────

async def send_summary(target, uid: int, month: dict):
    mid = month["id"]
    by_cat = get_expenses_by_category(uid, mid)
    ti = get_total_income(uid, mid)
    te = get_total_expenses(uid, mid)
    bal = ti - te

    lines = [t("summary_title", uid).format(month["name"])]
    lines.append(t("total_income", uid).format(fmt(ti)) + "\n")
    lines.append(t("expenses_by_cat", uid))

    for key in CATEGORY_KEYS:
        amount = by_cat.get(key, 0)
        if amount > 0:
            pct = (amount / te * 100) if te > 0 else 0
            bar_len = int(pct / 5)
            bar = "█" * bar_len + "░" * (20 - bar_len)
            lines.append(f"{cat_name(key, uid)}: {fmt(amount)} ({pct:.0f}%)\n{bar}")

    lines.append(f"\n{t('total_expenses', uid).format(fmt(te))}")

    if bal >= 0:
        lines.append(t("balance_pos", uid).format(fmt(bal)))
        if ti > 0:
            lines.append(t("saved_pct", uid).format(f"{bal / ti * 100:.0f}"))
    else:
        lines.append(t("balance_neg", uid).format(fmt(bal)))
        lines.append(t("over_budget", uid))

    await target.reply_text("\n".join(lines), parse_mode="Markdown")


# ─── Все записи ──────────────────────────────────────────────

async def send_all_entries(target, uid: int, month: dict):
    mid = month["id"]
    incomes = get_all_income(uid, mid)
    expenses = get_all_expenses(uid, mid)

    lines = [t("all_entries_title", uid).format(month["name"])]

    if incomes:
        lines.append(t("incomes_header", uid))
        for inc in incomes:
            lines.append(f"  {inc['date']} — {inc['name']}: {fmt(inc['amount'])}")

    if expenses:
        lines.append(f"\n{t('expenses_header', uid)}")
        for exp in expenses:
            lines.append(f"  {exp['date']} — {exp['name']}: {fmt(exp['amount'])} [{cat_name(exp['category'], uid)}]")

    if not incomes and not expenses:
        lines.append(t("empty", uid))

    buttons = []
    if expenses:
        for exp in expenses:
            buttons.append([
                InlineKeyboardButton(f"✏️ {exp['name']}", callback_data=f"edexp_{exp['id']}"),
                InlineKeyboardButton(f"🗑 {exp['name']}", callback_data=f"delexp_{exp['id']}"),
            ])
    if incomes:
        for inc in incomes:
            buttons.append([
                InlineKeyboardButton(f"✏️ {inc['name']}", callback_data=f"edinc_{inc['id']}"),
                InlineKeyboardButton(f"🗑 {inc['name']}", callback_data=f"delinc_{inc['id']}"),
            ])
    buttons.append([InlineKeyboardButton(t("btn_menu", uid), callback_data="go_menu")])

    text = "\n".join(lines)
    if len(text) > 4000:
        text = text[:4000] + "\n..."

    await target.reply_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons))


# ─── Callback-обработчик ────────────────────────────────────

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = query.from_user.id
    data = query.data

    # ── Язык ──
    if data.startswith("lang_"):
        lang = data.replace("lang_", "")
        set_lang(uid, lang)
        await query.message.reply_text(t("lang_set", uid), parse_mode="Markdown")

    elif data == "change_lang":
        keyboard = InlineKeyboardMarkup([
            [InlineKeyboardButton("🇷🇺 Русский", callback_data="lang_ru")],
            [InlineKeyboardButton("🇬🇧 English", callback_data="lang_en")],
            [InlineKeyboardButton("🇩🇪 Deutsch", callback_data="lang_de")],
        ])
        await query.message.reply_text(t("choose_lang", uid), reply_markup=keyboard)

    # ── Новый месяц ──
    elif data == "new_month":
        context.user_data["state"] = "waiting_month_name"
        await query.message.reply_text(t("new_month_ask", uid), parse_mode="Markdown")

    # ── Расход ──
    elif data == "add_expense":
        month = get_active_month(uid)
        if not month:
            await query.message.reply_text(t("no_active", uid))
            return
        context.user_data["state"] = "waiting_expense_name"
        await query.message.reply_text(t("new_expense", uid), parse_mode="Markdown")

    # ── Доход ──
    elif data == "add_income":
        month = get_active_month(uid)
        if not month:
            await query.message.reply_text(t("no_active", uid))
            return
        context.user_data["state"] = "waiting_income_name"
        await query.message.reply_text(t("new_income", uid), parse_mode="Markdown")

    # ── Категория (новый расход) ──
    elif data.startswith("cat_"):
        cat = data.replace("cat_", "")
        context.user_data["expense_category"] = cat
        context.user_data["state"] = "waiting_expense_date"
        await query.message.reply_text(t("enter_date", uid), parse_mode="Markdown")

    # ── Категория (редактирование) ──
    elif data.startswith("editcat_"):
        cat = data.replace("editcat_", "")
        ex_id = context.user_data["edit_expense_id"]
        old = get_expense_by_id(ex_id)
        if old:
            update_expense(
                ex_id,
                context.user_data.get("edit_exp_name", old["name"]),
                context.user_data.get("edit_exp_amount", old["amount"]),
                cat,
                context.user_data.get("edit_exp_date", old["date"]),
            )
        context.user_data["state"] = ""
        await query.message.reply_text(t("updated_exp", uid), parse_mode="Markdown")

    # ── Итоги ──
    elif data == "summary":
        month = get_active_month(uid)
        if not month:
            await query.message.reply_text(t("no_active", uid)); return
        await send_summary(query.message, uid, month)

    elif data.startswith("viewmonth_"):
        mid = int(data.replace("viewmonth_", ""))
        conn = sqlite3.connect(DB_PATH); conn.row_factory = sqlite3.Row
        month = conn.execute("SELECT * FROM months WHERE id=? AND user_id=?", (mid, uid)).fetchone()
        conn.close()
        if month:
            await send_summary(query.message, uid, dict(month))

    # ── Все записи ──
    elif data == "all_entries":
        month = get_active_month(uid)
        if not month:
            await query.message.reply_text(t("no_active", uid)); return
        await send_all_entries(query.message, uid, month)

    # ── Удаление ──
    elif data.startswith("delexp_"):
        delete_expense(int(data.replace("delexp_", "")))
        await query.message.reply_text(t("deleted_exp", uid))

    elif data.startswith("delinc_"):
        delete_income_entry(int(data.replace("delinc_", "")))
        await query.message.reply_text(t("deleted_inc", uid))

    # ── Редактирование расхода ──
    elif data.startswith("edexp_"):
        ex_id = int(data.replace("edexp_", ""))
        exp = get_expense_by_id(ex_id)
        if not exp:
            await query.message.reply_text(t("not_found", uid)); return
        context.user_data["edit_expense_id"] = ex_id
        context.user_data["state"] = "waiting_edit_exp_name"
        await query.message.reply_text(
            t("edit_expense", uid).format(exp["name"], fmt(exp["amount"]), cat_name(exp["category"], uid), exp["date"]),
            parse_mode="Markdown",
        )

    # ── Редактирование дохода ──
    elif data.startswith("edinc_"):
        inc_id = int(data.replace("edinc_", ""))
        inc = get_income_by_id(inc_id)
        if not inc:
            await query.message.reply_text(t("not_found", uid)); return
        context.user_data["edit_income_id"] = inc_id
        context.user_data["state"] = "waiting_edit_inc_name"
        await query.message.reply_text(
            t("edit_income", uid).format(inc["name"], fmt(inc["amount"]), inc["date"]),
            parse_mode="Markdown",
        )

    # ── Завершить месяц ──
    elif data == "close_month":
        month = get_active_month(uid)
        if not month:
            await query.message.reply_text(t("no_active", uid)); return
        buttons = [[
            InlineKeyboardButton(t("btn_yes", uid), callback_data="confirm_close"),
            InlineKeyboardButton(t("btn_cancel", uid), callback_data="cancel_close"),
        ]]
        await query.message.reply_text(
            t("close_confirm", uid).format(month["name"]),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons),
        )

    elif data == "confirm_close":
        month = get_active_month(uid)
        if month:
            await send_summary(query.message, uid, month)
            close_month(month["id"])
            buttons = [
                [InlineKeyboardButton(t("btn_new_month", uid), callback_data="new_month")],
                [InlineKeyboardButton(t("btn_history", uid), callback_data="history")],
            ]
            await query.message.reply_text(
                t("month_closed", uid).format(month["name"]),
                parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons),
            )

    elif data == "cancel_close":
        await query.message.reply_text(t("cancelled", uid))

    # ── История ──
    elif data == "history":
        closed = get_closed_months(uid)
        if not closed:
            await query.message.reply_text(t("history_empty", uid)); return
        buttons = []
        for m in closed:
            te = get_total_expenses(uid, m["id"])
            ti = get_total_income(uid, m["id"])
            buttons.append([InlineKeyboardButton(
                f"📅 {m['name']} | 💵{fmt(ti)} 💸{fmt(te)}",
                callback_data=f"viewmonth_{m['id']}",
            )])
        await query.message.reply_text(
            t("history_title", uid), parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── Меню ──
    elif data == "go_menu":
        await query.message.reply_text(t("press_menu", uid))


# ─── Обработка текста ────────────────────────────────────────

async def text_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = update.effective_user.id
    text = update.message.text.strip()
    state = context.user_data.get("state", "")

    # ── Новый месяц ──
    if state == "waiting_month_name":
        old = get_active_month(uid)
        if old:
            close_month(old["id"])
        create_month(uid, text)
        context.user_data["state"] = ""
        buttons = [
            [
                InlineKeyboardButton(t("btn_expense", uid), callback_data="add_expense"),
                InlineKeyboardButton(t("btn_income", uid), callback_data="add_income"),
            ],
        ]
        await update.message.reply_text(
            t("month_created", uid).format(text),
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── Расход: название ──
    elif state == "waiting_expense_name":
        context.user_data["expense_name"] = text
        context.user_data["state"] = "waiting_expense_amount"
        await update.message.reply_text(t("enter_amount", uid))

    # ── Расход: сумма ──
    elif state == "waiting_expense_amount":
        try:
            amount = float(text.replace(",", ".").replace(" ", ""))
            if amount <= 0: raise ValueError
        except ValueError:
            await update.message.reply_text(t("bad_number", uid)); return
        context.user_data["expense_amount"] = amount
        context.user_data["state"] = "waiting_expense_category"
        buttons = cat_buttons(uid)
        await update.message.reply_text(
            f"*{context.user_data['expense_name']}* — {fmt(amount)}\n\n{t('choose_cat', uid)}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── Расход: дата ──
    elif state == "waiting_expense_date":
        month = get_active_month(uid)
        if not month:
            context.user_data["state"] = ""; await update.message.reply_text(t("no_active", uid)); return
        date_str = parse_date(text)
        if not date_str:
            await update.message.reply_text(t("bad_date", uid)); return

        name = context.user_data["expense_name"]
        amount = context.user_data["expense_amount"]
        category = context.user_data["expense_category"]
        add_expense(uid, month["id"], name, amount, category, date_str)
        context.user_data["state"] = ""

        buttons = [
            [
                InlineKeyboardButton(t("btn_more_exp", uid), callback_data="add_expense"),
                InlineKeyboardButton(t("btn_income", uid), callback_data="add_income"),
            ],
            [
                InlineKeyboardButton(t("btn_summary", uid), callback_data="summary"),
                InlineKeyboardButton(t("btn_menu", uid), callback_data="go_menu"),
            ],
        ]
        await update.message.reply_text(
            f"{t('saved', uid)}\n\n💸 *{name}* — {fmt(amount)}\n📂 {cat_name(category, uid)}\n📅 {date_str}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── Доход: название ──
    elif state == "waiting_income_name":
        context.user_data["income_name"] = text
        context.user_data["state"] = "waiting_income_amount"
        await update.message.reply_text(t("enter_amount", uid))

    # ── Доход: сумма ──
    elif state == "waiting_income_amount":
        try:
            amount = float(text.replace(",", ".").replace(" ", ""))
            if amount <= 0: raise ValueError
        except ValueError:
            await update.message.reply_text(t("bad_number", uid)); return
        context.user_data["income_amount"] = amount
        context.user_data["state"] = "waiting_income_date"
        await update.message.reply_text(t("enter_date", uid), parse_mode="Markdown")

    # ── Доход: дата ──
    elif state == "waiting_income_date":
        month = get_active_month(uid)
        if not month:
            context.user_data["state"] = ""; await update.message.reply_text(t("no_active", uid)); return
        date_str = parse_date(text)
        if not date_str:
            await update.message.reply_text(t("bad_date", uid)); return

        name = context.user_data["income_name"]
        amount = context.user_data["income_amount"]
        add_income(uid, month["id"], name, amount, date_str)
        context.user_data["state"] = ""

        buttons = [
            [
                InlineKeyboardButton(t("btn_expense", uid), callback_data="add_expense"),
                InlineKeyboardButton(t("btn_more_inc", uid), callback_data="add_income"),
            ],
            [
                InlineKeyboardButton(t("btn_summary", uid), callback_data="summary"),
                InlineKeyboardButton(t("btn_menu", uid), callback_data="go_menu"),
            ],
        ]
        await update.message.reply_text(
            f"{t('saved', uid)}\n\n💵 *{name}* — {fmt(amount)}\n📅 {date_str}",
            parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(buttons),
        )

    # ── Редактирование расхода ──
    elif state == "waiting_edit_exp_name":
        if text != "-": context.user_data["edit_exp_name"] = text
        context.user_data["state"] = "waiting_edit_exp_amount"
        await update.message.reply_text(t("new_amount", uid))

    elif state == "waiting_edit_exp_amount":
        if text != "-":
            try:
                a = float(text.replace(",", ".").replace(" ", ""))
                if a <= 0: raise ValueError
                context.user_data["edit_exp_amount"] = a
            except ValueError:
                await update.message.reply_text(t("bad_input", uid)); return
        context.user_data["state"] = "waiting_edit_exp_date"
        await update.message.reply_text(t("new_date", uid))

    elif state == "waiting_edit_exp_date":
        ex_id = context.user_data["edit_expense_id"]
        old = get_expense_by_id(ex_id)
        if not old:
            context.user_data["state"] = ""; await update.message.reply_text(t("not_found", uid)); return
        if text != "-":
            ds = parse_date(text)
            if not ds: await update.message.reply_text(t("bad_date", uid)); return
            context.user_data["edit_exp_date"] = ds
        context.user_data["state"] = "waiting_edit_exp_category"
        buttons = cat_buttons(uid, "editcat_")
        cur = cat_name(old["category"], uid)
        buttons.append([InlineKeyboardButton(t("keep_cat", uid).format(cur), callback_data=f"editcat_{old['category']}")])
        await update.message.reply_text(t("new_cat", uid), reply_markup=InlineKeyboardMarkup(buttons))

    # ── Редактирование дохода ──
    elif state == "waiting_edit_inc_name":
        if text != "-": context.user_data["edit_inc_name"] = text
        context.user_data["state"] = "waiting_edit_inc_amount"
        await update.message.reply_text(t("new_amount", uid))

    elif state == "waiting_edit_inc_amount":
        if text != "-":
            try:
                a = float(text.replace(",", ".").replace(" ", ""))
                if a <= 0: raise ValueError
                context.user_data["edit_inc_amount"] = a
            except ValueError:
                await update.message.reply_text(t("bad_input", uid)); return
        context.user_data["state"] = "waiting_edit_inc_date"
        await update.message.reply_text(t("new_date", uid))

    elif state == "waiting_edit_inc_date":
        inc_id = context.user_data["edit_income_id"]
        old = get_income_by_id(inc_id)
        if not old:
            context.user_data["state"] = ""; await update.message.reply_text(t("not_found", uid)); return
        new_name = context.user_data.get("edit_inc_name", old["name"])
        new_amount = context.user_data.get("edit_inc_amount", old["amount"])
        new_date = old["date"]
        if text != "-":
            ds = parse_date(text)
            if not ds: await update.message.reply_text(t("bad_date", uid)); return
            new_date = ds
        update_income(inc_id, new_name, new_amount, new_date)
        context.user_data["state"] = ""
        await update.message.reply_text(
            t("updated_inc", uid).format(new_name, fmt(new_amount), new_date),
            parse_mode="Markdown",
        )

    # ── Ничего ──
    else:
        await update.message.reply_text(t("press_menu", uid))


# ─── Запуск ──────────────────────────────────────────────────

def main():
    init_db()
    app = Application.builder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_cmd))
    app.add_handler(CommandHandler("menu", menu))
    app.add_handler(CommandHandler("lang", lang_cmd))
    app.add_handler(CallbackQueryHandler(button_callback))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, text_handler))
    logger.info("💰 FinanceBot v3 запущен!")
    app.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()
