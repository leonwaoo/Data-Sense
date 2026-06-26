import { FileText, LayoutDashboard, LineChart, MessageSquareText, Plus, ShieldCheck, Sparkles, Stethoscope } from "lucide-react";
import type { SectionKey, UploadResponse } from "../../types";

const NAV_ITEMS: { key: SectionKey; label: string; icon: typeof LineChart; hint: string }[] = [
  { key: "overview", label: "Inicio", icon: LineChart, hint: "Leitura simples para decisao" },
  { key: "diagnostic", label: "Diagnostico", icon: Stethoscope, hint: "Causa raiz e acoes" },
  { key: "dashboard", label: "Graficos", icon: LayoutDashboard, hint: "Visualizacao dos dados" },
  { key: "details", label: "Detalhes", icon: FileText, hint: "Indicadores e qualidade" },
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
              <small>Arquivo pronto para analise</small>
            </div>
          </div>
        ) : (
          <p className="sidebar-empty">Envie um arquivo para liberar as secoes.</p>
        )}
      </div>
    </aside>
  );
}
