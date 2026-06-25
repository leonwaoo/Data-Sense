import { AlertTriangle, CheckCircle2, Compass, Sparkles } from "lucide-react";
import { MonthlyAnalysisSection } from "../managerial/MonthlyAnalysisSection";
import type { UploadResponse } from "../../types";

export function OverviewSection({ dataset }: { dataset: UploadResponse }) {
  const analysis = dataset.managerial_analysis;
  const rootCause = analysis?.root_cause_analysis;
  const topContributor = rootCause?.primary_contributor?.name;
  const mainAlert = analysis?.alerts?.[0];
  const mainRecommendation = rootCause?.recommendation ?? analysis?.recommendations?.[0];
  const summary = analysis?.summary?.[0] ?? "Arquivo carregado. O DataSense esta pronto para orientar a leitura gerencial.";

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
            <Compass size={20} />
            <span>Onde olhar primeiro</span>
            <strong>{topContributor ?? "Analise geral"}</strong>
            <p>{rootCause?.title ?? "Ainda nao ha causa raiz suficiente para destacar um ponto principal."}</p>
          </article>
          <article>
            <AlertTriangle size={20} />
            <span>Ponto de atencao</span>
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
