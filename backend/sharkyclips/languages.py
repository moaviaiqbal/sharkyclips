"""Supported languages registry, shared by the whole app (UI, transcription, outputs)."""

from __future__ import annotations

from dataclasses import asdict, dataclass

from .errors import SharkyClipsError

AUTO = "auto"


@dataclass(frozen=True)
class Language:
    code: str  # SharkyClips / ISO 639-1 code
    native_name: str
    english_name: str
    is_rtl: bool
    whisper_code: str  # code Whisper expects
    locale: str = ""  # BCP-47 tag for YouTube defaultLanguage / defaultAudioLanguage
    region: str = ""  # default ISO 3166 region (YouTube recordingDetails / hashtags)
    flag: str = ""  # emoji flag for the language switcher

    def to_dict(self) -> dict:
        return asdict(self)


# 1.2.53 Tier 1 list (research snapshot 2026-11): tr, en, es (es-ES + es-419), pt-BR, ru, de, fr,
# ar, zh, ja, hu. The code stays the short one ("pt" = Brazilian Portuguese, "es" + a variant).
_ALL = [
    Language("en", "English", "English", False, "en", "en", "US", "🇬🇧"),
    Language("tr", "Türkçe", "Turkish", False, "tr", "tr", "TR", "🇹🇷"),
    Language("es", "Español", "Spanish", False, "es", "es-419", "MX", "🇪🇸"),
    Language("pt", "Português (Brasil)", "Portuguese (Brazil)", False, "pt", "pt-BR", "BR", "🇧🇷"),
    Language("ru", "Русский", "Russian", False, "ru", "ru", "RU", "🇷🇺"),
    Language("de", "Deutsch", "German", False, "de", "de", "DE", "🇩🇪"),
    Language("fr", "Français", "French", False, "fr", "fr", "FR", "🇫🇷"),
    Language("ar", "العربية", "Arabic", True, "ar", "ar", "SA", "🇸🇦"),
    Language("zh", "中文", "Chinese", False, "zh", "zh-Hans", "CN", "🇨🇳"),
    Language("ja", "日本語", "Japanese", False, "ja", "ja", "JP", "🇯🇵"),
    Language("hu", "Magyar", "Hungarian", False, "hu", "hu", "HU", "🇭🇺"),
]

LANGUAGES: dict[str, Language] = {lang.code: lang for lang in _ALL}

# Codes people / old configs / browsers send that mean one of ours.
ALIASES = {"pt-br": "pt", "pt_br": "pt", "es-es": "es", "es-419": "es", "es-mx": "es", "es_419": "es",
           "zh-cn": "zh", "zh-hans": "zh", "zh_cn": "zh", "en-us": "en", "en-gb": "en", "ja-jp": "ja"}

# Spanish has two variants for titles / hashtags / YouTube locale (config "spanish_variant").
SPANISH_VARIANTS = {"es-419": ("es-419", "MX"), "es-ES": ("es", "ES")}

# First launch: English, unless a language was already chosen (1.2.53).
DEFAULT_UI_LANGUAGE = "en"
DEFAULT_OUTPUT_LANGUAGE = "en"


def codes() -> list[str]:
    return list(LANGUAGES)


def get(code: str | None) -> Language | None:
    if not code or not isinstance(code, str):
        return None
    c = code.strip().lower()
    return LANGUAGES.get(c) or LANGUAGES.get(ALIASES.get(c, ""))


def require(code: str) -> Language:
    lang = get(code)
    if lang is None:
        raise SharkyClipsError(
            f"Unsupported language '{code}'.",
            f"Use one of: {AUTO}, {', '.join(codes())}",
        )
    return lang


def from_whisper_code(whisper_code: str | None) -> Language | None:
    for lang in _ALL:
        if lang.whisper_code == whisper_code:
            return lang
    return None


def is_rtl(code: str | None) -> bool:
    lang = get(code)
    return bool(lang and lang.is_rtl)


def content_language(explicit: str | None = None, project=None) -> str:
    """THE language of everything SharkyClips writes for a clip (issue #5c / #1c): AI titles,
    descriptions, hashtags, hook / cover text, IG / TikTok captions and the YouTube metadata.

    Order: an explicit choice for this run > the project's own choice (meta `content_language`)
    > the "Content language" setting > the UI language > English. Never the language an older
    analysis happened to use: changing the setting must change the next titles.
    """
    from . import config

    cands: list = [explicit]
    if project is not None:
        try:
            cands.append((project.load_meta() or {}).get("content_language"))
        except Exception:  # noqa: BLE001 - an unreadable meta must not stop titles
            pass
    cfg = config.load()
    cands += [cfg.get("content_language"), cfg.get("output_language"), cfg.get("ui_language")]
    for c in cands:
        lang = get(c)
        if lang:
            return lang.code
    return "en"


def spanish_variant() -> str:
    from . import config

    v = str(config.get("spanish_variant") or "es-419")
    return v if v in SPANISH_VARIANTS else "es-419"


def publish_locale(code: str | None) -> str | None:
    """BCP-47 tag for YouTube snippet.defaultLanguage / defaultAudioLanguage."""
    lang = get(code)
    if not lang:
        return None
    if lang.code == "es":
        return SPANISH_VARIANTS[spanish_variant()][0]
    return lang.locale or lang.code


def publish_region(code: str | None) -> str | None:
    lang = get(code)
    if not lang:
        return None
    if lang.code == "es":
        return SPANISH_VARIANTS[spanish_variant()][1]
    return lang.region or None


def prompt_name(code: str | None) -> str:
    """The language name the LLM prompt asks for, with the variant ("Spanish (Latin America)")."""
    lang = get(code) or LANGUAGES["en"]
    if lang.code == "es":
        return "Spanish (Spain)" if spanish_variant() == "es-ES" else "Spanish (Latin America)"
    if lang.code == "zh":
        return "Simplified Chinese"
    if lang.code == "en":
        return "simple English (CEFR B2 or easier, short sentences, no jargon)"
    return lang.english_name
