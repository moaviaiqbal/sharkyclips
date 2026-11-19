"""One-off (1.2.53): make fr.ts consistently informal ("tu"), like gaming apps. Only lines that use
vous / votre / vos are rewritten (local LLM), placeholders are checked, everything else is kept."""
import importlib.util
import json
import re
from pathlib import Path

HERE = Path(__file__).resolve().parent
spec = importlib.util.spec_from_file_location("t", HERE / "translate-locales.py")
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)
PATH = t.ROOT / "fr.ts"
VOUS = re.compile(r"\b(vous|votre|vos)\b", re.I)


def ask(items: dict) -> dict:
    import urllib.request

    prompt = ("These are French UI texts of a gaming app. Rewrite each one in the informal 'tu' form "
              "(tu / ton / ta / tes / toi, verbs in the tu form, imperatives like 'Choisis', 'Clique'). "
              "Change nothing else: same meaning, same {placeholders}, same punctuation and names. "
              "Return only a JSON object with the same keys.\n\n" + json.dumps(items, ensure_ascii=False))
    body = {"model": t.MODEL, "stream": False, "think": False, "format": "json", "keep_alive": "10m",
            "options": {"temperature": 0.1, "num_ctx": 8192}, "messages": [{"role": "user", "content": prompt}]}
    req = urllib.request.Request(f"{t.OLLAMA}/api/chat", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=600) as r:
        txt = json.loads(r.read())["message"]["content"]
    return json.loads(txt[txt.find("{"): txt.rfind("}") + 1])


cur = t.parse(PATH)
todo = {k: v for k, v in cur.items() if VOUS.search(v)}
print(len(todo), "lines use vous")
new = {}
keys = list(todo)
for i in range(0, len(keys), 20):
    part = {k: todo[k] for k in keys[i:i + 20]}
    try:
        ans = ask(part)
    except Exception as exc:  # noqa: BLE001
        print("batch failed", exc)
        continue
    for k, v in ans.items():
        if k in part and isinstance(v, str) and t.ok(part[k], v) and not VOUS.search(v):
            new[k] = v
lines = PATH.read_text(encoding="utf-8").split("\n")
for i, line in enumerate(lines):
    m = t.LINE.match(line)
    if m and m.group(2) in new:
        lines[i] = f"{m.group(1)}{json.dumps(m.group(2), ensure_ascii=False)}: {json.dumps(new[m.group(2)], ensure_ascii=False)},"
PATH.write_text("\n".join(lines), encoding="utf-8", newline="\n")
print(len(new), "rewritten,", len(todo) - len(new), "kept")
