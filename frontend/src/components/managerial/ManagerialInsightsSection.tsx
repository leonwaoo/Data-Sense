import { BrainCircuit, Sparkles, TrendingUp } from "lucide-react";
import { RootCauseSection } from "./RootCauseSection";
import type { ManagerialAiReview, ManagerialAnalysis } from "../../types";

type ManagerialInsightsSectionProps = {
  analysis: ManagerialAnalysis;
  aiReview: ManagerialAiReview | null;
  isAiLoading: boolean;
  onAiReview: () => void;
};

export function ManagerialInsightsSection({
  analysis,
  aiReview,
  isAiLoading,
  onAiReview,
}: ManagerialInsightsSectionProps) {
  const primaryMetric = analysis.context.metric_map.primary_metric ?? "Metrica nao detectada";
  const supportMetrics = Object.values(analysis.context.metric_map.support_metrics);
  const rootCause = analysis.root_cause_analysis ?? null;
  const aiStatusLabel = aiReview?.ai_status === "completed"
    ? `IA ${aiReview.model ?? "ativa"}`
    : aiReview?.ai_status === "not_configured"
      ? "Regras locais"
      : aiReview?.ai_status === "failed"
        ? "IA indisponivel"
        : "Segunda leitura";

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

      <div className="managerial-ai-panel">
        <div className="managerial-ai-heading">
          <div>
            <BrainCircuit size={20} />
            <div>
              <strong>Leitura executiva</strong>
              <span>{aiStatusLabel}</span>
            </div>
          </div>
          <button disabled={isAiLoading} onClick={onAiReview} type="button">
            <Sparkles size={15} />
            {isAiLoading ? "Analisando..." : aiReview ? "Atualizar leitura" : "Gerar leitura"}
          </button>
        </div>

        {aiReview ? (
          <div className="managerial-ai-body">
            {aiReview.ai_status === "failed" && aiReview.ai_error ? (
              <p className="managerial-ai-error">{aiReview.ai_error}</p>
            ) : null}
            <p>{aiReview.executive_summary}</p>
            <div className="managerial-ai-grid">
              <article>
                <span>O que mudou</span>
                <strong>{aiReview.what_changed}</strong>
              </article>
              <article>
                <span>Impacto gerencial</span>
                <strong>{aiReview.managerial_impact}</strong>
              </article>
            </div>
            {aiReview.likely_causes.length ? (
              <div className="managerial-ai-list">
                <strong>Causas provaveis</strong>
                {aiReview.likely_causes.slice(0, 3).map((cause) => (
                  <article key={`${cause.title}-${cause.detail}`}>
                    <div>
                      <span>{cause.title}</span>
                      <small>Confianca {cause.confidence}</small>
                    </div>
                    <p>{cause.detail}</p>
                  </article>
                ))}
              </div>
            ) : null}
            <div className="managerial-ai-columns">
              <div>
                <strong>Recomendacoes</strong>
                {aiReview.recommendations.slice(0, 3).map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
              <div>
                <strong>Perguntas para investigar</strong>
                {aiReview.investigation_questions.slice(0, 3).map((item) => (
                  <p key={item}>{item}</p>
                ))}
              </div>
            </div>
          </div>
        ) : (
          <p className="managerial-ai-empty">
            Gere uma segunda leitura para transformar as evidencias calculadas em narrativa executiva.
          </p>
        )}
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
        <div className="managerial-list managerial-alert-list">
          <strong>Alertas</strong>
          {analysis.alerts.slice(0, 3).map((alert) => (
            <article key={alert}>
              <span>Alerta automatico</span>
              <p>{alert}</p>
            </article>
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
