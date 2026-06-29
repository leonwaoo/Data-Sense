import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  LabelList,
  Line,
  LineChart,
  Pie,
  PieChart,
  ReferenceDot,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPayload, ChartPointSelection } from "../../types";

type ChartDatum = Record<string, string | number>;

const compactNumber = new Intl.NumberFormat("pt-BR", {
  maximumFractionDigits: 1,
  notation: "compact",
});

function valueOf(item: ChartDatum | undefined, key: string): number {
  const value = item?.[key];
  return typeof value === "number" ? value : Number(value ?? 0);
}

function labelOf(item: ChartDatum | undefined, key: string): string {
  return String(item?.[key] ?? "");
}

function formatValue(value: string | number | undefined) {
  const numeric = typeof value === "number" ? value : Number(value);
  if (Number.isFinite(numeric)) return compactNumber.format(numeric);
  return String(value ?? "");
}

function sortedData(chart: ChartPayload) {
  if (chart.type === "bar") {
    return [...chart.data].sort((a, b) => Math.abs(valueOf(b, chart.y)) - Math.abs(valueOf(a, chart.y))).slice(0, 10);
  }
  if (chart.type === "pie") {
    return [...chart.data].sort((a, b) => valueOf(b, chart.y) - valueOf(a, chart.y)).slice(0, 8);
  }
  return chart.data;
}

function lineFocus(data: ChartDatum[], chart: ChartPayload) {
  return data.length ? data[data.length - 1] : null;
}

function buildSelection(chart: ChartPayload, datum: ChartDatum | undefined): ChartPointSelection | null {
  if (!datum) return null;
  const label = labelOf(datum, chart.x);
  return {
    chartId: chart.id,
    x: chart.x,
    y: chart.y,
    label,
    value: valueOf(datum, chart.y),
    datum,
  };
}

function activeSelection(chart: ChartPayload, state: unknown): ChartPointSelection | null {
  const payload = state as { activePayload?: { payload?: ChartDatum }[] };
  return buildSelection(chart, payload.activePayload?.[0]?.payload);
}

function CustomTooltip({ active, label, payload }: { active?: boolean; label?: string; payload?: { value?: string | number }[] }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="chart-tooltip">
      <span>{label}</span>
      <strong>{formatValue(payload[0]?.value)}</strong>
    </div>
  );
}

function ValueLabel({ x, y, width, value }: { x?: number; y?: number; width?: number; value?: string | number }) {
  if (x === undefined || y === undefined || width === undefined) return null;
  return (
    <text className="chart-value-label" dominantBaseline="middle" x={x + width + 8} y={y + 10}>
      {formatValue(value)}
    </text>
  );
}

function BarValueLabel(props: unknown) {
  return <ValueLabel {...(props as { x?: number; y?: number; width?: number; value?: string | number })} />;
}

export function ChartRenderer({
  chart,
  colors,
  height,
  onSelect,
}: {
  chart: ChartPayload;
  colors: string[];
  height: number;
  onSelect?: (selection: ChartPointSelection) => void;
}) {
  const data = sortedData(chart);
  const primary = colors[0] ?? "#1d4ed8";
  const comparison = colors[1] ?? "#2563eb";
  const focus = lineFocus(data, chart);
  const gradientId = `chart-fill-${chart.x.replace(/\W/g, "")}-${chart.y.replace(/\W/g, "")}`;
  const maxLabelWidth = data.some((item) => labelOf(item, chart.x).length > 18) ? 120 : 96;

  if (!data.length) {
    return <div className="chart-empty" style={{ minHeight: height }}>Sem dados suficientes para montar este grafico.</div>;
  }

  if (chart.type === "area") {
    return (
      <div className="chart-frame chart-frame-area">
        <ResponsiveContainer height={height} width="100%">
          <AreaChart
            data={data}
            margin={{ bottom: 4, left: 0, right: 24, top: 16 }}
            onClick={(state) => {
              const selection = activeSelection(chart, state);
              if (selection) onSelect?.(selection);
            }}
          >
            <defs>
              <linearGradient id={gradientId} x1="0" x2="0" y1="0" y2="1">
                <stop offset="0%" stopColor={primary} stopOpacity={0.28} />
                <stop offset="100%" stopColor={primary} stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis axisLine={false} dataKey={chart.x} minTickGap={20} tick={{ fill: "var(--chart-muted)", fontSize: 11 }} tickLine={false} />
            <YAxis axisLine={false} tick={{ fill: "var(--chart-muted)", fontSize: 11 }} tickFormatter={formatValue} tickLine={false} width={42} />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: "var(--chart-cursor)", strokeWidth: 1 }} />
            <Area dataKey={chart.y} fill={`url(#${gradientId})`} stroke={primary} strokeWidth={3} type="monotone" />
            {focus ? <ReferenceDot className="chart-attention-dot" fill={primary} r={5} stroke="#fff" strokeWidth={2} x={focus[chart.x]} y={focus[chart.y]} /> : null}
          </AreaChart>
        </ResponsiveContainer>
        {focus ? (
          <div className="chart-focus-note">
            <span>Ultimo ponto</span>
            <strong>{labelOf(focus, chart.x)}: {formatValue(focus[chart.y])}</strong>
          </div>
        ) : null}
      </div>
    );
  }

  if (chart.type === "line") {
    return (
      <div className="chart-frame chart-frame-line">
        <ResponsiveContainer height={height} width="100%">
          <LineChart
            data={data}
            margin={{ bottom: 4, left: 0, right: 24, top: 16 }}
            onClick={(state) => {
              const selection = activeSelection(chart, state);
              if (selection) onSelect?.(selection);
            }}
          >
            <CartesianGrid stroke="var(--chart-grid)" vertical={false} />
            <XAxis axisLine={false} dataKey={chart.x} minTickGap={20} tick={{ fill: "var(--chart-muted)", fontSize: 11 }} tickLine={false} />
            <YAxis axisLine={false} tick={{ fill: "var(--chart-muted)", fontSize: 11 }} tickFormatter={formatValue} tickLine={false} width={42} />
            <Tooltip content={<CustomTooltip />} cursor={{ stroke: "var(--chart-cursor)", strokeWidth: 1 }} />
            <Line activeDot={{ fill: primary, r: 6, stroke: "#fff", strokeWidth: 2 }} dataKey={chart.y} dot={false} stroke={primary} strokeWidth={3} type="monotone" />
            {focus ? <ReferenceDot className="chart-attention-dot" fill={primary} r={5} stroke="#fff" strokeWidth={2} x={focus[chart.x]} y={focus[chart.y]} /> : null}
          </LineChart>
        </ResponsiveContainer>
        {focus ? (
          <div className="chart-focus-note">
            <span>Ultimo ponto</span>
            <strong>{labelOf(focus, chart.x)}: {formatValue(focus[chart.y])}</strong>
          </div>
        ) : null}
      </div>
    );
  }

  if (chart.type === "pie") {
    const total = data.reduce((sum, item) => sum + Math.max(0, valueOf(item, chart.y)), 0);
    return (
      <div className="chart-frame chart-donut-layout">
        <ResponsiveContainer height={height} width="100%">
          <PieChart>
            <Tooltip content={<CustomTooltip />} />
            <Pie
              cx="50%"
              cy="50%"
              data={data}
              dataKey={chart.y}
              innerRadius="58%"
              nameKey={chart.x}
              outerRadius="82%"
              paddingAngle={2}
              onClick={(datum) => {
                const pieDatum = datum as ChartDatum & { payload?: ChartDatum };
                const selection = buildSelection(chart, pieDatum.payload ?? pieDatum);
                if (selection) onSelect?.(selection);
              }}
            >
              {data.map((_, index) => (
                <Cell fill={colors[index % colors.length]} key={index} stroke="#fff" strokeWidth={2} />
              ))}
            </Pie>
            <text className="chart-donut-total" dominantBaseline="middle" textAnchor="middle" x="50%" y="48%">
              {formatValue(total)}
            </text>
            <text className="chart-donut-caption" dominantBaseline="middle" textAnchor="middle" x="50%" y="57%">
              total
            </text>
          </PieChart>
        </ResponsiveContainer>
        <div className="chart-direct-legend">
          {data.slice(0, 5).map((item, index) => (
            <span key={`${item[chart.x]}-${index}`}>
              <i style={{ background: colors[index % colors.length] }} />
              {labelOf(item, chart.x)} <strong>{formatValue(item[chart.y])}</strong>
            </span>
          ))}
        </div>
      </div>
    );
  }

  return (
    <div className="chart-frame chart-frame-bar">
      <ResponsiveContainer height={height} width="100%">
        <BarChart
          data={data}
          layout="vertical"
          margin={{ bottom: 4, left: 8, right: 48, top: 8 }}
          onClick={(state) => {
            const selection = activeSelection(chart, state);
            if (selection) onSelect?.(selection);
          }}
        >
          <CartesianGrid horizontal={false} stroke="var(--chart-grid)" />
          <XAxis axisLine={false} tick={{ fill: "var(--chart-muted)", fontSize: 11 }} tickFormatter={formatValue} tickLine={false} type="number" />
          <YAxis
            axisLine={false}
            dataKey={chart.x}
            tick={{ fill: "var(--chart-text)", fontSize: 12 }}
            tickFormatter={(value) => String(value).length > 18 ? `${String(value).slice(0, 18)}...` : String(value)}
            tickLine={false}
            type="category"
            width={maxLabelWidth}
          />
          <Tooltip content={<CustomTooltip />} cursor={{ fill: "var(--chart-hover)" }} />
          <Bar background={{ fill: "var(--chart-track)" }} dataKey={chart.y} fill={primary} radius={[0, 8, 8, 0]}>
            <LabelList content={BarValueLabel} dataKey={chart.y} />
            {data.map((_, index) => (
              <Cell className={index === 0 ? "chart-bar-priority" : undefined} fill={index === 0 ? primary : comparison} fillOpacity={index === 0 ? 1 : 0.72} key={index} />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    </div>
  );
}
