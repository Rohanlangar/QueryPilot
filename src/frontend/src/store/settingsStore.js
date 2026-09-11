import { create } from 'zustand';

const useSettingsStore = create((set) => ({
  defaultRowLimit: 100,
  defaultChartType: 'auto',
  showSqlByDefault: true,
  queryCompletionAlerts: true,
  costWarningThreshold: 30,
  mode: 'online',
  apiEndpoint: '',
  selectedModel: '',

  updateSettings: (updates) => set((state) => ({ ...state, ...updates })),
}));

export default useSettingsStore;
