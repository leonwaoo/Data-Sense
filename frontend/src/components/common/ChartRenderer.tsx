import {
  Area,
  AreaChart,
  Bar,
  BarChart,
  CartesianGrid,
  Cell,
  Line,
  LineChart,
  Pie,
  PieChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import type { ChartPayload } from "../../types";

function getXAxisProps(chart: ChartPayload) {
  const hasManyPoints = chart.data.length > 10;
  return {
    interval: hasManyPoints ? ("preserveStartEnd" as const) : 0,
    minTickGap: chart.type === "line" || chart.type === "area" ? 18 : 12,
    tick: { fontSize: 11 },
  };
}

export function ChartRenderer({
  chart,
  colors,
  height,
}: {
  chart: ChartPayload;
  colors: string[];
  height: number;
}) {
  const xAxisProps = getXAxisProps(chart);

  if (chart.type === "area") {
    return (
      <ResponsiveContainer height={height} width="100%">
        <AreaChart data={chart.data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={chart.x} {...xAxisProps} />
          <YAxis />
          <Tooltip />
          <Area dataKey={chart.y} fill={colors[0]} fillOpacity={0.18} stroke={colors[0]} strokeWidth={3} type="monotone" />
        </AreaChart>
      </ResponsiveContainer>
    );
  }

  if (chart.type === "line") {
    return (
      <ResponsiveContainer height={height} width="100%">
        <LineChart data={chart.data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={chart.x} {...xAxisProps} />
          <YAxis />
          <Tooltip />
          <Line dataKey={chart.y} stroke={colors[0]} strokeWidth={3} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  if (chart.type === "pie") {
    return (
      <ResponsiveContainer height={height} width="100%">
        <PieChart>
          <Tooltip />
          <Pie data={chart.data} dataKey={chart.y} innerRadius={44} nameKey={chart.x} outerRadius={92} paddingAngle={2}>
            {chart.data.map((_, index) => (
              <Cell fill={colors[index % colors.length]} key={index} />
            ))}
          </Pie>
        </PieChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer height={height} width="100%">
      <BarChart data={chart.data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={chart.x} {...xAxisProps} />
        <YAxis />
        <Tooltip />
        <Bar dataKey={chart.y} fill={colors[0]} radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
}
