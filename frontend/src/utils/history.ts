import { HISTORY_STORAGE_KEY } from "../constants";
import type { DashboardPayload, HistoryItem, UploadResponse } from "../types";

export function loadHistory(): HistoryItem[] {
  try {
    const raw = localStorage.getItem(HISTORY_STORAGE_KEY);
    if (!raw) return [];
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed.slice(0, 6) : [];
  } catch {
    return [];
  }
}

export function saveHistory(upload: UploadResponse, dashboard: DashboardPayload) {
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

export function clearHistory() {
  localStorage.removeItem(HISTORY_STORAGE_KEY);
}
