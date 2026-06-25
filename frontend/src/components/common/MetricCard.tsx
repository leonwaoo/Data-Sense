import type { ReactNode } from "react";

export function MetricCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <article className="metric-card">
      <span className="metric-card-icon">{icon}</span>
      <span className="metric-card-label">{label}</span>
      <strong>{value}</strong>
    </article>
  );
}
