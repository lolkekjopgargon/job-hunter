#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Candidate Context & Rule Evaluator for Job Hunter.
Reads:
  - candidate_facts.md (single source of truth for facts)
  - candidate_preferences.md (search priorities and hard exclusions)
  - portfolio_index.md (curated portfolio bundles)
  - application_rules.md (truthfulness policy, taxonomy, approval gates)

Provides:
  - Vacancy filtering (hard exclusions: pure dev, SAMP/RP, shorts conveyor)
  - Fact status taxonomy matching (VERIFIED, ADJACENT, UNCONFIRMED, NOT MATCHED)
  - Portfolio selection (2-4 relevant links per role bundle)
  - Truthful cover letter generation (no hallucinations, explicit personal project/vibe-coding boundary)
  - Daily ranking and selection of top 10-15 vacancies.
"""

import os
import re
from typing import Dict, Any, List, Tuple, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

FACTS_FILE = os.path.join(SCRIPT_DIR, "candidate_facts.md")
PREFERENCES_FILE = os.path.join(SCRIPT_DIR, "candidate_preferences.md")
PORTFOLIO_FILE = os.path.join(SCRIPT_DIR, "portfolio_index.md")
RULES_FILE = os.path.join(SCRIPT_DIR, "application_rules.md")
from requirement_filter import evaluate_hard_technical_filter
from card_formatter import format_structured_role_description, sanitize_entity_text
from card_tasklists import build_materials_cheat_sheet

# Hard exclusion keywords (lowercased)
EXCLUDED_DEV_KEYWORDS = [
    "backend developer", "frontend developer", "fullstack developer",
    "software engineer", "software developer", "python developer",
    "javascript developer", "typescript developer", "gameplay programmer",
    "engine programmer", "tools programmer", "devops", "системный программист",
    "ведущий программист", "разработчик c++", "разработчик python",
    "разработчик go", "golang developer", "java developer",
    "sre", "site reliability", "shift engineer", "инженер sre", "дежурный инженер",
    "sysadmin", "системный администратор", "qa engineer", "тестировщик", "manual qa", "automation qa"
]

EXCLUDED_SAMP_KEYWORDS = [
    "samp", "sa-mp", "gta rp", "gta roleplay", "fivem",
    "гта рп", "ролеплей сервер", "samp сервер"
]

EXCLUDED_CONVEYOR_KEYWORDS = [
    "только shorts", "монтаж reels", "конвейер tiktok", "нарезка shorts",
    "нарезчик reels", "монтажер tiktok", "bulk editing", "массовый монтаж shorts"
]

PORTFOLIO_BUNDLES = {
    "narrative_designer": [
        {"name": "Narrative Sample (Dialogue & Lore)", "url": "https://drive.google.com/file/d/1xvJnbGAKg970oqK4wQ2VGYpVNMDA6G/view?usp=drive_link"},
        {"name": "Worldbuilding & Quest Sample", "url": "https://drive.google.com/file/d/1qkAr3uKa55h3asBVYJcRhajTRjvORlcx/view?usp=drive_link"},
        {"name": "ArtStation (Visual & Cinematic Staging)", "url": "https://www.artstation.com/tejedakardenas"}
    ],
    "dialogue_director": [
        {"name": "Narrative Sample (Dialogue Scene Writing)", "url": "https://drive.google.com/file/d/1xvJnbGAKg970oqK4wQ2VGYpVNMDA6G/view?usp=drive_link"},
        {"name": "Unreal Previs (Cinematic Dialogue & Camera Staging)", "url": "https://youtu.be/II82L2EZ8g0"},
        {"name": "Game Promo / Investor Presentation", "url": "https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk"},
        {"name": "ArtStation", "url": "https://www.artstation.com/tejedakardenas"}
    ],
    "game_designer": [
        {"name": "Game Design Specification", "url": "https://drive.google.com/file/d/1rgMxRtjwmq1XIpI5rt32LeBj8ZRrS93r/view?usp=drive_link"},
        {"name": "Combat Balance & Data Architecture", "url": "https://drive.google.com/file/d/1RO46ycLAckr803ahy8ULLimjzwcHr4Bx/view?usp=drive_link"},
        {"name": "RPG Life Tracker / Dynamic Quest Engine Demo", "url": "https://youtu.be/_teOplLx3QY"}
    ],
    "video_editor": [
        {"name": "Game Promo / Investor Presentation", "url": "https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk"},
        {"name": "Graduation Short Film", "url": "https://youtu.be/5f1FLQ6sHr8"},
        {"name": "Unreal Previs", "url": "https://youtu.be/II82L2EZ8g0"}
    ],
    "creative_producer": [
        {"name": "Game Promo / Investor Presentation", "url": "https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk"},
        {"name": "Unreal Previs", "url": "https://youtu.be/II82L2EZ8g0"},
        {"name": "Graduation Short Film", "url": "https://youtu.be/5f1FLQ6sHr8"},
        {"name": "ArtStation Portfolio", "url": "https://www.artstation.com/tejedakardenas"}
    ],
    "3d_generalist": [
        {"name": "ArtStation Portfolio", "url": "https://www.artstation.com/tejedakardenas"},
        {"name": "Unreal Previs", "url": "https://youtu.be/II82L2EZ8g0"},
        {"name": "Game Promo / Investor Presentation", "url": "https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk"}
    ],
    "ai_product": [
        {"name": "UE5 + Local LLM NPC Agent System Demo", "url": "https://youtu.be/l9lVrz5_dsc"},
        {"name": "RPG Life Tracker / Dynamic Quest Engine Demo", "url": "https://youtu.be/_teOplLx3QY"},
        {"name": "YouTube Channel", "url": "https://www.youtube.com/@tejedakardenas"}
    ]
}

CONTACTS_BLOCK = (
    "Павел Тэхэда Кардэнас\n"
    "lol.kek.jopgargon@gmail.com\n"
    "Telegram: @Pasha_tejeda"
)

RESUME_METADATA = {
    "game_designer": {
        "title": "Гейм-дизайнер (150 000 ₽)",
        "id": "ef85c34fff11045cfd0039ed1f314d32684a73",
        "url": "https://hh.ru/resume/ef85c34fff11045cfd0039ed1f314d32684a73"
    },
    "narrative_designer": {
        "title": "Нарративный дизайнер (130 000 ₽)",
        "id": "ca0eeaf4ff10d8370e0039ed1f67683771696e",
        "url": "https://hh.ru/resume/ca0eeaf4ff10d8370e0039ed1f67683771696e"
    },
    "dialogue_director": {
        "title": "Нарративный дизайнер (130 000 ₽)",
        "id": "ca0eeaf4ff10d8370e0039ed1f67683771696e",
        "url": "https://hh.ru/resume/ca0eeaf4ff10d8370e0039ed1f67683771696e"
    },
    "3d_generalist": {
        "title": "3D generalist (130 000 ₽)",
        "id": "413445ecff0b4f36200039ed1f474477685a36",
        "url": "https://hh.ru/resume/413445ecff0b4f36200039ed1f474477685a36"
    },
    "creative_producer": {
        "title": "3D generalist (130 000 ₽)",
        "id": "413445ecff0b4f36200039ed1f474477685a36",
        "url": "https://hh.ru/resume/413445ecff0b4f36200039ed1f474477685a36"
    },
    "video_editor": {
        "title": "3D generalist (130 000 ₽)",
        "id": "413445ecff0b4f36200039ed1f474477685a36",
        "url": "https://hh.ru/resume/413445ecff0b4f36200039ed1f474477685a36"
    },
    "ai_product": {
        "title": "3D generalist (130 000 ₽)",
        "id": "413445ecff0b4f36200039ed1f474477685a36",
        "url": "https://hh.ru/resume/413445ecff0b4f36200039ed1f474477685a36"
    }
}

def format_portfolio_plain(portfolio: List[Dict[str, str]]) -> str:
    """Formats portfolio links into strict plain text (Title:\nURL) without markdown or dashes."""
    blocks = []
    for p in portfolio:
        blocks.append(f"{p['name']}:\n{p['url']}")
    return "\n\n".join(blocks)


class CandidateContextEvaluator:
    def __init__(self):
        self.facts = self._read_file(FACTS_FILE)
        self.preferences = self._read_file(PREFERENCES_FILE)
        self.portfolio = self._read_file(PORTFOLIO_FILE)
        self.rules = self._read_file(RULES_FILE)

    def _read_file(self, path: str) -> str:
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read()
        return ""

    def is_hard_excluded(self, title: str, description: str) -> Tuple[bool, str]:
        """
        Checks vacancy title and description against hard exclusion rules.
        Uses requirement_filter for deep section analysis and technical mismatch.
        Returns: (is_excluded: bool, filter_note: str)
          - If verdict is REJECT: returns (True, reason)
          - If verdict is REVIEW: returns (False, reason)
          - If verdict is PASS: returns (False, "")
        """
        verdict, reason = evaluate_hard_technical_filter(title, description)
        if verdict == "REJECT":
            return True, reason
        elif verdict == "REVIEW":
            return False, reason
        return False, ""

    def evaluate_role_category(self, title: str, description: str) -> str:
        """Determines best matching target role category, prioritizing the vacancy title."""
        title_lower = title.lower()

        # 1. Exact matches in job title first
        if any(k in title_lower for k in ["creative producer", "креативный продюсер"]):
            return "creative_producer"
        if any(k in title_lower for k in ["dialogue", "постановка диалогов", "voiceover", "voice over", "озвучк"]):
            return "dialogue_director"
        if any(k in title_lower for k in ["гейм-дизайн", "геймдизайн", "game design", "level design", "левел-дизайн"]):
            return "game_designer"
        if any(k in title_lower for k in ["нарратив", "сценарист", "narrative", "writer"]):
            return "narrative_designer"
        if any(k in title_lower for k in ["видеомонтаж", "монтажер", "video edit", "trailer", "моушн", "motion"]):
            return "video_editor"
        if any(k in title_lower for k in ["3d", "моделлер", "artist", "художник", "unreal", "previs"]):
            return "3d_generalist"
        if re.search(r'\b(ai|llm|rag|neural|нейросет|нейронн)\b', title_lower):
            return "ai_product"

        # 2. Fallback to full text
        t = f"{title} {description}".lower()
        if any(k in t for k in ["creative producer", "креативный продюсер"]):
            return "creative_producer"
        if any(k in t for k in ["dialogue", "постановка диалогов", "диалог", "voiceover", "voice over", "озвучк", "голос"]):
            return "dialogue_director"
        if any(k in t for k in ["гейм-дизайн", "геймдизайн", "game design", "системный гейм"]):
            return "game_designer"
        if any(k in t for k in ["нарратив", "сценарист", "narrative", "writer", "сюжет"]):
            return "narrative_designer"
        if any(k in t for k in ["видеомонтаж", "монтажер", "video edit", "trailer", "трейлер", "промо"]):
            return "video_editor"
        if any(k in t for k in ["3d", "моделлер", "artist", "unreal", "previs"]):
            return "3d_generalist"
        if re.search(r'\b(ai|llm|rag|neural|нейросет|нейронн)\b', t):
            return "ai_product"
        return "game_designer"

    def analyze_taxonomy(self, role_category: str, title: str, description: str) -> Dict[str, List[str]]:
        """
        Classifies requirements into VERIFIED, ADJACENT, UNCONFIRMED, NOT MATCHED.
        Strictly prevents hallucinated experience.
        """
        desc_lower = description.lower()
        verified = []
        adjacent = []
        unconfirmed = []
        not_matched = []

        # 1. Check Engines / Tools
        if "unreal" in desc_lower or "ue4" in desc_lower or "ue5" in desc_lower:
            verified.append("Unreal Engine 5 (коммерческий опыт в Owlcat Games, CGF, личные проекты)")
        if "unity" in desc_lower:
            adjacent.append("Unity: смежный опыт разработки на Unreal Engine 5; коммерческий Unity не подтвержден")
        if "blender" in desc_lower:
            verified.append("Blender (моделирование, пайплайн)")
        if "davinci" in desc_lower or "монтаж" in desc_lower:
            verified.append("DaVinci Resolve (монтаж, цветокоррекция, пост-продакшн)")
        if "articy" in desc_lower:
            unconfirmed.append("Articy Draft (проприетарный софт, требуется ручное подтверждение)")
        if "ink" in desc_lower or "yarn" in desc_lower:
            unconfirmed.append("Ink / Yarn Spinner (требуется ручное подтверждение)")

        # 2. Check Role Specifics
        if role_category in ["narrative_designer", "dialogue_director"]:
            verified.append("Постановка и ревью диалоговых сцен (Owlcat Games: The Expanse: Osiris Reborn)")
            verified.append("Разработка лора, NPC и сайд-квестов (VEA Games)")
            verified.append("Драматургическое и режиссерское образование (Театральный институт им. Щукина, опыт в Вахтанговском театре)")
            verified.append("Озвучка персонажей в играх (Mafia: Definitive Edition, Cyberpunk 2077)")

        if role_category == "game_designer":
            verified.append("Системный геймдизайн, боевка, баланс и кор-лупы (личные проекты: RPG Tracker, Combat Spec)")
            adjacent.append("Коммерческий релизный опыт в должности штатного Lead Game Designer не подтвержден (только личные проекты)")

        if role_category in ["video_editor", "creative_producer"]:
            verified.append("Полный цикл режиссуры и монтажа: промо, презентации для инвесторов, короткометражные фильмы")
            verified.append("Работа со связкой Unreal Engine (камеры/превизы) + DaVinci Resolve")

        # 3. Check English requirement
        if any(k in desc_lower for k in ["b2", "c1", "upper-intermediate", "fluent english"]):
            unconfirmed.append("Формальный уровень английского B2/C1 (разговорный английский и видео в оригинале — уверенно, письменный требует факт-чека)")

        # 4. Check Franchise / Specific Games
        specific_game_match = re.search(r'(shadow fight|genshin|pubg|roblox|dota|cs:go|world of tanks|eve online)', desc_lower)
        if specific_game_match:
            game_name = specific_game_match.group(1).title()
            unconfirmed.append(f"Игровой опыт в франшизе «{game_name}» не подтвержден документально (требуется подтверждение Павла)")

        # 5. Check iGaming / Gambling / F2P
        if any(k in desc_lower for k in ["igaming", "слоты", "казино", "gambling"]):
            adjacent.append("Прямой опыт в индустрии iGaming отсутствует; смежный опыт в CG, нарративе и визуале")

        # 6. Check Character Sculpting vs Real-time / Scans
        title_lower = title.lower()
        is_character_role = any(k in f"{title_lower} {desc_lower}" for k in ["character", "персонаж", "персонажк", "скульпт", "sculpt"])
        requires_sculpting = any(k in desc_lower for k in ["sculpt", "скульпт", "zbrush", "high-poly sculpt", "хайполи скульпт", "анатоми", "anatomy", "from scratch"])
        if is_character_role and requires_sculpting:
            not_matched.append("MAJOR GAP: Скульптинг персонажей с нуля / анатомия в ZBrush (Павел НЕ персонажный скульптор; опыт строго в обработке 3D-сканов, ретопологии и подготовке персонажей под real-time/Unreal)")
        elif is_character_role:
            verified.append("Работа с персонажами: обработка 3D-сканов, ретопология, оптимизация и подготовка существующих ассетов под real-time/Unreal (без скульпта с нуля)")

        if role_category == "3d_generalist":
            verified.append("Unreal Engine 5 (пайплайн, сборка сцен, свет, камеры, превизы, realtime-визуал)")
            verified.append("3D пайплайн в Blender (моделирование, ретопология, UV, материалы)")
            verified.append("Опыт работы в нейросетевом департаменте студии CGF (R&D, generative neural tools, real-time)")

        # 7. Check for Questionnaire / Mandatory Forms / Test Tasks
        has_questionnaire = any(k in desc_lower for k in [
            "анкет", "заполните форму", "заполнить форму", "google form", "forms.gle",
            "тестовое задание", "ответьте на вопрос", "сопроводительное письмо обязательно",
            "тестовые вопросы", "опросник", "ссылка на форму", "ответить на вопросы"
        ])
        if has_form_or_test := has_questionnaire:
            unconfirmed.append("📝 Внимание: Требуется ручное заполнение анкеты или ответы на вопросы работодателя")

        return {
            "verified": verified,
            "adjacent": adjacent,
            "unconfirmed": unconfirmed,
            "not_matched": not_matched,
            "has_questionnaire": has_questionnaire
        }

    def select_portfolio_links(self, role_category: str) -> List[Dict[str, str]]:
        """Returns 2-4 curated portfolio links for the given role."""
        return PORTFOLIO_BUNDLES.get(role_category, PORTFOLIO_BUNDLES["narrative_designer"])[:3]

    def build_truthful_cover_letter(self, role_category: str, title: str, employer: str, taxonomy: Dict[str, List[str]], portfolio: List[Dict[str, str]], description: str = "") -> str:
        """
        Builds honest, direct, confident cover letter adhering strictly to application_rules.md Section 16 & 39.
        Returns pure author speech without hardcoded links or contacts (managed by Planka TaskLists).
        """
        return generate_tailored_cover_letter(
            role_cat=role_category,
            title=title,
            employer=employer,
            description=description,
            taxonomy=taxonomy
        )

    def build_card_content(self, vac: Dict[str, Any], role_cat: str, taxonomy: Dict[str, List[str]], portfolio: List[Dict[str, str]], cover_letter: str, review_note: str = "") -> str:
        """
        Builds the markdown body for the Planka card, preserving the existing format
        while embedding truthful taxonomy blocks, review notes, and unconfirmed warnings.
        """
        port_text = "\n".join([f"- [{p['name']}]({p['url']})" for p in portfolio])

        # If review note is present, ensure it's recorded in unconfirmed
        u_list = list(taxonomy["unconfirmed"])
        if review_note and review_note not in u_list:
            u_list.insert(0, review_note)

        v_block = "\n".join([f"• {item}" for item in taxonomy["verified"]]) if taxonomy["verified"] else "• Опыт подтвержден по резюме"
        a_block = "\n".join([f"• {item}" for item in taxonomy["adjacent"]]) if taxonomy["adjacent"] else "• Прямое соответствие"
        u_block = "\n".join([f"• {item}" for item in u_list]) if u_list else "• Все критические требования подтверждены"
        n_block = "\n".join([f"• {item}" for item in taxonomy["not_matched"]]) if taxonomy["not_matched"] else "• Явных блокеров не обнаружено"

        q_banner = ""
        if taxonomy.get("has_questionnaire"):
            q_banner = (
                "> [!WARNING]\n"
                "> 📝 **ТРЕБУЕТСЯ РУЧНОЕ ЗАПОЛНЕНИЕ АНКЕТЫ / ОТВЕТЫ НА ВОПРОСЫ!**\n"
                "> Работодатель требует заполнить стороннюю форму или ответить на обязательные вопросы при отклике на HH.\n\n"
            )

        review_banner = ""
        if review_note:
            review_banner = (
                "> [!WARNING]\n"
                f"> 🔍 **{review_note}**\n"
                "> В требованиях обнаружены технические навыки, глубина которых требует внимания при ручном скрининге.\n\n"
            )

        resume_info = RESUME_METADATA.get(role_cat, RESUME_METADATA["game_designer"])

        formatted_desc = format_structured_role_description(vac.get('description', ''))
        clean_emp = sanitize_entity_text(vac.get('employer', ''))
        clean_title = sanitize_entity_text(vac.get('title', ''))
        clean_salary = sanitize_entity_text(vac.get('salary', 'Не указана'))

        return (
            f"{q_banner}"
            f"{review_banner}"
            f"Прямая ссылка для перехода: [{vac['url']}]({vac['url']})\n\n"
            f"Компания: {clean_emp}  \n"
            f"Должность: {clean_title}  \n"
            f"Зарплата: {clean_salary}  \n"
            f"HH Vacancy ID: `{vac['id']}`  \n"
            f"Категория роли: `{role_cat.upper()}`  \n"
            f"📄 Выбранное резюме на HH: [{resume_info['title']}]({resume_info['url']})  \n"
            f"HH Resume ID: `{resume_info['id']}`\n\n"
            f"---\n\n"
            f"### 📋 Описание роли\n\n"
            f"{formatted_desc}\n\n"
            f"---\n\n"
            f"### 🛡️ FIT NOTES & GAPS\n\n"
            f"✓ **VERIFIED:**\n{v_block}\n\n"
            f"~ **ADJACENT:**\n{a_block}\n\n"
            f"⚠️ **UNCONFIRMED:**\n{u_block}\n\n"
            f"✗ **NOT MATCHED:**\n{n_block}\n\n"
            f"---\n\n"
            f"### 📁 Отобранное портфолио (2–4 ссылки)\n"
            f"{port_text}\n\n"
            f"---\n\n"
            f"### ✉️ READY-TO-SEND MESSAGE:\n"
            f"```text\n"
            f"{cover_letter}\n"
            f"```\n\n"
            f"👉 Быстрый переход для ручного отклика на HH: [{vac['url']}]({vac['url']})\n\n"
            f"{build_materials_cheat_sheet()}"
        )
