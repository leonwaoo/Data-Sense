import { ArrowRight, CalendarRange, Clock, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import {
  Area,
  AreaChart,
  CartesianGrid,
  Legend,
  Line,
  ReferenceDot,
  ReferenceLine,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { formatNumberCell } from "../../utils/format";
import type { ManagerialAnalysis } from "../../types";

type MonthlyAnalysisSectionProps = {
  analysis: ManagerialAnalysis;
  onApplyPeriodToDashboard?: (period: { date_from: string; date_to: string }) => void;
};

type MonthlyChartPoint = {
  period: string;
  label: string;
  value: number;
  previousYearValue: number | null;
  movingAverage: number | null;
};

type MonthOption = {
  value: string;
  label: string;
  order: number;
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

function yearFromPeriod(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  return match ? match[1] : null;
}

function monthFromPeriod(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  return match ? match[2] : null;
}

function monthOrder(period: string) {
  const month = monthFromPeriod(period);
  return month ? Number(month) : Number.MAX_SAFE_INTEGER;
}

function formatMonthLabel(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return period;
  const monthNumber = Number(match[2]);
  const monthName = monthNames[monthNumber - 1];
  return monthName ? `${match[2]} ${monthName}/${match[1]}` : period;
}

function formatMonthShort(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return period;
  const monthNumber = Number(match[2]);
  const monthName = monthNames[monthNumber - 1];
  return monthName ? `${match[2]} ${monthName.slice(0, 3)}` : period;
}

function movementLabel(variation: number | null | undefined) {
  if (typeof variation !== "number" || !Number.isFinite(variation) || variation === 0) return "Estavel";
  return variation > 0 ? "Subiu" : "Caiu";
}

function differenceLabel(value: number | null | undefined, previousValue: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value) || typeof previousValue !== "number" || !Number.isFinite(previousValue)) {
    return "Sem base anterior";
  }
  const difference = value - previousValue;
  if (difference === 0) return "Sem diferenca";
  const prefix = difference > 0 ? "+" : "-";
  return `${prefix}${formatNumberCell(Math.abs(difference))} vs mes anterior`;
}

function percentageLabel(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "n/d";
  return `${value >= 0 ? "+" : ""}${(value * 100).toFixed(1).replace(".", ",")}%`;
}

function compareLabel(current: number | null | undefined, previous: number | null | undefined) {
  if (typeof current !== "number" || !Number.isFinite(current) || typeof previous !== "number" || !Number.isFinite(previous)) {
    return "Sem ano anterior equivalente";
  }
  const difference = current - previous;
  const pct = previous ? difference / Math.abs(previous) : null;
  return `${difference >= 0 ? "+" : "-"}${formatNumberCell(Math.abs(difference))} (${percentageLabel(pct)})`;
}

function movingAverage(items: { value: number | null }[], index: number, windowSize = 3) {
  const start = Math.max(0, index - windowSize + 1);
  const values = items.slice(start, index + 1).map((item) => item.value).filter((item): item is number => typeof item === "number");
  if (!values.length) return null;
  return values.reduce((sum, value) => sum + value, 0) / values.length;
}

function chartPayloadPeriod(state: unknown) {
  const payload = state as { activePayload?: { payload?: MonthlyChartPoint }[] };
  return payload.activePayload?.[0]?.payload?.period;
}

function monthOptions(periods: string[]) {
  return periods
    .sort((left, right) => monthOrder(left) - monthOrder(right))
    .map((period) => ({
      value: period,
      label: formatMonthShort(period),
      order: monthOrder(period),
    }));
}

function monthRangeFromPeriod(period: string) {
  const match = /^(\d{4})-(\d{2})$/.exec(period);
  if (!match) return null;
  const year = Number(match[1]);
  const month = Number(match[2]);
  const lastDay = new Date(year, month, 0).getDate();
  return {
    date_from: `${match[1]}-${match[2]}-01`,
    date_to: `${match[1]}-${match[2]}-${String(lastDay).padStart(2, "0")}`,
  };
}

function periodRangeFromMonths(startPeriod: string, endPeriod: string) {
  const start = monthRangeFromPeriod(startPeriod);
  const end = monthRangeFromPeriod(endPeriod);
  if (!start || !end) return null;
  return { date_from: start.date_from, date_to: end.date_to };
}

function MonthlyTooltip({
  active,
  label,
  payload,
}: {
  active?: boolean;
  label?: string;
  payload?: { dataKey?: string; value?: number; color?: string }[];
}) {
  if (!active || !payload?.length) return null;
  return (
    <div className="monthly-chart-tooltip">
      <span>{label}</span>
      {payload.map((item) => (
        <strong key={`${item.dataKey}-${item.value}`} style={{ color: item.color ?? "#fff" }}>
          {item.dataKey === "value" ? "Ano atual" : item.dataKey === "previousYearValue" ? "Ano anterior" : "Media movel"}:{" "}
          {formatNumberCell(Number(item.value ?? 0))}
        </strong>
      ))}
    </div>
  );
}

export function MonthlyAnalysisSection({ analysis, onApplyPeriodToDashboard }: MonthlyAnalysisSectionProps) {
  const monthlyComparisons = useMemo(
    () => [...(analysis.monthly_comparisons ?? [])].sort((left, right) => periodOrder(left.period) - periodOrder(right.period)),
    [analysis.monthly_comparisons],
  );
  const latest = monthlyComparisons[monthlyComparisons.length - 1];
  const availableYears = Array.from(
    new Set(monthlyComparisons.map((item) => yearFromPeriod(item.period)).filter((item): item is string => Boolean(item))),
  ).sort((left, right) => Number(right) - Number(left));
  const latestYear = latest ? yearFromPeriod(latest.period) ?? "" : "";
  const [selectedYear, setSelectedYear] = useState(latestYear);
  const [selectedPeriod, setSelectedPeriod] = useState(latest?.period ?? "");
  const [rangeStart, setRangeStart] = useState(latest?.period ?? "");
  const [rangeEnd, setRangeEnd] = useState(latest?.period ?? "");

  useEffect(() => {
    if (!latest?.period || !latestYear) return;
    setSelectedYear(latestYear);
    setSelectedPeriod(latest.period);
  }, [latest?.period, latestYear]);

  const yearMonths = useMemo(
    () => monthlyComparisons.filter((item) => yearFromPeriod(item.period) === selectedYear).sort((left, right) => monthOrder(left.period) - monthOrder(right.period)),
    [monthlyComparisons, selectedYear],
  );

  const monthSelectOptions = useMemo(() => monthOptions(yearMonths.map((item) => item.period)), [yearMonths]);

  useEffect(() => {
    if (!yearMonths.length) return;
    const first = yearMonths[0].period;
    const last = yearMonths[yearMonths.length - 1].period;
    setRangeStart((current) => (yearMonths.some((item) => item.period === current) ? current : first));
    setRangeEnd((current) => (yearMonths.some((item) => item.period === current) ? current : last));
    setSelectedPeriod((current) => (yearMonths.some((item) => item.period === current) ? current : last));
  }, [yearMonths]);

  if (!monthlyComparisons.length || !latest || !yearMonths.length) return null;

  const startOption = monthSelectOptions.find((item) => item.value === rangeStart) ?? monthSelectOptions[0];
  const endOption = monthSelectOptions.find((item) => item.value === rangeEnd) ?? monthSelectOptions[monthSelectOptions.length - 1];
  const startOrder = Math.min(startOption.order, endOption.order);
  const endOrder = Math.max(startOption.order, endOption.order);

  const visibleMonths = yearMonths.filter((item) => {
    const order = monthOrder(item.period);
    return order >= startOrder && order <= endOrder;
  });

  const fallbackMonth = visibleMonths[visibleMonths.length - 1] ?? yearMonths[yearMonths.length - 1] ?? latest;
  const selectedMonth = visibleMonths.find((item) => item.period === selectedPeriod) ?? fallbackMonth;
  const previousYear = String(Number(selectedYear) - 1);
  const previousYearMap = new Map(
    monthlyComparisons
      .filter((item) => yearFromPeriod(item.period) === previousYear)
      .map((item) => [monthFromPeriod(item.period), item.value ?? null]),
  );

  const chartData: MonthlyChartPoint[] = visibleMonths.map((item, index) => ({
    period: item.period,
    label: formatMonthShort(item.period),
    value: item.value ?? 0,
    previousYearValue: previousYearMap.get(monthFromPeriod(item.period)) ?? null,
    movingAverage: movingAverage(visibleMonths, index),
  }));

  const selectedLabel = formatMonthShort(selectedMonth.period);
  const selectedChartPoint = chartData.find((item) => item.period === selectedMonth.period);
  const selectedMonthPreviousYear = previousYearMap.get(monthFromPeriod(selectedMonth.period)) ?? null;

  const totalPeriod = visibleMonths.reduce((sum, item) => sum + (item.value ?? 0), 0);
  const averagePeriod = visibleMonths.length ? totalPeriod / visibleMonths.length : 0;
  const bestMonth = [...visibleMonths].sort((left, right) => (right.value ?? 0) - (left.value ?? 0))[0] ?? null;
  const worstMonth = [...visibleMonths].sort((left, right) => (left.value ?? 0) - (right.value ?? 0))[0] ?? null;
  const biggestRise = [...visibleMonths]
    .filter((item) => typeof item.variation === "number")
    .sort((left, right) => (right.variation ?? 0) - (left.variation ?? 0))[0] ?? null;
  const biggestDrop = [...visibleMonths]
    .filter((item) => typeof item.variation === "number")
    .sort((left, right) => (left.variation ?? 0) - (right.variation ?? 0))[0] ?? null;
  const previousYearTotal = visibleMonths.reduce((sum, item) => sum + (previousYearMap.get(monthFromPeriod(item.period)) ?? 0), 0);
  const hasComparablePreviousYear = visibleMonths.some((item) => previousYearMap.get(monthFromPeriod(item.period)) != null);
  const ytdDelta = hasComparablePreviousYear ? totalPeriod - previousYearTotal : null;
  const ytdPct = hasComparablePreviousYear && previousYearTotal ? ytdDelta! / Math.abs(previousYearTotal) : null;
  const periodRange = periodRangeFromMonths(visibleMonths[0].period, visibleMonths[visibleMonths.length - 1].period);

  function handleYearChange(year: string) {
    setSelectedYear(year);
  }

  function handleChartClick(state: unknown) {
    const period = chartPayloadPeriod(state);
    if (period) setSelectedPeriod(period);
  }

  return (
    <section className="panel monthly-focus-panel simple-monthly-panel">
      <div className="monthly-focus-heading">
        <div>
          <Clock size={20} />
          <div>
            <h2>Leitura por periodo</h2>
            <span>Acompanhe meses, compare anos e leve o recorte direto para o dashboard</span>
          </div>
        </div>
        <span className={`monthly-status severity-${selectedMonth.severity}`}>{selectedMonth.status}</span>
      </div>

      <div className="monthly-control-bar">
        <div className="monthly-year-selector" aria-label="Selecionar ano">
          {availableYears.map((year) => (
            <button
              className={year === selectedYear ? "is-selected" : ""}
              key={year}
              onClick={() => handleYearChange(year)}
              type="button"
            >
              {year}
            </button>
          ))}
        </div>

        <div className="monthly-range-selector">
          <label>
            <span>Inicio</span>
            <select value={rangeStart} onChange={(event) => setRangeStart(event.target.value)}>
              {monthSelectOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          <label>
            <span>Fim</span>
            <select value={rangeEnd} onChange={(event) => setRangeEnd(event.target.value)}>
              {monthSelectOptions.map((option) => (
                <option key={option.value} value={option.value}>
                  {option.label}
                </option>
              ))}
            </select>
          </label>
          {periodRange && onApplyPeriodToDashboard ? (
            <button className="monthly-apply-button" onClick={() => onApplyPeriodToDashboard(periodRange)} type="button">
              <CalendarRange size={16} />
              Aplicar no dashboard
            </button>
          ) : null}
        </div>
      </div>

      <div className="monthly-summary-grid">
        <article>
          <span>Total do periodo</span>
          <strong>{formatNumberCell(totalPeriod)}</strong>
          <small>{formatMonthShort(visibleMonths[0].period)} ate {formatMonthShort(visibleMonths[visibleMonths.length - 1].period)}</small>
        </article>
        <article>
          <span>Media mensal</span>
          <strong>{formatNumberCell(averagePeriod)}</strong>
          <small>{visibleMonths.length} mes(es) no recorte</small>
        </article>
        <article>
          <span>Acumulado do ano</span>
          <strong>{percentageLabel(ytdPct)}</strong>
          <small>{hasComparablePreviousYear ? compareLabel(totalPeriod, previousYearTotal) : "Sem comparacao anual"}</small>
        </article>
        <article>
          <span>Melhor vs pior mes</span>
          <strong>{bestMonth ? formatMonthShort(bestMonth.period) : "n/d"}</strong>
          <small>{bestMonth && worstMonth ? `${formatNumberCell(bestMonth.value ?? 0)} contra ${formatMonthShort(worstMonth.period)}` : "n/d"}</small>
        </article>
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
        <div className="monthly-chart-card monthly-chart-card-compare">
          <div>
            <strong>Comparativo do ano</strong>
            <span>Area do ano selecionado, linha do ano anterior e media movel de 3 meses</span>
          </div>
          <ResponsiveContainer height={310} width="100%">
            <AreaChart data={chartData} margin={{ bottom: 8, left: 0, right: 20, top: 18 }} onClick={handleChartClick}>
              <defs>
                <linearGradient id="monthlyTrendFill" x1="0" x2="0" y1="0" y2="1">
                  <stop offset="0%" stopColor="#0f766e" stopOpacity={0.26} />
                  <stop offset="100%" stopColor="#0f766e" stopOpacity={0.02} />
                </linearGradient>
              </defs>
              <CartesianGrid stroke="#d7dee9" strokeDasharray="3 3" vertical={false} />
              <XAxis axisLine={false} dataKey="label" tick={{ fill: "#5b657a", fontSize: 12, fontWeight: 700 }} tickLine={false} />
              <YAxis axisLine={false} tick={{ fill: "#5b657a", fontSize: 11 }} tickFormatter={(value) => formatNumberCell(Number(value))} tickLine={false} width={48} />
              <Tooltip content={<MonthlyTooltip />} cursor={{ stroke: "#0f766e", strokeOpacity: 0.2 }} />
              <Legend />
              <ReferenceLine ifOverflow="extendDomain" stroke="#0f766e" strokeDasharray="4 4" strokeOpacity={0.7} x={selectedLabel} />
              <Area
                activeDot={{ fill: "#0f766e", r: 7, stroke: "#fff", strokeWidth: 3 }}
                dataKey="value"
                fill="url(#monthlyTrendFill)"
                name={selectedYear}
                stroke="#0f766e"
                strokeWidth={3}
                type="monotone"
              />
              <Line dataKey="previousYearValue" dot={false} name={previousYear} stroke="#e17c29" strokeDasharray="6 6" strokeWidth={2.5} type="monotone" />
              <Line dataKey="movingAverage" dot={false} name="Media movel 3m" stroke="#334155" strokeWidth={2} type="monotone" />
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
          <div className="monthly-reading-metrics">
            <article>
              <small>Valor do mes</small>
              <strong>{formatNumberCell(selectedMonth.value ?? 0)}</strong>
            </article>
            <article>
              <small>Diferenca mensal</small>
              <strong>{differenceLabel(selectedMonth.value, selectedMonth.previous_value)}</strong>
            </article>
            <article>
              <small>Variacao %</small>
              <strong>{percentageLabel(selectedMonth.variation_pct)}</strong>
            </article>
            <article>
              <small>Mesmo mes do ano anterior</small>
              <strong>{compareLabel(selectedMonth.value, selectedMonthPreviousYear)}</strong>
            </article>
          </div>
          <p>{selectedMonth.managerial_reading}</p>
          {selectedMonth.main_driver ? <small>{selectedMonth.main_driver.reading}</small> : null}
        </div>
      </div>

      <div className="monthly-insights-grid">
        <article>
          <div>
            <TrendingUp size={18} />
            <strong>Resumo automatico</strong>
          </div>
          <p>
            Em {selectedYear}, o recorte de {formatMonthShort(visibleMonths[0].period)} a {formatMonthShort(visibleMonths[visibleMonths.length - 1].period)}{" "}
            somou {formatNumberCell(totalPeriod)} com media de {formatNumberCell(averagePeriod)} por mes.
          </p>
        </article>
        <article>
          <div>
            <ArrowRight size={18} />
            <strong>Picos e vales</strong>
          </div>
          <p>
            Melhor mes: {bestMonth ? `${formatMonthLabel(bestMonth.period)} (${formatNumberCell(bestMonth.value ?? 0)})` : "n/d"}. Pior mes:{" "}
            {worstMonth ? `${formatMonthLabel(worstMonth.period)} (${formatNumberCell(worstMonth.value ?? 0)})` : "n/d"}.
          </p>
        </article>
        <article>
          <div>
            <CalendarRange size={18} />
            <strong>Movimentos extremos</strong>
          </div>
          <p>
            Maior alta: {biggestRise ? `${formatMonthLabel(biggestRise.period)} com ${differenceLabel(biggestRise.value, biggestRise.previous_value)}` : "n/d"}.
            Maior queda: {biggestDrop ? ` ${formatMonthLabel(biggestDrop.period)} com ${differenceLabel(biggestDrop.value, biggestDrop.previous_value)}.` : " n/d."}
          </p>
        </article>
      </div>
    </section>
  );
}
