interface EmptyStateProps {
  title: string;
  /** Say what to do about it — an empty axis explains nothing. */
  children: React.ReactNode;
}

export function EmptyState({ title, children }: EmptyStateProps) {
  return (
    <div className="empty-state" role="status">
      <h3>{title}</h3>
      <p>{children}</p>
    </div>
  );
}
