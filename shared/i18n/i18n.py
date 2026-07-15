#!/usr/bin/env python3
"""Shared i18n for Income Agent Hub (22 languages)."""
from __future__ import annotations

import json
from pathlib import Path

ROOT = Path(__file__).resolve().parent
LOCALES = ROOT / "locales.json"
LANGUAGES = ROOT / "languages.json"
DEFAULT_LANG = "ru"
SUPPORTED = list(json.loads(LANGUAGES.read_text(encoding="utf-8")).keys())

_cache: dict | None = None


def _load() -> dict:
    global _cache
    if _cache is None:
        _cache = json.loads(LOCALES.read_text(encoding="utf-8"))
    return _cache


def normalize_lang(code: str | None) -> str:
    if not code:
        return DEFAULT_LANG
    code = code.strip().lower().split("-")[0]
    return code if code in SUPPORTED else DEFAULT_LANG


def t(key: str, lang: str | None = None, **kwargs: str) -> str:
    data = _load()
    lang = normalize_lang(lang)
    bucket = data.get(key, {})
    text = bucket.get(lang) or bucket.get("en") or bucket.get("ru") or key
    for k, v in kwargs.items():
        text = text.replace(f"{{{k}}}", str(v))
    return text


def language_menu() -> list[tuple[str, str]]:
    names = json.loads(LANGUAGES.read_text(encoding="utf-8"))
    return [(code, names[code]) for code in SUPPORTED]