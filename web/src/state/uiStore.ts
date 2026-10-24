// useUiStore (dev_tasks.md §0.9): cross-panel UI state. The library panel registers its upload entry points so the
// chat's empty state ("Chọn file PDF", drop zone) and "Tải thêm tài liệu" reuse the same upload queue.
import { create } from "zustand";

interface UiState {
  openPicker: (() => void) | null;
  addFiles: ((files: File[]) => void) | null;
  aiAvailable: boolean;
  sessionExpired: boolean;
  registerUpload: (openPicker: () => void, addFiles: (files: File[]) => void) => void;
  setAiAvailable: (v: boolean) => void;
  setSessionExpired: (v: boolean) => void;
}

export const useUiStore = create<UiState>((set) => ({
  openPicker: null,
  addFiles: null,
  aiAvailable: true,
  sessionExpired: false,
  registerUpload: (openPicker, addFiles) => set({ openPicker, addFiles }),
  setAiAvailable: (aiAvailable) => set({ aiAvailable }),
  setSessionExpired: (sessionExpired) => set({ sessionExpired }),
}));
