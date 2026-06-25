import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumberCell, formatPercentCell, formatSignedCell } from "../../utils/format";
import type { ManagerialAnalysis, ManagerialMonthlyComparison } from "../../types";

type MonthlyChartPoint = {
  period: string;
  label: string;
  value: number;
  variation: number;
};

type MonthlyDotProps = {
  cx?: number;
  cy?: number;
  payload?: MonthlyChartPoint;
};

const monthNames = [
  "Janeiro",
  "Fevereiro",
  "Março",
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

function periodOrder(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return Number.MAX_SAFE_INTEGER;
  return Number(`${match[1]}${match[2]}`);
}

function formatMonthLabel(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return period;
  const monthNumber = Number(match[2]);
  const monthName = monthNames[monthNumber - 1];
  return monthName ? `${match[2]} ${monthName}/${match[1]}` : period;
}

function formatZScore(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? value.toFixed(2) : "-";
}

function chartPayloadPeriod(state: unknown) {
  const payload = state as { activePayload?: { payload?: MonthlyChartPoint }[] };
  return payload.activePayload?.[0]?.payload?.period;
}

export function MonthlyAnalysisSection({ analysis }: { analysis: ManagerialAnalysis }) {
  const monthlyComparisons = [...(analysis.monthly_comparisons ?? [])].sort(
    (left, right) => periodOrder(left.period) - periodOrder(right.period),
  );
  const latest = monthlyComparisons[monthlyComparisons.length - 1];
  const [selectedPeriod, setSelectedPeriod] = useState(latest?.period ?? "");

  useEffect(() => {
    if (latest?.period) {
      setSelectedPeriod(latest.period);
    }
  }, [latest?.period]);

  if (!monthlyComparisons.length || !latest) return null;

  const metric = analysis.context.metric_map.primary_metric ?? "Métrica principal";
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
    label: formatMonthLabel(item.period),
    value: item.value ?? 0,
    variation: item.variation ?? 0,
  }));
  const selectedLabel = formatMonthLabel(selectedMonth.period);
  const selectedDrivers = selectedMonth.drivers?.length
    ? selectedMonth.drivers
    : selectedMonth.main_driver
      ? [selectedMonth.main_driver]
      : [];

  function handleChartClick(state: unknown) {
    const period = chartPayloadPeriod(state);
    if (period) {
      setSelectedPeriod(period);
    }
  }

  function renderMonthlyDot(props: unknown) {
    const { cx, cy, payload } = props as MonthlyDotProps;
    if (typeof cx !== "number" || typeof cy !== "number" || !payload) {
      return <circle cx={0} cy={0} fill="transparent" r={0} />;
    }
    const selected = payload.period === selectedMonth.period;
    return (
      <circle
        className={selected ? "monthly-chart-dot is-selected" : "monthly-chart-dot"}
        cx={cx}
        cy={cy}
        fill={selected ? "#0f766e" : "#ffffff"}
        onClick={() => setSelectedPeriod(payload.period)}
        r={selected ? 6 : 3.5}
        stroke={selected ? "#0f766e" : "#0f766e"}
        strokeWidth={selected ? 3 : 2}
      />
    );
  }

  return (
    <section className="panel monthly-focus-panel">
      <div className="monthly-focus-heading">
        <div>
          <Clock size={20} />
          <div>
            <h2>Acompanhamento mês a mês</h2>
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
          <span>Mês selecionado</span>
          <strong>{formatMonthLabel(selectedMonth.period)}</strong>
          <small>{formatNumberCell(selectedMonth.value)}</small>
        </article>
        <article>
          <span>Variação mensal</span>
          <strong>{formatSignedCell(selectedMonth.variation)}</strong>
          <small>{formatPercentCell(selectedMonth.variation_pct)}</small>
        </article>
        <article>
          <span>Maior alta</span>
          <strong>{biggestIncrease ? formatMonthLabel(biggestIncrease.period) : "-"}</strong>
          <small>{formatSignedCell(biggestIncrease?.variation)}</small>
        </article>
        <article>
          <span>Maior queda</span>
          <strong>{biggestDrop ? formatMonthLabel(biggestDrop.period) : "-"}</strong>
          <small>{formatSignedCell(biggestDrop?.variation)}</small>
        </article>
      </div>

      <div className="monthly-focus-body">
        <div className="monthly-chart-card">
          <div>
            <strong>Evolução mensal</strong>
            <span>Linha simples para acompanhar tendência</span>
          </div>
          <ResponsiveContainer height={240} width="100%">
            <LineChart data={chartData} margin={{ bottom: 8, left: 0, right: 12, top: 14 }} onClick={handleChartClick}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="label" minTickGap={18} tick={{ fill: "#64748b", fontSize: 12 }} />
              <YAxis tick={{ fill: "#64748b", fontSize: 12 }} width={56} />
              <Tooltip formatter={(value) => formatNumberCell(Number(value))} labelFormatter={(label) => `Período ${label}`} />
              <ReferenceLine
                ifOverflow="extendDomain"
                stroke="#0f766e"
                strokeDasharray="4 4"
                strokeOpacity={0.7}
                x={selectedLabel}
              />
              <Line
                activeDot={{ r: 7, stroke: "#0f766e", strokeWidth: 3 }}
                dataKey="value"
                dot={renderMonthlyDot}
                name={metric}
                stroke="#0f766e"
                strokeWidth={2.5}
                type="monotone"
              />
            </LineChart>
          </ResponsiveContainer>
        </div>

        <div className="monthly-reading-card">
          <strong>Leitura de {formatMonthLabel(selectedMonth.period)}</strong>
          <p>{selectedMonth.managerial_reading}</p>
          {selectedMonth.main_driver ? <span>{selectedMonth.main_driver.reading}</span> : null}
          {abnormalMonths.length ? <small>{abnormalMonths.length} período(s) exigem atenção.</small> : <small>Nenhum período crítico nos últimos dados.</small>}
        </div>
      </div>

      <div className="monthly-detail-panel">
        <div className="monthly-detail-heading">
          <strong>Detalhes de {formatMonthLabel(selectedMonth.period)}</strong>
          <span>{selectedMonth.status}</span>
        </div>
        <div className="monthly-detail-grid">
          <article>
            <span>Valor do mês</span>
            <strong>{formatNumberCell(selectedMonth.value)}</strong>
          </article>
          <article>
            <span>Mês anterior</span>
            <strong>{formatNumberCell(selectedMonth.previous_value)}</strong>
          </article>
          <article>
            <span>Média histórica</span>
            <strong>{formatNumberCell(selectedMonth.historical_mean)}</strong>
          </article>
          <article>
            <span>Z-score</span>
            <strong>{formatZScore(selectedMonth.z_score)}</strong>
          </article>
        </div>
        {selectedDrivers.length ? (
          <div className="monthly-driver-list">
            {selectedDrivers.slice(0, 4).map((driver) => (
              <article key={`${selectedMonth.period}-${driver.driver}-${driver.column}`}>
                <div>
                  <strong>{driver.driver}</strong>
                  <span>{driver.column}</span>
                </div>
                <div>
                  <strong>{formatSignedCell(driver.variation)}</strong>
                  <span>{formatPercentCell(driver.variation_pct)}</span>
                </div>
                <p>{driver.reading}</p>
              </article>
            ))}
          </div>
        ) : null}
      </div>

      <div className="monthly-simple-table">
        <table>
          <thead>
            <tr>
              <th>Mês</th>
              <th>Valor</th>
              <th>Variação</th>
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
