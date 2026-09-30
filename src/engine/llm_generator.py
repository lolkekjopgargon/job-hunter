#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
llm_generator.py - Real LLM API Caller for Tailored Cover Letters.
Uses Google Gemini API or OpenRouter API to synthesize authentic, living cover letters.
Takes input strictly from candidate_facts and agent_system_prompt in the application settings
and the exact full description of the clicked vacancy.
NO hardcoded templates, NO mock fallbacks!
"""

import os
import sys
import json
import urllib.request
import urllib.error
from typing import Dict, Any, Optional

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", "..", "..", ".."))
JOB_HUNTER_DIR = os.path.abspath(os.path.join(SCRIPT_DIR, "..", "..", ".."))
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)
if JOB_HUNTER_DIR not in sys.path:
    sys.path.insert(0, JOB_HUNTER_DIR)

from db import get_setting


def _get_user_data_dir() -> str:
    """Returns the userData directory where .md files are stored.
    Derived from JOB_HUNTER_DB env var set by Electron main process."""
    env_db = os.environ.get("JOB_HUNTER_DB", "")
    if env_db:
        return os.path.dirname(os.path.abspath(env_db))
    # Dev fallback
    return JOB_HUNTER_DIR


def _read_md_file(filename: str) -> str:
    """Reads a .md file from userData directory, falls back to project dirs."""
    data_dir = _get_user_data_dir()
    # Primary: userData (AppData) — this is where the app saves via UI
    for folder in [data_dir, SCRIPT_DIR, JOB_HUNTER_DIR]:
        fp = os.path.join(folder, filename)
        if os.path.exists(fp):
            try:
                with open(fp, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:
                        return content
            except Exception:
                pass
    return ""


def get_agent_style_prompt() -> str:
    """Reads application_rules.md from userData.
    This file is created and edited by the user via the Settings UI.
    Returns empty string if the file doesn't exist yet — no hardcoded fallback."""
    return _read_md_file("application_rules.md")


def get_candidate_facts() -> str:
    """Reads candidate_facts.md from userData.
    This file is created and edited by the user via the Settings UI.
    Returns empty string if the file doesn't exist yet."""
    return _read_md_file("candidate_facts.md")



def generate_letter_gemini(api_key: str, model_name: str, vacancy: Dict[str, Any], regenerate: bool = False) -> str:
    facts = get_candidate_facts()
    system_rules = get_agent_style_prompt()

    regen_instruction = ""
    if regenerate:
        regen_instruction = (
            "\nВАЖНО: Это повторная генерация! Предложи ДРУГОЙ угол подачи и другие акценты из опыта кандидата. "
            "Не повторяй предыдущие формулировки, сделай текст свежим и живым."
        )

    user_prompt = f"""ВАКАНСИЯ РАБОТОДАТЕЛЯ:
Компания: {vacancy.get('employer', '')}
Должность: {vacancy.get('title', '')}
Зарплата: {vacancy.get('salary', 'Не указана')}
Полный текст требований и обязанностей:
{vacancy.get('full_description', '')[:4000]}

ПОДТВЕРЖДЁННЫЙ ОПЫТ И ФАКТЫ О КАНДИДАТЕ:
{facts[:4500]}
{regen_instruction}
"""

    # Cascade list of free-tier compatible Gemini models
    candidate_models = []
    if model_name and model_name.strip():
        candidate_models.append(model_name.strip())
    
    # Priority cascade list for Google AI Studio Free Tier (gemini-3.6-flash verified active for this key)
    for m in ["gemini-3.6-flash", "gemini-flash-latest", "gemini-2.5-pro", "gemini-pro-latest", "gemini-2.5-flash"]:
        if m not in candidate_models:
            candidate_models.append(m)

    last_error = ""
    for model in candidate_models:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={api_key}"
        payload = {
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": f"СИСТЕМНЫЕ ПРАВИЛА И СТИЛЬ:\n{system_rules}\n\n{user_prompt}"}]
                }
            ],
            "generationConfig": {
                "temperature": 0.85 if regenerate else 0.75,
                "maxOutputTokens": 1500
            }
        }

        req = urllib.request.Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                candidates = data.get("candidates", [])
                if candidates:
                    parts = candidates[0].get("content", {}).get("parts", [])
                    if parts:
                        return parts[0].get("text", "").strip()
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8", errors="ignore")
            last_error = f"Gemini API [{model}] Error [{he.code}]: {err_msg}"
            # If 404 (model not found / deprecated) or 429 (quota), try next model in cascade
            if he.code in (404, 400, 429, 503):
                continue
            raise Exception(last_error)
        except Exception as e:
            last_error = str(e)
            continue

    raise Exception(f"Не удалось получить ответ от Gemini API (проверены модели {candidate_models}): {last_error}")


def generate_letter_deepseek(api_key: str, model_name: str, vacancy: Dict[str, Any], regenerate: bool = False) -> str:
    facts = get_candidate_facts()
    system_rules = get_agent_style_prompt()

    regen_instruction = ""
    if regenerate:
        regen_instruction = (
            "\nВАЖНО: Это повторная генерация! Предложи ДРУГОЙ угол подачи и другие акценты из опыта кандидата. "
            "Не повторяй предыдущие формулировки, сделай текст свежим и живым."
        )

    user_prompt = f"""ВАКАНСИЯ:
Компания: {vacancy.get('employer', '')}
Должность: {vacancy.get('title', '')}
Зарплата: {vacancy.get('salary', 'Не указана')}
Описание требований и обязанностей:
{vacancy.get('full_description', '')[:4000]}

ОПЫТ И ФАКТЫ О КАНДИДАТЕ:
{facts[:4000]}
{regen_instruction}
"""

    model = model_name.strip() if model_name and model_name.strip() else "deepseek-chat"
    url = "https://api.deepseek.com/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.85 if regenerate else 0.7,
        "max_tokens": 1500
    }

    req_data = json.dumps(payload).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {api_key}",
        "Accept": "application/json",
    }

    last_err = ""
    for attempt in range(3):
        req = urllib.request.Request(url, data=req_data, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=45) as resp:
                data = json.loads(resp.read().decode("utf-8"))
                choices = data.get("choices", [])
                if choices:
                    return choices[0].get("message", {}).get("content", "").strip()
                raise Exception("DeepSeek API вернул пустой ответ")
        except urllib.error.HTTPError as he:
            err_msg = he.read().decode("utf-8", errors="ignore")
            raise Exception(f"DeepSeek API Error [{he.code}]: {err_msg}")
        except Exception as e:
            last_err = str(e)
            import time
            time.sleep(1.5)
            continue

    if "10054" in last_err or "forcibly closed" in last_err:
        raise Exception(
            "DeepSeek API: соединение сброшено (WinError 10054). "
            "Прямой хост api.deepseek.com блокируется или сбрасывается провайдером РФ. "
            "Включите VPN/прокси для прямого DeepSeek или выберите провайдер Gemini / OpenRouter в Настройках."
        )
    raise Exception(f"Ошибка запроса к DeepSeek API: {last_err}")



def generate_letter_openrouter(api_key: str, model_name: str, vacancy: Dict[str, Any], regenerate: bool = False) -> str:
    facts = get_candidate_facts()
    system_rules = get_agent_style_prompt()

    regen_instruction = ""
    if regenerate:
        regen_instruction = (
            "\nВАЖНО: Это повторная генерация! Предложи ДРУГОЙ угол подачи и другие акценты из опыта кандидата. "
            "Не повторяй предыдущие формулировки, сделай текст свежим и живым."
        )

    user_prompt = f"""ВАКАНСИЯ:
Компания: {vacancy.get('employer', '')}
Должность: {vacancy.get('title', '')}
Зарплата: {vacancy.get('salary', 'Не указана')}
Описание вакансии:
{vacancy.get('full_description', '')[:4000]}

ОПЫТ И ФАКТЫ О КАНДИДАТЕ:
{facts[:4000]}
{regen_instruction}
"""

    model = model_name.strip() or "meta-llama/llama-3.3-70b-instruct:free"
    url = "https://openrouter.ai/api/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system_rules},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.85 if regenerate else 0.75
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }
    )

    try:
        with urllib.request.urlopen(req, timeout=35) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            choices = data.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", "").strip()
            raise Exception("OpenRouter API вернул пустой ответ")
    except urllib.error.HTTPError as he:
        err_msg = he.read().decode("utf-8", errors="ignore")
        raise Exception(f"OpenRouter API Error [{he.code}]: {err_msg}")


def generate_tailored_letter(vacancy: Dict[str, Any], regenerate: bool = False) -> str:
    provider = get_setting("llm_provider", "gemini").lower().strip()

    # Read provider-specific key or fallback to general llm_api_key
    provider_key_map = {
        "deepseek": "llm_key_deepseek",
        "gemini": "llm_key_gemini",
        "openrouter": "llm_key_openrouter",
        "groq": "llm_key_groq",
    }
    specific_key_name = provider_key_map.get(provider, "")
    api_key = ""
    if specific_key_name:
        api_key = get_setting(specific_key_name, "").strip()

    if not api_key:
        api_key = get_setting("llm_api_key", "").strip()

    # Read provider-specific model or fallback to general llm_model
    provider_model_map = {
        "deepseek": ("llm_model_deepseek", "deepseek-chat"),
        "gemini": ("llm_model_gemini", "gemini-3.6-flash"),
        "openrouter": ("llm_model_openrouter", "meta-llama/llama-3.3-70b-instruct:free"),
        "groq": ("llm_model_groq", "llama-3.3-70b-versatile"),
    }
    model_setting_name, default_model = provider_model_map.get(provider, ("llm_model", "gemini-3.6-flash"))
    model_name = get_setting(model_setting_name, "").strip()
    if not model_name:
        model_name = get_setting("llm_model", default_model).strip() or default_model

    if not api_key:
        provider_title = provider.capitalize()
        raise Exception(
            f"API-ключ для провайдера «{provider_title}» не указан! Перейдите в «Настройки» -> «Нейросеть (LLM)» и введите ключ."
        )

    if "deepseek" in provider:
        letter_body = generate_letter_deepseek(api_key, model_name, vacancy, regenerate=regenerate)
    elif "openrouter" in provider or "groq" in provider:
        letter_body = generate_letter_openrouter(api_key, model_name, vacancy, regenerate=regenerate)
    else:
        letter_body = generate_letter_gemini(api_key, model_name, vacancy, regenerate=regenerate)

    if not letter_body:
        raise Exception("Нейросеть вернула пустой результат.")

    return letter_body

