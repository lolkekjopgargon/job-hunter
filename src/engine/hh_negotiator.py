#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hh_negotiator.py — Fast, Direct Status Checker for Applied Vacancies.
Inspects ONLY vacancies in the 'applied' ('Отклик отправлен') column.
Directly checks each vacancy page (https://hh.ru/vacancy/{id}) with authenticated cookies,
reading applicantVacancyResponseStatuses from embedded Lux state.
Immediately moves rejected vacancies to 'archive' and invitations to 'interview'.
"""

import os
import sys
import re
import json
import gzip
import html
import time
import urllib.request
import urllib.error
from typing import Dict, Any, List, Optional, Tuple
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from db import get_setting, get_connection, move_vacancy
from hh_scanner import hh_opener, read_response_body, DEFAULT_UA


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def fetch_hh_page_fast(url: str, token: str, xsrf: str, ua: str, timeout: int = 8) -> str:
    """Fast, reliable request to HeadHunter using the shared cookie jar from hh_scanner."""
    headers = {
        "User-Agent": ua or DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "https://hh.ru/",
        "Cookie": f"hhtoken={token}; _xsrf={xsrf}"
    }
    req = urllib.request.Request(url, headers=headers)
    try:
        with hh_opener.open(req, timeout=timeout) as resp:
            return read_response_body(resp)
    except Exception as e:
        print(f"⚠️ Ошибка запроса к {url}: {e}", file=sys.stderr, flush=True)
        return ""


def extract_vacancy_response_status(vid: str, html_text: str) -> Tuple[Optional[str], str]:
    """Inspects the vacancy page HTML for applicant response status.
    
    Uses HeadHunter's official applicantVacancyResponseStatuses JSON state.
    Returns: (target_list, status_text)
    """
    if not html_text:
        return (None, "Не удалось загрузить страницу")

    # 1. Parse official HH-Lux-InitialState -> applicantVacancyResponseStatuses
    lux_match = re.search(r'<template[^>]*id="HH-Lux-InitialState"[^>]*>(.*?)</template>', html_text, re.DOTALL)
    if lux_match:
        try:
            raw_json = html.unescape(lux_match.group(1).strip())
            lux_data = json.loads(raw_json)

            resp_statuses = lux_data.get("applicantVacancyResponseStatuses", {})
            vac_info = resp_statuses.get(str(vid), {})
            topic_list = vac_info.get("negotiations", {}).get("topicList", [])

            for topic in topic_list:
                discarded = topic.get("discarded", False)
                invited = topic.get("invited", False)
                last_state = str(topic.get("lastState") or "").upper()
                last_employer_state = str(topic.get("lastEmployerState") or "").upper()
                last_emp_name = str(topic.get("lastEmployerStateExtName") or "")

                if discarded or last_state == "DISCARD" or last_employer_state == "DISCARD":
                    return ("archive", last_emp_name or "Отказ работодателя")

                if invited or "INVIT" in last_state or "INVIT" in last_employer_state:
                    return ("interview", last_emp_name or "Приглашение на интервью")

                if topic.get("responded", False) or last_state == "RESPONSE":
                    return ("applied", "На рассмотрении")

            # Fallback within Lux data if vid is not under applicantVacancyResponseStatuses
            found_states = []
            def walk(obj, d=0):
                if d > 12:
                    return
                if isinstance(obj, dict):
                    st = (
                        obj.get("state")
                        or obj.get("employerState")
                        or obj.get("negotiationState")
                        or obj.get("responseState")
                    )
                    if isinstance(st, dict):
                        sid = str(st.get("id") or "").lower()
                        sname = str(st.get("name") or "")
                        found_states.append((sid, sname))
                    elif st and isinstance(st, str):
                        found_states.append((st.lower(), st))
                    for v in obj.values():
                        walk(v, d + 1)
                elif isinstance(obj, list):
                    for it in obj:
                        walk(it, d + 1)

            walk(lux_data)
            for sid, sname in found_states:
                if any(k in sid for k in ("discard", "decline", "reject")) or "отказ" in sname.lower():
                    return ("archive", sname or "Отказ работодателя")
                if any(k in sid for k in ("invit", "interview", "phone")) or "приглаш" in sname.lower():
                    return ("interview", sname or "Приглашение на интервью")
        except Exception:
            pass

    # 2. Check localized DOM badges (strict matching without hitting i18n translation tables)
    lower = html_text.lower()

    if (
        re.search(r'>\s*отказ\s*<', lower)
        or "bloko-status_discard" in lower
        or "bloko-status_danger" in lower
        or 'data-qa="negotiation-status-discard"' in lower
        or 'data-qa="response-discard"' in lower
        or "работодатель ответил отказом" in lower
        or "вам отказали" in lower
        or "к сожалению, работодатель не готов" in lower
        or "не готов пригласить вас" in lower
        or "отказ работодателя" in lower
    ):
        return ("archive", "Отказ работодателя")

    if (
        re.search(r'>\s*приглашение\s*<', lower)
        or "bloko-status_success" in lower
        or 'data-qa="negotiation-status-invit' in lower
        or "приглашение на интервью" in lower
        or "вас пригласили" in lower
    ):
        return ("interview", "Приглашение на интервью")

    if "вы откликнулись" in lower or "отклик доставлен" in lower or "на рассмотрении" in lower:
        return ("applied", "На рассмотрении")

    return (None, "Без изменений")


def save_status_and_move(
    vid: str,
    employer: str,
    title: str,
    status_text: str,
    target_list: Optional[str],
    old_list: str
) -> bool:
    """Atomic write for negotiation status and vacancy column update."""
    now_str = datetime.now().isoformat()
    for attempt in range(3):
        try:
            conn = get_connection()
            c = conn.cursor()
            c.execute("""
            INSERT OR REPLACE INTO negotiations (vacancy_id, employer, title, status, date_str, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            """, (vid, employer, title, status_text, "", now_str))
            
            moved = False
            if target_list and target_list != old_list:
                c.execute("UPDATE vacancies SET list_name = ?, updated_at = ? WHERE id = ?", (target_list, now_str, vid))
                moved = c.rowcount > 0
                
            conn.commit()
            conn.close()
            return moved
        except Exception as e:
            if "locked" in str(e).lower() and attempt < 2:
                time.sleep(0.5)
                continue
            print(f"⚠️ Ошибка сохранения в БД для {vid}: {e}", file=sys.stderr, flush=True)
            return False
    return False


def check_negotiations() -> Dict[str, Any]:
    print("🔍 Запуск точечной проверки статусов откликов...", file=sys.stderr, flush=True)

    token = get_setting("hh_token", "")
    xsrf = get_setting("hh_xsrf", "")
    ua = get_setting("user_agent", DEFAULT_UA)

    if not token:
        print("⚠️ Токен HeadHunter не найден. Войдите в аккаунт через Настройки.", file=sys.stderr, flush=True)
        return {"error": "Сессия HeadHunter не найдена. Нажмите «Войти через HeadHunter».", "updated": []}

    # 1. Select ONLY vacancies in the 'applied' ('Отклик отправлен') column and close connection immediately
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, title, employer, url, list_name FROM vacancies WHERE list_name = 'applied'")
    applied_vacancies = [dict(r) for r in c.fetchall()]
    conn.close()

    if not applied_vacancies:
        print("ℹ️ В колонке «Отклик отправлен» нет карточек для проверки.", file=sys.stderr, flush=True)
        return {"success": True, "updated": [], "message": "Нет вакансий в колонке «Отклик отправлен»"}

    print(f"📋 Вакансий на проверку в «Отклик отправлен»: {len(applied_vacancies)}", file=sys.stderr, flush=True)
    for v in applied_vacancies:
        print(f"   • {v.get('employer', 'Компания')} ‣ {v.get('title', 'Вакансия')} (ID: {v['id']})", file=sys.stderr, flush=True)

    # 2. Check each applied vacancy directly by fetching its vacancy page
    updates = []

    for vac in applied_vacancies:
        vid = str(vac["id"])
        employer = vac.get("employer") or "Компания"
        title = vac.get("title") or "Вакансия"
        old_list = vac.get("list_name") or "applied"

        print(f"🔍 Проверка вакансии: {employer} ‣ {title} (ID: {vid})...", file=sys.stderr, flush=True)

        url = f"https://hh.ru/vacancy/{vid}"
        page_html = fetch_hh_page_fast(url, token, xsrf, ua, timeout=8)

        target_list, status_text = extract_vacancy_response_status(vid, page_html)

        # Atomic commit per vacancy
        moved = save_status_and_move(vid, employer, title, status_text, target_list, old_list)

        if moved:
            updates.append({
                "vacancy_id": vid,
                "employer": employer,
                "title": title,
                "old_list": old_list,
                "new_list": target_list,
                "new_status": status_text
            })
            print(
                f"🎯 «{employer}» ‣ «{title}»: ОБНАРУЖЕН СТАТУС '{status_text}' -> карточка перенесена в «{target_list}»!",
                file=sys.stderr,
                flush=True
            )
        else:
            print(f"   ✓ «{employer}» ‣ «{title}»: статус '{status_text}' (без изменений)", file=sys.stderr, flush=True)

        time.sleep(0.3)

    print(
        f"✓ Проверка статусов завершена: проверено {len(applied_vacancies)} карточек, "
        f"перемещено: {len(updates)}",
        file=sys.stderr,
        flush=True
    )

    return {
        "success": True,
        "updated": updates,
        "total_checked": len(applied_vacancies)
    }



if __name__ == "__main__":
    res = check_negotiations()
    print("Результат:", json.dumps(res, ensure_ascii=False, indent=2))
