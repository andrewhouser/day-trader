/** Detect Ollama-specific errors from task error strings. */

const CONNECTION_PATTERNS = [
  /could not reach ollama/i,
  /connection\s*refused/i,
  /max retries exceeded/i,
  /failed to establish a new connection/i,
  /newconnectionerror/i,
  /httpconnectionpool/i,
  /connect timeout/i,
  /name or service not known/i,
  /no route to host/i,
];

const TIMEOUT_PATTERNS = [
  /read timed?\s*out/i,
  /timeout.*ollama/i,
  /ollama.*timeout/i,
  /readtimeout/i,
  /sockettimeout/i,
];

export type OllamaErrorKind = "connection" | "timeout" | null;

export function classifyOllamaError(error: string | null | undefined): OllamaErrorKind {
  if (!error) return null;
  for (const p of CONNECTION_PATTERNS) {
    if (p.test(error)) return "connection";
  }
  for (const p of TIMEOUT_PATTERNS) {
    if (p.test(error)) return "timeout";
  }
  return null;
}

export function ollamaErrorLabel(kind: OllamaErrorKind): string {
  switch (kind) {
    case "connection":
      return "⚡ Ollama unreachable";
    case "timeout":
      return "⏱ Ollama timeout";
    default:
      return "";
  }
}
