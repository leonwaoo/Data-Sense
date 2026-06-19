import {
  BarChart3,
  Database,
  Download,
  FileQuestion,
  FileSpreadsheet,
  LayoutDashboard,
  Lightbulb,
  ShieldCheck,
  Sparkles,
  TrendingUp,
  UploadCloud,
} from "lucide-react";
import type { DragEvent, ReactNode } from "react";
import { useEffect, useMemo, useState } from "react";
import { Bar, BarChart, CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? "https://data-sense-api.onrender.com" : "http://127.0.0.1:8000");

const SUPPORTED_FILE_ACCEPT =
  ".csv,.tsv,.txt,.xlsx,.xls,.json,text/csv,text/tab-separated-values,application/json,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

type CellValue = string | number | boolean | null;

type Profile = {
  dataset_id: string;
  file_name: string;
  rows: number;
  columns: number;
  column_names: string[];
  numeric_columns: string[];
  categorical_columns: string[];
  datetime_columns: string[];
  missing_values: Record<string, number>;
};

type Quality = {
  score: number;
  missing_total: number;
  duplicate_rows: number;
  empty_columns: string[];
  recommendations: string[];
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

type UploadResponse = {
  dataset_id: string;
  file_name: string;
  profile: Profile;
  preview: Record<string, CellValue>[];
  quality: Quality;
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
  quality: {
    score: number;
    missing_total: number;
    duplicate_rows: number;
    empty_columns: string[];
  };
};

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
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [chartSuggestions, setChartSuggestions] = useState<ChartSuggestion[]>([]);
  const [isUploading, setIsUploading] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);
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
      setIsDashboardLoading(true);
      const [suggestions, dashboardPayload] = await Promise.all([
        fetchChartSuggestions(uploadPayload.dataset_id).catch(() => []),
        fetchDashboard(uploadPayload.dataset_id).catch(() => null),
      ]);
      setChartSuggestions(suggestions);
      setDashboard(dashboardPayload);
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Erro inesperado no upload.");
    } finally {
      setIsUploading(false);
      setIsDashboardLoading(false);
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

  async function fetchDashboard(datasetId: string) {
    const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/dashboard`);

    if (!response.ok) return null;
    return (await response.json()) as DashboardPayload;
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

      {dataset ? <DashboardSection dashboard={dashboard} isLoading={isDashboardLoading} /> : null}

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
            <span>{dataset ? `${dataset.quality.missing_total} nulos` : "Sem dados"}</span>
          </div>
          {dataset ? (
            <div className="quality-list">
              <strong>Duplicatas: {dataset.quality.duplicate_rows}</strong>
              <strong>Colunas vazias: {dataset.quality.empty_columns.length}</strong>
              {dataset.quality.recommendations.map((recommendation) => (
                <p key={recommendation}>{recommendation}</p>
              ))}
            </div>
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

function EmptyState({ text }: { text: string }) {
  return <div className="empty-state">{text}</div>;
}

function DashboardSection({ dashboard, isLoading }: { dashboard: DashboardPayload | null; isLoading: boolean }) {
  const [chartTypes, setChartTypes] = useState<Record<string, string>>({});

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
    <section className="panel dashboard-panel">
      <div className="dashboard-heading">
        <div>
          <LayoutDashboard size={22} />
          <div>
            <h2>{dashboard.title}</h2>
            <span>{dashboard.subtitle}</span>
          </div>
        </div>
        <span className="domain-pill">
          {dashboard.domain.label} - {Math.round(dashboard.domain.confidence * 100)}%
        </span>
      </div>

      <div className="dashboard-kpis">
        {dashboard.kpis.map((kpi) => (
          <DashboardKpiCard key={`${kpi.label}-${kpi.value}`} kpi={kpi} />
        ))}
      </div>

      <div className="dashboard-chart-grid">
        {dashboard.charts.map((chart) => {
          const selectedType = chartTypes[chart.id] ?? chart.type;
          return (
            <article className="dashboard-chart-card" key={chart.id}>
              <div className="chart-card-heading">
                <div>
                  <strong>{chart.title}</strong>
                  <span>{chart.subtitle}</span>
                </div>
                <ChartTypeControl
                  activeType={selectedType}
                  availableTypes={chart.available_types ?? [chart.type]}
                  onChange={(type) => setChartTypes((current) => ({ ...current, [chart.id]: type }))}
                />
              </div>
              <ChartRenderer chart={{ ...chart, type: selectedType }} height={250} />
              <p>{chart.insight}</p>
            </article>
          );
        })}
      </div>

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
  return <ChartRenderer chart={chart} height={240} />;
}

function ChartRenderer({ chart, height }: { chart: ChartPayload; height: number }) {
  if (chart.type === "line") {
    return (
      <ResponsiveContainer height={height} width="100%">
        <LineChart data={chart.data}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis dataKey={chart.x} />
          <YAxis />
          <Tooltip />
          <Line dataKey={chart.y} stroke="#0f766e" strokeWidth={3} type="monotone" />
        </LineChart>
      </ResponsiveContainer>
    );
  }

  return (
    <ResponsiveContainer height={height} width="100%">
      <BarChart data={chart.data}>
        <CartesianGrid strokeDasharray="3 3" />
        <XAxis dataKey={chart.x} />
        <YAxis />
        <Tooltip />
        <Bar dataKey={chart.y} fill="#0f766e" radius={[6, 6, 0, 0]} />
      </BarChart>
    </ResponsiveContainer>
  );
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
