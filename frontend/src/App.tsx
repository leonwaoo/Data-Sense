import {
  ArrowDown,
  ArrowUp,
  BarChart3,
  Clock,
  Database,
  Download,
  Eye,
  EyeOff,
  FileImage,
  FileQuestion,
  FileSpreadsheet,
  Filter,
  ImagePlus,
  LayoutDashboard,
  Lightbulb,
  Palette,
  Printer,
  RotateCcw,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UploadCloud,
  X,
} from "lucide-react";
import type { CSSProperties, DragEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
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

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? "https://data-sense-api.onrender.com" : "http://127.0.0.1:8000");

const SUPPORTED_FILE_ACCEPT =
  ".csv,.tsv,.txt,.xlsx,.xls,.json,text/csv,text/tab-separated-values,application/json,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

type CellValue = string | number | boolean | null;

type Profile = {
  dataset_id: string;
  file_name: string;
  ingest_report?: {
    header_row_number?: number | null;
    metadata_rows_skipped?: number;
    parsed_rows?: number;
    raw_rows_estimate?: number;
    expected_data_rows?: number | null;
    warnings?: string[];
  };
  rows: number;
  columns: number;
  column_names: string[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  date_conversion_suggestions?: {
    column: string;
    suggested_type: string;
    confidence: number;
    message: string;
  }[];
  date_candidates?: {
    column: string;
    kind: string;
    confidence: number;
  }[];
  missing_values: Record<string, number>;
};

type ScoreBreakdownItem = {
  label: string;
  weight: number;
  lost_points: number;
  detail: string;
};

type NumericOutlierDetail = {
  column: string;
  row_index: number | string;
  value: number;
  mean: number;
  deviation_ratio: number;
  lower_bound: number;
  upper_bound: number;
};

type Quality = {
  score: number;
  score_breakdown?: ScoreBreakdownItem[];
  missing_total: number;
  duplicate_rows: number;
  empty_columns: string[];
  numeric_outliers?: Record<string, number>;
  numeric_outlier_details?: NumericOutlierDetail[];
  recommendations: string[];
};

type QualityAuditFinding = {
  id: string;
  severity: "critical" | "warning" | "info";
  category: string;
  title: string;
  detail: string;
  recommendation: string;
  evidence: string[];
};

type QualityAudit = {
  mode: "rules" | "ai";
  ai_enabled: boolean;
  ai_status: "not_configured" | "disabled" | "failed" | "completed";
  ai_error?: string;
  model: string | null;
  analysis_score: number;
  summary: string;
  findings: QualityAuditFinding[];
  recommendations: string[];
  checks: Record<string, unknown>;
};

type ChartPayload = {
  type: string;
  x: string;
  y: string;
  data: Record<string, string | number>[];
};

type Answer = {
  answer: string;
  calculation: string | null;
  table: Record<string, string | number>[];
  chart: ChartPayload | null;
};

type ManagerialInsight = {
  id: string;
  title: string;
  severity: "danger" | "warning" | "info" | "neutral";
  metric: string | null;
  period: string | null;
  what_changed: string;
  how_much: string;
  where: string;
  possible_causes: string[];
  managerial_impact: string;
  recommendation: string;
  confidence: "alta" | "media" | "baixa" | string;
  evidence: string[];
};

type ManagerialAnalysis = {
  mode: string;
  title: string;
  summary: string[];
  context: {
    domain: {
      type: string;
      label: string;
      confidence: number;
      reasons: string[];
    };
    metric_map: {
      primary_metric: string | null;
      support_metrics: Record<string, string>;
      mapped_columns: Record<string, string | null>;
    };
    time: {
      available: boolean;
      label?: string | null;
      columns: string[];
    };
    dimensions: { label: string; column: string }[];
    limitations: string[];
  };
  kpis: { label: string; value: string; detail: string }[];
  insights: ManagerialInsight[];
  alerts: string[];
  recommendations: string[];
  suggested_questions: string[];
};

type UploadResponse = {
  dataset_id: string;
  file_name: string;
  profile: Profile;
  preview: Record<string, CellValue>[];
  quality: Quality;
  managerial_analysis?: ManagerialAnalysis;
  supported_formats?: string[];
};

type ChartSuggestion = {
  title: string;
  type: string;
  x: string;
  y: string;
  reason: string;
};

type DashboardKpi = {
  label: string;
  value: string;
  detail: string;
  tone?: "neutral" | "accent" | "good" | "warning" | "danger";
};

type DashboardChart = ChartPayload & {
  id: string;
  title: string;
  subtitle: string;
  insight: string;
  available_types?: string[];
};

type DashboardPayload = {
  title: string;
  subtitle: string;
  domain: {
    type: string;
    label: string;
    confidence: number;
    reasons: string[];
  };
  kpis: DashboardKpi[];
  charts: DashboardChart[];
  insights: string[];
  filters: DashboardFilterControls;
  quality: {
    score: number;
    score_breakdown?: ScoreBreakdownItem[];
    missing_total: number;
    duplicate_rows: number;
    empty_columns: string[];
    numeric_outliers?: Record<string, number>;
    numeric_outlier_details?: NumericOutlierDetail[];
  };
};

type DashboardFilters = {
  date_from?: string;
  date_to?: string;
  categories: Record<string, string[]>;
};

type DashboardFilterControls = {
  date: {
    column: string;
    min: string;
    max: string;
    selected_from: string | null;
    selected_to: string | null;
  } | null;
  categories: {
    label: string;
    column: string;
    values: { value: string; count: number }[];
    selected: string[];
  }[];
  applied_count: number;
  rows_before_filter: number;
  rows_after_filter: number;
};

type DashboardTheme = "teal" | "blue" | "violet" | "graphite";

type DashboardSettings = {
  title: string;
  theme: DashboardTheme;
  logoDataUrl: string | null;
};

type HistoryItem = {
  datasetId: string;
  fileName: string;
  rows: number;
  columns: number;
  qualityScore: number;
  domainLabel: string;
  createdAt: string;
};

const HISTORY_STORAGE_KEY = "datasense-dashboard-history-v1";

const dashboardThemeMap: Record<DashboardTheme, { label: string; accent: string; soft: string; series: string[] }> = {
  teal: {
    label: "Verde",
    accent: "#0f766e",
    soft: "#ecfdf5",
    series: ["#0f766e", "#2563eb", "#d97706", "#7c3aed", "#be123c", "#15803d"],
  },
  blue: {
    label: "Azul",
    accent: "#2563eb",
    soft: "#eff6ff",
    series: ["#2563eb", "#0f766e", "#dc2626", "#9333ea", "#ca8a04", "#0891b2"],
  },
  violet: {
    label: "Violeta",
    accent: "#7c3aed",
    soft: "#f5f3ff",
    series: ["#7c3aed", "#0f766e", "#2563eb", "#d97706", "#be123c", "#15803d"],
  },
  graphite: {
    label: "Grafite",
    accent: "#334155",
    soft: "#f8fafc",
    series: ["#334155", "#0f766e", "#2563eb", "#d97706", "#7c3aed", "#be123c"],
  },
};

const defaultDashboardFilters: DashboardFilters = { categories: {} };

const suggestedQuestions = [
  "Quantas linhas e colunas existem?",
  "Qual coluna tem mais valores ausentes?",
  "Existem duplicatas?",
  "Qual o total de vendas?",
  "Mostre compras por mes.",
  "Top 5 fornecedores por compras.",
  "Mostre clientes por valor.",
  "Mostre quantidade por categoria.",
];

const sampleFiles = [
  { label: "Vendas CSV", fileName: "vendas_demo.csv", href: "/samples/vendas_demo.csv" },
  { label: "Vendas Excel", fileName: "vendas_demo.xlsx", href: "/samples/vendas_demo.xlsx" },
  { label: "Compras Excel", fileName: "compras_demo.xlsx", href: "/samples/compras_demo.xlsx" },
  { label: "Clientes JSON", fileName: "clientes_demo.json", href: "/samples/clientes_demo.json" },
  { label: "Estoque TSV", fileName: "estoque_financeiro_demo.tsv", href: "/samples/estoque_financeiro_demo.tsv" },
];

export function App() {
  const [dataset, setDataset] = useState<UploadResponse | null>(null);
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [dashboardFilters, setDashboardFilters] = useState<DashboardFilters>(defaultDashboardFilters);
  const [dashboardSettings, setDashboardSettings] = useState<DashboardSettings>({
    title: "Dashboard DataSense",
    theme: "teal",
    logoDataUrl: null,
  });
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [chartSuggestions, setChartSuggestions] = useState<ChartSuggestion[]>([]);
  const [qualityAudit, setQualityAudit] = useState<QualityAudit | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);
  const [isQualityAuditLoading, setIsQualityAuditLoading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<"pdf" | "png" | null>(null);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    const sampleName = new URLSearchParams(window.location.search).get("sample");
    const sample = sampleFiles.find((file) => file.fileName === sampleName);
    if (sample) void handleSampleUpload(sample);
  }, []);

  const missingChartData = useMemo(() => {
    if (!dataset) return [];
    return Object.entries(dataset.profile.missing_values)
      .map(([coluna, valores_ausentes]) => ({ coluna, valores_ausentes }))
      .sort((a, b) => b.valores_ausentes - a.valores_ausentes)
      .slice(0, 6);
  }, [dataset]);

  async function handleUpload(file: File | null) {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setAnswer(null);
    setDashboard(null);
    setChartSuggestions([]);
    setQualityAudit(null);
    setDashboardFilters(defaultDashboardFilters);

    const formData = new FormData();
    formData.append("file", file);

    try {
      const response = await fetch(`${API_BASE_URL}/datasets/upload`, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Nao foi possivel enviar o arquivo.");
      }

      const uploadPayload: UploadResponse = await response.json();
      setDataset(uploadPayload);
      setDashboardSettings((current) => ({
        ...current,
        title: `Dashboard - ${uploadPayload.file_name.replace(/\.[^.]+$/, "")}`,
      }));
      setIsDashboardLoading(true);
      setIsQualityAuditLoading(true);
      const [suggestions, dashboardPayload, auditPayload] = await Promise.all([
        fetchChartSuggestions(uploadPayload.dataset_id).catch(() => []),
        fetchDashboard(uploadPayload.dataset_id).catch(() => null),
        fetchQualityAudit(uploadPayload.dataset_id).catch(() => null),
      ]);
      setChartSuggestions(suggestions);
      setDashboard(dashboardPayload);
      setQualityAudit(auditPayload);
      if (dashboardPayload) {
        setHistory(saveHistory(uploadPayload, dashboardPayload));
      }
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Erro inesperado no upload.");
    } finally {
      setIsUploading(false);
      setIsDashboardLoading(false);
      setIsQualityAuditLoading(false);
    }
  }

  async function handleSampleUpload(sample: (typeof sampleFiles)[number]) {
    setError(null);

    try {
      const response = await fetch(sample.href);
      if (!response.ok) throw new Error("Nao foi possivel carregar o arquivo de teste.");

      const blob = await response.blob();
      const file = new File([blob], sample.fileName, {
        type: blob.type || "application/octet-stream",
      });
      await handleUpload(file);
    } catch (sampleError) {
      setError(sampleError instanceof Error ? sampleError.message : "Erro inesperado ao carregar o arquivo de teste.");
    }
  }

  function handleDragOver(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    if (!isUploading) setIsDragOver(true);
  }

  function handleDragLeave(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragOver(false);
  }

  function handleDrop(event: DragEvent<HTMLLabelElement>) {
    event.preventDefault();
    setIsDragOver(false);
    if (isUploading) return;

    void handleUpload(event.dataTransfer.files?.[0] ?? null);
  }

  async function fetchChartSuggestions(datasetId: string) {
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/charts/suggest`, {
      method: "POST",
    });

    if (!response.ok) return [];
    return (await response.json()) as ChartSuggestion[];
  }

  async function fetchDashboard(datasetId: string, filters?: DashboardFilters) {
    const hasFilters = !!filters && hasActiveFilters(filters);
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/dashboard`, {
      method: hasFilters ? "POST" : "GET",
      headers: hasFilters ? { "Content-Type": "application/json" } : undefined,
      body: hasFilters ? JSON.stringify(filters) : undefined,
    });

    if (!response.ok) return null;
    return (await response.json()) as DashboardPayload;
  }

  async function fetchQualityAudit(datasetId: string) {
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/quality/audit`);

    if (!response.ok) return null;
    return (await response.json()) as QualityAudit;
  }

  async function handleApplyDashboardFilters(filters: DashboardFilters) {
    if (!dataset) return;

    setDashboardFilters(filters);
    setIsDashboardLoading(true);
    setError(null);

    try {
      const filteredDashboard = await fetchDashboard(dataset.dataset_id, filters);
      setDashboard(filteredDashboard);
    } catch (filterError) {
      setError(filterError instanceof Error ? filterError.message : "Erro inesperado ao filtrar dashboard.");
    } finally {
      setIsDashboardLoading(false);
    }
  }

  function handleResetDashboardFilters() {
    void handleApplyDashboardFilters(defaultDashboardFilters);
  }

  function handleClearHistory() {
    localStorage.removeItem(HISTORY_STORAGE_KEY);
    setHistory([]);
  }

  async function handleAsk(nextQuestion = question) {
    if (!dataset || !nextQuestion.trim()) return;

    setQuestion(nextQuestion);
    setIsAsking(true);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/datasets/${dataset.dataset_id}/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: nextQuestion }),
      });

      if (!response.ok) {
        const payload = await response.json();
        throw new Error(payload.detail || "Nao foi possivel responder a pergunta.");
      }

      setAnswer(await response.json());
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : "Erro inesperado na pergunta.");
    } finally {
      setIsAsking(false);
    }
  }

  async function handleDownloadReport(format: "pdf" | "png") {
    if (!dataset) return;

    setExportingFormat(format);
    setError(null);

    try {
      const response = await fetch(`${API_BASE_URL}/datasets/${dataset.dataset_id}/report.${format}`);
      if (!response.ok) {
        const payload = await response.json().catch(() => null);
        throw new Error(payload?.detail || "Nao foi possivel gerar o relatorio.");
      }

      const blob = await response.blob();
      const url = URL.createObjectURL(blob);
      const anchor = document.createElement("a");
      anchor.href = url;
      anchor.download = `datasense-relatorio-${dataset.file_name.replace(/\.[^.]+$/, "")}.${format}`;
      document.body.appendChild(anchor);
      anchor.click();
      anchor.remove();
      URL.revokeObjectURL(url);
    } catch (reportError) {
      setError(reportError instanceof Error ? reportError.message : "Erro inesperado ao gerar relatorio.");
    } finally {
      setExportingFormat(null);
    }
  }

  return (
    <main className="app-shell">
      <section className="topbar">
        <div className="brand-hero">
          <div className="brand-row">
            <img alt="" className="brand-mark" src="/brand-mark.svg" />
            <div>
              <p className="eyebrow">DataSense</p>
              <strong>Analise assistida para planilhas</strong>
            </div>
          </div>
          <h1>Transforme planilhas em respostas, graficos e alertas de qualidade.</h1>
          <p className="hero-copy">
            Envie CSV, Excel, TSV ou JSON, veja o perfil dos dados e faca perguntas analiticas calculadas diretamente no dataset.
          </p>
        </div>
        <label
          className={`dropzone${isDragOver ? " is-dragover" : ""}${isUploading ? " is-uploading" : ""}`}
          onDragLeave={handleDragLeave}
          onDragOver={handleDragOver}
          onDrop={handleDrop}
        >
          <span className="dropzone-icon">{isUploading ? <FileSpreadsheet size={24} /> : <UploadCloud size={24} />}</span>
          <strong>{isUploading ? "Enviando arquivo..." : "Arraste o arquivo aqui"}</strong>
          <p>ou clique para selecionar uma planilha</p>
          <small>CSV, TSV, TXT, XLSX, XLS ou JSON ate 15 MB</small>
          <input
            accept={SUPPORTED_FILE_ACCEPT}
            disabled={isUploading}
            type="file"
            onChange={(event) => {
              void handleUpload(event.target.files?.[0] ?? null);
              event.currentTarget.value = "";
            }}
          />
        </label>
      </section>

      {error ? <div className="error-banner">{error}</div> : null}

      <section className="summary-grid">
        <MetricCard icon={<Database size={20} />} label="Dataset" value={dataset?.file_name ?? "Nenhum arquivo"} />
        <MetricCard icon={<BarChart3 size={20} />} label="Linhas" value={dataset ? dataset.profile.rows.toLocaleString("pt-BR") : "-"} />
        <MetricCard icon={<FileQuestion size={20} />} label="Colunas" value={dataset ? String(dataset.profile.columns) : "-"} />
        <MetricCard icon={<ShieldCheck size={20} />} label="Qualidade" value={dataset ? `${dataset.quality.score}/100` : "-"} />
      </section>

      <section className="insight-strip">
        <div>
          <Sparkles size={18} />
          <span>{dataset ? "Dataset carregado e pronto para analise" : "Teste com CSV, Excel, TSV, TXT ou JSON tabular"}</span>
        </div>
        <strong>{dataset ? `${dataset.profile.datetime_columns.length} data(s), ${dataset.profile.numeric_columns.length} metrica(s)` : "DataSense"}</strong>
      </section>

      <section className="sample-strip">
        <div>
          <FileSpreadsheet size={18} />
          <strong>Arquivos de teste</strong>
        </div>
        <nav aria-label="Arquivos de teste">
          {sampleFiles.map((file) => (
            <span className="sample-action" key={file.href}>
              <button disabled={isUploading} onClick={() => void handleSampleUpload(file)} type="button">
                {file.label}
              </button>
              <a aria-label={`Baixar ${file.label}`} download href={file.href}>
                <Download size={15} />
              </a>
            </span>
          ))}
        </nav>
      </section>

      <HistoryPanel history={history} onClear={handleClearHistory} />

      {dataset ? (
        <section className="report-strip">
          <div>
            <Download size={18} />
            <strong>Relatorio exportavel</strong>
            <span>Resumo, qualidade, insights, graficos e recomendacoes</span>
          </div>
          <div className="report-actions">
            <button disabled={!!exportingFormat} onClick={() => void handleDownloadReport("pdf")} type="button">
              <Download size={16} />
              {exportingFormat === "pdf" ? "Gerando PDF..." : "Baixar PDF"}
            </button>
            <button disabled={!!exportingFormat} onClick={() => void handleDownloadReport("png")} type="button">
              <Download size={16} />
              {exportingFormat === "png" ? "Gerando PNG..." : "Baixar PNG"}
            </button>
          </div>
        </section>
      ) : null}

      {dataset?.managerial_analysis ? <ManagerialInsightsSection analysis={dataset.managerial_analysis} /> : null}

      {dataset ? (
        <DashboardSection
          dashboard={dashboard}
          filters={dashboardFilters}
          isLoading={isDashboardLoading}
          settings={dashboardSettings}
          onApplyFilters={(filters) => void handleApplyDashboardFilters(filters)}
          onResetFilters={handleResetDashboardFilters}
          onSettingsChange={setDashboardSettings}
        />
      ) : null}

      <section className="workspace-grid">
        <div className="panel">
          <div className="panel-heading">
            <h2>Perfil do dataset</h2>
            <span>{dataset ? `${dataset.profile.numeric_columns.length} numericas` : "Aguardando arquivo"}</span>
          </div>
          {dataset ? (
            <>
              <div className="column-list">
                {dataset.profile.column_names.map((column) => (
                  <span key={column}>{column}</span>
                ))}
              </div>
              {dataset.profile.date_conversion_suggestions?.length ? (
                <div className="date-suggestion-list">
                  <strong>Sugestoes de conversao de data</strong>
                  {dataset.profile.date_conversion_suggestions.map((suggestion) => (
                    <p key={suggestion.column}>{suggestion.message}</p>
                  ))}
                </div>
              ) : null}
              {dataset.profile.ingest_report?.warnings?.length ? (
                <div className="ingest-report-list">
                  <strong>Sanidade da ingestao</strong>
                  {dataset.profile.ingest_report.header_row_number ? (
                    <p>
                      Cabecalho detectado na linha {dataset.profile.ingest_report.header_row_number};{" "}
                      {dataset.profile.ingest_report.metadata_rows_skipped ?? 0} linha(s) acima foram tratadas como metadado.
                    </p>
                  ) : null}
                  {dataset.profile.ingest_report.warnings.map((warning) => (
                    <p key={warning}>{warning}</p>
                  ))}
                </div>
              ) : null}
              <div className="chart-box">
                <ResponsiveContainer height={220} width="100%">
                  <BarChart data={missingChartData}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="coluna" />
                    <YAxis allowDecimals={false} />
                    <Tooltip />
                    <Bar dataKey="valores_ausentes" fill="#2563eb" radius={[6, 6, 0, 0]} />
                  </BarChart>
                </ResponsiveContainer>
              </div>
            </>
          ) : (
            <EmptyState text="Envie uma planilha para ver colunas, nulos e preview." />
          )}
        </div>

        <div className="panel">
          <div className="panel-heading">
            <h2>Auditoria de qualidade</h2>
            <span>{qualityAudit ? `${qualityAudit.analysis_score}/100 analise` : dataset ? `${dataset.quality.missing_total} nulos` : "Sem dados"}</span>
          </div>
          {dataset ? (
            <>
              <div className="quality-list">
                <strong>Duplicatas: {dataset.quality.duplicate_rows}</strong>
                <strong>Colunas vazias: {dataset.quality.empty_columns.length}</strong>
                {dataset.quality.recommendations.map((recommendation) => (
                  <p key={recommendation}>{recommendation}</p>
                ))}
              </div>
              {dataset.quality.score_breakdown?.length ? (
                <div className="score-breakdown-list">
                  <strong>Formula do score</strong>
                  {dataset.quality.score_breakdown.map((item) => (
                    <p key={item.label}>
                      {item.label}: peso {item.weight}, perda {item.lost_points.toLocaleString("pt-BR")} ponto(s).
                    </p>
                  ))}
                </div>
              ) : null}
              {dataset.quality.numeric_outlier_details?.length ? (
                <div className="outlier-list">
                  <strong>Outliers nomeados</strong>
                  {dataset.quality.numeric_outlier_details.slice(0, 4).map((item) => (
                    <p key={`${item.column}-${item.row_index}-${item.value}`}>
                      {item.column}, linha {item.row_index}: {item.value.toLocaleString("pt-BR")} ({item.deviation_ratio}x da media)
                    </p>
                  ))}
                </div>
              ) : null}
              {isQualityAuditLoading ? <div className="audit-loading">Revisando confiabilidade da analise...</div> : null}
              {qualityAudit ? <QualityAuditView audit={qualityAudit} /> : null}
            </>
          ) : (
            <EmptyState text="A auditoria sera gerada automaticamente apos o upload." />
          )}
        </div>
      </section>

      {chartSuggestions.length ? (
        <section className="panel">
          <div className="panel-heading">
            <h2>Graficos sugeridos</h2>
            <span>{chartSuggestions.length} ideias automaticas</span>
          </div>
          <div className="suggested-charts">
            {chartSuggestions.map((chart) => (
              <article key={`${chart.type}-${chart.x}-${chart.y}`}>
                <Lightbulb size={18} />
                <strong>{chart.title}</strong>
                <p>{chart.reason}</p>
                <span>
                  {chart.type} - {chart.x} / {chart.y}
                </span>
              </article>
            ))}
          </div>
        </section>
      ) : null}

      <section className="panel">
        <div className="panel-heading">
          <h2>Chat analitico</h2>
          <span>{dataset ? "Perguntas suportadas" : "Envie um arquivo primeiro"}</span>
        </div>
        <div className="suggestions">
          {suggestedQuestions.map((suggestion) => (
            <button disabled={!dataset || isAsking} key={suggestion} onClick={() => handleAsk(suggestion)} type="button">
              {suggestion}
            </button>
          ))}
        </div>
        <div className="ask-row">
          <input
            disabled={!dataset || isAsking}
            onChange={(event) => setQuestion(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") void handleAsk();
            }}
            placeholder="Ex.: Qual produto mais vendeu?"
            value={question}
          />
          <button disabled={!dataset || isAsking || !question.trim()} onClick={() => handleAsk()} type="button">
            {isAsking ? "Analisando..." : "Perguntar"}
          </button>
        </div>
        {answer ? <AnswerView answer={answer} /> : null}
      </section>

      {dataset ? (
        <section className="panel">
          <div className="panel-heading">
            <h2>Preview dos dados</h2>
            <span>Primeiras linhas</span>
          </div>
          <DataTable rows={dataset.preview} />
        </section>
      ) : null}
    </main>
  );
}

function MetricCard({ icon, label, value }: { icon: ReactNode; label: string; value: string }) {
  return (
    <article className="metric-card">
      {icon}
      <span>{label}</span>
      <strong>{value}</strong>
    </article>
  );
}

function ManagerialInsightsSection({ analysis }: { analysis: ManagerialAnalysis }) {
  const primaryMetric = analysis.context.metric_map.primary_metric ?? "Metrica nao detectada";
  const supportMetrics = Object.values(analysis.context.metric_map.support_metrics);

  return (
    <section className="panel managerial-panel">
      <div className="managerial-heading">
        <div>
          <TrendingUp size={22} />
          <div>
            <h2>Insights Gerenciais</h2>
            <span>
              {analysis.context.domain.label} - {Math.round(analysis.context.domain.confidence * 100)}% de confianca
            </span>
          </div>
        </div>
        <span className="domain-pill">{primaryMetric}</span>
      </div>

      <div className="managerial-summary">
        {analysis.summary.slice(0, 4).map((item) => (
          <p key={item}>{item}</p>
        ))}
      </div>

      <div className="managerial-context-grid">
        <article>
          <span>Tempo</span>
          <strong>{analysis.context.time.label ?? "Nao detectado"}</strong>
          <small>{analysis.context.time.columns.join(" + ") || "Sem coluna temporal"}</small>
        </article>
        <article>
          <span>Metricas de apoio</span>
          <strong>{supportMetrics.length ? supportMetrics.slice(0, 2).join(", ") : "Nenhuma"}</strong>
          <small>{supportMetrics.length > 2 ? `+${supportMetrics.length - 2} outra(s)` : "Usadas para explicar causas"}</small>
        </article>
        <article>
          <span>Dimensoes</span>
          <strong>{analysis.context.dimensions.map((item) => item.column).join(", ") || "Nao detectadas"}</strong>
          <small>Onde localizar a variacao</small>
        </article>
      </div>

      {analysis.kpis.length ? (
        <div className="managerial-kpis">
          {analysis.kpis.slice(0, 6).map((kpi) => (
            <article key={`${kpi.label}-${kpi.value}`}>
              <span>{kpi.label}</span>
              <strong>{kpi.value}</strong>
              <small>{kpi.detail}</small>
            </article>
          ))}
        </div>
      ) : null}

      <div className="managerial-insight-grid">
        {analysis.insights.slice(0, 4).map((insight) => (
          <article className={`managerial-insight-card severity-${insight.severity}`} key={insight.id}>
            <div>
              <strong>{insight.title}</strong>
              <span>Confianca {insight.confidence}</span>
            </div>
            <p>{insight.how_much}</p>
            <p>{insight.where}</p>
            <ul>
              {insight.possible_causes.slice(0, 2).map((cause) => (
                <li key={cause}>{cause}</li>
              ))}
            </ul>
            <footer>
              <span>{insight.managerial_impact}</span>
              <strong>{insight.recommendation}</strong>
            </footer>
          </article>
        ))}
      </div>

      <div className="managerial-bottom-grid">
        <div className="managerial-list">
          <strong>Alertas</strong>
          {analysis.alerts.slice(0, 3).map((alert) => (
            <p key={alert}>{alert}</p>
          ))}
        </div>
        <div className="managerial-list">
          <strong>Recomendacoes</strong>
          {analysis.recommendations.slice(0, 3).map((recommendation) => (
            <p key={recommendation}>{recommendation}</p>
          ))}
        </div>
        <div className="managerial-list">
          <strong>Perguntas sugeridas</strong>
          {analysis.suggested_questions.slice(0, 4).map((question) => (
            <p key={question}>{question}</p>
          ))}
        </div>
      </div>
    </section>
  );
}

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function QualityAuditView({ audit }: { audit: QualityAudit }) {
  const severityLabels: Record<QualityAuditFinding["severity"], string> = {
    critical: "Critico",
    warning: "Atencao",
    info: "Info",
  };
  const statusLabel =
    audit.ai_status === "completed"
      ? `IA ativa${audit.model ? ` - ${audit.model}` : ""}`
      : audit.ai_status === "failed"
        ? "IA indisponivel"
        : audit.ai_status === "disabled"
          ? "IA desativada"
          : "Regras locais";

  return (
    <div className="quality-audit-panel">
      <div className="quality-audit-header">
        <div>
          <span>Auditoria inteligente</span>
          <strong>{audit.analysis_score}/100</strong>
        </div>
        <small className={`audit-mode status-${audit.ai_status}`}>{statusLabel}</small>
      </div>
      <p>{audit.summary}</p>
      <div className="quality-findings">
        {audit.findings.map((finding) => (
          <article className={`quality-finding severity-${finding.severity}`} key={finding.id}>
            <div>
              <span>{severityLabels[finding.severity]}</span>
              <strong>{finding.title}</strong>
            </div>
            <p>{finding.detail}</p>
            <small>{finding.recommendation}</small>
            {finding.evidence.length ? (
              <ul>
                {finding.evidence.map((item) => (
                  <li key={item}>{item}</li>
                ))}
              </ul>
            ) : null}
          </article>
        ))}
      </div>
      {audit.ai_error ? <small className="audit-error">IA indisponivel: {audit.ai_error}</small> : null}
    </div>
  );
}

function HistoryPanel({ history, onClear }: { history: HistoryItem[]; onClear: () => void }) {
  if (!history.length) return null;

  return (
    <section className="history-strip">
      <div>
        <Clock size={18} />
        <strong>Historico local</strong>
      </div>
      <div className="history-list">
        {history.slice(0, 4).map((item) => (
          <article key={`${item.datasetId}-${item.createdAt}`}>
            <span>{item.fileName}</span>
            <small>
              {item.rows.toLocaleString("pt-BR")} linhas - qualidade {item.qualityScore}/100 - {item.domainLabel}
            </small>
          </article>
        ))}
      </div>
      <button aria-label="Limpar historico" onClick={onClear} type="button">
        <X size={16} />
      </button>
    </section>
  );
}

function DashboardSection({
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

  if (!dashboard) return null;

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

function DashboardCustomization({
  settings,
  onSettingsChange,
}: {
  settings: DashboardSettings;
  onSettingsChange: (settings: DashboardSettings | ((current: DashboardSettings) => DashboardSettings)) => void;
}) {
  function handleLogoUpload(file: File | null) {
    if (!file) return;

    const reader = new FileReader();
    reader.onload = () => {
      onSettingsChange((current) => ({ ...current, logoDataUrl: String(reader.result || "") }));
    };
    reader.readAsDataURL(file);
  }

  return (
    <div className="toolbox-block">
      <div className="toolbox-title">
        <Palette size={17} />
        <strong>Personalizacao</strong>
      </div>
      <label>
        <span>Titulo</span>
        <input
          value={settings.title}
          onChange={(event) => onSettingsChange((current) => ({ ...current, title: event.target.value }))}
        />
      </label>
      <label>
        <span>Tema</span>
        <select
          value={settings.theme}
          onChange={(event) =>
            onSettingsChange((current) => ({ ...current, theme: event.target.value as DashboardTheme }))
          }
        >
          {Object.entries(dashboardThemeMap).map(([key, theme]) => (
            <option key={key} value={key}>
              {theme.label}
            </option>
          ))}
        </select>
      </label>
      <div className="logo-actions">
        <label className="logo-picker">
          <ImagePlus size={16} />
          Logo
          <input accept="image/*" type="file" onChange={(event) => handleLogoUpload(event.target.files?.[0] ?? null)} />
        </label>
        {settings.logoDataUrl ? (
          <button onClick={() => onSettingsChange((current) => ({ ...current, logoDataUrl: null }))} type="button">
            <X size={15} />
          </button>
        ) : null}
      </div>
    </div>
  );
}

function DashboardFiltersPanel({
  controls,
  filters,
  onApply,
  onReset,
}: {
  controls: DashboardFilterControls;
  filters: DashboardFilters;
  onApply: (filters: DashboardFilters) => void;
  onReset: () => void;
}) {
  const [draft, setDraft] = useState<DashboardFilters>(filters);

  useEffect(() => {
    setDraft(filters);
  }, [filters, controls.applied_count, controls.rows_after_filter]);

  function toggleCategory(column: string, value: string) {
    setDraft((current) => {
      const selected = new Set(current.categories[column] ?? []);
      if (selected.has(value)) {
        selected.delete(value);
      } else {
        selected.add(value);
      }

      return {
        ...current,
        categories: {
          ...current.categories,
          [column]: Array.from(selected),
        },
      };
    });
  }

  return (
    <div className="toolbox-block dashboard-filter-block">
      <div className="toolbox-title">
        <Filter size={17} />
        <strong>Filtros</strong>
        <small>
          {controls.rows_after_filter.toLocaleString("pt-BR")} / {controls.rows_before_filter.toLocaleString("pt-BR")} linhas
        </small>
      </div>

      {controls.date ? (
        <div className="date-filter-grid">
          <label>
            <span>Inicio</span>
            <input
              max={controls.date.max}
              min={controls.date.min}
              type="date"
              value={draft.date_from ?? ""}
              onChange={(event) => setDraft((current) => ({ ...current, date_from: event.target.value || undefined }))}
            />
          </label>
          <label>
            <span>Fim</span>
            <input
              max={controls.date.max}
              min={controls.date.min}
              type="date"
              value={draft.date_to ?? ""}
              onChange={(event) => setDraft((current) => ({ ...current, date_to: event.target.value || undefined }))}
            />
          </label>
        </div>
      ) : null}

      <div className="filter-groups">
        {controls.categories.map((category) => (
          <div className="filter-group" key={category.column}>
            <strong>{category.column}</strong>
            <div>
              {category.values.slice(0, 6).map((item) => {
                const selected = (draft.categories[category.column] ?? []).includes(item.value);
                return (
                  <button
                    className={selected ? "is-selected" : ""}
                    key={item.value}
                    onClick={() => toggleCategory(category.column, item.value)}
                    type="button"
                  >
                    {item.value}
                  </button>
                );
              })}
            </div>
          </div>
        ))}
      </div>

      <div className="filter-actions">
        <button onClick={() => onApply(cleanFilters(draft))} type="button">
          Aplicar filtros
        </button>
        <button onClick={onReset} type="button">
          <RotateCcw size={15} />
          Limpar
        </button>
      </div>
    </div>
  );
}

function ChartTypeControl({
  activeType,
  availableTypes,
  onChange,
}: {
  activeType: string;
  availableTypes: string[];
  onChange: (type: string) => void;
}) {
  if (availableTypes.length <= 1) return <small>{activeType}</small>;

  return (
    <div className="chart-type-toggle" aria-label="Tipo do grafico">
      {availableTypes.map((type) => (
        <button className={type === activeType ? "is-active" : ""} key={type} onClick={() => onChange(type)} type="button">
          {type === "line" ? "Linha" : "Barra"}
        </button>
      ))}
    </div>
  );
}

function DashboardKpiCard({ kpi }: { kpi: DashboardKpi }) {
  return (
    <article className={`dashboard-kpi tone-${kpi.tone ?? "neutral"}`}>
      <span>{kpi.label}</span>
      <strong>{kpi.value}</strong>
      <small>{kpi.detail}</small>
    </article>
  );
}

function AnswerView({ answer }: { answer: Answer }) {
  return (
    <div className="answer-box">
      <p>{answer.answer}</p>
      {answer.calculation ? <small>Calculo: {answer.calculation}</small> : null}
      {answer.table.length ? <DataTable rows={answer.table} /> : null}
      {answer.chart ? <AnswerChart chart={answer.chart} /> : null}
    </div>
  );
}

function AnswerChart({ chart }: { chart: ChartPayload }) {
  return <ChartRenderer chart={chart} colors={dashboardThemeMap.teal.series} height={240} />;
}

function ChartRenderer({ chart, colors, height }: { chart: ChartPayload; colors: string[]; height: number }) {
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

function getXAxisProps(chart: ChartPayload) {
  const hasManyPoints = chart.data.length > 10;
  return {
    interval: hasManyPoints ? ("preserveStartEnd" as const) : 0,
    minTickGap: chart.type === "line" || chart.type === "area" ? 18 : 12,
    tick: { fontSize: 11 },
  };
}

function hasActiveFilters(filters: DashboardFilters) {
  return Boolean(
    filters.date_from ||
      filters.date_to ||
      Object.values(filters.categories).some((values) => values.length > 0),
  );
}

function cleanFilters(filters: DashboardFilters): DashboardFilters {
  const categories = Object.fromEntries(
    Object.entries(filters.categories)
      .map(([column, values]) => [column, values.filter(Boolean)])
      .filter(([, values]) => values.length > 0),
  );
  return {
    date_from: filters.date_from || undefined,
    date_to: filters.date_to || undefined,
    categories,
  };
}

function loadHistory(): HistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, 6) : [];
  } catch {
    return [];
  }
}

function saveHistory(upload: UploadResponse, dashboard: DashboardPayload) {
  const nextItem: HistoryItem = {
    datasetId: upload.dataset_id,
    fileName: upload.file_name,
    rows: upload.profile.rows,
    columns: upload.profile.columns,
    qualityScore: upload.quality.score,
    domainLabel: dashboard.domain.label,
    createdAt: new Date().toISOString(),
  };
  const nextHistory = [
    nextItem,
    ...loadHistory().filter((item) => item.fileName !== upload.file_name || item.rows !== upload.profile.rows),
  ].slice(0, 6);
  localStorage.setItem(HISTORY_STORAGE_KEY, JSON.stringify(nextHistory));
  return nextHistory;
}

async function exportDashboardAsPng(
  dashboard: DashboardPayload,
  settings: DashboardSettings,
  charts: DashboardChart[],
  theme: { accent: string; soft: string; series: string[] },
) {
  const width = 1400;
  const chartRows = Math.ceil(Math.min(charts.length, 4) / 2);
  const height = 470 + chartRows * 300 + Math.ceil(dashboard.insights.length / 2) * 54;
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
  drawPill(context, dashboard.domain.label, width - 305, 70, 230, theme.accent, theme.soft);

  let x = 70;
  let y = 170;
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

  y = 330;
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
  context.fillText("Principais leituras", 70, insightY);
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

  const barWidth = width / Math.max(data.length, 1) - 8;
  const baseline = valueToY(0);
  values.forEach((value, index) => {
    const valueY = valueToY(value);
    const barTop = Math.min(baseline, valueY);
    const barHeight = Math.max(Math.abs(valueY - baseline), 2);
    context.fillStyle = colors[index % colors.length];
    context.fillRect(x + index * (barWidth + 8), barTop, Math.max(barWidth, 8), barHeight);
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

function sanitizeFilename(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}

function DataTable({ rows }: { rows: Record<string, CellValue>[] }) {
  if (!rows.length) return <EmptyState text="Sem linhas para exibir." />;

  const columns = Object.keys(rows[0]);
  return (
    <div className="table-wrap">
      <table>
        <thead>
          <tr>
            {columns.map((column) => (
              <th key={column}>{column}</th>
            ))}
          </tr>
        </thead>
        <tbody>
          {rows.map((row, index) => (
            <tr key={index}>
              {columns.map((column) => (
                <td key={column}>{row[column] == null ? "-" : String(row[column])}</td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
