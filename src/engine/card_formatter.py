#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
card_formatter.py - Visual Formatter for Planka Vacancy Cards.

Handles:
1. Standardized salary labels:
   - "💰 до 100 000 ₽"
   - "💰 100 000 – 150 000 ₽"
   - "💰 150 000 – 200 000 ₽"
   - "💰 от 200 000 ₽"
   - "⚪ ЗП не указана"
2. Standardized resume labels:
   - "📄 Резюме: Гейм-дизайнер"
   - "📄 Резюме: Нарративный дизайнер"
   - "📄 Резюме: 3D generalist"
   - "📄 Резюме: Актер"
3. Clean card title formatting: "Компания ‣ Должность" (no salary, no remote tags).
4. Universal structured role description without monolithic text heaps.
"""

import re
import html
from requirement_filter import split_vacancy_sections


RESUME_LABELS = {
    "game_designer": "📄 Резюме: Гейм-дизайнер",
    "narrative_designer": "📄 Резюме: Нарративный дизайнер",
    "dialogue_director": "📄 Резюме: Нарративный дизайнер",
    "3d_generalist": "📄 Резюме: 3D generalist",
    "creative_producer": "📄 Резюме: 3D generalist",
    "video_editor": "📄 Резюме: 3D generalist",
    "ai_product": "📄 Резюме: 3D generalist",
    "actor": "📄 Резюме: Актер"
}

STANDARD_LABELS = [
    ("💰 до 100 000 ₽", "sunny-grass"),
    ("💰 100 000 – 150 000 ₽", "summer-sky"),
    ("💰 150 000 – 200 000 ₽", "orange-peel"),
    ("💰 от 200 000 ₽", "turquoise-sea"),
    ("⚪ ЗП не указана", "concrete"),
    ("📄 Резюме: Гейм-дизайнер", "summer-sky"),
    ("📄 Резюме: Нарративный дизайнер", "lavender-fields"),
    ("📄 Резюме: 3D generalist", "turquoise-sea"),
    ("📄 Резюме: Актер", "orange-peel"),
    ("🎮 Godot / GameDev", "summer-sky"),
    ("🏠 Удаленка", "turquoise-sea"),
    ("🤖 AI Письмо", "lavender-fields"),
    ("⚠️ Ручной вопрос", "berry-red"),
    ("📝 Ручная анкета / Форма", "berry-red")
]

ACTION_VERBS = (
    r"(?:Помогать|Самостоятельно|Придумывать|Формировать|Выстраивать|Вести|Участие|Создавать|"
    r"Проектировать|Писать|Собирать|Разбирать|Работать|Умение|Опыт|Понимание|Внимание|Интерес|"
    r"Знание|Владение|Настройка|Моделирование|Подбор|Выполнение|Подготовка|Разработка|Контроль|"
    r"Анализ|Оценка|Поддержка|Изучение|Внедрение|Управление|Организация|Взаимодействие|Готовность|"
    r"Уверенное|Хороший|Высокий|Отличное|Технический|Английский|Оказывать|Обеспечивать|Тестировать)"
)


def ensure_board_labels(board_id: str, token: str, planka_req_func) -> Dict[str, str]:
    """Ensures all standard salary, resume, and utility labels exist on Planka board."""
    b_data = planka_req_func("GET", f"boards/{board_id}", token=token)
    existing_labels = {l["name"]: l["id"] for l in b_data.get("included", {}).get("labels", [])}

    for idx, (name, color) in enumerate(STANDARD_LABELS):
        if name not in existing_labels:
            try:
                res = planka_req_func("POST", f"boards/{board_id}/labels", token=token, data={
                    "name": name,
                    "color": color,
                    "position": (idx + 1) * 10000
                })
                existing_labels[name] = res["item"]["id"]
            except Exception:
                pass

    return existing_labels


def parse_salary_details(raw_salary: str) -> Tuple[str, str]:
    """
    Parses verbose HH salary string into:
    (compact_title_str, salary_label_name)
    Example:
      "from 150 000 up to 300 000 ₽ per month before tax" -> ("150k–300k ₽", "💰 от 200 000 ₽")
      "Не указана" -> ("", "⚪ ЗП не указана")
    """
    if not raw_salary or "не указана" in raw_salary.lower() or raw_salary.strip() == "":
        return "", "⚪ ЗП не указана"

    curr = "₽"
    if any(k in raw_salary.lower() for k in ["usd", "$"]):
        curr = "$"
    elif any(k in raw_salary.lower() for k in ["eur", "€"]):
        curr = "€"
    elif any(k in raw_salary.lower() for k in ["kzt", "₸"]):
        curr = "₸"

    cleaned = raw_salary.replace("\u00a0", " ")
    nums = [int(n.replace(" ", "")) for n in re.findall(r'\b\d[\d\s]{2,}\b', cleaned)]

    if not nums:
        return "", "⚪ ЗП не указана"

    def fmt_num(val: int) -> str:
        if curr in ["$", "€"]:
            return f"{val:,}".replace(",", " ")
        if val >= 1000:
            if val % 1000 == 0:
                return f"{val // 1000}k"
            elif val % 100 == 0:
                return f"{val / 1000:.1f}k"
        return str(val)

    compact_str = ""
    target_val = nums[-1]

    if len(nums) >= 2:
        compact_str = f"{fmt_num(nums[0])}–{fmt_num(nums[1])} {curr}"
        target_val = nums[1]
    elif len(nums) == 1:
        if any(k in cleaned.lower() for k in ["от", "from"]):
            compact_str = f"от {fmt_num(nums[0])} {curr}"
        elif any(k in cleaned.lower() for k in ["до", "up to", "to"]):
            compact_str = f"до {fmt_num(nums[0])} {curr}"
        else:
            compact_str = f"{fmt_num(nums[0])} {curr}"
        target_val = nums[0]

    rub_val = target_val
    if curr == "$":
        rub_val = target_val * 90
    elif curr == "€":
        rub_val = target_val * 100

    if rub_val < 100000:
        label = "💰 до 100 000 ₽"
    elif 100000 <= rub_val < 150000:
        label = "💰 100 000 – 150 000 ₽"
    elif 150000 <= rub_val < 200000:
        label = "💰 150 000 – 200 000 ₽"
    else:
        label = "💰 от 200 000 ₽"

    return compact_str, label


def sanitize_entity_text(val: str) -> str:
    """Strips markdown bold/italic asterisks, underscores, hashes, HTML entities and extra whitespace."""
    if not val:
        return ""
    cleaned = html.unescape(val)
    cleaned = re.sub(r'[*_#`]+', ' ', cleaned)
    cleaned = cleaned.replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", " ")
    return re.sub(r'\s+', ' ', cleaned).strip()


def clean_job_title(title: str) -> str:
    """Strips remote markers, salary remnants, HTML entities, and stray brackets from title."""
    t = sanitize_entity_text(title)
    # Remove bracketed remote markers
    t = re.sub(r'[\(\[\{]\s*(?:удаленн?о|удалённ?о|дистанционн?о|remote|гибрид|удаленка|удалёнка)[^\)\]\}]*[\)\]\}]', '', t, flags=re.IGNORECASE)
    # Remove slash/dash remote e.g. "/ Удаленно" or "- remote"
    t = re.sub(r'\s*[/\\|\-–—]\s*(?:удаленн?о|удалённ?о|дистанционн?о|remote|гибрид|удаленка|удалёнка)\b.*', '', t, flags=re.IGNORECASE)
    # Remove standalone remote words
    t = re.sub(r'\b(?:удаленн?о|удалённ?о|дистанционн?о|remote)\b', '', t, flags=re.IGNORECASE)
    # Remove any lingering salary figures in brackets
    t = re.sub(r'[\(\[\{][\d\s\–\-\+kк₽\$€₸]+[\)\]\}]', '', t, flags=re.IGNORECASE)
    # Clean dangling empty brackets or punctuation
    t = re.sub(r'[\(\[\{]\s*[\)\]\}]', '', t)
    t = re.sub(r'\s+[/\\|\-–—,]\s*$', '', t)
    t = re.sub(r'\s+', ' ', t).strip()
    return t


def format_card_title(employer: str, title: str, raw_salary: str = "") -> str:
    """Formats single-line card title strictly as 'Компания ‣ Должность' (no salary, no remote tags)."""
    emp = sanitize_entity_text(employer)
    t = clean_job_title(title)
    return f"{emp} ‣ {t}"


def format_bullet_list(text: str, max_items: int = 12) -> List[str]:
    """Cleans up and converts raw text into clear, standardized bullet items."""
    if not text:
        return []

    lines = [l.strip() for l in text.split("\n") if l.strip()]
    raw_units = []

    for l in lines:
        if ";" in l:
            sub = [s.strip() for s in l.split(";") if len(s.strip()) > 3]
            raw_units.extend(sub)
        elif re.search(rf'(?<=[a-zа-яё\.\;\)])\s+(?={ACTION_VERBS}\b)', l):
            sub = re.split(rf'(?<=[a-zа-яё\.\;\)])\s+(?={ACTION_VERBS}\b)', l)
            raw_units.extend([s.strip() for s in sub if s.strip()])
        elif " - " in l or ":-" in l:
            sub = re.split(r'(?:\s+-\s+|:-)', l)
            raw_units.extend([s.strip() for s in sub if s.strip()])
        elif re.search(r'\.\s{2,}[А-ЯA-Z]', l):
            sub = re.split(r'(?<=\.)\s{2,}(?=[А-ЯA-Z])', l)
            raw_units.extend([s.strip() for s in sub if s.strip()])
        else:
            raw_units.append(l)

    bullets = []
    for unit in raw_units:
        clean = re.sub(r'^[•\-\*\d\.\)\s]+', '', unit).strip()
        clean = re.sub(r'[;,]$', '', clean).strip()
        if len(clean) > 3:
            clean = clean[0].upper() + clean[1:]
            bullets.append(f"• {clean}")

    return bullets[:max_items]


def clean_general_block(text: str) -> Tuple[str, str]:
    """Formats company/project overview block, separating intro paragraph and extracted bullets."""
    t = text.replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", " ")
    m_list = re.search(r'(?:факты[^\:]*:|:\s*-\s*|\s+-\s+\d|\s+-\s+[А-ЯA-Z])', t, re.IGNORECASE)
    if m_list:
        intro = t[:m_list.start()].strip()
        list_part = t[m_list.start():].strip()
        intro_sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', intro) if len(s.strip()) > 10]
        intro_text = " ".join(intro_sentences[:3])

        raw_bullets = re.split(r'(?:\s+-\s+|:\s*-\s*|\n-\s*)', list_part)
        bullets = []
        for b in raw_bullets:
            b_clean = re.sub(r'^(?:факты[^\:]*:|[•\-\*\d\.\)\s])+', '', b).strip()
            b_clean = re.sub(r'[;,]$', '', b_clean).strip()
            if len(b_clean) > 8:
                b_clean = b_clean[0].upper() + b_clean[1:]
                bullets.append(f"• {b_clean}")

        bullets_str = "\n".join(bullets[:8]) if bullets else ""
        return intro_text, bullets_str
    else:
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', t) if len(s.strip()) > 10]
        if len(sentences) > 2:
            p1 = " ".join(sentences[:2])
            p2 = " ".join(sentences[2:5])
            return f"{p1}\n\n{p2}", ""
        return " ".join(sentences), ""


def format_structured_role_description(description: str) -> str:
    """
    Parses flat description into clean, readable sections:
    - About Company / Project
    - Responsibilities
    - Requirements
    - Nice to have
    - Conditions
    Guarantees no card is ever left as a monolithic heap of text.
    """
    sections = split_vacancy_sections(description)
    blocks = []

    # 1. About Company / Project
    general = sections.get("general", "").strip()
    extracted_bullets = ""
    if general:
        intro_text, extracted_bullets = clean_general_block(general)
        if intro_text:
            blocks.append("**🏢 О проекте и компании**\n" + intro_text)

    # 2. Responsibilities
    resp = sections.get("responsibilities", "").strip()
    if resp:
        bullets = format_bullet_list(resp, max_items=12)
        if bullets:
            blocks.append("**🎯 Задачи и обязанности**\n" + "\n".join(bullets))
        else:
            blocks.append("**🎯 Задачи и обязанности**\n" + resp)
    elif extracted_bullets:
        blocks.append("**🎯 Ключевые детали роли / задачи**\n" + extracted_bullets)

    # 3. Must Have Requirements
    must = sections.get("must_have", "").strip()
    if must:
        bullets = format_bullet_list(must, max_items=12)
        if bullets:
            blocks.append("**📌 Требования**\n" + "\n".join(bullets))
        else:
            blocks.append("**📌 Требования**\n" + must)

    # 4. Nice to have
    nice = sections.get("nice_to_have", "").strip()
    if nice:
        bullets = format_bullet_list(nice, max_items=8)
        if bullets:
            blocks.append("**💡 Будет плюсом**\n" + "\n".join(bullets))
        else:
            blocks.append("**💡 Будет плюсом**\n" + nice)

    # 5. Conditions
    cond = sections.get("conditions", "").strip()
    if cond:
        bullets = format_bullet_list(cond, max_items=6)
        if bullets:
            blocks.append("**🎁 Условия**\n" + "\n".join(bullets))

    # Universal Fallback: If only 1 block exists and has no bullets, break it into intro + bullets
    if len(blocks) == 1 and "•" not in blocks[0]:
        text_inside = re.sub(r'\*\*[^\n]+\*\*\n', '', blocks[0]).strip()
        sentences = [s.strip() for s in re.split(r'(?<=[.!?])\s+', text_inside) if len(s.strip()) > 8]
        if len(sentences) >= 3:
            blocks = [
                "**🏢 О проекте и компании**\n" + " ".join(sentences[:2]),
                "**🎯 Ключевые детали роли**\n" + "\n".join([f"• {s}" for s in sentences[2:8]])
            ]

    if not blocks:
        clean_text = "\n".join([line.strip() for line in description.split("\n") if line.strip()])
        return clean_text

    return "\n\n".join(blocks)
