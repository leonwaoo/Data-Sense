import { dashboardThemeMap } from "../../constants";
import { ChartRenderer } from "../common/ChartRenderer";
import { DataTable } from "../common/DataTable";
import type { Answer, ChartPayload } from "../../types";

function AnswerChart({ chart }: { chart: ChartPayload }) {
  return <ChartRenderer chart={chart} colors={dashboardThemeMap.teal.series} height={240} />;
}

export function AnswerView({ answer }: { answer: Answer }) {
  return (
    <div className="answer-box">
      <p>{answer.answer}</p>
      {answer.calculation ? <small>Calculo: {answer.calculation}</small> : null}
      {answer.table.length ? <DataTable rows={answer.table} /> : null}
      {answer.chart ? <AnswerChart chart={answer.chart} /> : null}
    </div>
  );
}
