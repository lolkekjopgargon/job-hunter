#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
db.py - SQLite Database Manager for Job Hunter Desktop App.
Stores vacancies, card states, checklists, settings, and negotiation history in a single local file.
"""

import sqlite3
import json
import os
from typing import Dict, Any, List, Optional
from datetime import datetime

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
APP_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", ".."))

def find_db_path() -> str:
    env_path = os.environ.get("JOB_HUNTER_DB")
    if env_path:
        # Always trust JOB_HUNTER_DB from Electron main process.
        # Even if file doesn't exist yet — init_db() will create it there.
        db_dir = os.path.dirname(os.path.abspath(env_path))
        os.makedirs(db_dir, exist_ok=True)
        return env_path

    # Dev fallback: look for existing DB in standard locations
    candidates = [
        os.path.join(APP_DIR, "job_hunter.db"),
        os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", "job_hunter.db")),
        os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "App", "job_hunter.db")),
    ]
    for p in candidates:
        if os.path.exists(p):
            return p
    return os.path.join(APP_DIR, "job_hunter.db")

DB_PATH = find_db_path()


def get_connection() -> sqlite3.Connection:
    conn = sqlite3.connect(DB_PATH, timeout=30.0)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL")
        conn.execute("PRAGMA busy_timeout = 30000")
    except Exception:
        pass
    return conn



def init_db():
    conn = get_connection()
    c = conn.cursor()

    # 1. Vacancies table (Cards on Kanban)
    c.execute("""
    CREATE TABLE IF NOT EXISTS vacancies (
        id TEXT PRIMARY KEY,
        title TEXT NOT NULL,
        employer TEXT NOT NULL,
        url TEXT NOT NULL,
        salary TEXT,
        is_remote INTEGER DEFAULT 0,
        role_category TEXT NOT NULL,
        full_description TEXT,
        cover_letter TEXT,
        list_name TEXT DEFAULT 'backlog', -- backlog, approved, applied, interview, archive
        selected_resume_id TEXT,
        selected_materials_json TEXT,
        fit_notes_json TEXT,
        has_questionnaire INTEGER DEFAULT 0,
        manual_review_note TEXT,
        created_at TEXT,
        updated_at TEXT
    )
    """)

    # 2. Settings table
    c.execute("""
    CREATE TABLE IF NOT EXISTS settings (
        key TEXT PRIMARY KEY,
        value TEXT
    )
    """)

    # 3. Negotiations history (for status tracking)
    c.execute("""
    CREATE TABLE IF NOT EXISTS negotiations (
        vacancy_id TEXT PRIMARY KEY,
        employer TEXT,
        title TEXT,
        status TEXT,
        date_str TEXT,
        updated_at TEXT
    )
    """)

    # 4. Seen Vacancies table (Permanent deduplication)
    c.execute("""
    CREATE TABLE IF NOT EXISTS seen_vacancies (
        id TEXT PRIMARY KEY,
        title TEXT,
        employer TEXT,
        first_seen TEXT
    )
    """)

    # Sync existing vacancies to seen_vacancies
    c.execute("""
    INSERT OR IGNORE INTO seen_vacancies (id, title, employer, first_seen)
    SELECT id, title, employer, created_at FROM vacancies
    """)

    conn.commit()

    # Set default settings if not exists
    default_settings = {
        "scan_time": "11:00",
        "check_interval_min": "30",
        "llm_provider": "gemini",
        "llm_api_key": "",
        "llm_model": "gemini-2.5-flash",
        "hh_token": "",
        "hh_xsrf": "",
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36",
        "custom_contacts": "Ваше Имя
your.email@example.com
Telegram: @your_telegram",
        "custom_portfolio_links": json.dumps([
            {"id": "gd_spec", "title": "Game Design Specification (GDD / Notion)", "url": "https://drive.google.com/file/d/1rgMxRtjwmq1XIpI5rt32LeBj8ZRrS93r/view?usp=drive_link", "category": "game_design"},
            {"id": "combat_balance", "title": "Combat Balance & Data Architecture (Sheets)", "url": "https://drive.google.com/file/d/1RO46ycLAckr803ahy8ULLimjzwcHr4Bx/view?usp=drive_link", "category": "game_design"},
            {"id": "rpg_tracker", "title": "RPG Life Tracker / Dynamic Quest Engine Demo", "url": "https://youtu.be/_teOplLx3QY", "category": "game_design"},
            {"id": "artstation", "title": "ArtStation Portfolio (3D / UE5)", "url": "https://www.artstation.com/tejedakardenas", "category": "3d_art"},
            {"id": "ue5_previs", "title": "Unreal Engine 5 Previs Reel (Cinematics)", "url": "https://youtu.be/II82L2EZ8g0", "category": "3d_art"},
            {"id": "narrative_sample", "title": "Narrative Sample (Dialogue & Lore)", "url": "https://drive.google.com/file/d/1xvJnbGAKg970oqK4wQ2VGYpVNMDA6G/view?usp=drive_link", "category": "narrative"},
            {"id": "game_promo", "title": "Game Promo / Investor Presentation", "url": "https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk", "category": "game_design"},
            {"id": "acting_reel", "title": "Актерская визитка / Шоурил", "url": "https://youtu.be/5f1FLQ6sHr8", "category": "voice"}
        ], ensure_ascii=False),
        "search_queries": json.dumps([
            {
                "id": "gd",
                "name": "Гейм-дизайн",
                "query": "\"Гейм-дизайнер\" OR \"Game Designer\" OR \"Технический геймдизайнер\"",
                "resume_key": "game_designer",
                "salary_min": 120000,
                "schedule": "remote",
                "enabled": True
            },
            {
                "id": "narrative",
                "name": "Нарратив и озвучка",
                "query": "\"Нарративный дизайнер\" OR \"Narrative Designer\" OR \"Сценарист игр\"",
                "resume_key": "narrative_designer",
                "salary_min": 100000,
                "schedule": "remote",
                "enabled": True
            },
            {
                "id": "3d",
                "name": "3D Generalist / Art",
                "query": "\"3D Generalist\" OR \"3D Моделлер\" OR \"3D Artist\" OR \"3D Художник\"",
                "resume_key": "3d_generalist",
                "salary_min": 100000,
                "schedule": "remote",
                "enabled": True
            }
        ], ensure_ascii=False),
        # NOTE: agent_system_prompt and candidate_facts are NOT in DB defaults.
        # They live as .md files in userData — fully user-editable, never auto-reset.
    }

    for k, v in default_settings.items():
        c.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (k, v))

    # Auto-repair corrupted search_queries (e.g. from past encoding bugs with replacement chars  or empty lists)
    c.execute("SELECT value FROM settings WHERE key = 'search_queries'")
    row = c.fetchone()
    if row and ("\ufffd" in row["value"] or row["value"].strip() in ("", "[]")):
        c.execute("UPDATE settings SET value = ? WHERE key = 'search_queries'", (default_settings["search_queries"],))

    conn.commit()
    conn.close()


def get_setting(key: str, default: str = "") -> str:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT value FROM settings WHERE key = ?", (key,))
    row = c.fetchone()
    conn.close()
    return row["value"] if row else default


def set_setting(key: str, value: str):
    conn = get_connection()
    c = conn.cursor()
    c.execute("INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)", (key, value))
    conn.commit()
    conn.close()


def get_all_settings() -> Dict[str, str]:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT key, value FROM settings")
    rows = c.fetchall()
    conn.close()
    return {r["key"]: r["value"] for r in rows}


def save_vacancy(vac: Dict[str, Any]) -> bool:
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    try:
        c.execute("""
        INSERT OR REPLACE INTO vacancies (
            id, title, employer, url, salary, is_remote, role_category,
            full_description, cover_letter, list_name, selected_resume_id,
            selected_materials_json, fit_notes_json, has_questionnaire,
            manual_review_note, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, COALESCE((SELECT created_at FROM vacancies WHERE id = ?), ?), ?)
        """, (
            vac["id"], vac["title"], vac["employer"], vac["url"],
            vac.get("salary", "Не указана"), 1 if vac.get("is_remote") else 0,
            vac.get("role_category", "game_designer"),
            vac.get("full_description", ""), vac.get("cover_letter", ""),
            vac.get("list_name", "backlog"),
            vac.get("selected_resume_id", ""),
            json.dumps(vac.get("selected_materials", []), ensure_ascii=False) if isinstance(vac.get("selected_materials"), list) else vac.get("selected_materials_json", "[]"),
            json.dumps(vac.get("fit_notes", {}), ensure_ascii=False) if isinstance(vac.get("fit_notes"), dict) else vac.get("fit_notes_json", "{}"),
            1 if vac.get("has_questionnaire") else 0,
            vac.get("manual_review_note", ""),
            vac["id"], now, now
        ))
        conn.commit()
        return True
    finally:
        conn.close()


def get_vacancies_by_list(list_name: Optional[str] = None) -> List[Dict[str, Any]]:
    conn = get_connection()
    c = conn.cursor()
    if list_name:
        c.execute("SELECT * FROM vacancies WHERE list_name = ? ORDER BY updated_at DESC", (list_name,))
    else:
        c.execute("SELECT * FROM vacancies ORDER BY updated_at DESC")
    rows = c.fetchall()
    conn.close()

    result = []
    for r in rows:
        d = dict(r)
        d["selected_materials"] = json.loads(d.get("selected_materials_json") or "[]")
        d["fit_notes"] = json.loads(d.get("fit_notes_json") or "{}")
        result.append(d)
    return result


def move_vacancy(vacancy_id: str, new_list: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("UPDATE vacancies SET list_name = ?, updated_at = ? WHERE id = ?", (new_list, now, vacancy_id))
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def clear_archive() -> int:
    """Clears all vacancies in 'archive' from the Kanban board while permanently

    preserving them in seen_vacancies so the scanner never recommends them again.
    """
    conn = get_connection()
    c = conn.cursor()
    # 1. Guarantee every archive vacancy is safely recorded in seen_vacancies
    c.execute("""
    INSERT OR IGNORE INTO seen_vacancies (id, title, employer, first_seen)
    SELECT id, title, employer, created_at FROM vacancies WHERE list_name = 'archive'
    """)
    # 2. Delete from active board
    c.execute("DELETE FROM vacancies WHERE list_name = 'archive'")
    cleared_count = c.rowcount
    conn.commit()
    conn.close()
    return cleared_count



def update_vacancy_customization(vacancy_id: str, resume_id: str, materials: List[str], cover_letter: str) -> bool:
    conn = get_connection()
    c = conn.cursor()
    now = datetime.now().isoformat()
    c.execute("""
    UPDATE vacancies
    SET selected_resume_id = ?,
        selected_materials_json = ?,
        cover_letter = ?,
        updated_at = ?
    WHERE id = ?
    """, (resume_id, json.dumps(materials, ensure_ascii=False), cover_letter, now, vacancy_id))
    ok = c.rowcount > 0
    conn.commit()
    conn.close()
    return ok


def mark_seen_vacancy(vid: str, title: str = "", employer: str = ""):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "INSERT OR IGNORE INTO seen_vacancies (id, title, employer, first_seen) VALUES (?, ?, ?, ?)",
        (vid, title, employer, datetime.now().isoformat())
    )
    conn.commit()
    conn.close()


def get_all_seen_ids() -> set:
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM vacancies UNION SELECT id FROM seen_vacancies")
    ids = set(r[0] for r in c.fetchall())
    conn.close()
    return ids


if __name__ == "__main__":
    init_db()
    print(f"✓ SQLite database initialized at {DB_PATH}")
