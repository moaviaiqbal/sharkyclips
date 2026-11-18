"""Template titles (1.2.53): titles without any LLM, for very slow PCs (Light preset with < 6 GB
RAM) or when the LLM is off. Built from what the clip really contains: the strongest game event
of the clip (from the HUD scan / game profile), else a short line the streamer said.

Short, simple words in every content language (English: B2 or easier).
"""

from __future__ import annotations

import re

# {event} = the event word ("ACE", "WASTED"), {game} = the game name
PATTERNS = {
    "en": ["{event}! {game}", "{event} in {game}", "What a {event}"],
    "tr": ["{event}! {game}", "{game}: {event}", "Bu {event} çok iyi"],
    "es": ["¡{event}! {game}", "{event} en {game}", "Qué {event}"],
    "pt": ["{event}! {game}", "{event} no {game}", "Que {event}"],
    "ru": ["{event}! {game}", "{event} в {game}", "Вот это {event}"],
    "de": ["{event}! {game}", "{event} in {game}", "Was für ein {event}"],
    "fr": ["{event} ! {game}", "{event} sur {game}", "Quel {event}"],
    "ar": ["{event}! {game}", "{event} في {game}", "يا له من {event}"],
    "zh": ["{event}！{game}", "{game}：{event}", "这波{event}太强了"],
    "ja": ["{event}！{game}", "{game}で{event}", "神{event}"],
    "hu": ["{event}! {game}", "{event} a {game}-ban", "Micsoda {event}"],
}
NO_EVENT = {
    "en": "{game} moment", "tr": "{game} anı", "es": "Momento de {game}", "pt": "Momento de {game}",
    "ru": "Момент из {game}", "de": "{game}-Moment", "fr": "Moment {game}", "ar": "لحظة من {game}",
    "zh": "{game}名场面", "ja": "{game}の名場面", "hu": "{game} pillanat",
}


def _event_word(cand: dict) -> str | None:
    """The strongest game event of the clip, as a short upper-case word."""
    from ..game import gameprofiles

    best, best_s = None, 0.0
    for r in cand.get("reasons") or []:
        code = str(r.get("code") or "")
        s = float(r.get("strength") or 0)
        if s <= best_s:
            continue
        label = None
        for p in gameprofiles.all_profiles().values():
            ev = (p.get("events") or {}).get(code)
            if ev:
                label = ev.get("label")
                break
        if label is None and "_" in code and code.split("_", 1)[0] in ("lol", "df"):
            label = code.split("_", 1)[1].replace("kill", " kill").replace("_", " ").strip()
        if label:
            best, best_s = label.upper(), s
    return best


def _quote(cand: dict, limit: int = 60) -> str:
    text = re.sub(r"\s+", " ", str(cand.get("text") or "")).strip()
    if len(text) <= limit:
        return text
    cut = text[:limit].rsplit(" ", 1)[0]
    return cut + "…"


def titles(cand: dict, game: str | None, lang: str, n: int = 3) -> list[str]:
    lang = lang if lang in PATTERNS else "en"
    game = (game or "").strip()
    word = _event_word(cand)
    out: list[str] = []
    if word:
        for pat in PATTERNS[lang]:
            if "{game}" in pat and not game:
                continue
            out.append(pat.format(event=word, game=game).strip(" :!"))
    q = _quote(cand)
    if q:
        out.append(q if not game else f"{q} | {game}")
    if game:
        out.append(NO_EVENT[lang].format(game=game))
    seen: list[str] = []
    for t in out:
        t = t[:100]
        if t and t not in seen:
            seen.append(t)
    return seen[:n]
