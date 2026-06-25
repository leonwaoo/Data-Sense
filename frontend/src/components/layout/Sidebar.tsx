import { LayoutDashboard, LineChart, MessageSquareText, Plus, ShieldCheck, Sparkles, Stethoscope } from "lucide-react";
import type { SectionKey, UploadResponse } from "../../types";

const NAV_ITEMS: { key: SectionKey; label: string; icon: typeof LineChart; hint: string }[] = [
  { key: "overview", label: "Visao geral", icon: LineChart, hint: "Metricas e analise gerencial" },
  { key: "diagnostic", label: "Diagnostico", icon: Stethoscope, hint: "Causa raiz e leitura executiva" },
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard, hint: "KPIs e graficos automaticos" },
  { key: "chat", label: "Chat analitico", icon: MessageSquareText, hint: "Pergunte aos dados" },
  { key: "reports", label: "Relatorios", icon: ShieldCheck, hint: "Exportar e historico" },
];

export function Sidebar({
  active,
  dataset,
  onNavigate,
  onNewFile,
}: {
  active: SectionKey;
  dataset: UploadResponse | null;
  onNavigate: (section: SectionKey) => void;
  onNewFile: () => void;
}) {
  return (
    <aside className="sidebar">
      <div className="sidebar-brand">
        <img alt="" className="brand-mark" src="/brand-mark.svg" />
        <div>
          <strong>DataSense</strong>
          <span>Analise assistida</span>
        </div>
      </div>

      <button className="sidebar-newfile" onClick={onNewFile} type="button">
        <Plus size={16} />
        Novo arquivo
      </button>

      <nav className="sidebar-nav" aria-label="Secoes">
        {NAV_ITEMS.map((item) => {
          const Icon = item.icon;
          const disabled = !dataset;
          return (
            <button
              className={`sidebar-link${active === item.key ? " is-active" : ""}`}
              disabled={disabled}
              key={item.key}
              onClick={() => onNavigate(item.key)}
              type="button"
            >
              <Icon size={18} />
              <span>
                <strong>{item.label}</strong>
                <small>{item.hint}</small>
              </span>
            </button>
          );
        })}
      </nav>

      <div className="sidebar-footer">
        {dataset ? (
          <div className="sidebar-dataset">
            <Sparkles size={15} />
            <div>
              <strong>{dataset.file_name}</strong>
              <small>
                {dataset.profile.rows.toLocaleString("pt-BR")} linhas - qualidade {dataset.quality.score}/100
              </small>
            </div>
          </div>
        ) : (
          <p className="sidebar-empty">Envie um dataset para liberar as secoes.</p>
        )}
      </div>
    </aside>
  );
}
