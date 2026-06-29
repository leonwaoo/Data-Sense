import { AlertCircle, UploadCloud } from "lucide-react";
import { Suspense, lazy, useEffect, useRef, useState } from "react";
import type { DragEvent } from "react";
import {
  askQuestion,
  downloadPowerBi as apiDownloadPowerBi,
  downloadReport as apiDownloadReport,
  fetchDashboard,
  fetchManagerialAiReview,
  uploadDataset,
} from "./api";
import { SUPPORTED_FILE_ACCEPT, defaultDashboardFilters, sampleFiles } from "./constants";
import type { SampleFile } from "./constants";
import { Sidebar } from "./components/layout/Sidebar";
import { UploadView } from "./components/sections/UploadView";
import { clearHistory, loadHistory, saveHistory } from "./utils/history";
import type {
  Answer,
  DashboardFilters,
  DashboardPayload,
  DashboardSettings,
  HistoryItem,
  ManagerialAiReview,
  SectionKey,
  UploadResponse,
} from "./types";

const OverviewSection = lazy(async () => {
  const module = await import("./components/sections/OverviewSection");
  return { default: module.OverviewSection };
});

const DiagnosticSection = lazy(async () => {
  const module = await import("./components/sections/DiagnosticSection");
  return { default: module.DiagnosticSection };
});

const DashboardSection = lazy(async () => {
  const module = await import("./components/sections/DashboardSection");
  return { default: module.DashboardSection };
});

const DetailsSection = lazy(async () => {
  const module = await import("./components/sections/DetailsSection");
  return { default: module.DetailsSection };
});

const ChatSection = lazy(async () => {
  const module = await import("./components/sections/ChatSection");
  return { default: module.ChatSection };
});

const ReportsSection = lazy(async () => {
  const module = await import("./components/sections/ReportsSection");
  return { default: module.ReportsSection };
});

function firstAvailableText(...values: Array<string | null | undefined>) {
  return values.find((value) => value && value.trim()) ?? "n/d";
}

const SECTION_META: Record<SectionKey, { title: string; subtitle: string }> = {
  overview: { title: "Inicio", subtitle: "Resumo inicial para saber o que mudou, onde olhar e qual acao priorizar" },
  diagnostic: { title: "Diagnostico gerencial", subtitle: "Causa raiz provavel, impacto do movimento e acoes recomendadas" },
  dashboard: { title: "Graficos", subtitle: "Painel visual para confirmar movimentos, comparar recortes e aplicar filtros" },
  details: { title: "Detalhes", subtitle: "Estrutura do arquivo, confianca dos dados e indicadores usados na leitura" },
  chat: { title: "Chat analitico", subtitle: "Pergunte em linguagem natural para aprofundar a analise do arquivo" },
  reports: { title: "Relatorios", subtitle: "Exportacoes, exemplos prontos e historico para demonstracoes" },
};

export function App() {
  const [dataset, setDataset] = useState<UploadResponse | null>(null);
  const [section, setSection] = useState<SectionKey>("overview");
  const [dashboard, setDashboard] = useState<DashboardPayload | null>(null);
  const [managerialAiReview, setManagerialAiReview] = useState<ManagerialAiReview | null>(null);
  const [managerialAiModel, setManagerialAiModel] = useState("openai/gpt-4o-mini");
  const [dashboardFilters, setDashboardFilters] = useState<DashboardFilters>(defaultDashboardFilters);
  const [dashboardSettings, setDashboardSettings] = useState<DashboardSettings>({
    title: "Dashboard DataSense",
    theme: "teal",
    logoDataUrl: null,
  });
  const [history, setHistory] = useState<HistoryItem[]>(loadHistory);
  const [question, setQuestion] = useState("");
  const [answer, setAnswer] = useState<Answer | null>(null);
  const [isUploading, setIsUploading] = useState(false);
  const [isDashboardLoading, setIsDashboardLoading] = useState(false);
  const [isManagerialAiLoading, setIsManagerialAiLoading] = useState(false);
  const [isDragOver, setIsDragOver] = useState(false);
  const [isAsking, setIsAsking] = useState(false);
  const [exportingFormat, setExportingFormat] = useState<"pdf" | "png" | "powerbi" | null>(null);
  const [error, setError] = useState<string | null>(null);
  const fileInputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    const sampleName = new URLSearchParams(window.location.search).get("sample");
    const sample = sampleFiles.find((file) => file.fileName === sampleName);
    if (sample) void handleSampleUpload(sample);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function handleUpload(file: File | null) {
    if (!file) return;

    setIsUploading(true);
    setError(null);
    setAnswer(null);
    setDashboard(null);
    setManagerialAiReview(null);
    setDashboardFilters(defaultDashboardFilters);

    try {
      const uploadPayload = await uploadDataset(file);
      setDataset(uploadPayload);
      setSection("overview");
      setDashboardSettings((current) => ({
        ...current,
        title: `Dashboard - ${uploadPayload.file_name.replace(/\.[^.]+$/, "")}`,
      }));
      setIsDashboardLoading(true);
      const dashboardPayload = await fetchDashboard(uploadPayload.dataset_id).catch(() => null);
      setDashboard(dashboardPayload);
      if (dashboardPayload) {
        setHistory(saveHistory(uploadPayload, dashboardPayload));
      }
    } catch (uploadError) {
      setError(uploadError instanceof Error ? uploadError.message : "Erro inesperado no upload.");
    } finally {
      setIsUploading(false);
      setIsDashboardLoading(false);
    }
  }

  async function handleSampleUpload(sample: SampleFile) {
    setError(null);
    try {
      const response = await fetch(sample.href);
      if (!response.ok) throw new Error("Nao foi possivel carregar o arquivo de teste.");
      const blob = await response.blob();
      const file = new File([blob], sample.fileName, { type: blob.type || "application/octet-stream" });
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

  function handleApplyManagerialPeriod(period: { date_from: string; date_to: string }) {
    setSection("dashboard");
    void handleApplyDashboardFilters({
      ...dashboardFilters,
      date_from: period.date_from,
      date_to: period.date_to,
    });
  }

  function handleClearHistory() {
    clearHistory();
    setHistory([]);
  }

  async function handleAsk(nextQuestion = question) {
    if (!dataset || !nextQuestion.trim()) return;
    setQuestion(nextQuestion);
    setIsAsking(true);
    setError(null);
    try {
      setAnswer(await askQuestion(dataset.dataset_id, nextQuestion));
    } catch (askError) {
      setError(askError instanceof Error ? askError.message : "Erro inesperado na pergunta.");
    } finally {
      setIsAsking(false);
    }
  }

  async function handleManagerialAiReview(model = managerialAiModel) {
    if (!dataset) return;
    setIsManagerialAiLoading(true);
    setError(null);
    try {
      setManagerialAiReview(await fetchManagerialAiReview(dataset.dataset_id, model));
    } catch (reviewError) {
      setError(reviewError instanceof Error ? reviewError.message : "Erro inesperado na leitura gerencial com IA.");
    } finally {
      setIsManagerialAiLoading(false);
    }
  }

  async function handleDownloadReport(format: "pdf" | "png") {
    if (!dataset) return;
    setExportingFormat(format);
    setError(null);
    try {
      await apiDownloadReport(dataset.dataset_id, dataset.file_name, format);
    } catch (reportError) {
      setError(reportError instanceof Error ? reportError.message : "Erro inesperado ao gerar relatorio.");
    } finally {
      setExportingFormat(null);
    }
  }

  async function handleDownloadPowerBi() {
    if (!dataset) return;
    setExportingFormat("powerbi");
    setError(null);
    try {
      await apiDownloadPowerBi(dataset.dataset_id, dataset.file_name);
    } catch (powerBiError) {
      setError(powerBiError instanceof Error ? powerBiError.message : "Erro inesperado ao gerar pacote Power BI.");
    } finally {
      setExportingFormat(null);
    }
  }

  const meta = SECTION_META[section];
  const domainLabel = firstAvailableText(dataset?.managerial_analysis?.context.domain.label, dashboard?.domain.label);
  const primaryMetric = firstAvailableText(dataset?.managerial_analysis?.context.metric_map.primary_metric);
  const periodLabel = firstAvailableText(dataset?.managerial_analysis?.context.time.label);
  const qualityLabel = dataset ? `${dataset.quality.score}/100` : "n/d";

  return (
    <div className="app-shell">
      <Sidebar
        active={section}
        dataset={dataset}
        onNavigate={setSection}
        onNewFile={() => fileInputRef.current?.click()}
      />

      <input
        accept={SUPPORTED_FILE_ACCEPT}
        hidden
        ref={fileInputRef}
        type="file"
        onChange={(event) => {
          void handleUpload(event.target.files?.[0] ?? null);
          event.currentTarget.value = "";
        }}
      />

      <main className="app-content">
        {dataset ? (
          <header className="content-header">
            <div className="content-header-copy">
              <h1>{meta.title}</h1>
              <p>{meta.subtitle}</p>
            </div>
            <button className="header-upload" disabled={isUploading} onClick={() => fileInputRef.current?.click()} type="button">
              <UploadCloud size={16} />
              {isUploading ? "Enviando..." : "Trocar arquivo"}
            </button>
          </header>
        ) : null}

        {error ? (
          <div className="error-banner">
            <AlertCircle size={16} />
            {error}
          </div>
        ) : null}

        {dataset ? (
          <section className="context-strip" aria-label="Resumo do arquivo carregado">
            <article>
              <span>Arquivo</span>
              <strong>{dataset.file_name}</strong>
              <small>{dataset.profile.rows.toLocaleString("pt-BR")} linhas e {dataset.profile.columns} colunas</small>
            </article>
            <article>
              <span>Contexto</span>
              <strong>{domainLabel}</strong>
              <small>Leitura detectada automaticamente a partir da estrutura do arquivo</small>
            </article>
            <article>
              <span>Indicador principal</span>
              <strong>{primaryMetric}</strong>
              <small>Base usada na leitura executiva e nos comparativos</small>
            </article>
            <article>
              <span>Periodo e confianca</span>
              <strong>{periodLabel}</strong>
              <small>Qualidade dos dados: {qualityLabel}</small>
            </article>
          </section>
        ) : null}

        <div className="content-body" key={dataset ? section : "upload"}>
          {!dataset ? (
            <UploadView
              isDragOver={isDragOver}
              isUploading={isUploading}
              samples={sampleFiles}
              onDragLeave={handleDragLeave}
              onDragOver={handleDragOver}
              onDrop={handleDrop}
              onSampleUpload={(sample) => void handleSampleUpload(sample)}
              onUpload={(file) => void handleUpload(file)}
            />
          ) : (
            <Suspense fallback={<div className="panel section-loading">Carregando secao...</div>}>
              {section === "overview" ? (
                <OverviewSection dataset={dataset} onApplyPeriodToDashboard={handleApplyManagerialPeriod} />
              ) : section === "diagnostic" ? (
                <DiagnosticSection
                  aiReview={managerialAiReview}
                  aiModel={managerialAiModel}
                  analysis={dataset.managerial_analysis}
                  isManagerialAiLoading={isManagerialAiLoading}
                  onManagerialAiModelChange={setManagerialAiModel}
                  onManagerialAiReview={(model) => void handleManagerialAiReview(model)}
                />
              ) : section === "dashboard" ? (
                <DashboardSection
                  dashboard={dashboard}
                  filters={dashboardFilters}
                  isLoading={isDashboardLoading}
                  settings={dashboardSettings}
                  onApplyFilters={(filters) => void handleApplyDashboardFilters(filters)}
                  onResetFilters={handleResetDashboardFilters}
                  onSettingsChange={setDashboardSettings}
                />
              ) : section === "details" ? (
                <DetailsSection dashboard={dashboard} dataset={dataset} />
              ) : section === "chat" ? (
                <ChatSection
                  answer={answer}
                  dataset={dataset}
                  isAsking={isAsking}
                  question={question}
                  onAsk={handleAsk}
                  onQuestionChange={setQuestion}
                />
              ) : (
                <ReportsSection
                  dataset={dataset}
                  exportingFormat={exportingFormat}
                  history={history}
                  isUploading={isUploading}
                  samples={sampleFiles}
                  onClearHistory={handleClearHistory}
                  onDownloadPowerBi={() => void handleDownloadPowerBi()}
                  onDownloadReport={(format) => void handleDownloadReport(format)}
                  onSampleUpload={(sample) => void handleSampleUpload(sample)}
                />
              )}
            </Suspense>
          )}
        </div>
      </main>
    </div>
  );
}
