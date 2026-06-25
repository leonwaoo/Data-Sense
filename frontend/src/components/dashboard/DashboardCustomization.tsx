import { ImagePlus, Palette, X } from "lucide-react";
import { dashboardThemeMap } from "../../constants";
import type { DashboardSettings, DashboardTheme } from "../../types";

export function DashboardCustomization({
  settings,
  onSettingsChange,
}: {
  settings: DashboardSettings;
  onSettingsChange: (settings: DashboardSettings | ((current: DashboardSettings) => DashboardSettings)) => void;
}) {
  function handleLogoUpload(file: File | null) {
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      onSettingsChange((current) => ({ ...current, logoDataUrl: String(reader.result || "") }));
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="toolbox-block">
      <div className="toolbox-title">
        <Palette size={17} />
        <strong>Personalizacao</strong>
      </div>
      <label>
        <span>Titulo</span>
        <input
          value={settings.title}
          onChange={(event) => onSettingsChange((current) => ({ ...current, title: event.target.value }))}
        />
      </label>
      <label>
        <span>Tema</span>
        <select
          value={settings.theme}
          onChange={(event) =>
            onSettingsChange((current) => ({ ...current, theme: event.target.value as DashboardTheme }))
          }
        >
          {Object.entries(dashboardThemeMap).map(([key, theme]) => (
            <option key={key} value={key}>
              {theme.label}
            </option>
          ))}
        </select>
      </label>
      <div className="logo-actions">
        <label className="logo-picker">
          <ImagePlus size={16} />
          Logo
          <input accept="image/*" type="file" onChange={(event) => handleLogoUpload(event.target.files?.[0] ?? null)} />
        </label>
        {settings.logoDataUrl ? (
          <button onClick={() => onSettingsChange((current) => ({ ...current, logoDataUrl: null }))} type="button">
            <X size={15} />
          </button>
        ) : null}
      </div>
    </div>
  );
}
