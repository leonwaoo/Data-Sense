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

export function OverviewSection({ dataset }: { dataset: UploadResponse }) {
  const analysis = dataset.managerial_analysis;
  const rootCause = analysis?.root_cause_analysis;
  const topContributor = rootCause?.primary_contributor?.name;
  const mainAlert = analysis?.alerts?.[0];
  const mainRecommendation = rootCause?.recommendation ?? analysis?.recommendations?.[0];
  const summary = analysis?.summary?.[0] ?? "Arquivo carregado. O DataSense esta pronto para orientar a leitura gerencial.";
  const movement = rootCause?.movement;
  const period = formatPeriod(rootCause?.period);

  return (
    <div className="section-stack">
      <section className="panel executive-home">
        <div className="executive-home-heading">
          <div>
            <Sparkles size={22} />
            <div>
              <h2>Leitura para gestor</h2>
              <span>{dataset.file_name}</span>
            </div>
          </div>
        </div>

        <p className="executive-lead">{summary}</p>

        <div className="executive-card-grid">
          <article>
            <TrendingUp size={20} />
            <span>O que aconteceu</span>
            <strong>{directionText(movement?.direction)}</strong>
            <p>O movimento principal aparece em {period}. Use este mes como ponto de partida da leitura.</p>
          </article>
          <article>
            <Compass size={20} />
            <span>Onde olhar primeiro</span>
            <strong>{topContributor ?? "Analise geral"}</strong>
            <p>{topContributor ? "Este foi o recorte que mais apareceu como ponto de investigacao." : "Ainda nao ha um recorte unico para priorizar."}</p>
          </article>
          <article>
            <AlertTriangle size={20} />
            <span>Por que importa</span>
            <strong>{mainAlert ? "Requer validacao" : "Sem alerta critico"}</strong>
            <p>{mainAlert ?? "Nao encontramos um alerta prioritario nesta primeira leitura."}</p>
          </article>
          <article>
            <CheckCircle2 size={20} />
            <span>Proxima acao</span>
            <strong>Validar com a area responsavel</strong>
            <p>{mainRecommendation ?? "Use o diagnostico para escolher uma acao pratica a partir dos dados."}</p>
          </article>
        </div>
      </section>

      {analysis ? <MonthlyAnalysisSection analysis={analysis} /> : null}
    </div>
  );
}
