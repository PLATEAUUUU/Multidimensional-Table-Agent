import { create } from "zustand";
import type { InterviewState } from "../types/interview";

type ConnectionState = "idle" | "connecting" | "connected" | "retrying" | "closed";

type InterviewStore = {
  backendState: InterviewState | null;
  selectedStep: string;
  connectionState: ConnectionState;
  reconnectAttempts: number;
  lockReason: string | null;
  setConnectionState: (state: ConnectionState) => void;
  setReconnectAttempts: (value: number) => void;
  incrementReconnectAttempts: () => void;
  hydrateFromBackend: (state: InterviewState) => void;
  setSelectedStep: (step: string) => void;
};

export const useInterviewStore = create<InterviewStore>((set) => ({
  backendState: null,
  selectedStep: "init",
  connectionState: "idle",
  reconnectAttempts: 0,
  lockReason: null,
  setConnectionState: (connectionState) => set({ connectionState }),
  setReconnectAttempts: (reconnectAttempts) => set({ reconnectAttempts }),
  incrementReconnectAttempts: () =>
    set((current) => ({ reconnectAttempts: current.reconnectAttempts + 1 })),
  hydrateFromBackend: (backendState) =>
    set((current) => {
      const shouldLock = current.selectedStep !== backendState.current_step;
      return {
        backendState,
        lockReason: shouldLock
          ? `当前后端流程处于 ${backendState.current_step}，前端操作已锁定。`
          : null
      };
    }),
  setSelectedStep: (selectedStep) =>
    set((current) => {
      const shouldLock = current.backendState !== null && current.backendState.current_step !== selectedStep;
      return {
        selectedStep: shouldLock ? current.selectedStep : selectedStep,
        lockReason: shouldLock
          ? `当前后端流程处于 ${current.backendState?.current_step ?? "unknown"}，前端操作已锁定。`
          : null
      };
    })
}));
