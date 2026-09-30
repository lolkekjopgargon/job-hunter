#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hh_applier.py - 1-Click Application Submitter to HeadHunter.
Submits the application with the selected resume and living cover letter (stitched with dynamic materials and contacts).
"""

import os
import sys
import json
import re
import random
import string
import urllib.request
import urllib.error
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

from db import get_setting, get_connection, move_vacancy
from card_tasklists import CONTACTS_BLOCK, PORTFOLIO_OPTIONS


def generate_boundary() -> str:
    chars = string.ascii_letters + string.digits
    return "----WebKitFormBoundary" + "".join(random.choices(chars, k=16))


def build_final_letter(cover_letter: str, selected_materials: list) -> str:
    clean_speech = cover_letter.strip()

    # Dynamic mapping from user's custom portfolio links in DB
    url_to_label = {}
    try:
        raw_links = get_setting("custom_portfolio_links", "[]")
        parsed = json.loads(raw_links)
        if isinstance(parsed, list):
            for it in parsed:
                if isinstance(it, dict) and it.get("url"):
                    url_to_label[it["url"].strip()] = it.get("title", "").strip()
    except Exception:
        pass

    # Fallback to standard options
    for label, url, _ in PORTFOLIO_OPTIONS:
        if url.strip() not in url_to_label:
            url_to_label[url.strip()] = label

    links_lines = []
    if selected_materials:
        for raw_url in selected_materials:
            url = str(raw_url).strip()
            if not url:
                continue
            # If the user already has this URL in the cover letter text, DO NOT DUPLICATE!
            if url in clean_speech:
                continue
            label = url_to_label.get(url, "Материал из портфолио")
            clean_label = re.sub(r'^[^\w\s]+', '', label).strip()
            links_lines.append(f"{clean_label}:\n{url}")

    links_text = ""
    if links_lines:
        links_text = "\n\nПримеры проектных материалов:\n\n" + "\n\n".join(links_lines)

    # Contacts block: check custom_contacts from settings first
    user_contacts = get_setting("custom_contacts", "").strip() or CONTACTS_BLOCK
    first_contact_line = user_contacts.split("\n")[0].strip() if user_contacts else ""

    contacts_text = ""
    if user_contacts and (not first_contact_line or first_contact_line not in clean_speech):
        contacts_text = f"\n\n{user_contacts}"

    return f"{clean_speech}{links_text}{contacts_text}".strip()


def apply_to_vacancy(vacancy_id: str) -> Dict[str, Any]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM vacancies WHERE id = ?", (vacancy_id,))
    row = c.fetchone()
    conn.close()

    if not row:
        return {"success": False, "error": f"Вакансия {vacancy_id} не найдена в базе"}

    vac = dict(row)
    resume_id = vac.get("selected_resume_id")
    if not resume_id:
        return {"success": False, "error": "Не выбрано резюме для отклика"}

    # Resolve legacy key alias to actual HH hash if needed
    if len(resume_id) < 30:
        resumes_json = get_setting("hh_resumes", "[]")
        try:
            parsed_resumes = json.loads(resumes_json)
            resolved = False
            for pr in parsed_resumes:
                pr_id = pr.get("id", "")
                pr_title = pr.get("title", "").lower()
                if len(pr_id) >= 30 and (resume_id.lower() in pr_title or resume_id in pr_id):
                    resume_id = pr_id
                    resolved = True
                    break
            if not resolved and parsed_resumes and len(parsed_resumes[0].get("id", "")) >= 30:
                resume_id = parsed_resumes[0]["id"]
        except Exception:
            pass

    materials = json.loads(vac.get("selected_materials_json") or "[]")
    final_message = build_final_letter(vac.get("cover_letter", ""), materials)

    token = get_setting("hh_token")
    xsrf = get_setting("hh_xsrf")
    cookie_str = get_setting("hh_cookie_str")
    ua = get_setting("user_agent", "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36")

    # Construct robust cookie header
    cookie_header = cookie_str if cookie_str else f"hhtoken={token}; _xsrf={xsrf}"
    if f"_xsrf={xsrf}" not in cookie_header and xsrf:
        cookie_header += f"; _xsrf={xsrf}"
    if f"hhtoken={token}" not in cookie_header and token:
        cookie_header += f"; hhtoken={token}"

    url = "https://hh.ru/applicant/vacancy_response/popup"
    boundary = generate_boundary()

    headers = {
        "User-Agent": ua,
        "Accept": "application/json, text/javascript, */*; q=0.01",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "X-Xsrftoken": xsrf,
        "X-Requested-With": "XMLHttpRequest",
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "Origin": "https://hh.ru",
        "Referer": vac["url"],
        "Cookie": cookie_header
    }

    form_fields = [
        ("vacancy_id", str(vacancy_id)),
        ("resume_hash", str(resume_id)),
        ("letter", final_message),
        ("without_test", "true"),
        ("ignore_postpone", "true"),
        ("lux", "true"),
        ("mark_as_read", "true"),
        ("force_post", "true")
    ]

    body_lines = []
    for name, value in form_fields:
        body_lines.append(f"--{boundary}".encode("utf-8"))
        body_lines.append(f'Content-Disposition: form-data; name="{name}"'.encode("utf-8"))
        body_lines.append(b"")
        body_lines.append(str(value).encode("utf-8"))
    body_lines.append(f"--{boundary}--".encode("utf-8"))
    body_lines.append(b"")
    body_data = b"\r\n".join(body_lines)

    req = urllib.request.Request(url, data=body_data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            resp_body = resp.read().decode("utf-8", errors="ignore")
            
            # Parse response strictly
            is_valid = False
            error_detail = ""
            try:
                data = json.loads(resp_body)
                # Check for explicit errors
                if "error" in data:
                    err_type = data.get("error")
                    if err_type == "already_applied" or "negotiation" in str(data).lower():
                        move_vacancy(vacancy_id, "applied")
                        return {"success": True, "message": "Ранее отклик уже был подан на HH. Карточка перенесена в «Отправленные»."}
                    elif err_type == "test-required":
                        # Flag vacancy as requiring test
                        conn = get_connection()
                        c = conn.cursor()
                        c.execute("UPDATE vacancies SET has_questionnaire = 1 WHERE id = ?", (vacancy_id,))
                        conn.commit()
                        conn.close()
                        return {
                            "success": False,
                            "error": "Работодатель требует обязательное прохождение теста на сайте HH! Откройте вакансию на HH для ручного прохождения теста."
                        }
                    else:
                        error_detail = f"HH вернул ошибку: {data.get('description') or data.get('error') or resp_body[:200]}"
                elif "errors" in data and data["errors"]:
                    error_detail = f"HH вернул ошибку: {data['errors']}"
                elif "redirect" in data or "negotiationId" in data or "status" in data or "vacancy_response" in str(data):
                    is_valid = True
                else:
                    # Generic check: if response has html or redirect to login
                    if "login" in resp_body.lower() or "bad_authorization" in resp_body.lower():
                        error_detail = "Сессия HH устарела. Откройте «Настройки» -> «Поиск и HH» и нажмите «Войти через HeadHunter»."
                    else:
                        is_valid = True
            except Exception:
                # If not JSON, check if it's a redirect or html
                if "login" in resp_body.lower():
                    error_detail = "Сессия HH устарела. Требуется повторный вход в «Настройках»."
                else:
                    is_valid = True

            if not is_valid and error_detail:
                return {"success": False, "error": error_detail}

            # Successful response moves card to 'applied'
            move_vacancy(vacancy_id, "applied")
            return {
                "success": True,
                "message": f"Отклик успешно отправлен на вакансию {vac['employer']} ‣ {vac['title']}!",
                "response": resp_body[:200]
            }
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="ignore")
        if "already_applied" in err_body.lower() or "negotiation" in err_body.lower():
            move_vacancy(vacancy_id, "applied")
            return {"success": True, "message": "Ранее отклик уже был подан. Карточка перемещена в 'Отправленные'."}
        elif "test-required" in err_body.lower():
            conn = get_connection()
            c = conn.cursor()
            c.execute("UPDATE vacancies SET has_questionnaire = 1 WHERE id = ?", (vacancy_id,))
            conn.commit()
            conn.close()
            return {"success": False, "error": "Работодатель требует пройти тест на сайте HH! Откройте карточку на HH."}
        elif e.code == 403 or "auth" in err_body.lower():
            return {"success": False, "error": "Сессия HH устарела или отклонена. Войдите заново в «Настройках» -> «Поиск и HH»."}
        return {"success": False, "error": f"Ошибка HH ({e.code}): {err_body[:200]}"}
    except Exception as e:
        err_str = str(e)
        if "timed out" in err_str.lower():
            return {"success": False, "error": "Таймаут соединения с HeadHunter (сервер HH не ответил за 35 сек). Попробуйте повторить отправку."}
        return {"success": False, "error": f"Сетевая ошибка: {err_str}"}



if __name__ == "__main__":
    if len(sys.argv) > 1:
        vid = sys.argv[1]
        print(f"Отправка на {vid}...")
        res = apply_to_vacancy(vid)
        print("Результат:", res)
