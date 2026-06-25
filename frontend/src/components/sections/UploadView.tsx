import { Download, FileSpreadsheet, Sparkles, UploadCloud } from "lucide-react";
import type { DragEvent } from "react";
import { SUPPORTED_FILE_ACCEPT } from "../../constants";
import type { SampleFile } from "../../constants";

export function UploadView({
  samples,
  isUploading,
  isDragOver,
  onUpload,
  onSampleUpload,
  onDragOver,
  onDragLeave,
  onDrop,
}: {
  samples: readonly SampleFile[];
  isUploading: boolean;
  isDragOver: boolean;
  onUpload: (file: File | null) => void;
  onSampleUpload: (sample: SampleFile) => void;
  onDragOver: (event: DragEvent<HTMLLabelElement>) => void;
  onDragLeave: (event: DragEvent<HTMLLabelElement>) => void;
  onDrop: (event: DragEvent<HTMLLabelElement>) => void;
}) {
  return (
    <div className="upload-view">
      <div className="upload-hero">
        <span className="eyebrow">
          <Sparkles size={15} /> DataSense
        </span>
        <h1>Transforme planilhas em respostas, graficos e alertas de qualidade.</h1>
        <p>
          Envie CSV, Excel, TSV, TXT ou JSON tabular e acompanhe a evolucao mes a mes com leituras gerenciais
          calculadas diretamente no seu dataset.
        </p>
      </div>

      <label
        className={`dropzone${isDragOver ? " is-dragover" : ""}${isUploading ? " is-uploading" : ""}`}
        onDragLeave={onDragLeave}
        onDragOver={onDragOver}
        onDrop={onDrop}
      >
        <span className="dropzone-icon">
          {isUploading ? <FileSpreadsheet size={26} /> : <UploadCloud size={26} />}
        </span>
        <strong>{isUploading ? "Enviando arquivo..." : "Arraste o arquivo aqui"}</strong>
        <p>ou clique para selecionar uma planilha</p>
        <small>CSV, TSV, TXT, XLSX, XLS ou JSON ate 15 MB</small>
        <input
          accept={SUPPORTED_FILE_ACCEPT}
          disabled={isUploading}
          type="file"
          onChange={(event) => {
            onUpload(event.target.files?.[0] ?? null);
            event.currentTarget.value = "";
          }}
        />
      </label>

      <div className="upload-samples">
        <span>Ou comece com um exemplo:</span>
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
      </div>
    </div>
  );
}
