import type { DashboardKpi } from "../../types";

export function DashboardKpiCard({ kpi }: { kpi: DashboardKpi }) {
  return (
    <article className={`dashboard-kpi tone-${kpi.tone ?? "neutral"}`}>
      <span>{kpi.label}</span>
      <strong>{kpi.value}</strong>
      <small>{kpi.detail}</small>
    </article>
  );
}
