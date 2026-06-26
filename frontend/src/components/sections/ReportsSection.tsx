import { Clock, Download, FileSpreadsheet, X } from "lucide-react";
import type { SampleFile } from "../../constants";
import type { HistoryItem, UploadResponse } from "../../types";

export function ReportsSection({
  dataset,
  exportingFormat,
  history,
  samples,
  isUploading,
  onDownloadReport,
  onDownloadPowerBi,
  onSampleUpload,
  onClearHistory,
}: {
  dataset: UploadResponse;
  exportingFormat: "pdf" | "png" | "powerbi" | null;
  history: HistoryItem[];
  samples: readonly SampleFile[];
  isUploading: boolean;
  onDownloadReport: (format: "pdf" | "png") => void;
  onDownloadPowerBi: () => void;
  onSampleUpload: (sample: SampleFile) => void;
  onClearHistory: () => void;
}) {
  return (
    <div className="section-stack">
      <section className="panel report-strip">
        <div>
          <Download size={18} />
          <strong>Exportacao executiva unificada</strong>
          <span>Resumo executivo, principais mudancas, causa raiz e leituras por dimensao - {dataset.file_name}</span>
        </div>
        <div className="report-actions">
          <button disabled={!!exportingFormat} onClick={() => onDownloadReport("pdf")} type="button">
            <Download size={16} />
            {exportingFormat === "pdf" ? "Gerando PDF..." : "Baixar PDF"}
          </button>
          <button disabled={!!exportingFormat} onClick={() => onDownloadReport("png")} type="button">
            <Download size={16} />
            {exportingFormat === "png" ? "Gerando PNG..." : "Baixar PNG"}
          </button>
          <button disabled={!!exportingFormat} onClick={() => onDownloadPowerBi()} type="button">
            <FileSpreadsheet size={16} />
            {exportingFormat === "powerbi" ? "Gerando Power BI..." : "Power BI"}
          </button>
        </div>
      </section>

      <section className="panel sample-strip">
        <div>
          <FileSpreadsheet size={18} />
          <strong>Arquivos de teste</strong>
        </div>
        <nav aria-label="Arquivos de teste">
          {samples.map((file) => (
            <span className="sample-action" key={file.href}>
              <button disabled={isUploading} onClick={() => onSampleUpload(file)} type="button">
                {file.label}
              </button>
              <a aria-label={`Baixar ${file.label}`} download href={file.href}>
                <Download size={15} />
              </a>
            </span>
          ))}
        </nav>
      </section>

      {history.length ? (
        <section className="panel history-strip">
          <div>
            <Clock size={18} />
            <strong>Historico local</strong>
          </div>
          <div className="history-list">
            {history.slice(0, 4).map((item) => (
              <article key={`${item.datasetId}-${item.createdAt}`}>
                <span>{item.fileName}</span>
                <small>
                  {item.rows.toLocaleString("pt-BR")} linhas - qualidade {item.qualityScore}/100 - {item.domainLabel}
                </small>
              </article>
            ))}
          </div>
          <button aria-label="Limpar historico" onClick={onClearHistory} type="button">
            <X size={16} />
          </button>
        </section>
      ) : null}
    </div>
  );
}
