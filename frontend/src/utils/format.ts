import { numberFormatter, percentFormatter } from "../constants";

export function formatNumberCell(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? numberFormatter.format(value) : "-";
}

export function formatSignedCell(value: number | null | undefined) {
  if (typeof value !== "number" || !Number.isFinite(value)) return "-";
  return `${value >= 0 ? "+" : "-"}${numberFormatter.format(Math.abs(value))}`;
}

export function formatPercentCell(value: number | null | undefined) {
  return typeof value === "number" && Number.isFinite(value) ? percentFormatter.format(value) : "-";
}

export function sanitizeFilename(value: string) {
  return value
    .toLowerCase()
    .normalize("NFD")
    .replace(/[\u0300-\u036f]/g, "")
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")
    .slice(0, 80);
}
