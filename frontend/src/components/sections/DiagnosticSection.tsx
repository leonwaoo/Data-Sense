import { BrainCircuit } from "lucide-react";
import { ManagerialInsightsSection } from "../managerial/ManagerialInsightsSection";
import type { ManagerialAiReview, ManagerialAnalysis } from "../../types";

type DiagnosticSectionProps = {
  analysis: ManagerialAnalysis | null | undefined;
  aiReview: ManagerialAiReview | null;
  isManagerialAiLoading: boolean;
  onManagerialAiReview: () => void;
};

export function DiagnosticSection({
  analysis,
  aiReview,
  isManagerialAiLoading,
  onManagerialAiReview,
}: DiagnosticSectionProps) {
  if (!analysis) {
    return (
      <section className="panel diagnostic-empty">
        <div>
          <BrainCircuit size={20} />
          <strong>Diagnostico gerencial indisponivel</strong>
        </div>
        <p>Envie um dataset com metrica e tempo para liberar causa raiz, comparativos e leitura executiva.</p>
      </section>
    );
  }

  return (
    <div className="section-stack">
      <ManagerialInsightsSection
        aiReview={aiReview}
        analysis={analysis}
        isAiLoading={isManagerialAiLoading}
        onAiReview={onManagerialAiReview}
      />
    </div>
  );
}
