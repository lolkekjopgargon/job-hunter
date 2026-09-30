#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hh_scanner.py - HeadHunter Vacancy Search, 100% Full Text Extraction, and Filtering.
Supports customizable search queries, roles, and salary thresholds from SQLite settings.
"""

import os
import sys
import json
import re
import time
import http.cookiejar
import urllib.request
import urllib.parse
from typing import Dict, Any, List, Optional
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))
JOB_HUNTER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if JOB_HUNTER_DIR not in sys.path:
    sys.path.insert(0, JOB_HUNTER_DIR)

from db import get_setting, set_setting, save_vacancy, get_connection, get_all_seen_ids, mark_seen_vacancy
from llm_generator import generate_tailored_letter
from requirement_filter import evaluate_hard_technical_filter
from candidate_context import RESUME_METADATA, PORTFOLIO_BUNDLES


DEFAULT_RESUME_IDS = {
    "game_designer": "ef85c34fff11045cfd0039ed1f314d32684a73",
    "narrative_designer": "ca0eeaf4ff10d8370e0039ed1f67683771696e",
    "3d_generalist": "413445ecff0b4f36200039ed1f474477685a36",
    "3d_artist": "01a34415ff0e1804370039ed1f464c68596644",
    "actor": "090a2123ff0ed3b8920039ed1f36356b596268"
}

DEFAULT_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"

# Shared cookie jar to persist DDoS-guard cookies across requests
cookie_jar = http.cookiejar.CookieJar()
hh_opener = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(cookie_jar))


def clean_html(raw_html: str) -> str:
    text = re.sub(r"<br\s*/?>", "\n", raw_html, flags=re.IGNORECASE)
    text = re.sub(r"</p>", "\n\n", text, flags=re.IGNORECASE)
    text = re.sub(r"</li>", "\n", text, flags=re.IGNORECASE)
    text = re.sub(r"<li>", "• ", text, flags=re.IGNORECASE)
    text = re.sub(r"<[^>]+>", "", text)
    text = text.replace("&quot;", '"').replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&nbsp;", " ")
    return re.sub(r"\n{3,}", "\n\n", text).strip()


def extract_vacancy_description(html: str) -> str:
    """Accurately extracts the entire vacancy description container handling nested div elements."""
    marker = 'data-qa="vacancy-description"'
    idx = html.find(marker)
    if idx == -1:
        return ""
    start_tag_end = html.find(">", idx)
    if start_tag_end == -1:
        return ""
    content_start = start_tag_end + 1
    depth = 1
    pos = content_start
    while depth > 0 and pos < len(html):
        next_open = html.find("<div", pos)
        next_close = html.find("</div>", pos)
        if next_close == -1:
            break
        if next_open != -1 and next_open < next_close:
            depth += 1
            pos = next_open + 4
        else:
            depth -= 1
            if depth == 0:
                return html[content_start:next_close]
            pos = next_close + 6
    return html[content_start:pos]


import gzip


def read_response_body(resp, max_bytes: int = 2_500_000) -> str:
    chunks = []
    total = 0
    cl = resp.headers.get("Content-Length")
    expected = int(cl) if cl and cl.isdigit() else max_bytes
    limit = min(expected, max_bytes)
    while total < limit:
        to_read = min(32768, limit - total)
        try:
            chunk = resp.read(to_read)
        except Exception:
            break
        if not chunk:
            break
        chunks.append(chunk)
        total += len(chunk)
    raw = b"".join(chunks)
    if resp.headers.get("Content-Encoding") == "gzip":
        try:
            raw = gzip.decompress(raw)
        except Exception:
            pass
    return raw.decode("utf-8", errors="ignore")


def fetch_hh_page(url: str, cookies_dict: Dict[str, str], user_agent: str) -> str:
    headers = {
        "User-Agent": user_agent or DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cookie": f"hhtoken={cookies_dict.get('hhtoken', '')}; _xsrf={cookies_dict.get('_xsrf', '')}"
    }
    req = urllib.request.Request(url, headers=headers)
    with hh_opener.open(req, timeout=15) as resp:
        return read_response_body(resp)


def get_search_headers() -> Dict[str, str]:
    token = get_setting("hh_token")
    xsrf = get_setting("hh_xsrf")
    ua = get_setting("user_agent", DEFAULT_UA)
    return {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Cookie": f"hhtoken={token}; _xsrf={xsrf}"
    }


def fetch_full_vacancy_details(vac_id: str) -> Optional[Dict[str, Any]]:
    token = get_setting("hh_token")
    xsrf = get_setting("hh_xsrf")
    ua = get_setting("user_agent", DEFAULT_UA)

    url = f"https://hh.ru/vacancy/{vac_id}"
    try:
        html = fetch_hh_page(url, {"hhtoken": token, "_xsrf": xsrf}, ua)
        desc_html = extract_vacancy_description(html)
        if not desc_html:
            desc_m = re.search(r'data-qa="vacancy-description"[^>]*>(.*?)</div>', html, re.DOTALL)
            desc_html = desc_m.group(1) if desc_m else ""
        if not desc_html:
            return None

        full_text = clean_html(desc_html)

        # Check for skills tags
        skills_m = re.findall(r'data-qa="skills-element"[^>]*>(.*?)</span>', html)
        if skills_m:
            clean_skills = [clean_html(s) for s in skills_m if clean_html(s)]
            if clean_skills:
                full_text += "\n\n📌 **Ключевые навыки:** " + ", ".join(clean_skills)

        # Check for questionnaire requirement
        has_questionnaire = "ответьте на вопросы" in html.lower() or "заполните анкету" in html.lower() or "тестовое задание" in html.lower()

        return {
            "description": full_text,
            "has_questionnaire": has_questionnaire
        }
    except Exception as e:
        print(f"⚠️ Ошибка забора страницы {url}: {e}", file=sys.stderr, flush=True)
        return None


def refetch_vacancy_details(vid: str) -> Optional[Dict[str, Any]]:
    print(f"🔄 Обновление описания вакансии {vid} с HH...", flush=True)
    details = fetch_full_vacancy_details(vid)
    if not details:
        return None
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "UPDATE vacancies SET full_description = ?, has_questionnaire = ?, updated_at = ? WHERE id = ?",
        (details["description"], 1 if details["has_questionnaire"] else 0, datetime.now().isoformat(), vid)
    )
    conn.commit()
    c.execute("SELECT * FROM vacancies WHERE id = ?", (vid,))
    row = c.fetchone()
    conn.close()
    print(f"✓ Описание вакансии {vid} успешно обновлено ({len(details['description'])} симв.)", flush=True)
    return dict(row) if row else None


def run_scan() -> Dict[str, Any]:
    print("🔍 Запуск поиска вакансий на HeadHunter...", file=sys.stderr, flush=True)
    queries_json = get_setting("search_queries", "[]")
    try:
        queries = json.loads(queries_json)
    except Exception:
        queries = []

    # Fallback to sensible defaults if query list is empty or corrupted
    if not queries or all(not q.get("enabled", True) for q in queries) or any("\ufffd" in q.get("query", "") for q in queries):
        print("💡 Применяем проверенные поисковые запросы по геймдеву...", file=sys.stderr, flush=True)
        queries = [
            {"id": "gd", "name": "Гейм-дизайн", "query": '"Гейм-дизайнер" OR "Game Designer"', "resume_key": "game_designer", "salary_min": 100000, "schedule": "remote", "enabled": True},
            {"id": "narrative", "name": "Нарративный дизайн", "query": '"Нарративный дизайнер" OR "Narrative Designer"', "resume_key": "narrative_designer", "salary_min": 100000, "schedule": "remote", "enabled": True},
            {"id": "3d", "name": "3D Generalist", "query": '"3D Generalist" OR "3D Моделлер" OR "3D Artist"', "resume_key": "3d_generalist", "salary_min": 100000, "schedule": "remote", "enabled": True},
        ]
        set_setting("search_queries", json.dumps(queries, ensure_ascii=False))

    headers = get_search_headers()
    found_count = 0
    added_count = 0

    existing_ids = get_all_seen_ids()

    for q in queries:
        if not q.get("enabled", True):
            continue

        query_text = q.get("query", "")
        role_cat = q.get("resume_key", "game_designer")
        salary_min = q.get("salary_min", 100000)
        schedule = q.get("schedule", "remote")

        params = {
            "text": query_text,
            "search_field": "name",
            "order_by": "publication_time",
            "items_on_page": 20
        }
        if salary_min:
            params["salary"] = salary_min
        if schedule == "remote":
            params["schedule"] = "remote"

        search_url = f"https://hh.ru/search/vacancy?{urllib.parse.urlencode(params)}"
        print(f"🔍 Сканирование: «{q.get('name', query_text)}»...", file=sys.stderr, flush=True)

        try:
            req = urllib.request.Request(search_url, headers=headers)
            with hh_opener.open(req, timeout=15) as resp:
                html = read_response_body(resp)

            # Extract vacancy cards from HTML
            vac_blocks = html.split('data-qa="vacancy-serp__vacancy"')
            if len(vac_blocks) <= 1:
                vac_blocks = html.split('data-qa="vacancy-serp__vacancy')

            for b in vac_blocks[1:]:
                link_m = re.search(r'href="[^"]*hh\.ru/vacancy/(\d+)[^"]*"[^>]*data-qa="serp-item__title"', b)
                if not link_m:
                    link_m = re.search(r'data-qa="serp-item__title"[^>]*href="[^"]*hh\.ru/vacancy/(\d+)', b)
                if not link_m:
                    link_m = re.search(r'href="https://hh\.ru/vacancy/(\d+)', b)
                if not link_m:
                    continue
                vid = link_m.group(1)

                title_m = re.search(r'data-qa="serp-item__title-text"[^>]*>(.*?)</span>', b)
                if not title_m:
                    title_m = re.search(r'data-qa="serp-item__title"[^>]*>(.*?)</a>', b)
                title = clean_html(title_m.group(1)) if title_m else "Вакансия"

                if vid in existing_ids:
                    continue

                found_count += 1

                # Employer
                emp_m = re.search(r'data-qa="vacancy-serp__vacancy-employer"[^>]*>(.*?)</a>', b)
                if not emp_m:
                    emp_m = re.search(r'data-qa="vacancy-serp__vacancy-employer-text"[^>]*>(.*?)</span>', b)
                employer = clean_html(emp_m.group(1)) if emp_m else "Работодатель"

                # Salary
                sal_m = re.search(r'data-qa="vacancy-serp__vacancy-compensation[^"]*"[^>]*>(.*?)</span>', b)
                salary = clean_html(sal_m.group(1)) if sal_m else "Не указана"

                # Gentle delay before fetching details
                time.sleep(0.3)

                # Fetch 100% full description
                details = fetch_full_vacancy_details(vid)
                if not details:
                    continue

                full_desc = details["description"]
                has_q = details["has_questionnaire"]

                # Run hard exclusion technical filter
                decision, reason = evaluate_hard_technical_filter(title, full_desc)
                if decision == "REJECT":
                    print(f"   ✗ Отклонено жестким фильтром: {employer} ‣ {title} ({reason})", file=sys.stderr, flush=True)
                    # Even if rejected, remember it so we don't re-parse it tomorrow
                    mark_seen_vacancy(vid, title, employer)
                    existing_ids.add(vid)
                    continue
                filter_note = reason if decision == "REVIEW" else ""

                # Prepare vacancy record
                vac_record = {
                    "id": vid,
                    "title": title,
                    "employer": employer,
                    "url": f"https://hh.ru/vacancy/{vid}",
                    "salary": salary,
                    "is_remote": True if "удален" in b.lower() or schedule == "remote" else False,
                    "role_category": role_cat,
                    "full_description": full_desc,
                    "list_name": "backlog",
                    "selected_resume_id": DEFAULT_RESUME_IDS.get(role_cat, DEFAULT_RESUME_IDS["game_designer"]),
                    "has_questionnaire": has_q,
                    "manual_review_note": filter_note if filter_note else ""
                }

                # Default selected portfolio materials (2-4 links)
                portfolio = PORTFOLIO_BUNDLES.get(role_cat, PORTFOLIO_BUNDLES.get("game_designer", []))
                vac_record["selected_materials"] = [p["url"] for p in portfolio[:3]]

                # Cover letter will be generated on-demand by user in CardModal
                vac_record["cover_letter"] = ""

                # Save to SQLite and permanent deduplication store
                save_vacancy(vac_record)
                mark_seen_vacancy(vid, title, employer)
                existing_ids.add(vid)
                added_count += 1
                print(f"   ✓ Сохранено в Бэклог: {employer} ‣ {title} (ID: {vid})", file=sys.stderr, flush=True)

                if added_count >= 15:
                    print("🎯 Достигнут суточный лимит свежих вакансий (15). Завершаем сбор.", file=sys.stderr, flush=True)
                    break

        except Exception as e:
            print(f"⚠️ Ошибка поиска по запросу '{query_text}': {e}", file=sys.stderr, flush=True)

        if added_count >= 15:
            break

    now_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    set_setting("last_scan_date", datetime.now().strftime("%Y-%m-%d"))
    set_setting("last_scan_time", now_str)

    return {
        "found": found_count,
        "added": added_count,
        "scan_time": now_str
    }


if __name__ == "__main__":
    res = run_scan()
    print(f"\n🎉 Сбор завершен! Найдено: {res['found']}, добавлено в Бэклог: {res['added']}.")
