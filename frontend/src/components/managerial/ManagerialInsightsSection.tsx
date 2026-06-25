import { TrendingUp } from "lucide-react";
import { RootCauseSection } from "./RootCauseSection";
import type { ManagerialAnalysis } from "../../types";

export function ManagerialInsightsSection({ analysis }: { analysis: ManagerialAnalysis }) {
  const primaryMetric = analysis.context.metric_map.primary_metric ?? "Metrica nao detectada";
  const supportMetrics = Object.values(analysis.context.metric_map.support_metrics);
  const rootCause = analysis.root_cause_analysis ?? null;

  return (
    <section className="panel managerial-panel">
      <div className="managerial-heading">
        <div>
          <TrendingUp size={22} />
          <div>
            <h2>Insights Gerenciais</h2>
            <span>
              {analysis.context.domain.label} - {Math.round(analysis.context.domain.confidence * 100)}% de confianca
            </span>
          </div>
        </div>
        <span className="domain-pill">{primaryMetric}</span>
      </div>

      <div className="managerial-summary">
        {analysis.summary.slice(0, 4).map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>

      <div className="managerial-context-grid">
        <article>
          <span>Tempo</span>
          <strong>{analysis.context.time.label ?? "Nao detectado"}</strong>
          <small>{analysis.context.time.columns.join(" + ") || "Sem coluna temporal"}</small>
        </article>
        <article>
          <span>Metricas de apoio</span>
          <strong>{supportMetrics.length ? supportMetrics.slice(0, 2).join(", ") : "Nenhuma"}</strong>
          <small>{supportMetrics.length > 2 ? `+${supportMetrics.length - 2} outra(s)` : "Usadas para explicar causas"}</small>
        </article>
        <article>
          <span>Dimensoes</span>
          <strong>{analysis.context.dimensions.map((item) => item.column).join(", ") || "Nao detectadas"}</strong>
          <small>Onde localizar a variacao</small>
        </article>
      </div>

      {analysis.kpis.length ? (
        <div className="managerial-kpis">
          {analysis.kpis.slice(0, 6).map((kpi) => (
            <article key={`${kpi.label}-${kpi.value}`}>
              <span>{kpi.label}</span>
              <strong>{kpi.value}</strong>
              <small>{kpi.detail}</small>
            </article>
          ))}
        </div>
      ) : null}

      <RootCauseSection rootCause={rootCause} />

      <div className="managerial-insight-grid">
        {analysis.insights.slice(0, 4).map((insight) => (
          <article className={`managerial-insight-card severity-${insight.severity}`} key={insight.id}>
            <div>
              <strong>{insight.title}</strong>
              <span>Confianca {insight.confidence}</span>
            </div>
            <p>{insight.how_much}</p>
            <p>{insight.where}</p>
            <ul>
              {insight.possible_causes.slice(0, 2).map((cause) => (
                <li key={cause}>{cause}</li>
              ))}
            </ul>
            <footer>
              <span>{insight.managerial_impact}</span>
              <strong>{insight.recommendation}</strong>
            </footer>
          </article>
        ))}
      </div>

      <div className="managerial-bottom-grid">
        <div className="managerial-list">
          <strong>Alertas</strong>
          {analysis.alerts.slice(0, 3).map((alert) => (
            <p key={alert}>{alert}</p>
          ))}
        </div>
        <div className="managerial-list">
          <strong>Recomendacoes</strong>
          {analysis.recommendations.slice(0, 3).map((recommendation) => (
            <p key={recommendation}>{recommendation}</p>
          ))}
        </div>
        <div className="managerial-list">
          <strong>Perguntas sugeridas</strong>
          {analysis.suggested_questions.slice(0, 4).map((question) => (
            <p key={question}>{question}</p>
          ))}
        </div>
      </div>
    </section>
  );
}
