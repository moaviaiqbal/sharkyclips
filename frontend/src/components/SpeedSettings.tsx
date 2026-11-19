import { useEffect, useState } from "react";
import { api, type Settings as SettingsT } from "../api";
import { UI_LANGUAGES, useI18n } from "../i18n";
import { useToast } from "../toast";
import { Segmented, Toggle } from "./ui";

/** 1.2.53: where the AI runs + the Light preset for slow PCs. */
export function DeviceSettings({ settings, save }: { settings: SettingsT; save: (p: Partial<SettingsT>) => Promise<void> }) {
  const { t, num } = useI18n();
  const st = settings.perf;
  const m = st?.machine;
  const gpu = m?.nvidia_name ? `${m.nvidia_name} (${num(m.nvidia_vram_gb ?? 0, 0)} GB)` : m?.apple_silicon ? "Apple Silicon" : t("perf.no_gpu");
  return (
    <div style={{ display: "grid", gap: 14 }}>
      {st?.weak && (
        <div className={`notice perf-note${st.light ? "" : " notice-warn"}`} role="status">
          <span>
            {t("perf.slow_pc")} {st.light && t("perf.slow_pc_light")}
          </span>
          {!st.light && (
            <button className="btn btn-sm" onClick={() => save({ performance_preset: "light" })}>
              {t("perf.use_light")}
            </button>
          )}
        </div>
      )}
      <div>
        <Segmented<"auto" | "cpu" | "gpu">
          block
          label={t("perf.device")}
          value={settings.processing_device ?? "auto"}
          options={(["auto", "cpu", "gpu"] as const).map((v) => ({ value: v, label: t(`perf.device.${v}`) }))}
          onChange={(v) => save({ processing_device: v })}
        />
        <div className="field-hint" style={{ marginTop: 6 }}>
          {t("perf.device_desc")} {st && t("perf.device_now", { where: t(`perf.where.${st.device}`) })}
        </div>
      </div>
      <div>
        <Segmented<"auto" | "light" | "normal">
          block
          label={t("perf.preset")}
          value={settings.performance_preset ?? "auto"}
          options={(["auto", "light", "normal"] as const).map((v) => ({ value: v, label: t(`perf.preset.${v}`) }))}
          onChange={(v) => save({ performance_preset: v })}
        />
        <div className="field-hint" style={{ marginTop: 6 }}>
          {t("perf.preset_desc")}
        </div>
      </div>
      {st?.light && (
        <div className="toggle-line">
          <Toggle checked={!!settings.voices_on_light} onChange={(v) => save({ voices_on_light: v })} label={t("perf.voices_on_light")} />
          <span>{t("perf.voices_on_light")}</span>
        </div>
      )}
      {m && (
        <div className="field-hint mono">
          {t("perf.machine", { threads: num(m.threads), ram: num(m.ram_gb, 0), gpu })}
        </div>
      )}
    </div>
  );
}


/** 1.2.53 Easy mode settings: content language (+ Spanish style) and the speed controls. */
export function LanguageSpeedCard() {
  const { t } = useI18n();
  const toast = useToast();
  const [settings, setSettings] = useState<SettingsT | null>(null);
  useEffect(() => {
    api.settings().then(setSettings).catch(() => {});
  }, []);
  const save = async (p: Partial<SettingsT>) => {
    try {
      setSettings(await api.saveSettings(p));
    } catch (e: any) {
      toast({ kind: "err", text: e.message, hint: e.hint });
    }
  };
  if (!settings) return null;
  return (
    <section className="card ez-set-card" id="content-language" aria-labelledby="ez-set-lang">
      <h2 id="ez-set-lang">{t("settings.content_language")}</h2>
      <p className="muted" style={{ marginTop: 0 }}>
        {t("settings.content_language_desc")}
      </p>
      <div style={{ display: "grid", gap: 12 }}>
        <select
          className="select"
          aria-label={t("settings.content_language")}
          value={settings.output_language}
          onChange={(e) => {
            const code = e.target.value;
            save({ output_language: code }).then(() =>
              toast({ kind: "ok", text: t("settings.content_language_changed", { lang: UI_LANGUAGES.find((l) => l.code === code)?.name ?? code }) }),
            );
          }}
        >
          {UI_LANGUAGES.map((l) => (
            <option key={l.code} value={l.code}>
              {l.name}
            </option>
          ))}
        </select>
        {settings.output_language === "es" && (
          <Segmented<"es-419" | "es-ES">
            label={t("settings.spanish_variant")}
            value={settings.spanish_variant ?? "es-419"}
            options={(["es-419", "es-ES"] as const).map((v) => ({ value: v, label: t(`settings.spanish_variant.${v}`) }))}
            onChange={(v) => save({ spanish_variant: v })}
          />
        )}
        <h3 style={{ margin: "8px 0 0" }}>{t("perf.title")}</h3>
        <DeviceSettings settings={settings} save={save} />
      </div>
    </section>
  );
}
