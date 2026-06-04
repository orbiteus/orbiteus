export interface RealtimeMessage {
  event: string;
  model?: string;
  record_id?: string;
  tenant_id?: string;
  actor?: string | null;
  request_id?: string | null;
  ts?: string | null;
  diff?: Record<string, [unknown, unknown]> | null;
  /** Agent run SSE fields (`agent_run.updated`). */
  run_id?: string;
  status?: string;
  output_text?: string | null;
  tokens_used?: number | null;
  error_message?: string | null;
  tool_trace?: Array<Record<string, unknown>>;
}
