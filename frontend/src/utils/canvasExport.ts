import { sanitizeFilename } from "./format";
import type { DashboardChart, DashboardPayload, DashboardSettings } from "../types";

export async function exportDashboardAsPng(
  dashboard: DashboardPayload,
  settings: DashboardSettings,
  charts: DashboardChart[],
  theme: { accent: string; soft: string; series: string[] },
) {
  const selectedFrom = dashboard.filters.date?.selected_from;
  const selectedTo = dashboard.filters.date?.selected_to;
  const periodLabel = selectedFrom && selectedTo ? `Periodo: ${selectedFrom} ate ${selectedTo}` : "Periodo: visao completa";
  const width = 1400;
  const chartRows = Math.ceil(Math.min(charts.length, 4) / 2);
  const height = 620 + chartRows * 300 + Math.ceil(dashboard.insights.length / 2) * 54;
  const canvas = document.createElement("canvas");
  canvas.width = width;
  canvas.height = height;
  const context = canvas.getContext("2d");
  if (!context) return;

  context.fillStyle = "#eef3f8";
  context.fillRect(0, 0, width, height);
  drawRoundRect(context, 40, 34, width - 80, height - 68, 22, "#ffffff", "#dbe5ef");

  if (settings.logoDataUrl) {
    const logo = await loadImage(settings.logoDataUrl).catch(() => null);
    if (logo) {
      context.drawImage(logo, 70, 64, 58, 58);
    }
  } else {
    drawRoundRect(context, 70, 64, 58, 58, 14, theme.soft, "#b6d9d3");
    context.fillStyle = theme.accent;
    context.font = "700 26px Arial";
    context.fillText("DS", 82, 101);
  }

  context.fillStyle = "#0f172a";
  context.font = "800 34px Arial";
  context.fillText(settings.title || dashboard.title, 150, 86);
  context.fillStyle = "#64748b";
  context.font = "500 18px Arial";
  drawWrappedText(context, dashboard.subtitle, 150, 116, 980, 24);
  context.fillStyle = "#526173";
  context.font = "700 14px Arial";
  context.fillText(periodLabel, 150, 144);
  drawPill(context, dashboard.domain.label, width - 305, 70, 230, theme.accent, theme.soft);

  let y = 176;
  drawRoundRect(context, 70, y, 760, 92, 16, theme.soft, "#dbe5ef");
  context.fillStyle = theme.accent;
  context.font = "800 15px Arial";
  context.fillText("Resumo executivo", 92, y + 28);
  context.fillStyle = "#0f172a";
  context.font = "800 20px Arial";
  drawWrappedText(context, dashboard.insights[0] || "Arquivo pronto para exploracao visual.", 92, y + 58, 700, 24);
  drawRoundRect(context, 860, y, 200, 92, 16, "#f8fafc", "#dbe5ef");
  context.fillStyle = "#64748b";
  context.font = "800 13px Arial";
  context.fillText("Linhas analisadas", 880, y + 30);
  context.fillStyle = "#0f172a";
  context.font = "800 24px Arial";
  context.fillText(dashboard.filters.rows_after_filter.toLocaleString("pt-BR"), 880, y + 64);
  drawRoundRect(context, 1085, y, 210, 92, 16, "#f8fafc", "#dbe5ef");
  context.fillStyle = "#64748b";
  context.font = "800 13px Arial";
  context.fillText("Graficos ativos", 1105, y + 30);
  context.fillStyle = "#0f172a";
  context.font = "800 24px Arial";
  context.fillText(String(charts.length), 1105, y + 64);

  y = 285;
  const x = 70;
  const kpiWidth = 196;
  dashboard.kpis.slice(0, 6).forEach((kpi, index) => {
    const cardX = x + index * (kpiWidth + 14);
    drawRoundRect(context, cardX, y, kpiWidth, 112, 14, "#f8fafc", "#dbe5ef");
    context.fillStyle = "#526173";
    context.font = "700 15px Arial";
    drawWrappedText(context, kpi.label, cardX + 16, y + 28, kpiWidth - 32, 18);
    context.fillStyle = "#0f172a";
    context.font = "800 25px Arial";
    drawWrappedText(context, kpi.value, cardX + 16, y + 62, kpiWidth - 32, 28);
    context.fillStyle = "#64748b";
    context.font = "500 13px Arial";
    drawWrappedText(context, kpi.detail, cardX + 16, y + 90, kpiWidth - 32, 16);
  });

  y = 430;
  charts.slice(0, 4).forEach((chart, index) => {
    const chartX = 70 + (index % 2) * 630;
    const chartY = y + Math.floor(index / 2) * 300;
    drawRoundRect(context, chartX, chartY, 594, 258, 16, "#f8fafc", "#dbe5ef");
    context.fillStyle = "#0f172a";
    context.font = "800 19px Arial";
    context.fillText(chart.title, chartX + 20, chartY + 32);
    context.fillStyle = "#64748b";
    context.font = "500 13px Arial";
    drawWrappedText(context, chart.insight, chartX + 20, chartY + 55, 540, 18);
    drawCanvasChart(context, chart, chartX + 28, chartY + 92, 536, 130, theme.series);
  });

  const insightY = y + chartRows * 300 + 8;
  context.fillStyle = "#0f172a";
  context.font = "800 21px Arial";
  context.fillText("Alertas e proximas leituras", 70, insightY);
  dashboard.insights.slice(0, 6).forEach((insight, index) => {
    const chipX = 70 + (index % 2) * 630;
    const chipY = insightY + 26 + Math.floor(index / 2) * 54;
    drawRoundRect(context, chipX, chipY, 594, 40, 20, "#ffffff", "#dbe5ef");
    context.fillStyle = "#334155";
    context.font = "600 14px Arial";
    drawWrappedText(context, insight, chipX + 16, chipY + 25, 552, 18);
  });

  const anchor = document.createElement("a");
  anchor.download = `${sanitizeFilename(settings.title || dashboard.title)}.png`;
  anchor.href = canvas.toDataURL("image/png");
  anchor.click();
}

function drawCanvasChart(
  context: CanvasRenderingContext2D,
  chart: DashboardChart,
  x: number,
  y: number,
  width: number,
  height: number,
  colors: string[],
) {
  const data = chart.type === "line" || chart.type === "area" ? chart.data.slice(0, 24) : chart.data.slice(0, 10);
  const values = data.map((row) => Number(row[chart.y]) || 0);
  const min = Math.min(...values, 0);
  const max = Math.max(...values, 1);
  const span = Math.max(max - min, 1);
  const valueToY = (value: number) => y + height - ((value - min) / span) * height;

  context.strokeStyle = "#cbd5e1";
  context.lineWidth = 1;
  context.beginPath();
  context.moveTo(x, y + height);
  context.lineTo(x + width, y + height);
  context.stroke();

  if (chart.type === "line" || chart.type === "area") {
    context.strokeStyle = colors[0];
    context.fillStyle = `${colors[0]}22`;
    context.lineWidth = 4;
    context.beginPath();
    data.forEach((_, index) => {
      const pointX = x + (index / Math.max(data.length - 1, 1)) * width;
      const pointY = valueToY(values[index]);
      if (index === 0) context.moveTo(pointX, pointY);
      else context.lineTo(pointX, pointY);
    });
    context.stroke();
    return;
  }

  if (chart.type === "pie") {
    const total = values.reduce((sum, value) => sum + value, 0) || 1;
    let start = -Math.PI / 2;
    values.forEach((value, index) => {
      const angle = (value / total) * Math.PI * 2;
      context.fillStyle = colors[index % colors.length];
      context.beginPath();
      context.moveTo(x + width / 2, y + height / 2);
      context.arc(x + width / 2, y + height / 2, Math.min(width, height) / 2, start, start + angle);
      context.closePath();
      context.fill();
      start += angle;
    });
    return;
  }

  const sorted = data
    .map((row, index) => ({ row, value: values[index] }))
    .sort((left, right) => Math.abs(right.value) - Math.abs(left.value))
    .slice(0, 6);
  const maxBar = Math.max(...sorted.map((item) => Math.abs(item.value)), 1);
  const rowHeight = height / Math.max(sorted.length, 1);
  sorted.forEach((item, index) => {
    const label = String(item.row[chart.x] ?? "");
    const barWidth = (Math.abs(item.value) / maxBar) * (width - 170);
    const rowY = y + index * rowHeight + 5;
    context.fillStyle = "#334155";
    context.font = "700 12px Arial";
    drawWrappedText(context, label.length > 18 ? `${label.slice(0, 18)}...` : label, x, rowY + 15, 140, 14);
    context.fillStyle = index === 0 ? colors[0] : colors[1] || colors[0];
    context.globalAlpha = index === 0 ? 1 : 0.72;
    context.fillRect(x + 150, rowY, Math.max(barWidth, 4), Math.max(rowHeight - 10, 8));
    context.globalAlpha = 1;
  });
}

function drawRoundRect(
  context: CanvasRenderingContext2D,
  x: number,
  y: number,
  width: number,
  height: number,
  radius: number,
  fill: string,
  stroke?: string,
) {
  context.beginPath();
  context.moveTo(x + radius, y);
  context.lineTo(x + width - radius, y);
  context.quadraticCurveTo(x + width, y, x + width, y + radius);
  context.lineTo(x + width, y + height - radius);
  context.quadraticCurveTo(x + width, y + height, x + width - radius, y + height);
  context.lineTo(x + radius, y + height);
  context.quadraticCurveTo(x, y + height, x, y + height - radius);
  context.lineTo(x, y + radius);
  context.quadraticCurveTo(x, y, x + radius, y);
  context.closePath();
  context.fillStyle = fill;
  context.fill();
  if (stroke) {
    context.strokeStyle = stroke;
    context.lineWidth = 1;
    context.stroke();
  }
}

function drawPill(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  width: number,
  accent: string,
  fill: string,
) {
  drawRoundRect(context, x, y, width, 38, 19, fill, "#dbe5ef");
  context.fillStyle = accent;
  context.font = "800 15px Arial";
  context.fillText(text, x + 18, y + 25);
}

function drawWrappedText(
  context: CanvasRenderingContext2D,
  text: string,
  x: number,
  y: number,
  maxWidth: number,
  lineHeight: number,
) {
  const words = String(text).split(" ");
  let line = "";
  words.forEach((word) => {
    const nextLine = line ? `${line} ${word}` : word;
    if (context.measureText(nextLine).width > maxWidth && line) {
      context.fillText(line, x, y);
      y += lineHeight;
      line = word;
    } else {
      line = nextLine;
    }
  });
  if (line) context.fillText(line, x, y);
}

function loadImage(src: string) {
  return new Promise<HTMLImageElement>((resolve, reject) => {
    const image = new Image();
    image.onload = () => resolve(image);
    image.onerror = reject;
    image.src = src;
  });
}
