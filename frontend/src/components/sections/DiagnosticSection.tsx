import { BrainCircuit } from "lucide-react";
import { ManagerialInsightsSection } from "../managerial/ManagerialInsightsSection";
import type { ManagerialAiReview, ManagerialAnalysis } from "../../types";

type DiagnosticSectionProps = {
  analysis: ManagerialAnalysis | null | undefined;
  aiReview: ManagerialAiReview | null;
  aiModel: string;
  isManagerialAiLoading: boolean;
  onManagerialAiModelChange: (model: string) => void;
  onManagerialAiReview: (model?: string) => void;
};

export function DiagnosticSection({
  analysis,
  aiReview,
  aiModel,
  isManagerialAiLoading,
  onManagerialAiModelChange,
  onManagerialAiReview,
}: DiagnosticSectionProps) {
  if (!analysis) {
    return (
      <section className="panel diagnostic-empty">
        <div>
          <BrainCircuit size={20} />
          <strong>Diagnostico gerencial indisponivel</strong>
        </div>
        <p>Envie um arquivo com indicador e periodo para liberar causa raiz, comparativos e leitura executiva.</p>
      </section>
    );
  }

  return (
    <div className="section-stack">
      <section className="panel diagnostic-strip">
        <div>
          <strong>Diagnostico gerencial</strong>
          <span>Resumo executivo, causa raiz, leituras por recorte, alertas e recomendacoes</span>
        </div>
      </section>
      <ManagerialInsightsSection
        aiReview={aiReview}
        aiModel={aiModel}
        analysis={analysis}
        isAiLoading={isManagerialAiLoading}
        onAiModelChange={onManagerialAiModelChange}
        onAiReview={onManagerialAiReview}
      />
    </div>
  );
}
