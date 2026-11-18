import { useEffect, useId, useRef, useState } from "react";
import { UI_LANGUAGES, useI18n } from "../i18n";
import { chooseLanguage } from "../meta";

/**
 * 1.2.53: the language switcher (top bar + home screen): flag + language name.
 * Flags are small inline SVGs (Windows has no flag emoji). A flag stands for the language, not a
 * country: English = GB, Portuguese = Brazil, Arabic = Saudi Arabia, Spanish = Spain.
 */
export function Flag({ code, size = 18 }: { code: string; size?: number }) {
  const h = Math.round((size * 2) / 3);
  const common = { width: size, height: h, viewBox: "0 0 30 20", "aria-hidden": true, focusable: false, className: "flag" } as const;
  switch (code) {
    case "gb":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#012169" />
          <path d="M0 0L30 20M30 0L0 20" stroke="#fff" strokeWidth="4" />
          <path d="M0 0L30 20M30 0L0 20" stroke="#C8102E" strokeWidth="1.6" />
          <path d="M15 0V20M0 10H30" stroke="#fff" strokeWidth="6" />
          <path d="M15 0V20M0 10H30" stroke="#C8102E" strokeWidth="3.4" />
        </svg>
      );
    case "tr":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#E30A17" />
          <circle cx="11" cy="10" r="5" fill="#fff" />
          <circle cx="12.3" cy="10" r="4" fill="#E30A17" />
          <path d="M16.2 10l3.6-1.2-2.2 3.1V8.1l2.2 3.1z" fill="#fff" />
        </svg>
      );
    case "es":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#AA151B" />
          <rect y="5" width="30" height="10" fill="#F1BF00" />
        </svg>
      );
    case "br":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#009C3B" />
          <path d="M15 2.5L27 10 15 17.5 3 10z" fill="#FFDF00" />
          <circle cx="15" cy="10" r="4.2" fill="#002776" />
        </svg>
      );
    case "ru":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#fff" />
          <rect y="6.67" width="30" height="6.67" fill="#0039A6" />
          <rect y="13.33" width="30" height="6.67" fill="#D52B1E" />
        </svg>
      );
    case "de":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#000" />
          <rect y="6.67" width="30" height="6.67" fill="#DD0000" />
          <rect y="13.33" width="30" height="6.67" fill="#FFCE00" />
        </svg>
      );
    case "fr":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#fff" />
          <rect width="10" height="20" fill="#002395" />
          <rect x="20" width="10" height="20" fill="#ED2939" />
        </svg>
      );
    case "sa":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#006C35" />
          <path d="M8 8.5h14M9 10.5h12" stroke="#fff" strokeWidth="1" />
          <path d="M9 14h12" stroke="#fff" strokeWidth="1.2" />
        </svg>
      );
    case "cn":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#DE2910" />
          <path d="M6 3l1.2 3.6H11L8 8.8l1.1 3.6L6 10.2 2.9 12.4 4 8.8 1 6.6h3.8z" fill="#FFDE00" />
        </svg>
      );
    case "jp":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#fff" stroke="#ddd" strokeWidth="0.6" />
          <circle cx="15" cy="10" r="5.5" fill="#BC002D" />
        </svg>
      );
    case "hu":
      return (
        <svg {...common}>
          <rect width="30" height="20" fill="#CD2A3E" />
          <rect y="6.67" width="30" height="6.67" fill="#fff" />
          <rect y="13.33" width="30" height="6.67" fill="#436F4D" />
        </svg>
      );
    default:
      return null;
  }
}

export function LanguageSwitcher({ compact, big }: { compact?: boolean; big?: boolean }) {
  const { t, lang, setLang } = useI18n();
  const [open, setOpen] = useState(false);
  const box = useRef<HTMLDivElement>(null);
  const list = useRef<HTMLUListElement>(null);
  const id = useId();
  const cur = UI_LANGUAGES.find((l) => l.code === lang) ?? UI_LANGUAGES[0];

  useEffect(() => {
    if (!open) return;
    const close = (e: MouseEvent) => !box.current?.contains(e.target as Node) && setOpen(false);
    window.addEventListener("mousedown", close);
    list.current?.querySelector<HTMLButtonElement>('[aria-current="true"]')?.focus({ preventScroll: true });
    return () => window.removeEventListener("mousedown", close);
  }, [open]);

  const pick = (code: string) => {
    chooseLanguage(code, setLang);
    setOpen(false);
  };
  const onListKey = (e: React.KeyboardEvent) => {
    const items = Array.from(list.current?.querySelectorAll<HTMLButtonElement>("button") ?? []);
    const i = items.indexOf(document.activeElement as HTMLButtonElement);
    if (e.key === "ArrowDown" || e.key === "ArrowUp") {
      e.preventDefault();
      const n = (i + (e.key === "ArrowDown" ? 1 : -1) + items.length) % items.length;
      items[n]?.focus();
    } else if (e.key === "Home" || e.key === "End") {
      e.preventDefault();
      items[e.key === "Home" ? 0 : items.length - 1]?.focus();
    } else if (e.key === "Escape") {
      e.preventDefault();
      e.stopPropagation();
      setOpen(false);
      box.current?.querySelector<HTMLButtonElement>(".lang-btn")?.focus();
    } else if (e.key === "Tab") setOpen(false);
  };

  return (
    <div className={`lang-switch${big ? " lang-switch-big" : ""}`} ref={box}>
      <button
        type="button"
        className={`btn ${big ? "" : "btn-ghost btn-sm "}lang-btn`}
        aria-haspopup="true"
        aria-expanded={open}
        aria-controls={id}
        aria-label={`${t("lang.label")}: ${cur.name}`}
        onClick={() => setOpen((v) => !v)}
      >
        <Flag code={cur.flag} />
        {!compact && <span lang={cur.code}>{cur.name}</span>}
        <span className="lang-caret" aria-hidden="true">
          ▾
        </span>
      </button>
      {open && (
        <ul className="lang-menu" id={id} ref={list} onKeyDown={onListKey} aria-label={t("lang.label")}>
          {UI_LANGUAGES.map((l) => (
            <li key={l.code}>
              <button type="button" aria-current={l.code === lang ? "true" : undefined} onClick={() => pick(l.code)} lang={l.code}>
                <Flag code={l.flag} />
                <span>{l.name}</span>
                {l.code === lang && (
                  <span className="lang-check" aria-hidden="true">
                    ✓
                  </span>
                )}
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
