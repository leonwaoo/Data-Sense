import { AlertTriangle, CheckCircle2, Compass, Sparkles, TrendingUp } from "lucide-react";
import { MonthlyAnalysisSection } from "../managerial/MonthlyAnalysisSection";
import type { UploadResponse } from "../../types";

const monthNames = [
  "Janeiro",
  "Fevereiro",
  "Marco",
  "Abril",
  "Maio",
  "Junho",
  "Julho",
  "Agosto",
  "Setembro",
  "Outubro",
  "Novembro",
  "Dezembro",
];

function formatPeriod(period: string | null | undefined) {
  const match = /^(\d{4})-(\d{2})$/.exec(String(period ?? ""));
  if (!match) return period ?? "periodo analisado";
  const monthName = monthNames[Number(match[2]) - 1];
  return monthName ? `${match[2]} ${monthName}/${match[1]}` : period ?? "periodo analisado";
}

function directionText(direction: string | undefined) {
  if (direction === "alta") return "Subiu";
  if (direction === "queda") return "Caiu";
  return "Mudou";
}

export function OverviewSection({
  dataset,
  onApplyPeriodToDashboard,
}: {
  dataset: UploadResponse;
  onApplyPeriodToDashboard?: (period: { date_from: string; date_to: string }) => void;
}) {
  const analysis = dataset.managerial_analysis;
  const rootCause = analysis?.root_cause_analysis;
  const topContributor = rootCause?.primary_contributor?.name;
  const mainAlert = analysis?.alerts?.[0];
  const mainRecommendation = rootCause?.recommendation ?? analysis?.recommendations?.[0];
  const summary = analysis?.summary?.[0] ?? "Arquivo carregado. O DataSense esta pronto para orientar a leitura gerencial.";
  const movement = rootCause?.movement;
  const period = formatPeriod(rootCause?.period);
  const topOpportunity = analysis?.comparative_summary?.cards?.find((card) => card.tone === "good");
  const nextQuestion = analysis?.suggested_questions?.[0];
  const domainLabel = analysis?.context.domain.label ?? "Analise automatica";
  const primaryMetric = analysis?.context.metric_map.primary_metric ?? "Indicador principal";
  const timeLabel = analysis?.context.time.label ?? "Periodo nao identificado";

  return (
    <div className="section-stack">
      <section className="panel executive-home">
        <div className="executive-home-heading">
          <div>
            <Sparkles size={22} />
            <div>
              <h2>Ponto de partida para decisao</h2>
              <span>{dataset.file_name}</span>
            </div>
          </div>
        </div>

        <p className="executive-lead">{summary}</p>

        <div className="executive-context-strip">
          <span>{domainLabel}</span>
          <span>{primaryMetric}</span>
          <span>{timeLabel}</span>
          <span>Qualidade {dataset.quality.score}/100</span>
        </div>

        <div className="executive-card-grid">
          <article>
            <TrendingUp size={20} />
            <span>Principal movimento</span>
            <strong>{directionText(movement?.direction)}</strong>
            <p>O movimento principal aparece em {period}. Comece por esse ponto para explicar o resultado ao time.</p>
          </article>
          <article>
            <AlertTriangle size={20} />
            <span>Maior risco</span>
            <strong>{mainAlert ? "Validar agora" : "Sem risco critico"}</strong>
            <p>{mainAlert ?? "Nao apareceu um alerta dominante nesta primeira leitura."}</p>
          </article>
          <article>
            <Compass size={20} />
            <span>Melhor oportunidade</span>
            <strong>{topOpportunity?.label ?? topContributor ?? "Encontrar o recorte lider"}</strong>
            <p>
              {topOpportunity?.detail ??
                (topContributor
                  ? `${topContributor} apareceu como o recorte mais promissor para explicar a variacao.`
                  : "Ainda falta um recorte forte; use o diagnostico para descobrir quem puxou o movimento.")}
            </p>
          </article>
          <article>
            <CheckCircle2 size={20} />
            <span>Acao imediata</span>
            <strong>{nextQuestion ? "Levar a conversa adiante" : "Validar com a area responsavel"}</strong>
            <p>{mainRecommendation ?? nextQuestion ?? "Use o diagnostico para escolher a proxima acao com base nos dados."}</p>
          </article>
        </div>

        <div className="executive-next-steps">
          <article>
            <strong>1. Confirme o contexto</strong>
            <p>Veja se o indicador e o periodo detectados fazem sentido para a leitura que voce precisa apresentar.</p>
          </article>
          <article>
            <strong>2. Explique a variacao</strong>
            <p>Abra o diagnostico para entender causa raiz, impacto e recortes que concentraram a mudanca.</p>
          </article>
          <article>
            <strong>3. Leve para a apresentacao</strong>
            <p>Use graficos, chat e relatorios para transformar a leitura inicial em uma historia executiva consistente.</p>
          </article>
        </div>
      </section>

      {analysis ? <MonthlyAnalysisSection analysis={analysis} onApplyPeriodToDashboard={onApplyPeriodToDashboard} /> : null}
    </div>
  );
}
