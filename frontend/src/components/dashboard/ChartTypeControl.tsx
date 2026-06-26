export function ChartTypeControl({
  activeType,
  availableTypes,
  onChange,
}: {
  activeType: string;
  availableTypes: string[];
  onChange: (type: string) => void;
}) {
  if (availableTypes.length <= 1) return <small>{activeType}</small>;

  function label(type: string) {
    if (type === "line") return "Linha";
    if (type === "area") return "Area";
    if (type === "pie") return "Pizza";
    return "Barra";
  }

  return (
    <div className="chart-type-toggle" aria-label="Tipo do grafico">
      {availableTypes.map((type) => (
        <button className={type === activeType ? "is-active" : ""} key={type} onClick={() => onChange(type)} type="button">
          {label(type)}
        </button>
      ))}
    </div>
  );
}
