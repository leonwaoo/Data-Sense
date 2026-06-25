import { EmptyState } from "./EmptyState";
import type { CellValue } from "../../types";

export function DataTable({ rows }: { rows: Record<string, CellValue>[] }) {
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
