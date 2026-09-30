import React, { useState, useEffect } from 'react';
import { KanbanBoard } from './components/Board/KanbanBoard';
import { SettingsView } from './components/Settings/SettingsView';
import { LogModal } from './components/LogModal/LogModal';
import { Vacancy, AppSettings, LogEntry } from './types';
import { LayoutGrid, Settings, RefreshCw, Briefcase, CheckCircle2, AlertCircle, Terminal, Send, Search, Loader2, ClipboardCheck } from 'lucide-react';

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<'board' | 'settings'>('board');
  const [vacancies, setVacancies] = useState<Vacancy[]>([]);
  const [settings, setSettings] = useState<AppSettings>({
    hh_token: '',
    hh_xsrf: '',
    llm_provider: 'gemini',
    llm_api_key: '',
    llm_model: 'gemini-2.0-flash',
    scan_time: '11:00',
    check_interval_min: '30',
    search_queries: '[]',
  });
  const [hhStatus, setHhStatus] = useState<{ authenticated: boolean; user?: string }>({ authenticated: false });
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [logs, setLogs] = useState<LogEntry[]>([]);
  const [isLogModalOpen, setIsLogModalOpen] = useState(false);
  const [isScanning, setIsScanning] = useState(false);
  const [isCheckingNeg, setIsCheckingNeg] = useState(false);
  const [isBatchApplying, setIsBatchApplying] = useState(false);

  const electronAPI = (window as any).electronAPI;

  const loadData = async () => {
    setIsRefreshing(true);
    try {
      if (electronAPI) {
        const vRes = await electronAPI.getVacancies();
        if (vRes.success) setVacancies(vRes.vacancies || []);

        const sRes = await electronAPI.getSettings();
        if (sRes.success) setSettings(sRes.settings || {});

        const aRes = await electronAPI.checkHhAuth();
        setHhStatus(aRes);
      }
    } catch (e) {
      console.error('Error loading data:', e);
    } finally {
      setIsRefreshing(false);
    }
  };

  useEffect(() => {
    loadData();

    if (electronAPI) {
      electronAPI.onNegotiationUpdate(() => {
        loadData();
      });

      electronAPI.onEngineLog((log: LogEntry) => {
        setLogs((prev) => [...prev.slice(-499), log]);
      });
    }
  }, []);

  const handleMoveVacancy = async (id: string, targetList: Vacancy['list_name']) => {
    if (electronAPI) {
      await electronAPI.moveVacancy(id, targetList);
      setVacancies((prev) =>
        prev.map((v) => (v.id === id ? { ...v, list_name: targetList } : v))
      );
    }
  };

  const handleUpdateCustomization = async (id: string, resumeId: string, materials: string[], letter: string) => {
    if (electronAPI) {
      await electronAPI.updateCustomization(id, resumeId, materials, letter);
      setVacancies((prev) =>
        prev.map((v) =>
          v.id === id
            ? { ...v, selected_resume_id: resumeId, selected_materials: materials, cover_letter: letter }
            : v
        )
      );
    }
  };

  const handleApplyVacancy = async (id: string) => {
    if (electronAPI) {
      const res = await electronAPI.applyVacancy(id);
      if (!res.success) {
        throw new Error(res.error || 'Ошибка отправки отклика');
      }
      setVacancies((prev) =>
        prev.map((v) => (v.id === id ? { ...v, list_name: 'applied' } : v))
      );
    }
  };

  const handleTriggerScan = async () => {
    if (electronAPI) {
      setIsScanning(true);
      try {
        await electronAPI.runScan();
      } catch (err) {
        console.error('Scan error:', err);
      } finally {
        setIsScanning(false);
        await loadData();
      }
    }
  };

  const handleBatchApply = async () => {
    if (electronAPI) {
      setIsBatchApplying(true);
      try {
        await electronAPI.applyApproved();
      } catch (err) {
        console.error('Batch apply error:', err);
      } finally {
        setIsBatchApplying(false);
        await loadData();
      }
    }
  };

  const handleSaveSetting = async (key: string, value: string) => {
    if (electronAPI) {
      await electronAPI.setSetting(key, value);
      setSettings((prev) => ({ ...prev, [key]: value }));
    }
  };

  const handleTriggerNegotiations = async () => {
    if (electronAPI) {
      setIsCheckingNeg(true);
      try {
        await electronAPI.checkNegotiations();
        await loadData();
      } catch (err) {
        console.error('Negotiations check error:', err);
      } finally {
        setIsCheckingNeg(false);
      }
    }
  };

  const handleLoadKnowledge = async (name: string): Promise<string> => {
    if (electronAPI) {
      const res = await electronAPI.getKnowledge(name);
      return res.content || '';
    }
    return '';
  };

  const handleSaveKnowledge = async (name: string, content: string): Promise<boolean> => {
    if (electronAPI) {
      const res = await electronAPI.saveKnowledge(name, content);
      return res.success || false;
    }
    return false;
  };

  const backlogCount = vacancies.filter((v) => v.list_name === 'backlog').length;
  const approvedCount = vacancies.filter((v) => v.list_name === 'approved').length;

  return (
    <div className="h-screen w-screen flex flex-col bg-planka-bg text-planka-text overflow-hidden">
      
      {/* Top Application Bar */}
      <header className="h-14 border-b border-planka-border/50 bg-planka-sidebar px-4 flex items-center justify-between flex-shrink-0 select-none shadow-md z-10 gap-3">
        
        {/* Left: Brand + Quick Stats */}
        <div className="flex items-center gap-5 flex-shrink-0">
          <div className="flex items-center gap-2.5">
            <div className="w-8 h-8 rounded-lg bg-planka-accent flex items-center justify-center text-white shadow-sm shadow-indigo-900/50">
              <Briefcase className="w-4 h-4" />
            </div>
            <div>
              <span className="font-extrabold text-sm text-white tracking-tight">Job Hunter</span>
              <span className="ml-2 text-[10px] font-mono text-planka-accent bg-planka-accent/15 px-1.5 py-0.5 rounded border border-planka-accent/30">
                v1.0 Desktop
              </span>
            </div>
          </div>

          {/* Quick Counters */}
          <div className="hidden lg:flex items-center gap-2 text-xs">
            <span className="text-planka-textMuted">Бэклог:</span>
            <span className="font-semibold text-white bg-planka-card px-2 py-0.5 rounded border border-planka-border/40">
              {backlogCount}
            </span>
            {approvedCount > 0 && (
              <>
                <span className="text-planka-textMuted ml-1">Одобрено:</span>
                <span className="font-semibold text-amber-400 bg-amber-950/40 px-2 py-0.5 rounded border border-amber-800/40">
                  {approvedCount}
                </span>
              </>
            )}
          </div>
        </div>

        {/* Center-Left Action Buttons: Scan, Check Statuses & Batch Apply */}
        <div className="flex items-center gap-2">
          <button
            onClick={handleTriggerScan}
            disabled={isScanning}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all ${
              isScanning
                ? 'bg-planka-card text-planka-textMuted border border-planka-border cursor-not-allowed'
                : 'bg-indigo-600 hover:bg-indigo-500 text-white shadow-indigo-900/40 active:scale-95'
            }`}
            title="Запустить поиск новых вакансий на HeadHunter"
          >
            {isScanning ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-indigo-400" />
                <span>Идет поиск...</span>
              </>
            ) : (
              <>
                <Search className="w-3.5 h-3.5" />
                <span>Сканировать HH</span>
              </>
            )}
          </button>

          <button
            onClick={handleTriggerNegotiations}
            disabled={isCheckingNeg}
            className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all ${
              isCheckingNeg
                ? 'bg-planka-card text-planka-textMuted border border-planka-border cursor-not-allowed'
                : 'bg-violet-700 hover:bg-violet-600 text-white shadow-violet-950/40 active:scale-95'
            }`}
            title="Проверить статусы откликов на HeadHunter и обновить карточки"
          >
            {isCheckingNeg ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin text-violet-300" />
                <span>Проверка...</span>
              </>
            ) : (
              <>
                <ClipboardCheck className="w-3.5 h-3.5" />
                <span>Статусы HH</span>
              </>
            )}
          </button>

          {approvedCount > 0 && (
            <button
              onClick={handleBatchApply}
              disabled={isBatchApplying}
              className={`flex items-center gap-2 px-3 py-1.5 rounded-lg text-xs font-semibold shadow-sm transition-all ${
                isBatchApplying
                  ? 'bg-planka-card text-planka-textMuted border border-planka-border cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-950/40 active:scale-95 animate-pulse'
              }`}
              title="Отправить отклики на все одобренные вакансии"
            >
              {isBatchApplying ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-emerald-300" />
                  <span>Отправка откликов...</span>
                </>
              ) : (
                <>
                  <Send className="w-3.5 h-3.5" />
                  <span>Отправить одобренные ({approvedCount})</span>
                </>
              )}
            </button>
          )}

          <button
            onClick={() => setIsLogModalOpen(true)}
            className="flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg text-xs font-medium bg-planka-card/80 hover:bg-planka-card text-planka-text border border-planka-border/50 hover:text-white transition-colors"
            title="Открыть терминал логов"
          >
            <Terminal className="w-3.5 h-3.5 text-indigo-400" />
            <span className="hidden sm:inline">Логи</span>
            {logs.length > 0 && (
              <span className="ml-1 px-1.5 py-0.2 text-[10px] font-mono bg-indigo-950/60 text-indigo-300 border border-indigo-800/40 rounded-full">
                {logs.length}
              </span>
            )}
          </button>
        </div>

        {/* Center: Navigation Tabs */}
        <nav className="flex items-center gap-1 bg-planka-bg p-1 rounded-xl border border-planka-border/40">
          <button
            onClick={() => setActiveTab('board')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'board'
                ? 'bg-planka-accent text-white shadow-sm shadow-indigo-950/50'
                : 'text-planka-textMuted hover:text-white hover:bg-planka-card'
            }`}
          >
            <LayoutGrid className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Канбан-доска</span>
          </button>

          <button
            onClick={() => setActiveTab('settings')}
            className={`flex items-center gap-2 px-3.5 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              activeTab === 'settings'
                ? 'bg-planka-accent text-white shadow-sm shadow-indigo-950/50'
                : 'text-planka-textMuted hover:text-white hover:bg-planka-card'
            }`}
          >
            <Settings className="w-3.5 h-3.5" />
            <span className="hidden md:inline">Настройки</span>
          </button>
        </nav>

        {/* Right: HH Status Badge + Quick Refresh */}
        <div className="flex items-center gap-2 flex-shrink-0">
          <div
            className={`hidden md:flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${
              hhStatus.authenticated
                ? 'bg-emerald-950/40 text-emerald-300 border-emerald-800/40'
                : 'bg-amber-950/40 text-amber-300 border-amber-800/40'
            }`}
            title={hhStatus.authenticated ? 'Сессия HeadHunter активна' : 'Требуется войти в HeadHunter'}
          >
            {hhStatus.authenticated ? (
              <>
                <CheckCircle2 className="w-3.5 h-3.5 text-emerald-400" />
                <span className="truncate max-w-[120px]">{hhStatus.user || 'HH Активен'}</span>
              </>
            ) : (
              <>
                <AlertCircle className="w-3.5 h-3.5 text-amber-400" />
                <span>HH: Нужен вход</span>
              </>
            )}
          </div>

          <button
            onClick={loadData}
            disabled={isRefreshing}
            className="p-2 text-planka-textMuted hover:text-white hover:bg-planka-card rounded-lg transition-colors"
            title="Обновить данные"
          >
            <RefreshCw className={`w-4 h-4 ${isRefreshing ? 'animate-spin text-planka-accent' : ''}`} />
          </button>
        </div>

      </header>

      {/* Main Content Area */}
      <main className="flex-1 flex overflow-hidden">
        {activeTab === 'board' && (
          <KanbanBoard
            vacancies={vacancies}
            settings={settings}
            onRefresh={loadData}
            onMoveVacancy={handleMoveVacancy}
            onUpdateCustomization={handleUpdateCustomization}
            onApplyVacancy={handleApplyVacancy}
          />
        )}

        {activeTab === 'settings' && (
          <SettingsView
            settings={settings}
            onSaveSetting={handleSaveSetting}
          />
        )}
      </main>

      {/* Log Terminal Modal */}
      <LogModal
        isOpen={isLogModalOpen}
        onClose={() => setIsLogModalOpen(false)}
        logs={logs}
        onClearLogs={() => setLogs([])}
      />

    </div>
  );
};

export default App;
