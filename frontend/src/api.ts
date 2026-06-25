import { API_BASE_URL } from "./constants";
import { hasActiveFilters } from "./utils/filters";
import type { Answer, DashboardFilters, DashboardPayload, UploadResponse } from "./types";

export async function uploadDataset(file: File): Promise<UploadResponse> {
  const formData = new FormData();
  formData.append("file", file);
  const response = await fetch(`${API_BASE_URL}/datasets/upload`, { method: "POST", body: formData });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Nao foi possivel enviar o arquivo.");
  }
  return (await response.json()) as UploadResponse;
}

export async function fetchDashboard(
  datasetId: string,
  filters?: DashboardFilters,
): Promise<DashboardPayload | null> {
  const useFilters = !!filters && hasActiveFilters(filters);
  const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/dashboard`, {
    method: useFilters ? "POST" : "GET",
    headers: useFilters ? { "Content-Type": "application/json" } : undefined,
    body: useFilters ? JSON.stringify(filters) : undefined,
  });
  if (!response.ok) return null;
  return (await response.json()) as DashboardPayload;
}

export async function askQuestion(datasetId: string, question: string): Promise<Answer> {
  const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/ask`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Nao foi possivel responder a pergunta.");
  }
  return (await response.json()) as Answer;
}

function triggerDownload(blob: Blob, fileName: string) {
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = fileName;
  document.body.appendChild(anchor);
  anchor.click();
  anchor.remove();
  URL.revokeObjectURL(url);
}

export async function downloadReport(datasetId: string, fileName: string, format: "pdf" | "png") {
  const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/report.${format}`);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Nao foi possivel gerar o relatorio.");
  }
  const blob = await response.blob();
  triggerDownload(blob, `datasense-relatorio-${fileName.replace(/\.[^.]+$/, "")}.${format}`);
}

export async function downloadPowerBi(datasetId: string, fileName: string) {
  const response = await fetch(`${API_BASE_URL}/datasets/${datasetId}/powerbi.zip`);
  if (!response.ok) {
    const payload = await response.json().catch(() => null);
    throw new Error(payload?.detail || "Nao foi possivel gerar o pacote Power BI.");
  }
  const blob = await response.blob();
  triggerDownload(blob, `datasense-powerbi-${fileName.replace(/\.[^.]+$/, "")}.zip`);
}
