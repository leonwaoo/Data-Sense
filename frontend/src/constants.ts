import type { DashboardFilters, DashboardTheme } from "./types";

export const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL ??
  (import.meta.env.PROD ? "https://data-sense-api.onrender.com" : "http://127.0.0.1:8000");

export const SUPPORTED_FILE_ACCEPT =
  ".csv,.tsv,.txt,.xlsx,.xls,.json,text/csv,text/tab-separated-values,application/json,application/vnd.ms-excel,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet";

export const HISTORY_STORAGE_KEY = "datasense-dashboard-history-v1";

export const dashboardThemeMap: Record<
  DashboardTheme,
  { label: string; accent: string; soft: string; series: string[] }
> = {
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

export const defaultDashboardFilters: DashboardFilters = { categories: {} };

export const fallbackSuggestedQuestions = [
  "Quantas linhas e colunas existem?",
  "Qual coluna tem mais valores ausentes?",
  "Existem duplicatas?",
  "Qual o total de vendas?",
  "Mostre compras por mes.",
  "Top 5 fornecedores por compras.",
  "Mostre clientes por valor.",
  "Mostre quantidade por categoria.",
];

export const sampleFiles = [
  { label: "Vendas CSV", fileName: "vendas_demo.csv", href: "/samples/vendas_demo.csv" },
  { label: "Vendas Excel", fileName: "vendas_demo.xlsx", href: "/samples/vendas_demo.xlsx" },
  { label: "Compras Excel", fileName: "compras_demo.xlsx", href: "/samples/compras_demo.xlsx" },
  { label: "Clientes JSON", fileName: "clientes_demo.json", href: "/samples/clientes_demo.json" },
  { label: "Estoque TSV", fileName: "estoque_financeiro_demo.tsv", href: "/samples/estoque_financeiro_demo.tsv" },
];

export type SampleFile = (typeof sampleFiles)[number];

export const numberFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 2 });
export const percentFormatter = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 1, style: "percent" });
