#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
requirement_filter.py - Hard Requirement Pre-Filter for Job Hunter.

Analyzes vacancy title and description BEFORE creating cards in Planka.
Separates MUST HAVE vs NICE TO HAVE sections.
Rejects vacancies where key duties require unconfirmed deep technical specialization:
  - Advanced/High-level SQL, complex queries, DB administration
  - Professional software engineering (Python/JS/TS/C++/C# backend/frontend)
  - Gameplay/Engine/Tools programming as primary role
  - DevOps, CI/CD, Kubernetes, Docker as main specialization
  - Data Engineering, DBA, Professional Data Science / ML Engineering
  - Professional BI infrastructure requiring deep SQL
  - Shader / graphics programming (HLSL/GLSL)
  - Technical art with mandatory pipeline tool coding
  - Heavy Excel/VBA financial analytics
  - QA automation coding
  - System / network administration
  - GTA SAMP / RP ecosystems, TikTok/Shorts conveyors

Preserves:
  - Skills appearing only in NICE TO HAVE / БУДЕТ ПЛЮСОМ
  - Basic / secondary tools (e.g. basic SELECT, reading code, scripting for balance/prototypes)
  - AI / LLM workflows, prompting, local LLM usage (matches candidate_facts.md)

Returns:
  - ("REJECT", "REJECTED: <reason>")
  - ("REVIEW", "REVIEW REQUIRED: possible technical mismatch - <reason>")
  - ("PASS", "")
"""

import sys
import re
import html
from typing import Dict, Tuple, List, Optional

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")


# ----------------------------------------------------------------------
# 1. SECTION HEADERS PARSER
# ----------------------------------------------------------------------

MUST_HAVE_HEADERS = [
    r"требования\s*к\s*кандидату",
    r"требования",
    r"что\s*для\s*нас\s*важно",
    r"что\s*мы\s*жд[её]м\s*(?:от\s*вас|от\s*кандидата)?",
    r"мы\s*жд[её]м\s*от\s*кандидата",
    r"от\s*вас",
    r"мы\s*ожидаем",
    r"наш\s*идеальный\s*кандидат",
    r"кого\s*мы\s*ищем",
    r"необходимые\s*навыки",
    r"необходимый\s*опыт",
    r"hard\s*skills",
    r"стек\s*(?:технологий)?",
    r"профессиональные\s*требования",
    r"что\s*важно",
    r"наши\s*ожидания",
    r"обязательно",
    r"critical\s*requirements",
    r"requirements",
    r"must\s*have",
    r"what\s*you\s*need",
    r"qualifications",
    r"skills"
]

NICE_TO_HAVE_HEADERS = [
    r"будет\s*(?:большим\s*)?плюсом",
    r"плюсом\s*будет",
    r"будет\s*преимуществом",
    r"преимуществом\s*будет",
    r"как\s*плюс",
    r"желательно",
    r"желательные\s*требования",
    r"приветствуется",
    r"дополнительным\s*плюсом",
    r"дополнительно",
    r"nice\s*to\s*have",
    r"would\s*be\s*a\s*plus",
    r"bonus\s*points",
    r"good\s*to\s*have"
]

RESPONSIBILITIES_HEADERS = [
    r"обязанности",
    r"задачи",
    r"чем\s*предстоит\s*заниматься",
    r"что\s*предстоит\s*делать",
    r"предстоит\s*делать",
    r"что\s*делать",
    r"ваши\s*задачи",
    r"зона\s*ответственности",
    r"key\s*responsibilities",
    r"responsibilities",
    r"what\s*you\s*will\s*do",
    r"duties",
    r"вам\s*предстоит",
    r"сейчас\s*мы\s*(?:находимся\s*в\s*поиске|ищем)",
    r"мы\s*(?:в\s*поиске|ищем)",
    r"ищем\s+(?:в\s+команду|специалиста|дизайнера|продюсера|художника)"
]

CONDITIONS_HEADERS = [
    r"мы\s*предлагаем",
    r"условия\s*(?:работы)?",
    r"что\s*мы\s*предлагаем",
    r"наши\s*условия",
    r"что\s*мы\s*предоставляем",
    r"почему\s*у\s*нас\s*хочется\s*работать",
    r"benefits",
    r"what\s*we\s*offer",
    r"conditions",
    r"compensation"
]


def split_vacancy_sections(description: str) -> Dict[str, str]:
    """
    Parses plain text vacancy description into logical sections:
    'must_have', 'nice_to_have', 'responsibilities', 'conditions', 'general'.
    Handles multi-line formatting, HTML artifacts, and inline headers without strict colons.
    """
    # Normalize HTML breaks, entities and spaces
    text = html.unescape(description).replace("\u00a0", " ").replace("\u202f", " ").replace("\u200b", " ")
    text = re.sub(r'####\s*[^\n]+\n', '\n', text)
    text = re.sub(r'</?(?:p|div|li|br|h[1-6]|tr)[^>]*>', '\n', text, flags=re.IGNORECASE)
    text = re.sub(r'<.*?>', ' ', text)

    must_pattern = r"(?:" + "|".join(MUST_HAVE_HEADERS) + r")"
    nice_pattern = r"(?:" + "|".join(NICE_TO_HAVE_HEADERS) + r")"
    resp_pattern = r"(?:" + "|".join(RESPONSIBILITIES_HEADERS) + r")"
    cond_pattern = r"(?:" + "|".join(CONDITIONS_HEADERS) + r")"

    combined_regex = re.compile(
        rf"(?:^|[\n\.\;\!\?]\s*|\b)("
        rf"(?P<nice>{nice_pattern})|"
        rf"(?P<must>{must_pattern})|"
        rf"(?P<resp>{resp_pattern})|"
        rf"(?P<cond>{cond_pattern})"
        rf")(?:\s*[:\-\n]|\s{{2,}}|\s+(?=[A-ZА-ЯЁ•\-\*]))",
        flags=re.IGNORECASE
    )

    matches = list(combined_regex.finditer(text))

    sections: Dict[str, List[str]] = {
        "must_have": [],
        "nice_to_have": [],
        "responsibilities": [],
        "conditions": [],
        "general": []
    }

    if not matches:
        sections["general"].append(text.strip())
        return {k: "\n".join(v).strip() for k, v in sections.items()}

    first_start = matches[0].start()
    if first_start > 0:
        sections["general"].append(text[:first_start].strip())

    for idx, match in enumerate(matches):
        start = match.end()
        end = matches[idx + 1].start() if idx + 1 < len(matches) else len(text)
        chunk = text[start:end].strip()

        if match.group("nice"):
            sections["nice_to_have"].append(chunk)
        elif match.group("must"):
            sections["must_have"].append(chunk)
        elif match.group("resp"):
            sections["responsibilities"].append(chunk)
        elif match.group("cond"):
            sections["conditions"].append(chunk)
        else:
            sections["general"].append(chunk)

    return {k: "\n".join(v).strip() for k, v in sections.items()}


# ----------------------------------------------------------------------
# 2. HARD TECHNICAL MISMATCH PATTERNS
# ----------------------------------------------------------------------

# Title hard exclusions (pure engineering/dev roles)
TITLE_DEV_EXCLUSIONS = [
    r"\bbackend\s+(?:developer|engineer|разработчик)\b",
    r"\bfrontend\s+(?:developer|engineer|разработчик)\b",
    r"\bfullstack\s+(?:developer|engineer|разработчик)\b",
    r"\bsoftware\s+(?:developer|engineer|инженер)\b",
    r"\bpython\s+(?:developer|engineer|разработчик)\b",
    r"\b(?:c\+\+|cpp)\s+(?:developer|engineer|разработчик)\b",
    r"\b(?:c#|csharp|\.net)\s+(?:developer|engineer|разработчик)\b",
    r"\b(?:javascript|typescript|js|ts)\s+(?:developer|engineer|разработчик)\b",
    r"\b(?:golang|go)\s+(?:developer|engineer|разработчик)\b",
    r"\bjava\s+(?:developer|engineer|разработчик)\b",
    r"\bgameplay\s+programmer\b",
    r"\bengine\s+programmer\b",
    r"\btools\s+programmer\b",
    r"\bпрограммист\s+геймплея\b",
    r"\bпрограммист\s+движка\b",
    r"\bразработчик\s+игровых\s+механик\b",
    r"\bdevops\b",
    r"\bsre\b",
    r"\bqa\s+automation\b",
    r"\bqa\s+auto\b",
    r"\bавтотестировщик\b",
    r"\bсистемный\s+администратор\b",
    r"\bsysadmin\b",
    r"\bdata\s+engineer\b",
    r"\bдата\s+инженер\b",
    r"\bdata\s+scientist\b",
    r"\bml\s+engineer\b",
    r"\bdatabase\s+administrator\b",
    r"\bадминистратор\s+баз\s+данных\b",
    r"\bdba\b"
]

# GTA SAMP / RP exclusions
SAMP_PATTERNS = [
    r"\bsamp\b", r"\bsa-mp\b", r"\bgta\s*rp\b", r"\bgta\s*roleplay\b",
    r"\bfivem\b", r"\bгта\s*рп\b", r"\bролеплей\s+сервер\b", r"\bsamp\s+сервер\b"
]

# TikTok conveyor exclusions
CONVEYOR_PATTERNS = [
    r"только\s+shorts", r"монтаж\s+reels", r"конвейер\s+tiktok",
    r"нарезка\s+shorts", r"нарезчик\s+reels", r"монтажер\s+tiktok",
    r"bulk\s+editing", r"массовый\s+монтаж\s+shorts"
]


def check_title_hard_exclusions(title: str) -> Optional[Tuple[str, str]]:
    """Checks if job title is an outright engineering / disallowed role."""
    title_lower = title.lower()

    for p in TITLE_DEV_EXCLUSIONS:
        if re.search(p, title_lower):
            # Check if it's a game designer or narrative title with a minor tech mention
            if any(ok in title_lower for ok in ["game design", "гейм-дизайн", "геймдизайн", "narrative", "нарратив", "3d", "creative producer", "видео"]):
                # Allow dual titles to proceed to requirement analysis
                break
            return ("REJECT", f"REJECTED: pure software engineering role in title ('{title}')")

    for p in SAMP_PATTERNS:
        if re.search(p, title_lower):
            return ("REJECT", f"REJECTED: GTA SAMP / RP ecosystem project ('{title}')")

    for p in CONVEYOR_PATTERNS:
        if re.search(p, title_lower):
            return ("REJECT", f"REJECTED: high-volume Shorts/TikTok conveyor ('{title}')")

    return None


def evaluate_hard_technical_filter(title: str, description: str) -> Tuple[str, str]:
    """
    Evaluates whether vacancy requires unconfirmed high-level technical specialization.
    Separates MUST HAVE and RESPONSIBILITIES from NICE TO HAVE.
    """
    # 1. Quick check on title
    title_check = check_title_hard_exclusions(title)
    if title_check:
        return title_check

    # 2. Check SAMP/RP or Shorts in full text
    full_text_lower = f"{title}\n{description}".lower()
    for p in SAMP_PATTERNS:
        if re.search(p, full_text_lower):
            return ("REJECT", "REJECTED: GTA SAMP / RP ecosystem project")
    for p in CONVEYOR_PATTERNS:
        if re.search(p, full_text_lower):
            return ("REJECT", "REJECTED: high-volume Shorts/TikTok conveyor")

    # 3. Parse sections
    sections = split_vacancy_sections(description)
    must_have = sections["must_have"].lower()
    responsibilities = sections["responsibilities"].lower()
    nice_to_have = sections["nice_to_have"].lower()

    # Core requirement scope = MUST HAVE + RESPONSIBILITIES
    # If a requirement was not parsed into any heading, check general as fallback
    core_scope = f"{must_have}\n{responsibilities}"
    if not must_have and not responsibilities:
        core_scope = sections["general"].lower()

    # ------------------------------------------------------------------
    # 4. SQL HARD MISMATCH
    # ------------------------------------------------------------------
    # Disqualifiers: advanced SQL, complex queries, DB admin, query optimization, DWH
    advanced_sql_patterns = [
        r"sql\s+(?:на\s+)?(?:высоком|продвинутом|глубоком|экспертном)\s+уровне",
        r"(?:высокий|продвинутый|глубокий|экспертный)\s+уровень\s+(?:знания\s+)?sql",
        r"advanced\s+sql",
        r"сложные\s+sql[\s-]запросы",
        r"написание\s+сложных\s+(?:sql[\s-]?)?запросов",
        r"оптимизаци(?:я|и)\s+(?:sql[\s-]?)?запросов",
        r"query\s+optimization",
        r"хранилищ[ае]\s+данных\s+(?:dwh|data\s+warehouse)",
        r"(?:построение|разработка|моделирование)\s+dwh",
        r"опыт\s+(?:работы\s+с\s+)?sql\s+(?:от\s+)?[2-5]\b",
        r"sql\s+[2-5]\+\s*(?:года|лет|years)",
        r"знание\s+sql\s+на\s+уровне\s+написания\s+(?:хранимых\s+процедур|триггеров|сложных)",
        r"(?:postgresql|mysql|clickhouse|oracle)\s+(?:администрирование|dba|оптимизация)",
        r"глубокие\s+знания\s+sql"
    ]

    for p in advanced_sql_patterns:
        if re.search(p, core_scope):
            # Double-check it's not actually in nice-to-have
            if not re.search(p, nice_to_have):
                return ("REJECT", "REJECTED: hard technical mismatch - advanced SQL required")

    # ------------------------------------------------------------------
    # 5. PROFESSIONAL SOFTWARE ENGINEERING / BACKEND / FRONTEND
    # ------------------------------------------------------------------
    prog_patterns = [
        r"коммерческий\s+опыт\s+разработки\s+на\s+(?:python|c\+\+|cpp|c#|javascript|typescript)\s+(?:от\s+)?[2-5]",
        r"(?:3\+|2\+|4\+|5\+)\s*(?:года|лет)\s+(?:опыта\s+)?(?:коммерческой\s+)?разработки\s+на\s+(?:python|c\+\+|c#)",
        r"профессиональн(?:ый|ое)\s+владение\s+(?:python|c\+\+|c#|java|golang)",
        r"написание\s+(?:чистого\s+)?продакшн[\s-]кода",
        r"проектирование\s+архитектуры\s+(?:приложений|бэкенда|микросервисов)",
        r"backend\s+разработк[аеи]",
        r"frontend\s+разработк[аеи]",
        r"fullstack\s+разработк[аеи]",
        r"разработка\s+микросервисов\s+на\s+(?:go|python|java)",
        r"разработка\s+клиент-серверной\s+архитектуры\s+в\s+роли\s+программиста",
        r"глубокое\s+понимание\s+алгоритмов\s+и\s+структур\s+данных\s+для\s+разработки\s+по"
    ]

    for p in prog_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: professional software engineering / backend development required")

    # ------------------------------------------------------------------
    # 6. GAMEPLAY / ENGINE / TOOLS PROGRAMMING (as primary role)
    # ------------------------------------------------------------------
    game_prog_patterns = [
        r"разработка\s+игрового\s+движка",
        r"программирование\s+физики\s+и\s+рендера\s+на\s+c\+\+",
        r"gameplay\s+programming\s+(?:as\s+main|c\+\+)",
        r"написание\s+игровых\s+механик\s+строго\s+на\s+c\+\+",
        r"senior\s+c\+\+\s+(?:gameplay|engine)\s+developer"
    ]

    for p in game_prog_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: gameplay / engine programming required as primary duty")

    # ------------------------------------------------------------------
    # 7. DEVOPS / INFRASTRUCTURE
    # ------------------------------------------------------------------
    devops_patterns = [
        r"развертывание\s+и\s+поддержка\s+kubernetes",
        r"настройка\s+кластеров\s+k8s",
        r"управление\s+инфраструктурой\s+через\s+terraform",
        r"devops\s+(?:инженер|практики\s+как\s+основная\s+задача)",
        r"настройка\s+ci/cd\s+пайплайнов\s+как\s+основная\s+обязанность"
    ]

    for p in devops_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: DevOps / CI/CD infrastructure required as primary duty")

    # ------------------------------------------------------------------
    # 8. DATA SCIENCE / ML ENGINEERING / DATA ENGINEERING (primary profession)
    # ------------------------------------------------------------------
    # Note: Using AI tools/LLM is fine; building/training PyTorch models as primary ML engineer is rejected
    ml_patterns = [
        r"обучение\s+(?:нейронных\s+сетей|ml[\s-]моделей|deep\s+learning)",
        r"training\s+(?:ml|deep\s+learning)\s+models",
        r"data\s+engineering\s+пайплайны",
        r"построение\s+etl[\s-]пайплайнов\s+на\s+airflow",
        r"apache\s+spark\s+и\s+hadoop\s+для\s+обработки\s+данных",
        r"исследование\s+и\s+разработка\s+алгоритмов\s+компьютерного\s+зрения\s+(?:cv)",
        r"математическая\s+статистика\s+для\s+ml[\s-]исследований"
    ]

    for p in ml_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: role is primarily data engineering / scientific ML, not game/creative/product work")

    # ------------------------------------------------------------------
    # 9. PROFESSIONAL BI / ANALYTICAL INFRASTRUCTURE WITH DEEP SQL
    # ------------------------------------------------------------------
    bi_patterns = [
        r"(?:tableau|power\s*bi|looker|superset)\s+на\s+(?:высоком|продвинутом)\s+уровне\s+с\s+sql",
        r"построение\s+корпоративной\s+bi[\s-]отчетности\s+и\s+dwh",
        r"сквозная\s+продуктовая\s+аналитика\s+с\s+написанием\s+сложного\s+sql",
        r"моделирование\s+dwh\s+и\s+bi\s+витрин"
    ]

    for p in bi_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: professional BI infrastructure / complex analytics required")

    # ------------------------------------------------------------------
    # 10. SHADER / GRAPHICS PROGRAMMING
    # ------------------------------------------------------------------
    shader_patterns = [
        r"написание\s+шейдеров\s+на\s+(?:hlsl|glsl)\s+(?:как\s+основная\s+задача|от\s+2\s+лет)",
        r"graphics\s+programmer\s+(?:hlsl|directx|vulkan)",
        r"низкоуровневое\s+программирование\s+графики"
    ]

    for p in shader_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: low-level shader / graphics programming required")

    # ------------------------------------------------------------------
    # 11. TECHNICAL ART PIPELINE WITH MANDATORY SCRIPTING AS MAIN DUTY
    # ------------------------------------------------------------------
    tech_art_code_patterns = [
        r"написание\s+плагинов\s+и\s+тулов\s+на\s+python\s+для\s+(?:maya|3ds\s*max|houdini)\s+как\s+основная\s+задача",
        r"разработка\s+dcc[\s-]пайплайнов\s+на\s+python\s+в\s+качестве\s+tech\s+art\s+lead",
        r"rigging\s+pipeline\s+automation\s+with\s+python\s+tools"
    ]

    for p in tech_art_code_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: technical art tool programming required as primary duty")

    # ------------------------------------------------------------------
    # 12. ADVANCED EXCEL / VBA / FINANCIAL QUANT ANALYTICS
    # ------------------------------------------------------------------
    vba_patterns = [
        r"программирование\s+макросов\s+(?:vba)\s+на\s+высоком\s+уровне",
        r"разработка\s+сложных\s+моделей\s+на\s+vba\s+для\s+финансовых\s+расчетов",
        r"advanced\s+vba\s+and\s+macro\s+development"
    ]

    for p in vba_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: advanced VBA / complex quantitative macro modeling required")

    # ------------------------------------------------------------------
    # 13. QA AUTOMATION CODING
    # ------------------------------------------------------------------
    qa_auto_patterns = [
        r"разработка\s+автотестов\s+на\s+(?:python|java|c#|typescript)",
        r"создание\s+фреймворков\s+автоматизации\s+тестирования",
        r"automation\s+qa\s+(?:engineer|framework)"
    ]

    for p in qa_auto_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: professional QA automation coding required")

    # ------------------------------------------------------------------
    # 14. SYSTEM / NETWORK ADMINISTRATION
    # ------------------------------------------------------------------
    sysadmin_patterns = [
        r"администрирование\s+серверов\s+(?:linux|windows\s+server)",
        r"настройка\s+сетевого\s+оборудования\s+(?:cisco|mikrotik)",
        r"network\s+engineering\s+and\s+routing"
    ]

    for p in sysadmin_patterns:
        if re.search(p, core_scope) and not re.search(p, nice_to_have):
            return ("REJECT", "REJECTED: system / network administration required")

    # ------------------------------------------------------------------
    # 15. DOUBT / REVIEW REQUIRED CHECK
    # ------------------------------------------------------------------
    # If a technical requirement is mentioned in must_have but its depth is ambiguous
    # (e.g. mentions SQL without explicit "high level", or mentions python scripting without "3+ years")
    ambiguous_checks = [
        (r"\bsql\b", "требуется SQL (глубина не уточнена, проверить при скрининге)"),
        (r"\bpython\b", "упомянут Python в требованиях (проверить объем кодинга)"),
        (r"\b(?:tableau|power\s*bi|looker)\b", "упомянуты BI-системы (проверить требования к DWH)"),
        (r"\b(?:c\+\+|c#)\b", "упомянут C++/C# в требованиях (проверить требуется ли глубокий кодинг)"),
        (r"\b(vba|макрос)\b", "упомянут VBA в требованиях")
    ]

    for pattern, note in ambiguous_checks:
        if re.search(pattern, must_have) and not re.search(pattern, nice_to_have):
            return ("REVIEW", f"REVIEW REQUIRED: possible technical mismatch ({note})")

    return ("PASS", "")


if __name__ == "__main__":
    # Self-test / demonstration examples
    test_cases = [
        {
            "title": "Economy Game Designer (Pines Peak)",
            "desc": "Обязанности: баланс. Требования: Опыт построения моделей; Знания и опыт работы с Excel, Google sheets, SQL на высоком уровне; Tableau. Будет плюсом: Python."
        },
        {
            "title": "Game Designer (PvP)",
            "desc": "Обязанности: проектирование правил и боевого кор-лупа. Требования: системный геймдизайн. Будет плюсом: базовый SQL, понимание принципов кода."
        },
        {
            "title": "Middle Python Backend Developer",
            "desc": "Требования: 3+ года коммерческой разработки на Python, Django, PostgreSQL."
        },
        {
            "title": "Narrative Designer",
            "desc": "Обязанности: сценарии квестов. Требования: отличный русский язык, опыт в UE5. Будет плюсом: можно использовать Python для прототипирования."
        },
        {
            "title": "Lead Game Designer",
            "desc": "Требования: опыт в геймдеве от 3 лет, знание SQL, аналитическое мышление."
        }
    ]

    print("Running requirement_filter self-test:\n")
    for t in test_cases:
        verdict, reason = evaluate_hard_technical_filter(t["title"], t["desc"])
        print(f"[{verdict}] {t['title']}")
        if reason:
            print(f"  Reason: {reason}")
        print()
