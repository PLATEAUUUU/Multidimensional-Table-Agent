import type { InterviewState } from "../types/interview";

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? "http://localhost:8000/api/v1";

export async function fetchInitialSession(sessionId: string): Promise<InterviewState> {
  const response = await fetch(`${API_BASE_URL}/sessions/${sessionId}`);
  if (!response.ok) {
    throw new Error("Failed to fetch initial session state");
  }
  return response.json() as Promise<InterviewState>;
}

