export type TokenUsage = {
  prompt: number;
  completion: number;
  total: number;
};

export type RouteDecision = {
  decision?: string;
  next_agent?: string;
  reason?: string;
};

export type InterviewState = {
  session_id: string;
  candidate_id: string;
  messages: Array<Record<string, unknown>>;
  trace_id: string;
  token_usage: TokenUsage;
  current_step: string;
  is_safe: boolean;
  round_status?: string;
  route_decision?: RouteDecision;
  active_agent?: string;
};

export type WsEnvelope =
  | { type: "session_state"; payload: InterviewState }
  | { type: "pong"; trace_id: string };

