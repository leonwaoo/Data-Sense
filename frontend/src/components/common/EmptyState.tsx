export function EmptyState({ text }: { text: string }) {
  return (
    <div className="empty-state">
      <strong>Conteudo ainda nao disponivel</strong>
      <span>{text}</span>
    </div>
  );
}
