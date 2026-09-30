#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
hh_resume_fetcher.py — Fetches user's resumes from HeadHunter Web Cabinet.
Connects directly to https://hh.ru/applicant/resumes using session cookies.
Parses resumes (both from HH-Lux-InitialState JSON and HTML DOM fallback).
Saves results into DB setting 'hh_resumes'.
"""

import os
import sys
import json
import re
import gzip
import html
import urllib.request
import urllib.error
from typing import Dict, Any, List

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from db import get_setting, set_setting


def clean_text(s: str) -> str:
    if not s:
        return ""
    s = re.sub(r'<[^>]+>', '', s)
    s = html.unescape(s)
    return re.sub(r'\s+', ' ', s).strip()


def fetch_hh_resumes() -> Dict[str, Any]:
    """Fetches user's resumes from https://hh.ru/applicant/resumes using web session cookies.

    Returns:
        {"success": True, "resumes": [...], "count": N} or {"success": False, "error": "..."}
    """
    token = get_setting("hh_token", "")
    xsrf = get_setting("hh_xsrf", "")
    cookie_str = get_setting("hh_cookie_str", "")
    ua = get_setting(
        "user_agent",
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36"
    )

    if not token and not cookie_str:
        return {"success": False, "error": "Сессия HeadHunter не найдена. Нажмите «Войти через HeadHunter»."}

    # Construct complete cookie header
    cookie_header = cookie_str if cookie_str else f"hhtoken={token}; _xsrf={xsrf}"
    if f"_xsrf={xsrf}" not in cookie_header and xsrf:
        cookie_header += f"; _xsrf={xsrf}"
    if f"hhtoken={token}" not in cookie_header and token:
        cookie_header += f"; hhtoken={token}"

    headers = {
        "User-Agent": ua,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
        "Accept-Language": "ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7",
        "Accept-Encoding": "gzip, deflate",
        "Connection": "keep-alive",
        "Referer": "https://hh.ru/",
        "Cookie": cookie_header
    }

    url = "https://hh.ru/applicant/resumes"
    req = urllib.request.Request(url, headers=headers)

    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            final_url = resp.geturl()
            if "login" in final_url or "/account/login" in final_url:
                return {
                    "success": False,
                    "error": "Сессия устарела — сайт HH перенаправил на страницу входа. Нажмите «Войти через HeadHunter»."
                }

            raw = resp.read()
            if resp.headers.get("Content-Encoding") == "gzip":
                try:
                    raw = gzip.decompress(raw)
                except Exception:
                    pass
            page_html = raw.decode("utf-8", errors="ignore")
    except urllib.error.HTTPError as he:
        return {"success": False, "error": f"Ошибка запроса HH ({he.code})"}
    except Exception as e:
        return {"success": False, "error": f"Сетевая ошибка: {e}"}

    resumes: List[Dict[str, Any]] = []
    seen_ids = set()

    # Helper to clean up any messy concatenated text
    def sanitize_resume_title(raw_title: str, salary_str: str = "") -> str:
        t = raw_title.strip()
        # Remove English employment / schedule garbage injected by HH DOM
        t = re.sub(r'^(?:Permanent job|Part-time job|Full day|Remote work|Shift schedule|Fly-in fly-out)[,\s]*', '', t, flags=re.IGNORECASE)
        t = re.sub(r'(?:Permanent job|part-time job|Full day|Remote work|Shift schedule|Fly-in fly-out)[,\s]*', '', t, flags=re.IGNORECASE)
        # Remove trailing location / metadata garbage
        t = re.sub(r'(?:At the employer\'s location|Remote and more|Many people don\'t see your resume).*$', '', t, flags=re.IGNORECASE).strip()
        # Remove inline salary if already attached to title
        t = re.sub(r'\d[\d\s\u2009\xa0]*\s*(?:₽|руб|rur|rub).*$', '', t, flags=re.IGNORECASE).strip()
        t = t.strip('·•,- ')
        if salary_str:
            return f"{t} — {salary_str}" if t else salary_str
        return t

    # Strategy 1: Check ResumeProfileFront-InitialState (the official SSR state for applicant resumes)
    profile_match = re.search(r'<template[^>]*class="ResumeProfileFront-InitialState"[^>]*>(.*?)</template>', page_html, re.DOTALL)
    if profile_match:
        try:
            raw_json = html.unescape(profile_match.group(1).strip())
            p_data = json.loads(raw_json)
            applicant_resumes = p_data.get("applicantResumes", [])

            for item in applicant_resumes:
                attrs = item.get("_attributes", {})
                r_id = attrs.get("hash") or str(attrs.get("id") or "")
                if not r_id or r_id in seen_ids:
                    continue

                # Title extraction
                title_field = item.get("title")
                r_title = ""
                if isinstance(title_field, list) and title_field and isinstance(title_field[0], dict):
                    r_title = title_field[0].get("string") or ""
                elif isinstance(title_field, str):
                    r_title = title_field

                # Salary extraction
                salary_field = item.get("salary")
                r_salary = ""
                if isinstance(salary_field, list) and salary_field and isinstance(salary_field[0], dict):
                    amt = salary_field[0].get("amount")
                    curr = salary_field[0].get("currency", "RUR")
                    curr_sym = "₽" if curr in ("RUR", "RUB") else curr
                    if amt:
                        r_salary = f"{amt:,} {curr_sym}".replace(",", " ")

                # Status
                st = attrs.get("status") or "Опубликовано"
                r_status = "Опубликовано" if st in ("approved", "modified", "active") else str(st)

                clean_display = sanitize_resume_title(r_title, r_salary)
                if not clean_display:
                    clean_display = f"Резюме ({r_id[:8]}...)"

                seen_ids.add(r_id)
                resumes.append({
                    "id": r_id,
                    "title": clean_display,
                    "status": r_status,
                    "url": f"https://hh.ru/resume/{r_id}"
                })
        except Exception as e:
            print(f"⚠️ Ошибка парсинга ResumeProfileFront-InitialState: {e}", file=sys.stderr, flush=True)

    # Strategy 2: Check data-qa="resume" with clean data-qa-title in HTML DOM
    if not resumes:
        card_matches = re.finditer(r'<div[^>]*data-qa="resume"[^>]*data-qa-title="([^"]+)"', page_html)
        for m in card_matches:
            title = m.group(1).strip()
            block = page_html[m.start():m.start() + 3000]

            hash_m = re.search(r'/resume/([a-f0-9]{38,44})', block)
            r_id = hash_m.group(1) if hash_m else ""

            if not r_id or r_id in seen_ids:
                continue

            # Extract salary if present
            salary_m = re.search(r'data-qa="cell-text-content"[^>]*>(\d[\d\s\u2009\xa0]*\s*<!--.*?-->\s*₽|\d[\d\s\u2009\xa0]*\s*₽)', block)
            salary = ""
            if salary_m:
                raw_sal = re.sub(r'<[^>]+>', '', salary_m.group(1))
                raw_sal = raw_sal.replace('\u2009', ' ').replace('\xa0', ' ').strip()
                sal_match = re.search(r'(\d[\d\s]*\s*₽)', raw_sal)
                if sal_match:
                    salary = sal_match.group(1).strip()

            clean_display = sanitize_resume_title(title, salary)
            seen_ids.add(r_id)
            resumes.append({
                "id": r_id,
                "title": clean_display,
                "status": "Опубликовано",
                "url": f"https://hh.ru/resume/{r_id}"
            })

    # Strategy 3: HTML DOM link matches fallback
    if not resumes:
        link_matches = re.finditer(
            r'href="(?:\/resume\/|https:\/\/hh\.ru\/resume\/)([a-f0-9]{38,44})[^"]*"[^>]*>(.*?)<\/a>',
            page_html,
            re.DOTALL
        )
        for m in link_matches:
            r_id = m.group(1)
            raw_title = m.group(2)
            clean_t = clean_text(raw_title)

            # Ignore generic utility links
            if not clean_t or clean_t.lower() in ("открыть", "редактировать", "скачать", "поделиться"):
                continue

            if r_id not in seen_ids:
                seen_ids.add(r_id)
                clean_display = sanitize_resume_title(clean_t)
                resumes.append({
                    "id": r_id,
                    "title": clean_display or f"Резюме {r_id[:8]}...",
                    "status": "Опубликовано",
                    "url": f"https://hh.ru/resume/{r_id}"
                })

    # Strategy 3: Any resume link href matching 38-44 hex pattern without link text, fallback to title search
    if not resumes:
        hashes = re.findall(r'/resume/([a-f0-9]{38,44})', page_html)
        for h in set(hashes):
            if h not in seen_ids:
                seen_ids.add(h)
                resumes.append({
                    "id": h,
                    "title": f"Резюме {h[:8]}...",
                    "status": "Опубликовано",
                    "url": f"https://hh.ru/resume/{h}"
                })

    if not resumes:
        # Check if the page actually says user has no resumes
        if "нет резюме" in page_html.lower() or "создайте резюме" in page_html.lower():
            return {
                "success": False,
                "error": "На аккаунте HeadHunter нет созданных резюме. Создайте хотя бы одно резюме на hh.ru."
            }
        return {
            "success": False,
            "error": "Не удалось извлечь резюме со страницы https://hh.ru/applicant/resumes. Проверьте авторизацию."
        }

    # Save to SQLite settings as JSON string
    set_setting("hh_resumes", json.dumps(resumes, ensure_ascii=False))

    print(f"✓ Успешно спарсено {len(resumes)} резюме с HeadHunter:", file=sys.stderr, flush=True)
    for r in resumes:
        print(f"  • {r['title']} [{r['status']}] (ID: {r['id'][:10]}...)", file=sys.stderr, flush=True)

    return {"success": True, "resumes": resumes, "count": len(resumes)}


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    result = fetch_hh_resumes()
    print(json.dumps(result, ensure_ascii=False, indent=2))

