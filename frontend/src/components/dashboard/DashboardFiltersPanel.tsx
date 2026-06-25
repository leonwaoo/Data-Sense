import { Filter, RotateCcw } from "lucide-react";
import { useEffect, useState } from "react";
import { cleanFilters } from "../../utils/filters";
import type { DashboardFilterControls, DashboardFilters } from "../../types";

export function DashboardFiltersPanel({
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
        categories: { ...current.categories, [column]: Array.from(selected) },
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
