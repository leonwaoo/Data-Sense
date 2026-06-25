import { BarChart3, Database, ShieldCheck, TableProperties } from "lucide-react";
import { MetricCard } from "../common/MetricCard";
import type { DashboardPayload, UploadResponse } from "../../types";

export function DetailsSection({
  dataset,
  dashboard,
}: {
  dataset: UploadResponse;
  dashboard: DashboardPayload | null;
}) {
  const profile = dataset.profile;
  const quality = dataset.quality;
  const analysis = dataset.managerial_analysis;
  const supportMetrics = Object.values(analysis?.context.metric_map.support_metrics ?? {});

  return (
    <div className="section-stack">
      <section className="panel">
        <div className="panel-heading">
          <div>
            <h2>Detalhes tecnicos</h2>
            <span>Estrutura, qualidade e metricas usadas pela analise</span>
          </div>
        </div>

        <div className="summary-grid">
          <MetricCard icon={<Database size={20} />} label="Arquivo" value={dataset.file_name} />
          <MetricCard icon={<TableProperties size={20} />} label="Linhas" value={profile.rows.toLocaleString("pt-BR")} />
          <MetricCard icon={<BarChart3 size={20} />} label="Colunas" value={String(profile.columns)} />
          <MetricCard icon={<ShieldCheck size={20} />} label="Qualidade" value={`${quality.score}/100`} />
        </div>
      </section>

      <section className="panel technical-grid-panel">
        <article>
          <strong>Campos detectados</strong>
          <p>Datas: {profile.datetime_columns.join(", ") || "nenhuma"}</p>
          <p>Numericas: {profile.numeric_columns.join(", ") || "nenhuma"}</p>
          <p>Categorias: {profile.categorical_columns.join(", ") || "nenhuma"}</p>
        </article>
        <article>
          <strong>Qualidade dos dados</strong>
          <p>Nulos totais: {quality.missing_total.toLocaleString("pt-BR")}</p>
          <p>Duplicatas: {quality.duplicate_rows.toLocaleString("pt-BR")}</p>
          <p>Colunas vazias: {quality.empty_columns.length || 0}</p>
        </article>
        <article>
          <strong>Analise gerencial</strong>
          <p>Metrica principal: {analysis?.context.metric_map.primary_metric ?? "nao detectada"}</p>
          <p>Tempo: {analysis?.context.time.label ?? "nao detectado"}</p>
          <p>Apoio: {supportMetrics.join(", ") || "nenhum"}</p>
        </article>
      </section>

      {dashboard?.kpis?.length ? (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>KPIs calculados</h2>
              <span>Indicadores usados como base do dashboard</span>
            </div>
          </div>
          <div className="technical-kpi-list">
            {dashboard.kpis.map((kpi) => (
              <article key={`${kpi.label}-${kpi.value}`}>
                <span>{kpi.label}</span>
                <strong>{kpi.value}</strong>
                <small>{kpi.detail}</small>
              </article>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
