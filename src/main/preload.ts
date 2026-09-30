import { contextBridge, ipcRenderer } from 'electron';

export interface IElectronAPI {
  getVacancies: (listName?: string) => Promise<any>;
  moveVacancy: (vacancyId: string, newList: string) => Promise<any>;
  updateCustomization: (vacancyId: string, resumeId: string, materials: string[], coverLetter: string) => Promise<any>;
  applyVacancy: (vacancyId: string) => Promise<any>;
  runScan: () => Promise<any>;
  scanHH: () => Promise<any>;
  checkNegotiations: () => Promise<any>;
  clearArchive: () => Promise<any>;
  fetchHhResumes: () => Promise<any>;
  getSettings: () => Promise<any>;
  setSetting: (key: string, value: string) => Promise<any>;
  checkHhAuth: () => Promise<any>;
  startHhAuth: () => Promise<any>;
  getKnowledge: (name: string) => Promise<any>;
  saveKnowledge: (name: string, content: string) => Promise<any>;
  migratePlanka: () => Promise<any>;
  generateLetter: (vacancyId: string) => Promise<any>;
  applyApproved: () => Promise<any>;
  refetchVacancy: (vacancyId: string) => Promise<any>;
  onNegotiationUpdate: (callback: (data: any) => void) => void;
  onEngineLog: (callback: (data: any) => void) => void;
}

const api: IElectronAPI = {
  getVacancies: (listName?: string) => ipcRenderer.invoke('get-vacancies', listName),
  moveVacancy: (vacancyId: string, newList: string) => ipcRenderer.invoke('move-vacancy', vacancyId, newList),
  updateCustomization: (vacancyId: string, resumeId: string, materials: string[], coverLetter: string) =>
    ipcRenderer.invoke('update-customization', vacancyId, resumeId, materials, coverLetter),
  applyVacancy: (vacancyId: string) => ipcRenderer.invoke('apply-vacancy', vacancyId),
  runScan: () => ipcRenderer.invoke('run-scan'),
  scanHH: () => ipcRenderer.invoke('run-scan'),
  checkNegotiations: () => ipcRenderer.invoke('check-negotiations'),
  clearArchive: () => ipcRenderer.invoke('clear-archive'),
  fetchHhResumes: () => ipcRenderer.invoke('fetch-hh-resumes'),
  getSettings: () => ipcRenderer.invoke('get-settings'),
  setSetting: (key: string, value: string) => ipcRenderer.invoke('set-setting', key, value),
  checkHhAuth: () => ipcRenderer.invoke('check-hh-auth'),
  startHhAuth: () => ipcRenderer.invoke('start-hh-auth'),
  getKnowledge: (name: string) => ipcRenderer.invoke('get-knowledge', name),
  saveKnowledge: (name: string, content: string) => ipcRenderer.invoke('save-knowledge', name, content),
  migratePlanka: () => ipcRenderer.invoke('migrate-planka'),
  generateLetter: (vacancyId: string) => ipcRenderer.invoke('generate-letter', vacancyId),
  applyApproved: () => ipcRenderer.invoke('apply-approved'),
  refetchVacancy: (vacancyId: string) => ipcRenderer.invoke('refetch-vacancy', vacancyId),
  onNegotiationUpdate: (callback: (data: any) => void) => {
    ipcRenderer.on('negotiations-update', (_event, value) => callback(value));
  },
  onEngineLog: (callback: (data: any) => void) => {
    ipcRenderer.on('engine-log', (_event, value) => callback(value));
  },
};

contextBridge.exposeInMainWorld('electronAPI', api);
