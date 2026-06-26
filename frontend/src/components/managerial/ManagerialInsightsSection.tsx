import { BrainCircuit, Sparkles, TrendingUp } from "lucide-react";
import { RootCauseSection } from "./RootCauseSection";
import type { ManagerialAiReview, ManagerialAnalysis } from "../../types";

type ManagerialInsightsSectionProps = {
  analysis: ManagerialAnalysis;
  aiReview: ManagerialAiReview | null;
  aiModel: string;
  isAiLoading: boolean;
  onAiModelChange: (model: string) => void;
  onAiReview: (model?: string) => void;
};

export function ManagerialInsightsSection({
  analysis,
  aiReview,
  aiModel,
  isAiLoading,
  onAiModelChange,
  onAiReview,
}: ManagerialInsightsSectionProps) {
  const rootCause = analysis.root_cause_analysis ?? null;
  const dimensionNarratives = analysis.dimension_narratives ?? rootCause?.dimension_narratives ?? [];
  const comparativeCards = analysis.comparative_summary?.cards ?? [];
  const comparativeReadings = analysis.comparative_summary?.readings ?? [];
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
            <h2>Diagnostico para decisao</h2>
            <span>{analysis.context.domain.label}</span>
          </div>
        </div>
        <span className="domain-pill">{analysis.context.domain.label}</span>
      </div>

      <div className="managerial-summary">
        <div className="managerial-section-heading">
          <strong>Resumo executivo</strong>
          <span>Visao inicial da mudanca mais relevante</span>
        </div>
        {analysis.summary.slice(0, 4).map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>

      {comparativeCards.length || comparativeReadings.length ? (
        <div className="managerial-comparative-panel">
          <div className="managerial-section-heading">
            <strong>Comparativos gerenciais</strong>
            <span>Mes contra mes, acumulado, media movel e pontos fora do padrao</span>
          </div>
          {comparativeCards.length ? (
            <div className="managerial-comparative-cards">
              {comparativeCards.slice(0, 4).map((card) => (
                <article className={`comparison-tone-${card.tone ?? "neutral"}`} key={`${card.label}-${card.value}`}>
                  <span>{card.label}</span>
                  <strong>{card.value}</strong>
                  <small>{card.detail}</small>
                </article>
              ))}
            </div>
          ) : null}
          {comparativeReadings.length ? (
            <div className="managerial-comparative-readings">
              {comparativeReadings.slice(0, 3).map((reading) => (
                <p key={reading}>{reading}</p>
              ))}
            </div>
          ) : null}
        </div>
      ) : null}

      <div className="managerial-ai-panel">
        <div className="managerial-ai-heading">
          <div>
            <BrainCircuit size={20} />
            <div>
              <strong>Leitura executiva</strong>
              <span>{aiStatusLabel}</span>
            </div>
          </div>
          <div className="managerial-ai-actions">
            <label className="managerial-model-field">
              <span>Modelo OpenRouter</span>
              <input
                list="managerial-ai-models"
                placeholder="openai/gpt-4o-mini"
                value={aiModel}
                onChange={(event) => onAiModelChange(event.target.value)}
              />
            </label>
            <datalist id="managerial-ai-models">
              <option value="openai/gpt-4o-mini" />
              <option value="openai/gpt-4o" />
              <option value="anthropic/claude-3.5-sonnet" />
              <option value="google/gemini-2.0-flash-001" />
              <option value="meta-llama/llama-3.1-70b-instruct" />
            </datalist>
            <button disabled={isAiLoading} onClick={() => onAiReview(aiModel)} type="button">
              <Sparkles size={15} />
              {isAiLoading ? "Analisando..." : aiReview ? "Atualizar leitura" : "Gerar leitura"}
            </button>
          </div>
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
            Gere uma segunda leitura para transformar os sinais encontrados em uma explicacao executiva.
          </p>
        )}
      </div>

      <RootCauseSection rootCause={rootCause} />

      {dimensionNarratives.length ? (
        <div className="dimension-narratives-panel">
          <div className="dimension-narratives-heading">
            <div>
              <strong>Leituras por dimensao</strong>
              <span>Onde mudou, quem puxou e o que merece validacao gerencial</span>
            </div>
          </div>
          <div className="dimension-narratives-grid">
            {dimensionNarratives.slice(0, 4).map((item) => (
              <article className="dimension-narrative-card" key={item.dimension}>
                <div>
                  <strong>{item.label}</strong>
                  <span>{item.priority?.level ?? item.share_concentration.level} prioridade</span>
                </div>
                <p>{item.narrative}</p>
                <small>{item.managerial_impact}</small>
                {item.priority?.reason ? <small>{item.priority.reason}</small> : null}
                <div className="dimension-narrative-movers">
                  {(item.top_movers ?? []).slice(0, 3).map((mover) => (
                    <span key={`${item.dimension}-${mover.name}`}>{mover.name}</span>
                  ))}
                </div>
                {(item.top_movers?.[0]?.context ?? []).length ? (
                  <div className="dimension-narrative-context">
                    {(item.top_movers?.[0]?.context ?? []).slice(0, 3).map((context) => (
                      <span key={`${item.dimension}-${context.dimension}-${context.name}`}>
                        {context.dimension}: <strong>{context.name}</strong>
                      </span>
                    ))}
                  </div>
                ) : null}
                {(item.validation_questions ?? []).length ? (
                  <div className="dimension-narrative-questions">
                    {(item.validation_questions ?? []).slice(0, 2).map((question) => (
                      <p key={`${item.dimension}-${question}`}>{question}</p>
                    ))}
                  </div>
                ) : null}
                {(item.action_checklist ?? []).length ? (
                  <ul className="dimension-narrative-actions">
                    {(item.action_checklist ?? []).slice(0, 3).map((action) => (
                      <li key={`${item.dimension}-${action}`}>{action}</li>
                    ))}
                  </ul>
                ) : null}
                {item.recommendation ? <footer>{item.recommendation}</footer> : null}
              </article>
            ))}
          </div>
        </div>
      ) : null}

      <div className="managerial-bottom-grid">
        <div className="managerial-list managerial-alert-list">
          <strong>Pontos de atencao</strong>
          {analysis.alerts.slice(0, 3).map((alert) => (
            <article key={alert}>
              <span>Validar</span>
              <p>{alert}</p>
            </article>
          ))}
        </div>
        <div className="managerial-list">
          <strong>O que fazer agora</strong>
          {analysis.recommendations.slice(0, 3).map((recommendation) => (
            <p key={recommendation}>{recommendation}</p>
          ))}
        </div>
        <div className="managerial-list">
          <strong>Perguntas para a equipe</strong>
          {analysis.suggested_questions.slice(0, 4).map((question) => (
            <p key={question}>{question}</p>
          ))}
        </div>
      </div>
    </section>
  );
}
