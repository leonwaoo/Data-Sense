import { Clock } from "lucide-react";
import { useEffect, useState } from "react";
import { CartesianGrid, Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis } from "recharts";
import { formatNumberCell } from "../../utils/format";
import type { ManagerialAnalysis } from "../../types";

type MonthlyChartPoint = {
  period: string;
  label: string;
  value: number;
};

type MonthlyDotProps = {
  cx?: number;
  cy?: number;
  payload?: MonthlyChartPoint;
};

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
        stroke="#0f766e"
        strokeWidth={selected ? 3 : 2}
      />
    );
  }

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
          <ResponsiveContainer height={240} width="100%">
            <LineChart data={chartData} margin={{ bottom: 8, left: 0, right: 12, top: 14 }} onClick={handleChartClick}>
              <CartesianGrid stroke="#e2e8f0" strokeDasharray="3 3" />
              <XAxis dataKey="label" minTickGap={18} tick={{ fill: "#64748b", fontSize: 12 }} />
              <Tooltip formatter={(value) => formatNumberCell(Number(value))} labelFormatter={(label) => `Periodo ${label}`} />
              <ReferenceLine ifOverflow="extendDomain" stroke="#0f766e" strokeDasharray="4 4" strokeOpacity={0.75} x={selectedLabel} />
              <Line
                activeDot={{ r: 7, stroke: "#0f766e", strokeWidth: 3 }}
                dataKey="value"
                dot={renderMonthlyDot}
                name="Valor"
                stroke="#0f766e"
                strokeWidth={2.5}
                type="monotone"
              />
            </LineChart>
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
