import { BarChart3 } from "lucide-react";
import type { RootCauseAnalysis } from "../../types";

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

export function RootCauseSection({ rootCause }: { rootCause: RootCauseAnalysis | null }) {
  if (!rootCause) return null;

  const movement = rootCause.movement;
  const responsible = rootCause.responsible_month;
  const impactRanking = rootCause.dimension_impact_ranking ?? [];
  const concentrationAlerts = rootCause.concentration_alerts ?? [];
  const direction = movement.direction === "alta" ? "Subiu" : movement.direction === "queda" ? "Caiu" : "Mudou";

  return (
    <div className="root-cause-panel simple-root-cause">
      <div className="root-cause-heading">
        <div>
          <BarChart3 size={18} />
          <div>
            <strong>Causa raiz</strong>
            <span>Onde comecar a investigacao</span>
          </div>
        </div>
        <span className={`confidence-pill confidence-${rootCause.confidence}`}>Leitura {rootCause.confidence}</span>
      </div>

      <div className="root-cause-summary">
        {rootCause.summary.slice(0, 3).map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>

      <div className="root-cause-grid">
        <article>
          <span>O que aconteceu</span>
          <strong>{direction}</strong>
          <small>{formatPeriod(responsible.period)}</small>
        </article>
        <article>
          <span>Onde olhar</span>
          <strong>{rootCause.primary_contributor?.name ?? "Nao identificado"}</strong>
          <small>Principal recorte encontrado</small>
        </article>
        <article>
          <span>Decisao sugerida</span>
          <strong>Validar causa</strong>
          <small>Confirmar com a area responsavel</small>
        </article>
      </div>

      {impactRanking.length ? (
        <div className="root-cause-ranking">
          <div>
            <strong>Quem mais puxou</strong>
            <span>Lista simples dos recortes mais importantes</span>
          </div>
          <div className="impact-ranking-list">
            {impactRanking.slice(0, 5).map((item) => (
              <div className="impact-ranking-row simplified" key={`${item.dimension}-${item.name}`}>
                <span>{item.name}</span>
                <small>{item.label}</small>
                <em>{item.recurrence_flag ?? "pontual"}</em>
              </div>
            ))}
          </div>
        </div>
      ) : null}

      {concentrationAlerts.length ? (
        <div className="root-cause-alerts">
          {concentrationAlerts.slice(0, 2).map((alert) => (
            <span key={alert}>{alert}</span>
          ))}
        </div>
      ) : null}

      <footer className="root-cause-recommendation">
        <strong>Acao recomendada</strong>
        <span>{rootCause.recommendation}</span>
      </footer>
    </div>
  );
}
