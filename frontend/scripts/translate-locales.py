"""Fill missing UI strings in frontend/src/i18n/locales/<lang>.ts with the local LLM (Ollama).

    python frontend/scripts/translate-locales.py es pt fr ja        # new locales (all keys)
    python frontend/scripts/translate-locales.py --all              # every locale: only missing keys

Only keys missing from a locale are translated; existing human translations are never touched.
Every answer is checked: same {placeholders}, no empty text, product names kept. A string that
fails twice stays English (the app falls back to English for it anyway) and is listed at the end
so a person can fix it. Machine-translated locales are marked in the file header.
"""

from __future__ import annotations

import json
import re
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "i18n" / "locales"
OLLAMA = "http://127.0.0.1:11434"
MODEL = "qwen3.5:4b"  # fits fully on an 8 GB GPU next to other apps; good enough, fast
BATCH = 25
NAMES = {
    "es": "Spanish (neutral Latin American Spanish that people in Spain also read easily; use 'tú')",
    "pt": "Brazilian Portuguese (use 'você')",
    "fr": "French (use 'tu' like gaming apps do)",
    "ja": "Japanese (polite but short, like a modern app)",
    "tr": "Turkish", "ru": "Russian", "de": "German (use 'du')", "hu": "Hungarian (use tegező form)",
    "ar": "Modern Standard Arabic", "zh": "Simplified Chinese",
}
KEEP = ["SharkyClips", "YouTube", "TikTok", "Instagram", "Reels", "Shorts", "Kick", "Twitch", "OBS", "Whisper",
        "Ollama", "Telegram", "Google", "Meta", "Facebook", "Discord", "GPU", "CPU", "RAM", "VRAM", "LLM", "AI",
        "OCR", "HUD", "MP4", "PNG", "Wi-Fi", "PIN", "URL", "TikTok Studio", "Chrome", "Edge"]
LINE = re.compile(r'^(\s*)"([^"]+)":\s*"((?:[^"\\]|\\.)*)",?\s*$')
PH = re.compile(r"\{\w+\}")


def parse(path: Path) -> dict[str, str]:
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        m = LINE.match(line)
        if m:
            out[m.group(2)] = json.loads('"' + m.group(3) + '"')
    return out


def ask(lang: str, items: dict[str, str]) -> dict[str, str]:
    prompt = (
        f"Translate the values of this JSON object from English to {NAMES.get(lang, lang)}.\n"
        "They are short texts of the user interface of SharkyClips, a free desktop app that makes short clips "
        "from gaming streams and posts them to YouTube / TikTok / Instagram.\n"
        "Rules:\n"
        "- Keep the JSON keys exactly. Return only a JSON object with the same keys.\n"
        "- Keep every {placeholder} exactly as it is (same name, same braces).\n"
        f"- Keep these names unchanged: {', '.join(KEEP)}.\n"
        "- Keep emoji, arrows (→), dots (…), keyboard keys (Ctrl, Shift, Esc) and numbers.\n"
        "- Simple, friendly, short words. Same tone as the English. No explanations.\n\n"
        + json.dumps(items, ensure_ascii=False, indent=0)
    )
    body = {"model": MODEL, "stream": False, "think": False, "format": "json", "keep_alive": "10m",
            "options": {"temperature": 0.2, "num_ctx": 8192},
            "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(f"{OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        data = json.loads(r.read())
    txt = data["message"]["content"]
    obj = json.loads(txt[txt.find("{"): txt.rfind("}") + 1])
    return {k: v for k, v in obj.items() if isinstance(v, str)}


def ok(src: str, out: str) -> bool:
    if not out.strip():
        return False
    if sorted(PH.findall(src)) != sorted(PH.findall(out)):
        return False
    for name in KEEP:
        if name in src and len(name) > 3 and name not in out and name not in ("Reels", "Shorts"):
            return False
    return len(out) < max(40, len(src) * 4)


def write(lang: str, keys: list[str], en: dict[str, str], cur: dict[str, str], machine: bool) -> None:
    """A new locale file is written in en.ts order. An existing file is never rewritten: only the
    keys it doesn't have yet are added before its closing brace (its own plural forms, comments
    and order stay as they are)."""
    path = ROOT / f"{lang}.ts"
    if path.is_file():
        text = path.read_text(encoding="utf-8")
        have = set(parse(path))
        add = [k for k in keys if k in cur and k not in have]
        if not add:
            return
        i = text.rindex("};")
        lines = "".join(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(cur[k], ensure_ascii=False)},\n" for k in add)
        path.write_text(text[:i] + lines + text[i:], encoding="utf-8", newline="\n")
        return
    head = []
    if machine:
        head = ["// Machine-translated with a local LLM (frontend/scripts/translate-locales.py), then checked",
                "// for placeholders and names. Fixes from native speakers are very welcome."]
    lines = head + [f"const {lang}: Record<string, string> = {{"]
    for k in keys:
        if k in cur:
            lines.append(f"  {json.dumps(k, ensure_ascii=False)}: {json.dumps(cur[k], ensure_ascii=False)},")
    lines += ["};", "", f"export default {lang};", ""]
    path.write_text("\n".join(lines), encoding="utf-8", newline="\n")


def run(lang: str) -> list[str]:
    en = parse(ROOT / "en.ts")
    path = ROOT / f"{lang}.ts"
    cur = parse(path) if path.is_file() else {}
    machine = not path.is_file() or "machine-translated" in path.read_text(encoding="utf-8")[:300]
    no_one = lang in ("zh", "ja")  # Intl.PluralRules: only "other"
    plural = re.compile(r"_(zero|one|two|few|many|other)$")
    have_base = {plural.sub("", k) for k in cur}  # a locale's own plural forms cover the key already
    todo = [k for k in en if k not in cur and not k.endswith(("_zero", "_two", "_few", "_many"))
            and not (no_one and k.endswith("_one")) and not (plural.search(k) and plural.sub("", k) in have_base)]
    failed: list[str] = []
    print(f"{lang}: {len(todo)} keys to translate", flush=True)
    t0 = time.time()
    for i in range(0, len(todo), BATCH):
        part = {k: en[k] for k in todo[i:i + BATCH]}
        got: dict[str, str] = {}
        for attempt in range(2):
            try:
                ans = ask(lang, {k: v for k, v in part.items() if k not in got})
            except Exception as exc:  # noqa: BLE001
                print(f"  batch {i}: {exc}", flush=True)
                time.sleep(3)
                continue
            for k, v in ans.items():
                if k in part and ok(part[k], v):
                    got[k] = v
            if len(got) == len(part):
                break
        for k in part:
            if k in got:
                cur[k] = got[k]
            else:  # stays English (the key must exist in every locale); listed at the end
                failed.append(k)
                cur[k] = en[k]
        write(lang, list(en), en, cur, machine)
        done = min(i + BATCH, len(todo))
        rate = (time.time() - t0) / max(1, done)
        print(f"  {lang} {done}/{len(todo)}  ~{rate * (len(todo) - done) / 60:.0f} min left", flush=True)
    return failed


if __name__ == "__main__":
    args = sys.argv[1:]
    langs = [p.stem for p in ROOT.glob("*.ts") if p.stem != "en"] if args == ["--all"] else args
    report = {}
    for lg in langs:
        report[lg] = run(lg)
    print(json.dumps({k: len(v) for k, v in report.items()}), flush=True)
    for lg, ks in report.items():
        if ks:
            print(lg, "left in English:", ", ".join(ks[:40]), flush=True)
