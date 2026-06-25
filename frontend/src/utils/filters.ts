import type { DashboardFilters } from "../types";

export function hasActiveFilters(filters: DashboardFilters) {
  return Boolean(
    filters.date_from ||
      filters.date_to ||
      Object.values(filters.categories).some((values) => values.length > 0),
  );
}

export function cleanFilters(filters: DashboardFilters): DashboardFilters {
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
