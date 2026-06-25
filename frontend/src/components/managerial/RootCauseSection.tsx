import { BarChart3 } from "lucide-react";
import { WaterfallMiniChart } from "./WaterfallMiniChart";
import { formatPercentCell, formatSignedCell } from "../../utils/format";
import type { RootCauseAnalysis } from "../../types";

export function RootCauseSection({ rootCause }: { rootCause: RootCauseAnalysis | null }) {
  if (!rootCause) return null;

  const primaryDimension = rootCause.dimension_drivers.find((item) => item.contributors.length > 0);
  const contributors = primaryDimension?.contributors ?? [];
  const movement = rootCause.movement;
  const responsible = rootCause.responsible_month;

  return (
    <div className="root-cause-panel">
      <div className="root-cause-heading">
        <div>
          <BarChart3 size={18} />
          <div>
            <strong>{rootCause.title}</strong>
            <span>
              {rootCause.metric} - {rootCause.previous_period ?? "periodo anterior"} para {rootCause.period}
            </span>
          </div>
        </div>
        <span className={`confidence-pill confidence-${rootCause.confidence}`}>Confianca {rootCause.confidence}</span>
      </div>

      <div className="root-cause-summary">
        {rootCause.summary.slice(0, 4).map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>

      <div className="root-cause-grid">
        <article>
          <span>O que mudou</span>
          <strong>{formatSignedCell(movement.variation)}</strong>
          <small>{formatPercentCell(movement.variation_pct)} contra o periodo anterior</small>
        </article>
        <article>
          <span>Mes responsavel</span>
          <strong>{responsible.period}</strong>
          <small>{formatSignedCell(responsible.historical_delta)} contra a media historica</small>
        </article>
        <article>
          <span>Quem puxou</span>
          <strong>{rootCause.primary_contributor?.name ?? "Nao identificado"}</strong>
          <small>{formatSignedCell(rootCause.primary_contributor?.variation)} de contribuicao</small>
        </article>
      </div>

      <div className="root-cause-detail-grid">
        <div className="root-cause-list">
          <div>
            <strong>{primaryDimension?.label ?? "Contribuintes"}</strong>
            <span>{contributors.length ? "Maiores impactos na variacao" : "Sem recorte suficiente"}</span>
          </div>
          {contributors.slice(0, 5).map((contributor) => (
            <div className="contributor-row" key={`${primaryDimension?.dimension}-${contributor.name}`}>
              <span>{contributor.name}</span>
              <strong>{formatSignedCell(contributor.variation)}</strong>
              <small>{formatPercentCell(contributor.share_of_abs_change)}</small>
            </div>
          ))}
        </div>

        <WaterfallMiniChart steps={rootCause.waterfall.steps} />
      </div>

      <footer className="root-cause-recommendation">
        <strong>Acao recomendada</strong>
        <span>{rootCause.recommendation}</span>
      </footer>
    </div>
  );
}
