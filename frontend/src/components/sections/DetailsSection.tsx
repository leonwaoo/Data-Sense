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
            <span>Estrutura, qualidade e indicadores usados pela analise</span>
          </div>
        </div>

        <div className="summary-grid">
          <MetricCard icon={<Database size={20} />} label="Arquivo" value={dataset.file_name} />
          <MetricCard icon={<TableProperties size={20} />} label="Linhas" value={profile.rows.toLocaleString("pt-BR")} />
          <MetricCard icon={<BarChart3 size={20} />} label="Colunas" value={String(profile.columns)} />
          <MetricCard icon={<ShieldCheck size={20} />} label="Pontuacao" value={`${quality.score}/100`} />
        </div>
      </section>

      <section className="panel technical-grid-panel">
        <article>
          <strong>Campos encontrados</strong>
          <p>Datas: {profile.datetime_columns.join(", ") || "nenhuma"}</p>
          <p>Numericos: {profile.numeric_columns.join(", ") || "nenhum"}</p>
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
          <p>Indicador principal: {analysis?.context.metric_map.primary_metric ?? "nao detectado"}</p>
          <p>Periodo: {analysis?.context.time.label ?? "nao detectado"}</p>
          <p>Fatores de apoio: {supportMetrics.join(", ") || "nenhum"}</p>
        </article>
      </section>

      {dashboard?.kpis?.length ? (
        <section className="panel">
          <div className="panel-heading">
            <div>
              <h2>Indicadores calculados</h2>
              <span>Base numerica usada nos graficos e relatorios</span>
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
