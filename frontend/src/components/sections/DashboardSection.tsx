import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  Eye,
  EyeOff,
  FileImage,
  Filter,
  LayoutDashboard,
  ListChecks,
  Printer,
  SlidersHorizontal,
  TrendingUp,
  X,
} from "lucide-react";
import { useEffect, useMemo, useState } from "react";
import type { CSSProperties } from "react";
import { dashboardThemeMap } from "../../constants";
import { exportDashboardAsPng } from "../../utils/canvasExport";
import { ChartRenderer } from "../common/ChartRenderer";
import { EmptyState } from "../common/EmptyState";
import { ChartTypeControl } from "../dashboard/ChartTypeControl";
import { DashboardCustomization } from "../dashboard/DashboardCustomization";
import { DashboardFiltersPanel } from "../dashboard/DashboardFiltersPanel";
import { cleanFilters } from "../../utils/filters";
import type { ChartPointSelection, DashboardChart, DashboardFilters, DashboardPayload, DashboardSettings } from "../../types";

type DrilldownState = {
  chart: DashboardChart;
  selection: ChartPointSelection;
  filterApplied: boolean;
  reading: {
    whatChanged: string;
    howMuch: string;
    possibleCause: string;
    recommendation: string;
    alert: string | null;
  };
};

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
  const [drilldown, setDrilldown] = useState<DrilldownState | null>(null);
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
  const featuredChart = orderedCharts[0] ?? null;
  const secondaryCharts = orderedCharts.slice(1);
  const highlightKpis = dashboard?.kpis.slice(0, 4) ?? [];
  const visibleRows = dashboard?.filters.rows_after_filter ?? 0;
  const totalRows = dashboard?.filters.rows_before_filter ?? 0;
  const appliedDateLabel = dashboard?.filters.date?.selected_from && dashboard?.filters.date?.selected_to
    ? `${dashboard.filters.date.selected_from} ate ${dashboard.filters.date.selected_to}`
    : null;
  const activeCategoryFilters = dashboard?.filters.categories.filter((category) => category.selected.length) ?? [];
  const filterSummary = appliedDateLabel
    ? `Periodo ativo: ${appliedDateLabel}`
    : activeCategoryFilters.length
      ? `${activeCategoryFilters.length} filtro(s) de categoria aplicados`
      : "Visao completa do arquivo";

  function readSelection(chart: DashboardChart, selection: ChartPointSelection): DrilldownState["reading"] {
    const pointInsight = chart.point_insights?.[selection.label];
    if (pointInsight) {
      return {
        whatChanged: pointInsight.what_changed,
        howMuch: pointInsight.how_much,
        possibleCause: pointInsight.possible_cause,
        recommendation: pointInsight.recommendation,
        alert: pointInsight.alert ?? null,
      };
    }

    const value = selection.value;
    const total = chart.data.reduce((sum, row) => sum + Math.abs(Number(row[chart.y]) || 0), 0);
    const share = total ? Math.abs(value) / total : 0;
    const currentIndex = chart.data.findIndex((row) => String(row[chart.x]) === selection.label);
    const previousValue = currentIndex > 0 ? Number(chart.data[currentIndex - 1]?.[chart.y]) || 0 : null;
    const variation = previousValue !== null ? value - previousValue : null;
    const variationPct = previousValue ? variation! / Math.abs(previousValue) : null;
    const isMonth = chart.period_grain === "month";
    const alert = share >= 0.8
      ? `${selection.label} concentra ${(share * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% do resultado exibido.`
      : variationPct !== null && Math.abs(variationPct) >= 0.5
        ? `Movimento fora do padrao: ${(variationPct * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}% contra o ponto anterior.`
        : null;

    return {
      whatChanged: isMonth
        ? `O periodo ${selection.label} foi selecionado no grafico ${chart.title}.`
        : `${selection.label} foi selecionado em ${chart.title}.`,
      howMuch: variation !== null
        ? `Valor ${value.toLocaleString("pt-BR")} com variacao de ${variation.toLocaleString("pt-BR")} contra o ponto anterior.`
        : `Valor exibido: ${value.toLocaleString("pt-BR")}. Participacao no grafico: ${(share * 100).toLocaleString("pt-BR", { maximumFractionDigits: 1 })}%.`,
      possibleCause: isMonth
        ? "Pode haver efeito de sazonalidade, entrada/saida operacional, mudanca comercial ou ajuste pontual nesse periodo."
        : share >= 0.6
          ? "A concentracao sugere que este recorte pode estar puxando a leitura geral do painel."
          : "A leitura deve ser comparada com outros recortes e com o periodo para separar efeito pontual de tendencia.",
      recommendation: chart.filter_column
        ? `Validar os registros de ${selection.label} e comparar com os demais recortes antes de tomar decisao.`
        : "Usar este ponto como sinal de investigacao e conferir a base em Detalhes.",
      alert,
    };
  }

  function monthRange(period: string) {
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

  function applySelectionFilter(chart: DashboardChart, selection: ChartPointSelection) {
    if (!chart.filter_column) return false;
    if (chart.period_grain === "month") {
      const range = monthRange(selection.label);
      if (!range) return false;
      onApplyFilters(cleanFilters({ ...filters, ...range, categories: filters.categories }));
      return true;
    }

    const categoryExists = dashboard?.filters.categories.some((category) => category.column === chart.filter_column);
    if (!categoryExists) return false;
    onApplyFilters(cleanFilters({
      ...filters,
      categories: {
        ...filters.categories,
        [chart.filter_column]: [selection.label],
      },
    }));
    return true;
  }

  function handleChartSelection(chart: DashboardChart, selection: ChartPointSelection) {
    const filterApplied = applySelectionFilter(chart, selection);
    setDrilldown({
      chart,
      selection,
      filterApplied,
      reading: readSelection(chart, selection),
    });
  }

  function clearDrilldown() {
    setDrilldown(null);
    onResetFilters();
  }

  function chartAlert(chart: DashboardChart) {
    if (!chart.data.length) return null;
    const values = chart.data.map((row) => Math.abs(Number(row[chart.y]) || 0));
    const total = values.reduce((sum, value) => sum + value, 0);
    const max = Math.max(...values);
    if (total && max / total >= 0.8) return "Concentracao alta";
    if (chart.type === "line" || chart.type === "area") {
      const last = Number(chart.data[chart.data.length - 1]?.[chart.y]) || 0;
      const previous = Number(chart.data[chart.data.length - 2]?.[chart.y]) || 0;
      if (previous && Math.abs((last - previous) / Math.abs(previous)) >= 0.5) return "Movimento forte";
    }
    return null;
  }

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
        <EmptyState text="Montando graficos e leituras do arquivo." />
      </section>
    );
  }

  if (!dashboard) return <EmptyState text="Envie um arquivo para gerar os graficos automaticos." />;

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
            <h2>{settings.title || "Graficos do arquivo"}</h2>
            <span>Uma visao limpa para acompanhar os principais movimentos</span>
          </div>
        </div>
        <span className="domain-pill">{dashboard.domain.label}</span>
      </div>

      <div className="dashboard-executive-strip">
        <article className="dashboard-executive-card dashboard-executive-main">
          <div>
            <TrendingUp size={18} />
            <span>Leitura principal</span>
          </div>
          <strong>{dashboard.insights[0] ?? "Arquivo pronto para exploracao visual."}</strong>
        </article>
        <article className="dashboard-executive-card">
          <div>
            <ListChecks size={18} />
            <span>Dados em analise</span>
          </div>
          <strong>{visibleRows.toLocaleString("pt-BR")} linhas</strong>
          <small>{totalRows && totalRows !== visibleRows ? `de ${totalRows.toLocaleString("pt-BR")} apos filtros` : "sem filtros aplicados"}</small>
        </article>
        <article className="dashboard-executive-card">
          <div>
            <BarChart3 size={18} />
            <span>Graficos ativos</span>
          </div>
          <strong>{orderedCharts.length}</strong>
          <small>{hiddenCharts.size ? `${hiddenCharts.size} oculto(s)` : "todos visiveis"}</small>
        </article>
      </div>

      <div className="dashboard-context-banner">
        <div>
          <strong>Recorte em exibicao</strong>
          <span>{filterSummary}</span>
        </div>
        <small>
          {dashboard.filters.applied_count
            ? "Os graficos e KPIs ja refletem os filtros ativos."
            : "Nenhum filtro ativo: use o painel de ajustes para focar em um periodo ou recorte."}
        </small>
      </div>

      {highlightKpis.length ? (
        <div className="dashboard-kpi-ribbon">
          {highlightKpis.map((kpi) => (
            <article className={`dashboard-kpi-chip tone-${kpi.tone ?? "neutral"}`} key={`${kpi.label}-${kpi.value}`}>
              <span>{kpi.label}</span>
              <strong>{kpi.value}</strong>
              <small>{kpi.detail}</small>
            </article>
          ))}
        </div>
      ) : null}

      <details className="dashboard-controls no-print">
        <summary>
          <SlidersHorizontal size={16} />
          Ajustes e filtros
          {dashboard.filters.applied_count ? <span>{dashboard.filters.applied_count}</span> : null}
        </summary>
        <div className="dashboard-toolbox">
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
      </details>

      {drilldown ? (
        <aside className="dashboard-drilldown-panel">
          <div className="dashboard-drilldown-heading">
            <div>
              <span>Leitura do clique</span>
              <strong>{drilldown.selection.label}</strong>
            </div>
            <button aria-label="Fechar leitura" onClick={() => setDrilldown(null)} type="button">
              <X size={16} />
            </button>
          </div>
          {drilldown.reading.alert ? <p className="dashboard-drilldown-alert">{drilldown.reading.alert}</p> : null}
          <div className="dashboard-drilldown-list">
            <article>
              <span>O que mudou</span>
              <p>{drilldown.reading.whatChanged}</p>
            </article>
            <article>
              <span>Quanto mudou</span>
              <p>{drilldown.reading.howMuch}</p>
            </article>
            <article>
              <span>Por que pode ter mudado</span>
              <p>{drilldown.reading.possibleCause}</p>
            </article>
            <article>
              <span>Acao recomendada</span>
              <p>{drilldown.reading.recommendation}</p>
            </article>
          </div>
          <div className="dashboard-drilldown-actions">
            <span>{drilldown.filterApplied ? "Filtro aplicado automaticamente" : "Clique sem filtro automatico"}</span>
            <button onClick={clearDrilldown} type="button">
              <Filter size={15} />
              Limpar selecao
            </button>
          </div>
        </aside>
      ) : null}

      {featuredChart ? (
        <div className="dashboard-chart-section">
          <div className="dashboard-chart-section-heading">
            <span>Grafico principal</span>
            <strong>Comece por aqui</strong>
          </div>
          <article className="dashboard-chart-card dashboard-featured-chart">
            <div className="chart-card-heading">
              <div>
                <strong>{featuredChart.title}</strong>
                <span>{featuredChart.subtitle}</span>
              </div>
              <div className="chart-actions no-print">
                <ChartTypeControl
                  activeType={chartTypes[featuredChart.id] ?? featuredChart.type}
                  availableTypes={featuredChart.available_types ?? [featuredChart.type]}
                  onChange={(type) => setChartTypes((current) => ({ ...current, [featuredChart.id]: type }))}
                />
              </div>
              {chartAlert(featuredChart) ? <span className="chart-alert-badge">{chartAlert(featuredChart)}</span> : null}
            </div>
            <ChartRenderer
              chart={{ ...featuredChart, type: chartTypes[featuredChart.id] ?? featuredChart.type }}
              colors={theme.series}
              height={330}
              onSelect={(selection) => handleChartSelection(featuredChart, selection)}
            />
            <p>{featuredChart.insight}</p>
          </article>
        </div>
      ) : null}

      {secondaryCharts.length ? (
        <div className="dashboard-chart-section">
          <div className="dashboard-chart-section-heading">
            <span>Graficos de apoio</span>
            <strong>Compare rankings, qualidade e distribuicoes</strong>
          </div>
          <div className="dashboard-chart-grid">
            {secondaryCharts.map((chart) => {
              const selectedType = chartTypes[chart.id] ?? chart.type;
              return (
                <article className="dashboard-chart-card" key={chart.id}>
                  <div className="chart-card-heading">
                    <div>
                      <strong>{chart.title}</strong>
                      <span>{chart.subtitle}</span>
                    </div>
                    {chartAlert(chart) ? <span className="chart-alert-badge">{chartAlert(chart)}</span> : null}
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
                  <ChartRenderer
                    chart={{ ...chart, type: selectedType }}
                    colors={theme.series}
                    height={230}
                    onSelect={(selection) => handleChartSelection(chart, selection)}
                  />
                  <p>{chart.insight}</p>
                </article>
              );
            })}
          </div>
        </div>
      ) : null}

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
