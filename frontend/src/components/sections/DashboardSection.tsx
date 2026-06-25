import { ArrowDown, ArrowUp, Eye, EyeOff, FileImage, LayoutDashboard, Printer, TrendingUp } from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { dashboardThemeMap } from "../../constants";
import { exportDashboardAsPng } from "../../utils/canvasExport";
import { ChartRenderer } from "../common/ChartRenderer";
import { EmptyState } from "../common/EmptyState";
import { ChartTypeControl } from "../dashboard/ChartTypeControl";
import { DashboardCustomization } from "../dashboard/DashboardCustomization";
import { DashboardFiltersPanel } from "../dashboard/DashboardFiltersPanel";
import { DashboardKpiCard } from "../dashboard/DashboardKpiCard";
import type { DashboardChart, DashboardFilters, DashboardPayload, DashboardSettings } from "../../types";

export function DashboardSection({
  dashboard,
  filters,
  isLoading,
  settings,
  onApplyFilters,
  onResetFilters,
  onSettingsChange,
}: {
  dashboard: DashboardPayload | null;
  filters: DashboardFilters;
  isLoading: boolean;
  settings: DashboardSettings;
  onApplyFilters: (filters: DashboardFilters) => void;
  onResetFilters: () => void;
  onSettingsChange: (settings: DashboardSettings | ((current: DashboardSettings) => DashboardSettings)) => void;
}) {
  const [chartTypes, setChartTypes] = useState<Record<string, string>>({});
  const [chartOrder, setChartOrder] = useState<string[]>([]);
  const [hiddenCharts, setHiddenCharts] = useState<Set<string>>(new Set());
  const [isExportingDashboard, setIsExportingDashboard] = useState<"png" | null>(null);
  const theme = dashboardThemeMap[settings.theme] ?? dashboardThemeMap.teal;
  const chartIds = useMemo(() => dashboard?.charts.map((chart) => chart.id).join("|") ?? "", [dashboard]);

  useEffect(() => {
    if (!dashboard) return;
    setChartOrder(dashboard.charts.map((chart) => chart.id));
    setHiddenCharts(new Set());
  }, [chartIds, dashboard]);

  const orderedCharts = useMemo(() => {
    if (!dashboard) return [];
    const byId = new Map(dashboard.charts.map((chart) => [chart.id, chart]));
    const ordered = chartOrder.map((id) => byId.get(id)).filter((chart): chart is DashboardChart => !!chart);
    const missing = dashboard.charts.filter((chart) => !chartOrder.includes(chart.id));
    return [...ordered, ...missing].filter((chart) => !hiddenCharts.has(chart.id));
  }, [chartOrder, dashboard, hiddenCharts]);

  function moveChart(chartId: string, direction: -1 | 1) {
    setChartOrder((current) => {
      const next = current.length ? [...current] : dashboard?.charts.map((chart) => chart.id) ?? [];
      const index = next.indexOf(chartId);
      const target = index + direction;
      if (index < 0 || target < 0 || target >= next.length) return current;
      [next[index], next[target]] = [next[target], next[index]];
      return next;
    });
  }

  function hideChart(chartId: string) {
    setHiddenCharts((current) => new Set(current).add(chartId));
  }

  function showChart(chartId: string) {
    setHiddenCharts((current) => {
      const next = new Set(current);
      next.delete(chartId);
      return next;
    });
  }

  function handlePrintDashboard() {
    document.body.classList.add("printing-dashboard");
    window.setTimeout(() => {
      window.print();
      window.setTimeout(() => document.body.classList.remove("printing-dashboard"), 300);
    }, 50);
  }

  async function handleExportDashboardPng() {
    if (!dashboard) return;
    setIsExportingDashboard("png");
    try {
      await exportDashboardAsPng(
        dashboard,
        settings,
        orderedCharts.map((chart) => ({ ...chart, type: chartTypes[chart.id] ?? chart.type })),
        theme,
      );
    } finally {
      setIsExportingDashboard(null);
    }
  }

  if (isLoading) {
    return (
      <section className="panel dashboard-panel">
        <div className="panel-heading">
          <h2>Dashboard automatico</h2>
          <span>Gerando visualizacoes</span>
        </div>
        <EmptyState text="Montando KPIs, rankings, evolucao e qualidade do dataset." />
      </section>
    );
  }

  if (!dashboard) return <EmptyState text="Envie um dataset para gerar o dashboard automatico." />;

  return (
    <section
      className={`panel dashboard-panel dashboard-theme-${settings.theme} dashboard-export-target`}
      style={
        {
          "--dashboard-accent": theme.accent,
          "--dashboard-soft": theme.soft,
        } as CSSProperties
      }
    >
      <div className="dashboard-heading">
        <div>
          {settings.logoDataUrl ? <img alt="" className="dashboard-logo" src={settings.logoDataUrl} /> : <LayoutDashboard size={22} />}
          <div>
            <h2>{settings.title || dashboard.title}</h2>
            <span>{dashboard.subtitle}</span>
          </div>
        </div>
        <span className="domain-pill">
          {dashboard.domain.label} - {Math.round(dashboard.domain.confidence * 100)}%
        </span>
      </div>

      <div className="dashboard-toolbox no-print">
        <DashboardCustomization settings={settings} onSettingsChange={onSettingsChange} />
        <DashboardFiltersPanel
          controls={dashboard.filters}
          filters={filters}
          onApply={onApplyFilters}
          onReset={onResetFilters}
        />
        <div className="dashboard-export-actions">
          <button onClick={handlePrintDashboard} type="button">
            <Printer size={16} />
            Exportar PDF
          </button>
          <button disabled={!!isExportingDashboard} onClick={() => void handleExportDashboardPng()} type="button">
            <FileImage size={16} />
            {isExportingDashboard ? "Gerando PNG..." : "Exportar PNG"}
          </button>
        </div>
      </div>

      <div className="dashboard-kpis">
        {dashboard.kpis.map((kpi) => (
          <DashboardKpiCard key={`${kpi.label}-${kpi.value}`} kpi={kpi} />
        ))}
      </div>

      <div className="dashboard-chart-grid">
        {orderedCharts.map((chart) => {
          const selectedType = chartTypes[chart.id] ?? chart.type;
          return (
            <article className="dashboard-chart-card" key={chart.id}>
              <div className="chart-card-heading">
                <div>
                  <strong>{chart.title}</strong>
                  <span>{chart.subtitle}</span>
                </div>
                <div className="chart-actions no-print">
                  <ChartTypeControl
                    activeType={selectedType}
                    availableTypes={chart.available_types ?? [chart.type]}
                    onChange={(type) => setChartTypes((current) => ({ ...current, [chart.id]: type }))}
                  />
                  <button aria-label="Mover grafico para cima" onClick={() => moveChart(chart.id, -1)} type="button">
                    <ArrowUp size={15} />
                  </button>
                  <button aria-label="Mover grafico para baixo" onClick={() => moveChart(chart.id, 1)} type="button">
                    <ArrowDown size={15} />
                  </button>
                  <button aria-label="Ocultar grafico" onClick={() => hideChart(chart.id)} type="button">
                    <EyeOff size={15} />
                  </button>
                </div>
              </div>
              <ChartRenderer chart={{ ...chart, type: selectedType }} colors={theme.series} height={250} />
              <p>{chart.insight}</p>
            </article>
          );
        })}
      </div>

      {hiddenCharts.size ? (
        <div className="hidden-chart-list no-print">
          {dashboard.charts
            .filter((chart) => hiddenCharts.has(chart.id))
            .map((chart) => (
              <button key={chart.id} onClick={() => showChart(chart.id)} type="button">
                <Eye size={15} />
                Mostrar {chart.title}
              </button>
            ))}
        </div>
      ) : null}

      {dashboard.insights.length ? (
        <div className="dashboard-insights">
          <div>
            <TrendingUp size={18} />
            <strong>Principais leituras</strong>
          </div>
          {dashboard.insights.map((insight) => (
            <span key={insight}>{insight}</span>
          ))}
        </div>
      ) : null}
    </section>
  );
}
