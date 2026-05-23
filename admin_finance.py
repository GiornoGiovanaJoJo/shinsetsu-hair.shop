"""Хранение заявок и финансов для админ-панели (JSON на диске)."""

import json
import os
import re
import uuid
from datetime import datetime, timezone
from threading import Lock
from typing import Any, Dict, List, Optional

DATA_DIR = "data"
DATA_FILE = os.path.join(DATA_DIR, "admin_finance.json")
SEED_FILE = os.path.join(DATA_DIR, "leads_seed.json")

LEAD_STATUSES = ("new", "contacted", "bought", "rejected")
EXPENSE_CATEGORY_PRESETS = ("marketing", "salary", "rent", "logistics", "other")

_lock = Lock()


def _utc_now() -> str:
    return datetime.now(timezone.utc).replace(microsecond=0).isoformat()


def _month_key(iso_dt: str) -> str:
    return iso_dt[:7]


def _normalize_phone(phone: str) -> str:
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits


def is_test_submission(name: str, phone: str, city: str) -> bool:
    return _is_test_fields(name, phone, city)


def is_test_lead(lead: Dict[str, Any]) -> bool:
    return _is_test_fields(
        str(lead.get("name", "")),
        str(lead.get("phone", "")),
        str(lead.get("city", "")),
    )


def _is_test_fields(name: str, phone: str, city: str) -> bool:
    if str(name).strip().lower() == "deploycheck":
        return True
    phone_digits = _normalize_phone(phone)
    if phone_digits in ("70000000000", "00000000000"):
        return True
    if str(city).strip().lower() == "test":
        return True
    return False


def _empty_store() -> Dict[str, Any]:
    return {"leads": [], "expenses": []}


def _load() -> Dict[str, Any]:
    if not os.path.exists(DATA_FILE):
        return _empty_store()
    try:
        with open(DATA_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return _empty_store()
    if not isinstance(data.get("leads"), list):
        data["leads"] = []
    if not isinstance(data.get("expenses"), list):
        data["expenses"] = []
    return data


def _save(data: Dict[str, Any]) -> None:
    os.makedirs(DATA_DIR, exist_ok=True)
    tmp = DATA_FILE + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp, DATA_FILE)


def _lead_identity_key(lead: Dict[str, Any]) -> str:
    return _normalize_phone(str(lead.get("phone", ""))) or str(lead.get("id", ""))


def purge_test_leads() -> int:
    with _lock:
        data = _load()
        before = len(data["leads"])
        data["leads"] = [l for l in data["leads"] if not is_test_lead(l)]
        removed = before - len(data["leads"])
        if removed:
            _save(data)
        return removed


def ensure_seed_leads() -> int:
    """Добавляет заявки из leads_seed.json, если их ещё нет (по телефону)."""
    if not os.path.exists(SEED_FILE):
        return 0
    try:
        with open(SEED_FILE, "r", encoding="utf-8") as f:
            seeds = json.load(f)
    except (json.JSONDecodeError, OSError):
        return 0
    if not isinstance(seeds, list):
        return 0

    added = 0
    with _lock:
        data = _load()
        existing_phones = {_lead_identity_key(l) for l in data["leads"]}
        for seed in seeds:
            if not isinstance(seed, dict) or is_test_lead(seed):
                continue
            key = _lead_identity_key(seed)
            if key in existing_phones:
                continue
            lead = dict(seed)
            lead.setdefault("id", uuid.uuid4().hex[:12])
            lead.setdefault("type", "calculate")
            lead.setdefault("status", "contacted")
            lead.setdefault("created_at", _utc_now())
            data["leads"].append(lead)
            existing_phones.add(key)
            added += 1
        if added:
            _save(data)
    return added


def init_finance_store() -> None:
    purge_test_leads()
    ensure_seed_leads()


def _filter_real_leads(leads: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    return [l for l in leads if not is_test_lead(l)]


def add_calculate_lead(
    *,
    name: str,
    phone: str,
    city: str,
    email: Optional[str],
    message: Optional[str],
    length: str,
    color: str,
    structure: str,
    condition: str,
    estimated_price: int,
    photo_count: int,
) -> Optional[Dict[str, Any]]:
    if is_test_submission(name, phone, city):
        return None
    lead = {
        "id": uuid.uuid4().hex[:12],
        "type": "calculate",
        "created_at": _utc_now(),
        "status": "new",
        "estimated_price": estimated_price,
        "actual_amount": None,
        "closed_at": None,
        "name": name,
        "phone": phone,
        "city": city,
        "email": email or "",
        "message": message or "",
        "length": length,
        "color": color,
        "structure": structure,
        "condition": condition,
        "photo_count": photo_count,
        "notes": "",
    }
    with _lock:
        data = _load()
        data["leads"].insert(0, lead)
        _save(data)
    return lead


def add_callback_lead(*, fullname: str, phone: str) -> Optional[Dict[str, Any]]:
    if is_test_submission(fullname, phone, ""):
        return None
    lead = {
        "id": uuid.uuid4().hex[:12],
        "type": "callback",
        "created_at": _utc_now(),
        "status": "new",
        "estimated_price": None,
        "actual_amount": None,
        "closed_at": None,
        "name": fullname,
        "phone": phone,
        "city": "",
        "email": "",
        "message": "",
        "length": "",
        "color": "",
        "structure": "",
        "condition": "",
        "photo_count": 0,
        "notes": "",
    }
    with _lock:
        data = _load()
        data["leads"].insert(0, lead)
        _save(data)
    return lead


def add_manual_lead(payload: Dict[str, Any]) -> Dict[str, Any]:
    name = str(payload.get("name", "")).strip()
    phone = str(payload.get("phone", "")).strip()
    city = str(payload.get("city", "")).strip()
    if not name or not phone:
        raise ValueError("Укажите имя и телефон")

    lead_type = payload.get("type") if payload.get("type") in ("calculate", "callback") else "calculate"
    est = payload.get("estimated_price")
    estimated_price = int(est) if est not in (None, "", "null") else None
    actual = payload.get("actual_amount")
    actual_amount = int(actual) if actual not in (None, "", "null") else None
    status = payload.get("status") if payload.get("status") in LEAD_STATUSES else "new"
    created_at = str(payload.get("created_at") or _utc_now())

    lead = {
        "id": uuid.uuid4().hex[:12],
        "type": lead_type,
        "created_at": created_at,
        "status": status,
        "estimated_price": estimated_price,
        "actual_amount": actual_amount,
        "closed_at": _utc_now() if status == "bought" else None,
        "name": name,
        "phone": phone,
        "city": city,
        "email": str(payload.get("email") or ""),
        "message": str(payload.get("message") or ""),
        "length": str(payload.get("length") or ""),
        "color": str(payload.get("color") or ""),
        "structure": str(payload.get("structure") or ""),
        "condition": str(payload.get("condition") or ""),
        "photo_count": int(payload.get("photo_count") or 0),
        "notes": str(payload.get("notes") or "Добавлено вручную"),
    }
    with _lock:
        data = _load()
        data["leads"].insert(0, lead)
        _save(data)
    return lead


def list_leads(month: Optional[str] = None, status: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        leads = _filter_real_leads(list(_load()["leads"]))
    if status and status != "all":
        leads = [l for l in leads if l.get("status") == status]
    if month:
        leads = [l for l in leads if _month_key(l.get("created_at", "")) == month]
    leads.sort(key=lambda l: l.get("created_at", ""), reverse=True)
    return leads


def update_lead(lead_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with _lock:
        data = _load()
        for lead in data["leads"]:
            if lead.get("id") != lead_id:
                continue
            if "status" in patch and patch["status"] in LEAD_STATUSES:
                old_status = lead.get("status")
                lead["status"] = patch["status"]
                if patch["status"] == "bought" and old_status != "bought":
                    lead["closed_at"] = _utc_now()
                if patch["status"] != "bought":
                    lead["closed_at"] = None
            if "actual_amount" in patch:
                val = patch["actual_amount"]
                lead["actual_amount"] = int(val) if val not in (None, "", "null") else None
            if "estimated_price" in patch:
                val = patch["estimated_price"]
                lead["estimated_price"] = int(val) if val not in (None, "", "null") else None
            for key in ("notes", "name", "phone", "city", "email", "message", "length", "color", "structure"):
                if key in patch:
                    lead[key] = str(patch[key] or "")
            _save(data)
            return dict(lead)
    return None


def delete_lead(lead_id: str) -> bool:
    with _lock:
        data = _load()
        before = len(data["leads"])
        data["leads"] = [l for l in data["leads"] if l.get("id") != lead_id]
        if len(data["leads"]) == before:
            return False
        _save(data)
        return True


def _normalize_expense_category(payload: Dict[str, Any]) -> str:
    preset = str(payload.get("category") or "").strip()
    custom = str(payload.get("category_custom") or "").strip()
    if preset == "custom" and custom:
        return custom[:80]
    if preset in EXPENSE_CATEGORY_PRESETS:
        return preset
    if custom:
        return custom[:80]
    if preset:
        return preset[:80]
    return "other"


def expense_category_label(category: str) -> str:
    labels = {
        "marketing": "Реклама",
        "salary": "Зарплата",
        "rent": "Аренда",
        "logistics": "Логистика",
        "other": "Прочее",
    }
    return labels.get(category, category)


def list_expenses(month: Optional[str] = None) -> List[Dict[str, Any]]:
    with _lock:
        expenses = list(_load()["expenses"])
    if not month:
        return expenses
    result = []
    for exp in expenses:
        if exp.get("is_recurring"):
            result.append(exp)
        elif _month_key(exp.get("date", "")) == month:
            result.append(exp)
    return result


def add_expense(payload: Dict[str, Any]) -> Dict[str, Any]:
    category = _normalize_expense_category(payload)
    expense = {
        "id": uuid.uuid4().hex[:12],
        "title": str(payload.get("title", "")).strip() or "Без названия",
        "amount": max(0, int(payload.get("amount", 0) or 0)),
        "category": category,
        "is_recurring": bool(payload.get("is_recurring")),
        "date": str(payload.get("date") or _utc_now()[:10]),
        "notes": str(payload.get("notes") or ""),
    }
    with _lock:
        data = _load()
        data["expenses"].insert(0, expense)
        _save(data)
    return expense


def update_expense(expense_id: str, patch: Dict[str, Any]) -> Optional[Dict[str, Any]]:
    with _lock:
        data = _load()
        for exp in data["expenses"]:
            if exp.get("id") != expense_id:
                continue
            if "title" in patch:
                exp["title"] = str(patch["title"] or "").strip() or exp["title"]
            if "amount" in patch:
                exp["amount"] = max(0, int(patch["amount"] or 0))
            if "category" in patch or "category_custom" in patch:
                exp["category"] = _normalize_expense_category(patch)
            if "is_recurring" in patch:
                exp["is_recurring"] = bool(patch["is_recurring"])
            if "date" in patch:
                exp["date"] = str(patch["date"] or exp.get("date", ""))
            if "notes" in patch:
                exp["notes"] = str(patch["notes"] or "")
            _save(data)
            return dict(exp)
    return None


def delete_expense(expense_id: str) -> bool:
    with _lock:
        data = _load()
        before = len(data["expenses"])
        data["expenses"] = [e for e in data["expenses"] if e.get("id") != expense_id]
        if len(data["expenses"]) == before:
            return False
        _save(data)
        return True


def month_summary(month: str) -> Dict[str, Any]:
    with _lock:
        store = _load()

    leads = _filter_real_leads(store["leads"])
    expenses = store["expenses"]

    income_actual = 0
    income_pipeline = 0
    bought_count = 0
    new_count = 0

    for lead in leads:
        status = lead.get("status", "new")
        est = int(lead.get("estimated_price") or 0)
        actual = lead.get("actual_amount")
        created_month = _month_key(lead.get("created_at", ""))
        closed_month = _month_key(lead.get("closed_at") or "") if lead.get("closed_at") else ""

        if status == "bought" and closed_month == month:
            income_actual += int(actual if actual is not None else est)
            bought_count += 1
        elif status in ("new", "contacted") and created_month == month:
            pipeline_val = int(actual if actual is not None else est)
            income_pipeline += pipeline_val
            new_count += 1

    expense_total = 0
    expense_items = []
    for exp in expenses:
        amount = int(exp.get("amount") or 0)
        if exp.get("is_recurring"):
            expense_total += amount
            expense_items.append({**exp, "applied_month": month})
        elif _month_key(exp.get("date", "")) == month:
            expense_total += amount
            expense_items.append(exp)

    return {
        "month": month,
        "income_actual": income_actual,
        "income_pipeline": income_pipeline,
        "expense_total": expense_total,
        "profit": income_actual - expense_total,
        "bought_count": bought_count,
        "pipeline_count": new_count,
        "expense_count": len(expense_items),
    }


def overview(months_back: int = 6) -> Dict[str, Any]:
    now = datetime.now(timezone.utc)
    month_keys = []
    y, m = now.year, now.month
    for _ in range(months_back):
        month_keys.append(f"{y:04d}-{m:02d}")
        m -= 1
        if m < 1:
            m = 12
            y -= 1
    month_keys.reverse()

    with _lock:
        store = _load()
        totals = {
            "leads": len(_filter_real_leads(store["leads"])),
            "expenses": len(store["expenses"]),
        }

    return {
        "months": [_month_summary_row(mk) for mk in month_keys],
        "totals": totals,
    }


def _month_summary_row(month: str) -> Dict[str, Any]:
    s = month_summary(month)
    return {
        "month": month,
        "income": s["income_actual"],
        "pipeline": s["income_pipeline"],
        "expenses": s["expense_total"],
        "profit": s["profit"],
    }
