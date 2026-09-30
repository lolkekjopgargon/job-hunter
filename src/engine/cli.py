#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
cli.py - JSON-RPC and CLI Gateway for Electron to interact with Python Engine.
Handles:
- scan: runs HH search + LLM generator
- check_negotiations: checks status updates on HH
- apply: submits application for a vacancy
- get_vacancies: lists cards by list_name
- move_vacancy: moves card to another list
- update_customization: updates selected resume/materials/letter
- get_settings: gets all settings
- set_setting: updates a single setting
- get_knowledge: reads candidate_facts.md, application_rules.md, or portfolio_index.md
- save_knowledge: writes candidate_facts.md, application_rules.md, or portfolio_index.md
- check_hh_auth: validates HH session
"""

import sys
import os
import json
import re
import urllib.request
from typing import Dict, Any

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))
JOB_HUNTER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if JOB_HUNTER_DIR not in sys.path:
    sys.path.insert(0, JOB_HUNTER_DIR)

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
sys.stdin.reconfigure(encoding="utf-8")

from db import (
    init_db, get_vacancies_by_list, move_vacancy, clear_archive,
    update_vacancy_customization, get_all_settings,
    set_setting, get_setting, get_connection, DB_PATH
)
from datetime import datetime
from hh_scanner import run_scan, refetch_vacancy_details
from hh_negotiator import check_negotiations
from hh_applier import apply_to_vacancy
from hh_resume_fetcher import fetch_hh_resumes
from llm_generator import generate_tailored_letter

# Directory where the DB lives — guaranteed writable in both dev and packaged mode.
DB_DIR = os.path.dirname(os.path.abspath(DB_PATH))



def check_hh_auth() -> Dict[str, Any]:
    token = get_setting("hh_token")
    xsrf = get_setting("hh_xsrf")
    cookie_str = get_setting("hh_cookie_str")
    ua = get_setting("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    cookie_header = cookie_str if cookie_str else f"hhtoken={token}; _xsrf={xsrf}"
    if f"_xsrf={xsrf}" not in cookie_header and xsrf:
        cookie_header += f"; _xsrf={xsrf}"
    if f"hhtoken={token}" not in cookie_header and token:
        cookie_header += f"; hhtoken={token}"

    if not token and not cookie_str:
        return {"authenticated": False, "error": "Требуется авторизация в HeadHunter"}

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Connection": "close",
        "Cookie": cookie_header
    }
    url = "https://hh.ru/applicant/resumes"
    req = urllib.request.Request(url, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.geturl()
            status_code = resp.getcode()
            html_text = resp.read().decode("utf-8", errors="ignore")
            if status_code == 200 and "login" not in final_url and ("/applicant/" in final_url or "/resumes" in final_url or "/me" in final_url):
                # Search user name in HTML if available
                user_match = re.search(r'data-qa="mainmenu_applicantProfile"[^>]*>(.*?)<', html_text)
                user_name = user_match.group(1).strip() if user_match else "Павел Тэхэда Кардэнас"
                return {"authenticated": True, "user": user_name, "status": "active"}
            return {"authenticated": False, "error": "Сессия устарела, требуется повторный вход"}
    except urllib.error.HTTPError as he:
        if he.code in (401, 403):
            return {"authenticated": False, "error": "Сессия устарела или отклонена HeadHunter"}
        return {"authenticated": False, "error": f"Ошибка сети [{he.code}]"}
    except Exception as e:
        err_str = str(e)
        # Timeout means HH is slow, NOT that we are logged out — keep session as valid
        if "timed out" in err_str.lower():
            saved_token = get_setting("hh_token")
            if saved_token or get_setting("hh_cookie_str"):
                return {"authenticated": True, "user": "Павел Тэхэда Кардэнас", "status": "active"}
        return {"authenticated": False, "error": err_str}


def get_knowledge_file(name: str) -> str:
    """Reads user content from .md files. Primary location: DB_DIR (userData)."""
    filename_map = {
        "rules": "application_rules.md",
        "facts": "candidate_facts.md",
    }
    if name in filename_map:
        filename = filename_map[name]
        for folder in [DB_DIR, SCRIPT_DIR, JOB_HUNTER_DIR, PROJECT_ROOT]:
            fp = os.path.join(folder, filename)
            if os.path.exists(fp):
                try:
                    with open(fp, "r", encoding="utf-8") as f:
                        content = f.read()
                        if content.strip():
                            return content
                except Exception:
                    pass
        return ""

    path_map = {
        "portfolio": os.path.join(JOB_HUNTER_DIR, "portfolio_index.md"),
    }
    path = path_map.get(name)
    if path and os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return f.read()
    return ""


def save_knowledge_file(name: str, content: str) -> bool:
    """Saves user content as .md file in DB_DIR (userData). No DB — file is the source of truth."""
    filename_map = {
        "rules": "application_rules.md",
        "facts": "candidate_facts.md",
    }
    if name in filename_map:
        fp = os.path.join(DB_DIR, filename_map[name])
        with open(fp, "w", encoding="utf-8") as f:
            f.write(content)
        return True

    path_map = {
        "portfolio": os.path.join(JOB_HUNTER_DIR, "portfolio_index.md"),
    }
    path = path_map.get(name)
    if path:
        with open(path, "w", encoding="utf-8") as f:
            f.write(content)
        return True
    return False




def migrate_planka_cards() -> Dict[str, Any]:
    """Imports cards from the existing local Planka board into SQLite job_hunter.db."""
    planka_base = "http://localhost:8100/api"
    config_path = os.path.join(JOB_HUNTER_DIR, "config.json")
    if not os.path.exists(config_path):
        return {"success": False, "error": "config.json не найден"}

    with open(config_path, "r", encoding="utf-8") as f:
        cfg = json.load(f)

    board_id = cfg.get("planka", {}).get("board_id", "1869072348972320193")
    try:
        # Login to Planka
        login_req = urllib.request.Request(
            f"{planka_base}/access-tokens",
            data=json.dumps({"emailOrUsername": "admin@local.host", "password": "admin"}).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )
        with urllib.request.urlopen(login_req, timeout=5) as resp:
            token = json.loads(resp.read().decode("utf-8"))["item"]

        # Fetch board data
        board_req = urllib.request.Request(
            f"{planka_base}/boards/{board_id}",
            headers={"Authorization": f"Bearer {token}"}
        )
        with urllib.request.urlopen(board_req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))["included"]

        lists_data = {l["id"]: (l.get("name") or "").lower() for l in data.get("lists", [])}
        cards = data.get("cards", [])

        # List name mapping
        def map_list_name(raw_name: str) -> str:
            raw = (raw_name or "").lower()
            if "бэклог" in raw or "найдено" in raw:
                return "backlog"
            elif "одобрено" in raw:
                return "approved"
            elif "отклик" in raw or "отправлен" in raw:
                return "applied"
            elif "интервью" in raw or "созвон" in raw or "приглаш" in raw:
                return "interview"
            elif "отказ" in raw or "архив" in raw:
                return "archive"
            return "backlog"

        imported = 0
        from db import save_vacancy
        import re

        for c in cards:
            desc = c.get("description", "")
            title_raw = c.get("name", "")

            # Extract HH Vacancy ID
            m_id = re.search(r"HH Vacancy ID:\s*`?(\d+)`?", desc)
            if not m_id:
                m_id = re.search(r"/vacancy/(\d+)", desc)
            vac_id = m_id.group(1).strip() if m_id else f"planka_{c.get('id')}"

            # Extract Employer and Title
            employer = "Работодатель"
            m_emp = re.search(r"Компания:\s*([^\n]+)", desc)
            if m_emp:
                employer = m_emp.group(1).strip()
            elif " ‣ " in title_raw:
                employer = title_raw.split(" ‣ ")[0].strip()

            title = title_raw
            m_title = re.search(r"Должность:\s*([^\n]+)", desc)
            if m_title:
                title = m_title.group(1).strip()
            elif " ‣ " in title_raw:
                title = title_raw.split(" ‣ ")[1].strip()

            # Clean emoji from title
            title = re.sub(r'^[^\w\s]+', '', title).strip()

            # Extract Salary
            salary = "По договоренности"
            m_sal = re.search(r"Зарплата:\s*([^\n]+)", desc)
            if m_sal:
                salary = m_sal.group(1).strip()

            # Extract URL
            url = f"https://hh.ru/vacancy/{vac_id}" if vac_id.isdigit() else "https://hh.ru"
            m_url = re.search(r"Прямая ссылка для перехода:\s*(https?://[^\s]+)", desc)
            if m_url:
                url = m_url.group(1).strip()

            # Extract Cover Letter
            cover_letter = ""
            m_cov = re.search(r"### ✉️ READY-TO-SEND MESSAGE:\s*\n+(.*?)(?=\n---\n|\n### 📚|\Z)", desc, re.DOTALL)
            if m_cov:
                cover_letter = m_cov.group(1).strip()

            # Extract Selected Resume ID
            m_res = re.search(r"HH Resume ID:\s*`?([a-f0-9]+)`?", desc)
            selected_resume = m_res.group(1).strip() if m_res else "ef85c34fff11045cfd0039ed1f314d32684a73"

            # Extract Role category
            m_cat = re.search(r"Категория роли:\s*`?([^`\n]+)`?", desc)
            role_cat = m_cat.group(1).strip() if m_cat else "game_designer"

            # Determine list
            raw_list = lists_data.get(c.get("listId"), "бэклог")
            list_name = map_list_name(raw_list)

            # Extract full description or role description
            m_desc = re.search(r"### 📋 Описание роли\s*\n+(.*?)(?=\n---\n|\n### 🛡️|\Z)", desc, re.DOTALL)
            full_desc = m_desc.group(1).strip() if m_desc else desc

            vac_obj = {
                "id": vac_id,
                "title": title,
                "employer": employer,
                "url": url,
                "salary": salary,
                "is_remote": 1 if "удал" in desc.lower() else 0,
                "role_category": role_cat,
                "full_description": full_desc,
                "cover_letter": cover_letter,
                "list_name": list_name,
                "selected_resume_id": selected_resume,
                "selected_materials_json": "[]",
                "fit_notes_json": "{}",
                "has_questionnaire": 0,
                "manual_review_note": ""
            }
            save_vacancy(vac_obj)
            imported += 1

        return {"success": True, "imported_count": imported}
    except Exception as e:
        return {"success": False, "error": f"Ошибка миграции из Planka: {str(e)}"}


def generate_letter_for_vacancy(vid: str, regenerate: bool = False) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM vacancies WHERE id = ?", (vid,))
    row = c.fetchone()
    conn.close()
    if not row:
        return {"success": False, "error": f"Вакансия {vid} не найдена в базе"}

    vac = dict(row)
    mode_str = "повторной перегенерации" if regenerate else "генерации"
    print(f"✨ Запуск {mode_str} живого ИИ-письма: {vac.get('employer')} ‣ {vac.get('title')}...", file=sys.stderr, flush=True)
    try:
        letter = generate_tailored_letter(vac, regenerate=regenerate)
    except Exception as e:
        err_msg = str(e)
        print(f"⚠️ Ошибка генерации письма ИИ: {err_msg}", file=sys.stderr, flush=True)
        return {"success": False, "error": err_msg}

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE vacancies SET cover_letter = ?, updated_at = ? WHERE id = ?",
        (letter, datetime.now().isoformat(), vid)
    )
    conn.commit()
    conn.close()
    print(f"✓ Живое письмо успешно сгенерировано ({len(letter)} симв.) и сохранено!", file=sys.stderr, flush=True)
    return {"success": True, "cover_letter": letter}


def apply_all_approved() -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, employer, title FROM vacancies WHERE list_name = 'approved'")
    approved_rows = c.fetchall()
    conn.close()

    total = len(approved_rows)
    if total == 0:
        print("ℹ️ В колонке «⭐ Одобрено мной» нет вакансий для отправки.", flush=True)
        return {"success": True, "total": 0, "sent": 0, "errors": []}

    print(f"🚀 Старт пакетной отправки откликов для {total} одобренных вакансий...", flush=True)
    sent = 0
    errors = []

    for i, row in enumerate(approved_rows, 1):
        vid = row["id"]
        emp = row["employer"]
        title = row["title"]
        print(f"[{i}/{total}] Отправка отклика: {emp} ‣ {title}...", flush=True)

        res = apply_to_vacancy(vid)
        if res.get("success"):
            sent += 1
            print(f"   ✓ Отклик успешно отправлен на HH! Карточка перенесена в «Отклик отправлен».", flush=True)
        else:
            err = res.get("error", "Неизвестная ошибка")
            errors.append(f"{emp} ‣ {title}: {err}")
            print(f"   ⚠️ Ошибка отправки: {err}", flush=True)

    print(f"🎯 Итог пакетной отправки: успешно отправлено {sent} из {total}.", flush=True)
    return {"success": True, "total": total, "sent": sent, "errors": errors}


def handle_request(req_data: Dict[str, Any]) -> Dict[str, Any]:
    action = req_data.get("action", "")

    if action == "init":
        init_db()
        return {"success": True, "message": "Database initialized"}

    elif action == "migrate_planka":
        return migrate_planka_cards()

    elif action == "get_vacancies":
        list_name = req_data.get("list_name")
        return {"success": True, "vacancies": get_vacancies_by_list(list_name)}

    elif action == "move_vacancy":
        vid = req_data.get("vacancy_id")
        nlist = req_data.get("new_list")
        ok = move_vacancy(vid, nlist)
        return {"success": ok}

    elif action == "update_customization":
        vid = req_data.get("vacancy_id")
        rid = req_data.get("resume_id")
        mats = req_data.get("materials", [])
        letter = req_data.get("cover_letter", "")
        ok = update_vacancy_customization(vid, rid, mats, letter)
        return {"success": ok}

    elif action == "apply":
        vid = req_data.get("vacancy_id")
        return apply_to_vacancy(vid)

    elif action == "apply_approved":
        return apply_all_approved()

    elif action == "generate_letter":
        vid = req_data.get("vacancy_id")
        regen = bool(req_data.get("regenerate", False))
        return generate_letter_for_vacancy(vid, regenerate=regen)

    elif action == "refetch_vacancy":
        vid = req_data.get("vacancy_id")
        vac = refetch_vacancy_details(vid)
        return {"success": bool(vac), "vacancy": vac}

    elif action == "scan":
        res = run_scan()
        return {"success": True, "scan_result": res}

    elif action == "check_negotiations":
        res = check_negotiations()
        return {"success": True, "negotiations_result": res}

    elif action == "clear_archive":
        count = clear_archive()
        return {"success": True, "cleared": count}

    elif action == "fetch_hh_resumes":
        return fetch_hh_resumes()

    elif action == "get_settings":
        return {"success": True, "settings": get_all_settings()}

    elif action == "set_setting":
        key = req_data.get("key")
        val = req_data.get("value")
        set_setting(key, val)
        return {"success": True}

    elif action == "check_hh_auth":
        return check_hh_auth()

    elif action == "get_knowledge":
        name = req_data.get("name", "facts")
        return {"success": True, "content": get_knowledge_file(name)}

    elif action == "save_knowledge":
        name = req_data.get("name", "facts")
        content = req_data.get("content", "")
        ok = save_knowledge_file(name, content)
        return {"success": ok}

    return {"success": False, "error": f"Неизвестное действие: {action}"}


if __name__ == "__main__":
    init_db()
    if len(sys.argv) > 1:
        # CLI invocation with JSON argument
        try:
            req_obj = json.loads(sys.argv[1])
            res = handle_request(req_obj)
            print(json.dumps(res, ensure_ascii=False))
        except Exception as e:
            print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False))
    else:
        # Interactive pipe mode
        for line in sys.stdin:
            line = line.strip()
            if not line:
                continue
            try:
                req_obj = json.loads(line)
                res = handle_request(req_obj)
                print(json.dumps(res, ensure_ascii=False), flush=True)
            except Exception as e:
                print(json.dumps({"success": False, "error": str(e)}, ensure_ascii=False), flush=True)
