import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ReferenceDot, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { formatNumberCell } from "../../utils/format";
import type { ManagerialAnalysis } from "../../types";

type MonthlyChartPoint = {
  period: string;
  label: string;
  value: number;
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

function movementLabel(variation: number | null | undefined) {
  if (typeof variation !== "number" || !Number.isFinite(variation) || variation === 0) return "Estavel";
  return variation > 0 ? "Subiu" : "Caiu";
}

function chartPayloadPeriod(state: unknown) {
  const payload = state as { activePayload?: { payload?: MonthlyChartPoint }[] };
  return payload.activePayload?.[0]?.payload?.period;
}

function MonthlyTooltip({ active, label, payload }: { active?: boolean; label?: string; payload?: { value?: number }[] }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="monthly-chart-tooltip">
      <span>{label}</span>
      <strong>{formatNumberCell(Number(payload[0]?.value ?? 0))}</strong>
    </div>
  );
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

  const visibleMonths = monthlyComparisons.slice(-12);
  const selectedMonth = visibleMonths.find((item) => item.period === selectedPeriod) ?? latest;
  const chartData = visibleMonths.map((item) => ({
    period: item.period,
    label: formatMonthLabel(item.period),
    value: item.value ?? 0,
  }));
  const selectedLabel = formatMonthLabel(selectedMonth.period);

  function handleChartClick(state: unknown) {
    const period = chartPayloadPeriod(state);
    if (period) setSelectedPeriod(period);
  }

  const selectedChartPoint = chartData.find((item) => item.period === selectedMonth.period);

  return (
    <section className="panel monthly-focus-panel simple-monthly-panel">
      <div className="monthly-focus-heading">
        <div>
          <Clock size={20} />
          <div>
            <h2>Mes a mes</h2>
            <span>Toque em um mes para ver a leitura daquele periodo</span>
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
            <strong>{movementLabel(item.variation)}</strong>
          </button>
        ))}
      </div>

      <div className="monthly-focus-body">
        <div className="monthly-chart-card">
          <div>
            <strong>Tendencia visual</strong>
            <span>O marcador indica o mes selecionado</span>
          </div>
          <ResponsiveContainer height={260} width="100%">
            <AreaChart data={chartData} margin={{ bottom: 6, left: 0, right: 20, top: 18 }} onClick={handleChartClick}>
              <defs>
                <linearGradient id="monthlyTrendFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#0f766e" stopOpacity={0.24} />
                  <stop offset="100%" stopColor="#0f766e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#e5e7eb" vertical={false} />
              <XAxis axisLine={false} dataKey="label" minTickGap={18} tick={{ fill: "#64748b", fontSize: 12 }} tickLine={false} />
              <YAxis axisLine={false} tick={{ fill: "#64748b", fontSize: 11 }} tickFormatter={(value) => formatNumberCell(Number(value))} tickLine={false} width={46} />
              <Tooltip content={<MonthlyTooltip />} cursor={{ stroke: "#0f766e", strokeOpacity: 0.25 }} />
              <ReferenceLine ifOverflow="extendDomain" stroke="#0f766e" strokeDasharray="4 4" strokeOpacity={0.75} x={selectedLabel} />
              <Area
                activeDot={{ fill: "#0f766e", r: 7, stroke: "#fff", strokeWidth: 3 }}
                dataKey="value"
                fill="url(#monthlyTrendFill)"
                name="Valor"
                stroke="#0f766e"
                strokeWidth={3}
                type="monotone"
              />
              {selectedChartPoint ? (
                <ReferenceDot
                  className="monthly-chart-dot is-selected"
                  fill="#0f766e"
                  r={6}
                  stroke="#fff"
                  strokeWidth={3}
                  x={selectedChartPoint.label}
                  y={selectedChartPoint.value}
                />
              ) : null}
            </AreaChart>
          </ResponsiveContainer>
        </div>

        <div className="monthly-reading-card">
          <strong>{formatMonthLabel(selectedMonth.period)}</strong>
          <span>{movementLabel(selectedMonth.variation)}</span>
          <p>{selectedMonth.managerial_reading}</p>
          {selectedMonth.main_driver ? <small>{selectedMonth.main_driver.reading}</small> : null}
        </div>
      </div>
    </section>
  );
}
