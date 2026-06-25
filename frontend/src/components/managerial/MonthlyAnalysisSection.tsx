import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumberCell, formatPercentCell, formatSignedCell } from "../../utils/format";
import type { ManagerialAnalysis, ManagerialMonthlyComparison } from "../../types";

const monthNames = [
  "janeiro",
  "fevereiro",
  "marco",
  "abril",
  "maio",
  "junho",
  "julho",
  "agosto",
  "setembro",
  "outubro",
  "novembro",
  "dezembro",
];

function formatMonthLabel(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return period;
  const monthNumber = Number(match[2]);
  const monthName = monthNames[monthNumber - 1];
  return monthName ? `${match[2]} ${monthName}` : period;
}

export function MonthlyAnalysisSection({ analysis }: { analysis: ManagerialAnalysis }) {
  const monthlyComparisons = analysis.monthly_comparisons ?? [];
  const latest = monthlyComparisons[monthlyComparisons.length - 1];
  const [selectedPeriod, setSelectedPeriod] = useState(latest?.period ?? "");

  useEffect(() => {
    if (latest?.period) {
      setSelectedPeriod(latest.period);
    }
  }, [latest?.period]);

  if (!monthlyComparisons.length || !latest) return null;

  const metric = analysis.context.metric_map.primary_metric ?? "Metrica principal";
  const visibleMonths = monthlyComparisons.slice(-12);
  const selectedMonth = visibleMonths.find((item) => item.period === selectedPeriod) ?? latest;
  const movements = monthlyComparisons.filter((item) => typeof item.variation === "number" && Number.isFinite(item.variation));
  const biggestIncrease = movements.reduce<ManagerialMonthlyComparison | null>(
    (best, item) => (!best || (item.variation ?? 0) > (best.variation ?? 0) ? item : best),
    null,
  );
  const biggestDrop = movements.reduce<ManagerialMonthlyComparison | null>(
    (worst, item) => (!worst || (item.variation ?? 0) < (worst.variation ?? 0) ? item : worst),
    null,
  );
  const abnormalMonths = monthlyComparisons.filter((item) => item.status === "Fora do padrao" || item.severity === "danger");
  const chartData = visibleMonths.map((item) => ({
    period: item.period,
    value: item.value ?? 0,
    variation: item.variation ?? 0,
  }));

  return (
    <section className="panel monthly-focus-panel">
      <div className="monthly-focus-heading">
        <div>
          <Clock size={20} />
          <div>
            <h2>Acompanhamento mes a mes</h2>
            <span>{metric} - foco em {formatMonthLabel(selectedMonth.period)}</span>
          </div>
        </div>
        <span className={`monthly-status severity-${selectedMonth.severity}`}>{selectedMonth.status}</span>
      </div>

      <div className="monthly-selector" aria-label="Selecionar mes para analise">
        {visibleMonths.map((item) => (
          <button
            className={item.period === selectedMonth.period ? "is-selected" : ""}
            key={item.period}
            onClick={() => setSelectedPeriod(item.period)}
            type="button"
          >
            <span>{formatMonthLabel(item.period)}</span>
            <strong>{formatSignedCell(item.variation)}</strong>
          </button>
        ))}
      </div>

      <div className="monthly-focus-kpis">
        <article>
          <span>Mes selecionado</span>
          <strong>{formatMonthLabel(selectedMonth.period)}</strong>
          <small>{formatNumberCell(selectedMonth.value)}</small>
        </article>
        <article>
          <span>Variacao mensal</span>
          <strong>{formatSignedCell(selectedMonth.variation)}</strong>
          <small>{formatPercentCell(selectedMonth.variation_pct)}</small>
        </article>
        <article>
          <span>Maior alta</span>
          <strong>{biggestIncrease?.period ?? "-"}</strong>
          <small>{formatSignedCell(biggestIncrease?.variation)}</small>
        </article>
        <article>
          <span>Maior queda</span>
          <strong>{biggestDrop?.period ?? "-"}</strong>
          <small>{formatSignedCell(biggestDrop?.variation)}</small>
        </article>
      </div>

      <div className="monthly-focus-body">
        <div className="monthly-chart-card">
          <div>
            <strong>Evolucao mensal</strong>
            <span>linha simples para acompanhar tendencia</span>
          </div>
          <ResponsiveContainer height={240} width="100%">
            <LineChart data={chartData} margin={{ bottom: 8, left: 0, right: 12, top: 14 }}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="period" minTickGap={18} tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} width={56} />
              <Tooltip formatter={(value) => formatNumberCell(Number(value))} labelFormatter={(label) => `Periodo ${label}`} />
              <Line dataKey="value" dot={{ r: 3 }} name={metric} stroke="#0f766e" strokeWidth={2.5} type="monotone" />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="monthly-reading-card">
          <strong>Leitura de {formatMonthLabel(selectedMonth.period)}</strong>
          <p>{selectedMonth.managerial_reading}</p>
          {selectedMonth.main_driver ? <span>{selectedMonth.main_driver.reading}</span> : null}
          {abnormalMonths.length ? <small>{abnormalMonths.length} periodo(s) exigem atencao.</small> : <small>Nenhum periodo critico nos ultimos dados.</small>}
        </div>
      </div>

      <div className="monthly-simple-table">
        <table>
          <thead>
            <tr>
              <th>Mes</th>
              <th>Valor</th>
              <th>Variacao</th>
              <th>%</th>
              <th>Status</th>
              <th>Leitura</th>
            </tr>
          </thead>
          <tbody>
            {visibleMonths.map((item) => (
              <tr
                className={item.period === selectedMonth.period ? "is-selected" : ""}
                key={item.period}
                onClick={() => setSelectedPeriod(item.period)}
              >
                <td>{formatMonthLabel(item.period)}</td>
                <td>{formatNumberCell(item.value)}</td>
                <td>{formatSignedCell(item.variation)}</td>
                <td>{formatPercentCell(item.variation_pct)}</td>
                <td>
                  <span className={`monthly-status severity-${item.severity}`}>{item.status}</span>
                </td>
                <td>{item.managerial_reading}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
