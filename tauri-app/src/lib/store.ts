import { create } from "zustand";

import type { PipelineState } from "./types";
import type { StateSocketStatus } from "./api";

interface AppState {
  state: PipelineState | null;
  status: StateSocketStatus;
  setState: (state: PipelineState) => void;
  setStatus: (status: StateSocketStatus) => void;
}

export const useAppStore = create<AppState>((set) => ({
  state: null,
  status: "connecting",
  setState: (state) => set({ state }),
  setStatus: (status) => set({ status }),
}));
