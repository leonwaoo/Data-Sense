import { ArrowRight, Download, FileSpreadsheet, SearchCheck, Sparkles, UploadCloud } from "lucide-react";
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
        <h1>Leve uma planilha bruta para uma leitura executiva clara em poucos minutos.</h1>
        <p>
          Envie CSV, Excel, TSV, TXT ou JSON tabular. O DataSense identifica o contexto do arquivo, monta a leitura
          inicial, mostra os principais movimentos e abre caminho para graficos, chat e exportacao.
        </p>
        <div className="upload-flow">
          <article>
            <strong>1. Envie</strong>
            <span>Carregue a planilha ou use um exemplo pronto para demo.</span>
          </article>
          <article>
            <strong>2. Entenda</strong>
            <span>Receba contexto, risco, oportunidade e comparativos automaticamente.</span>
          </article>
          <article>
            <strong>3. Aja</strong>
            <span>Explore graficos, pergunte aos dados e exporte a leitura executiva.</span>
          </article>
        </div>
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

      <div className="upload-expectations">
        <article>
          <SearchCheck size={18} />
          <div>
            <strong>O que voce recebe logo depois</strong>
            <p>Perfil do arquivo, diagnostico gerencial, leitura por periodo, dashboard inicial e perguntas sugeridas.</p>
          </div>
        </article>
        <article>
          <ArrowRight size={18} />
          <div>
            <strong>Quando vale usar os exemplos</strong>
            <p>Para demonstrar o produto rapidamente, validar layouts e testar vendas, compras, clientes e estoque.</p>
          </div>
        </article>
      </div>

      <div className="upload-samples">
        <span>Comece por um cenario pronto para contar a historia do produto:</span>
        <nav aria-label="Arquivos de teste" className="sample-card-grid">
          {samples.map((file) => (
            <article className="sample-card" key={file.href}>
              <div>
                <strong>{file.label}</strong>
                <p>{file.description}</p>
              </div>
              <span className="sample-action">
                <button disabled={isUploading} onClick={() => onSampleUpload(file)} type="button">
                  Abrir exemplo
                </button>
                <a aria-label={`Baixar ${file.label}`} download href={file.href}>
                  <Download size={15} />
                </a>
              </span>
            </article>
          ))}
        </nav>
      </div>
    </div>
  );
}
