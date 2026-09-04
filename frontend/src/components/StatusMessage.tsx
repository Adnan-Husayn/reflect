interface StatusMessageProps {
  message: string | null;
  tone?: "error" | "info";
}

export function StatusMessage({ message, tone = "error" }: StatusMessageProps) {
  if (!message) return null;
  return (
    <p
      role={tone === "error" ? "alert" : "status"}
      className={tone === "error" ? "status-message status-error" : "status-message status-info"}
    >
      {message}
    </p>
  );
}
