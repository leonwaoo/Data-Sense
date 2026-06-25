import { BarChart3, Database, FileQuestion, ShieldCheck, Sparkles } from "lucide-react";
import { MetricCard } from "../common/MetricCard";
import { MonthlyAnalysisSection } from "../managerial/MonthlyAnalysisSection";
import type { UploadResponse } from "../../types";

export function OverviewSection({ dataset }: { dataset: UploadResponse }) {
  const profile = dataset.profile;

  return (
    <div className="section-stack">
      <div className="summary-grid">
        <MetricCard icon={<Database size={20} />} label="Dataset" value={dataset.file_name} />
        <MetricCard icon={<BarChart3 size={20} />} label="Linhas" value={profile.rows.toLocaleString("pt-BR")} />
        <MetricCard icon={<FileQuestion size={20} />} label="Colunas" value={String(profile.columns)} />
        <MetricCard icon={<ShieldCheck size={20} />} label="Qualidade" value={`${dataset.quality.score}/100`} />
      </div>

      <div className="insight-strip">
        <div>
          <Sparkles size={18} />
          <span>Dataset carregado e pronto para analise</span>
        </div>
        <strong>
          {profile.datetime_columns.length} data(s), {profile.numeric_columns.length} metrica(s)
        </strong>
      </div>

      {dataset.managerial_analysis ? <MonthlyAnalysisSection analysis={dataset.managerial_analysis} /> : null}
    </div>
  );
}
