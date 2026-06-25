import { Send } from "lucide-react";
import { fallbackSuggestedQuestions } from "../../constants";
import { AnswerView } from "../chat/AnswerView";
import { DataTable } from "../common/DataTable";
import type { Answer, UploadResponse } from "../../types";

export function ChatSection({
  dataset,
  question,
  answer,
  isAsking,
  onQuestionChange,
  onAsk,
}: {
  dataset: UploadResponse;
  question: string;
  answer: Answer | null;
  isAsking: boolean;
  onQuestionChange: (value: string) => void;
  onAsk: (question?: string) => void;
}) {
  const suggestions = dataset.suggested_questions?.length
    ? dataset.suggested_questions.map((item) => item.question)
    : fallbackSuggestedQuestions;

  return (
    <div className="section-stack">
      <section className="panel chat-panel">
        <div className="panel-heading">
          <h2>Chat analitico</h2>
          <span>Pergunte em linguagem natural</span>
        </div>

        <div className="suggestions">
          {suggestions.map((suggestion) => (
            <button disabled={isAsking} key={suggestion} onClick={() => onAsk(suggestion)} type="button">
              {suggestion}
            </button>
          ))}
        </div>

        <div className="ask-row">
          <input
            disabled={isAsking}
            onChange={(event) => onQuestionChange(event.target.value)}
            onKeyDown={(event) => {
              if (event.key === "Enter") onAsk();
            }}
            placeholder="Ex.: Qual produto mais vendeu?"
            value={question}
          />
          <button disabled={isAsking || !question.trim()} onClick={() => onAsk()} type="button">
            <Send size={16} />
            {isAsking ? "Analisando..." : "Perguntar"}
          </button>
        </div>

        {answer ? <AnswerView answer={answer} /> : null}
      </section>

      <section className="panel">
        <div className="panel-heading">
          <h2>Preview dos dados</h2>
          <span>Primeiras linhas</span>
        </div>
        <DataTable rows={dataset.preview} />
      </section>
    </div>
  );
}
