import { formatNumberCell, formatSignedCell } from "../../utils/format";
import type { CSSProperties } from "react";
import type { RootCauseWaterfallStep } from "../../types";

export function WaterfallMiniChart({ steps }: { steps: RootCauseWaterfallStep[] }) {
  if (!steps.length) {
    return (
      <div className="root-cause-waterfall">
        <strong>Waterfall</strong>
        <p>Sem passos suficientes para montar a ponte de variacao.</p>
      </div>
    );
  }

  const magnitudes = steps.map((step) => Math.abs(step.delta ?? step.value ?? 0));
  const maxMagnitude = Math.max(...magnitudes, 1);

  return (
    <div className="root-cause-waterfall">
      <div>
        <strong>Waterfall da variacao</strong>
        <span>Inicio, contribuicoes e fim</span>
      </div>
      <div className="waterfall-steps">
        {steps.slice(0, 7).map((step) => {
          const displayValue = step.delta ?? step.value;
          const width = Math.max(8, Math.min(100, (Math.abs(displayValue ?? 0) / maxMagnitude) * 100));
          const style = { "--bar-width": `${width}%` } as CSSProperties;
          return (
            <div className={`waterfall-step kind-${step.kind}`} key={`${step.kind}-${step.label}`}>
              <span>{step.label}</span>
              <div className="waterfall-bar-track">
                <i style={style} />
              </div>
              <strong>{step.delta === null || step.delta === undefined ? formatNumberCell(step.value) : formatSignedCell(step.delta)}</strong>
            </div>
          );
        })}
      </div>
    </div>
  );
}
