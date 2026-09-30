#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
card_tasklists.py - Modular Planka TaskList Manager for Job Hunter.

Manages interactive Planka TaskLists for:
1. "📄 Резюме для отклика" (Single active selection between GD, Narrative, 3D, Actor).
2. "🔗 Портфолио и материалы" (Interactive checkboxes with name and direct URL).

Provides:
- setup_card_tasklists(): Initializes or updates tasklists on Planka cards.
- extract_selected_application_params(): Reads active resume and selected links from Planka.
- build_final_cover_letter(): Stitches clean agent speech + selected links + contacts.
- build_materials_cheat_sheet(): Generates compact bottom cheat-sheet for card description.
"""

import re
from typing import Dict, Any, List, Tuple, Optional

# Standard Resume Registry (HH Title, Resume Hash, Primary Role Keys)
RESUME_OPTIONS = [
    ("🎮 Гейм-дизайнер (150 000 ₽)", "ef85c34fff11045cfd0039ed1f314d32684a73", ["game_designer"]),
    ("📖 Нарративный дизайнер (130 000 ₽)", "ca0eeaf4ff10d8370e0039ed1f67683771696e", ["narrative_designer", "dialogue_director"]),
    ("🎨 3D generalist (130 000 ₽)", "413445ecff0b4f36200039ed1f474477685a36", ["3d_generalist", "creative_producer", "video_editor", "ai_product"]),
    ("🎭 Актер / Диктор (100 000 ₽)", "090a2123ff0ed3b8920039ed1f36356b596268", ["actor"])
]

# Standard Portfolio Registry (Label, URL, Primary Relevant Role Categories)
PORTFOLIO_OPTIONS = [
    ("📄 Game Design Specification", "https://drive.google.com/file/d/1rgMxRtjwmq1XIpI5rt32LeBj8ZRrS93r/view?usp=drive_link", ["game_designer"]),
    ("📊 Combat Balance & Data Architecture", "https://drive.google.com/file/d/1RO46ycLAckr803ahy8ULLimjzwcHr4Bx/view?usp=drive_link", ["game_designer"]),
    ("⚔️ RPG Life Tracker Prototype", "https://youtu.be/_teOplLx3QY", ["game_designer", "ai_product"]),
    ("🎨 ArtStation (3D / UE)", "https://www.artstation.com/tejedakardenas", ["3d_generalist", "creative_producer", "dialogue_director"]),
    ("🎬 Unreal Engine 5 Previs", "https://youtu.be/II82L2EZ8g0", ["3d_generalist", "creative_producer", "video_editor", "dialogue_director"]),
    ("📈 Game Promo / Investor Presentation", "https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk", ["creative_producer", "video_editor", "3d_generalist"]),
    ("🎙️ Шоурил / Короткометражный фильм", "https://youtu.be/5f1FLQ6sHr8", ["creative_producer", "video_editor", "actor"]),
    ("🤖 UE5 + Local LLM NPC System Demo", "https://youtu.be/l9lVrz5_dsc", ["ai_product", "game_designer"]),
    ("📖 Сценарий диалогов (The Expanse)", "https://drive.google.com/file/d/1xvJnbGAKg970oqK4wQ2VGYpVNMDA6G/view?usp=drive_link", ["narrative_designer", "dialogue_director"])
]

CONTACTS_BLOCK = (
    "Павел Тэхэда Кардэнас\n"
    "lol.kek.jopgargon@gmail.com\n"
    "Telegram: @Pasha_tejeda"
)


def build_materials_cheat_sheet() -> str:
    """Generates clean cheat-sheet for the bottom of card description."""
    lines = [
        "---",
        "### 📚 Реестр портфолио (шпаргалка для быстрой вставки):"
    ]
    for label, url, _ in PORTFOLIO_OPTIONS:
        clean_label = re.sub(r'^[^\w\s]+', '', label).strip()
        lines.append(f"• **{clean_label}:** {url}")
    lines.append("")
    lines.append("📇 **Прямые контакты:** Telegram: `@Pasha_tejeda` | Email: `lol.kek.jopgargon@gmail.com`")
    return "\n".join(lines)


def setup_card_tasklists(
    card_id: str,
    role_category: str,
    token: str,
    planka_req,
    existing_task_lists: Optional[List[Dict[str, Any]]] = None,
    existing_tasks: Optional[List[Dict[str, Any]]] = None,
    preselected_urls: Optional[List[str]] = None
) -> None:
    """
    Initializes standard Planka TaskLists on card:
    1. '📄 Резюме для отклика'
    2. '🔗 Портфолио и материалы'
    """
    if existing_task_lists is None or existing_tasks is None:
        c_data = planka_req("GET", f"cards/{card_id}", token=token)
        inc = c_data.get("included", {})
        existing_task_lists = inc.get("taskLists", [])
        existing_tasks = inc.get("tasks", [])

    card_tls = {tl["name"]: tl["id"] for tl in existing_task_lists if tl.get("cardId") == card_id}

    # 1. Setup TaskList: 📄 Резюме для отклика
    res_list_name = "📄 Резюме для отклика"
    if res_list_name not in card_tls:
        tl_res = planka_req("POST", f"cards/{card_id}/task-lists", token=token, data={
            "name": res_list_name,
            "position": 10000
        })
        tl_id = tl_res["item"]["id"]
        for idx, (title, _, target_roles) in enumerate(RESUME_OPTIONS):
            is_match = (role_category in target_roles)
            if not is_match and role_category not in ["narrative_designer", "dialogue_director", "3d_generalist", "creative_producer", "video_editor", "actor", "ai_product"] and idx == 0:
                is_match = True

            planka_req("POST", f"task-lists/{tl_id}/tasks", token=token, data={
                "name": title,
                "isCompleted": is_match,
                "position": (idx + 1) * 1000
            })

    # 2. Setup TaskList: 🔗 Портфолио и материалы
    links_list_name = "🔗 Портфолио и материалы"
    if links_list_name not in card_tls:
        tl_res = planka_req("POST", f"cards/{card_id}/task-lists", token=token, data={
            "name": links_list_name,
            "position": 20000
        })
        tl_id = tl_res["item"]["id"]
        for idx, (label, url, target_roles) in enumerate(PORTFOLIO_OPTIONS):
            if preselected_urls:
                is_checked = any(u in url or url in u for u in preselected_urls)
            else:
                is_checked = (role_category in target_roles)

            planka_req("POST", f"task-lists/{tl_id}/tasks", token=token, data={
                "name": f"{label}: {url}",
                "isCompleted": is_checked,
                "position": (idx + 1) * 1000
            })


def extract_selected_application_params(
    card_id: str,
    token: str,
    planka_req,
    fallback_resume_id: Optional[str] = None
) -> Dict[str, Any]:
    """
    Reads active resume and selected links from Planka card tasklists.
    User edits/checkboxes take absolute precedence!
    """
    b_data = planka_req("GET", f"cards/{card_id}", token=token)
    inc = b_data.get("included", {})
    task_lists = inc.get("taskLists", [])
    tasks = inc.get("tasks", [])

    card_tl_map = {tl["name"]: tl["id"] for tl in task_lists if tl.get("cardId") == card_id}

    # Extract Active Resume
    selected_resume_id = fallback_resume_id
    selected_resume_title = ""
    res_tl_id = card_tl_map.get("📄 Резюме для отклика")

    if res_tl_id:
        res_tasks = [t for t in tasks if t.get("taskListId") == res_tl_id and t.get("isCompleted")]
        if res_tasks:
            first_task = res_tasks[0]
            t_name = first_task.get("name", "")
            for title, r_id, _ in RESUME_OPTIONS:
                if title == t_name or any(k in t_name.lower() for k in title.lower().split()[:2]):
                    selected_resume_id = r_id
                    selected_resume_title = title
                    break

    # Extract Active Links (Support custom links added by user!)
    selected_materials = []
    links_tl_id = card_tl_map.get("🔗 Портфолио и материалы")

    if links_tl_id:
        link_tasks = [t for t in tasks if t.get("taskListId") == links_tl_id and t.get("isCompleted")]
        for lt in link_tasks:
            raw_name = lt.get("name", "")
            url_match = re.search(r'(https?://[^\s]+)', raw_name)
            if url_match:
                url = url_match.group(1).strip()
                label_part = raw_name.replace(url, "").strip().rstrip(":").strip()
                label = re.sub(r'^[^\w\s]+', '', label_part).strip()
                if not label:
                    label = "Материалы"
                selected_materials.append({"name": label, "url": url})
            elif raw_name.strip():
                selected_materials.append({"name": raw_name.strip(), "url": ""})

    return {
        "resume_id": selected_resume_id,
        "resume_title": selected_resume_title,
        "selected_materials": selected_materials
    }


def build_final_cover_letter(
    raw_speech: str,
    selected_materials: List[Dict[str, str]],
    contacts_block: Optional[str] = None
) -> str:
    """
    Assembles final dispatch letter adhering strictly to application_rules.md:
    1. Clean living author speech.
    2. Checked portfolio items (formatted Title:\nURL).
    3. Contacts block.
    """
    contacts = contacts_block or CONTACTS_BLOCK

    clean_speech = raw_speech.strip()
    clean_speech = re.sub(r"^```[a-zA-Z]*\r?\n?", "", clean_speech)
    clean_speech = re.sub(r"\r?\n?```$", "", clean_speech)
    clean_speech = clean_speech.strip("` \r\n\t")
    clean_speech = re.sub(r'Павел\s+Тэхэда.*$', '', clean_speech, flags=re.DOTALL | re.IGNORECASE).strip()
    clean_speech = re.sub(r'Примеры\s+проектных\s+материалов.*$', '', clean_speech, flags=re.DOTALL | re.IGNORECASE).strip()
    clean_speech = re.sub(r'Примеры\s+материалов.*$', '', clean_speech, flags=re.DOTALL | re.IGNORECASE).strip()
    clean_speech = re.sub(r'Материалы\s+из\s+портфолио.*$', '', clean_speech, flags=re.DOTALL | re.IGNORECASE).strip()
    clean_speech = re.sub(r'Материалы\s+по\s+теме.*$', '', clean_speech, flags=re.DOTALL | re.IGNORECASE).strip()

    blocks = [clean_speech]

    if selected_materials:
        mat_lines = ["Примеры проектных материалов:"]
        for mat in selected_materials:
            name = mat.get("name", "Материал").strip()
            url = mat.get("url", "").strip()
            if url:
                mat_lines.append(f"\n{name}:\n{url}")
            else:
                mat_lines.append(f"\n{name}")
        blocks.append("\n".join(mat_lines))

    blocks.append(contacts)

    return "\n\n".join(blocks).strip()
