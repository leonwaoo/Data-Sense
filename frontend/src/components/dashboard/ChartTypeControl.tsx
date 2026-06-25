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

  return (
    <div className="chart-type-toggle" aria-label="Tipo do grafico">
      {availableTypes.map((type) => (
        <button className={type === activeType ? "is-active" : ""} key={type} onClick={() => onChange(type)} type="button">
          {type === "line" ? "Linha" : "Barra"}
        </button>
      ))}
    </div>
  );
}
