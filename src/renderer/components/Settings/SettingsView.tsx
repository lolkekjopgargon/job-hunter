import React, { useState, useEffect } from 'react';
import { AppSettings, SearchQueryItem, PortfolioLink } from '../../types';
import { AgentStyleSettings } from './AgentStyleSettings';
import { ContactsSettings } from './ContactsSettings';
import { PortfolioLinksSettings } from './PortfolioLinksSettings';
import { LogIn, Key, Search, Save, CheckCircle2, AlertCircle, RefreshCw, Plus, Trash2, Bot, Link2, UserCheck, FileText, Loader2, ExternalLink, Copy, Check } from 'lucide-react';
import { formatResumeTitle } from '../../utils/resumeFormatter';

interface SettingsViewProps {
  settings: AppSettings;
  onSaveSetting: (key: string, value: string) => Promise<void>;
}

export const SettingsView: React.FC<SettingsViewProps> = ({
  settings,
  onSaveSetting,
}) => {
  const [activeTab, setActiveTab] = useState<'search' | 'llm' | 'prompt' | 'links' | 'contacts'>('search');
  const [hhStatus, setHhStatus] = useState<{ authenticated: boolean; user?: string; error?: string }>({
    authenticated: false,
  });
  const [isAuthenticating, setIsAuthenticating] = useState(false);
  const [saveSuccess, setSaveSuccess] = useState(false);
  const [isFetchingResumes, setIsFetchingResumes] = useState(false);
  const [fetchResumesError, setFetchResumesError] = useState<string | null>(null);
  const [fetchResumesSuccess, setFetchResumesSuccess] = useState(false);
  const [copiedId, setCopiedId] = useState<string | null>(null);
  const [hhResumes, setHhResumes] = useState<Array<{ id: string; title: string; status?: string; url?: string }>>([]);

  const [llmProvider, setLlmProvider] = useState(settings.llm_provider || 'gemini');

  const [providerKeys, setProviderKeys] = useState<{ [key: string]: string }>({
    gemini: settings.llm_key_gemini || (settings.llm_provider === 'gemini' ? settings.llm_api_key : '') || '',
    deepseek: settings.llm_key_deepseek || (settings.llm_provider === 'deepseek' ? settings.llm_api_key : '') || '',
    openrouter: settings.llm_key_openrouter || (settings.llm_provider === 'openrouter' ? settings.llm_api_key : '') || '',
    groq: settings.llm_key_groq || (settings.llm_provider === 'groq' ? settings.llm_api_key : '') || '',
  });

  const [providerModels, setProviderModels] = useState<{ [key: string]: string }>({
    gemini: settings.llm_model_gemini || (settings.llm_provider === 'gemini' ? settings.llm_model : '') || 'gemini-3.6-flash',
    deepseek: settings.llm_model_deepseek || (settings.llm_provider === 'deepseek' ? settings.llm_model : '') || 'deepseek-chat',
    openrouter: settings.llm_model_openrouter || (settings.llm_provider === 'openrouter' ? settings.llm_model : '') || 'meta-llama/llama-3.3-70b-instruct:free',
    groq: settings.llm_model_groq || (settings.llm_provider === 'groq' ? settings.llm_model : '') || 'llama-3.3-70b-versatile',
  });

  const [llmApiKey, setLlmApiKey] = useState(
    providerKeys[settings.llm_provider || 'gemini'] || settings.llm_api_key || ''
  );
  const [llmModel, setLlmModel] = useState(
    providerModels[settings.llm_provider || 'gemini'] || settings.llm_model || 'gemini-3.6-flash'
  );

  const [agentPrompt, setAgentPrompt] = useState(settings.agent_system_prompt || '');
  const [contacts, setContacts] = useState(settings.custom_contacts || '');
  const [showManualCookies, setShowManualCookies] = useState(false);
  const [manualHhToken, setManualHhToken] = useState(settings.hh_token || '');
  const [manualXsrf, setManualXsrf] = useState(settings.hh_xsrf || '');

  const [queries, setQueries] = useState<SearchQueryItem[]>(() => {
    try { return JSON.parse(settings.search_queries || '[]'); } catch { return []; }
  });

  const [links, setLinks] = useState<PortfolioLink[]>(() => {
    try { return JSON.parse(settings.custom_portfolio_links || '[]'); } catch { return []; }
  });

  const electronAPI = (window as any).electronAPI;

  const checkAuth = async () => {
    if (electronAPI) {
      const res = await electronAPI.checkHhAuth();
      setHhStatus(res);
    }
  };

  // Load saved HH resumes
  useEffect(() => {
    try {
      const saved = (settings as any).hh_resumes;
      if (saved) {
        const parsed = JSON.parse(saved);
        if (Array.isArray(parsed) && parsed.length > 0) setHhResumes(parsed);
      }
    } catch {}
  }, [(settings as any).hh_resumes]);

  useEffect(() => {
    if (settings.agent_system_prompt) setAgentPrompt(settings.agent_system_prompt);
  }, [settings.agent_system_prompt]);

  useEffect(() => {
    if (settings.search_queries) {
      try {
        const parsed = JSON.parse(settings.search_queries);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setQueries(parsed);
        }
      } catch {}
    }
  }, [settings.search_queries]);

  useEffect(() => {
    if (settings.custom_portfolio_links) {
      try {
        const parsed = JSON.parse(settings.custom_portfolio_links);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setLinks(parsed);
        }
      } catch {}
    }
  }, [settings.custom_portfolio_links]);

  useEffect(() => { checkAuth(); }, []);

  const handleStartHhAuth = async () => {
    setIsAuthenticating(true);
    try {
      if (electronAPI) {
        const res = await electronAPI.startHhAuth();
        setHhStatus(res);
        // Auto-fetch resumes after login
        handleFetchResumes();
      }
    } finally {
      setIsAuthenticating(false);
    }
  };

  const handleFetchResumes = async () => {
    setIsFetchingResumes(true);
    setFetchResumesError(null);
    setFetchResumesSuccess(false);
    try {
      const res = await electronAPI?.fetchHhResumes?.();
      if (res?.success && Array.isArray(res.resumes) && res.resumes.length > 0) {
        setHhResumes(res.resumes);
        setFetchResumesSuccess(true);
        setTimeout(() => setFetchResumesSuccess(false), 4000);
      } else {
        setFetchResumesError(res?.error || 'Не удалось найти резюме на странице кабинета');
      }
    } catch (e: any) {
      setFetchResumesError(e?.message || 'Ошибка связи с движком HH');
    } finally {
      setIsFetchingResumes(false);
    }
  };

  const handleCopyId = (id: string) => {
    navigator.clipboard.writeText(id);
    setCopiedId(id);
    setTimeout(() => setCopiedId(null), 2000);
  };

  const handleProviderChange = (newProvider: string) => {
    const updatedKeys = { ...providerKeys, [llmProvider]: llmApiKey };
    const updatedModels = { ...providerModels, [llmProvider]: llmModel };
    setProviderKeys(updatedKeys);
    setProviderModels(updatedModels);
    setLlmProvider(newProvider);
    setLlmApiKey(updatedKeys[newProvider] || '');
    setLlmModel(updatedModels[newProvider] || (
      newProvider === 'deepseek' ? 'deepseek-chat' :
      newProvider === 'gemini' ? 'gemini-3.6-flash' :
      newProvider === 'openrouter' ? 'meta-llama/llama-3.3-70b-instruct:free' :
      'llama-3.3-70b-versatile'
    ));
  };

  const handleSaveAll = async () => {
    const currentKeys = { ...providerKeys, [llmProvider]: llmApiKey };
    const currentModels = { ...providerModels, [llmProvider]: llmModel };

    await onSaveSetting('llm_provider', llmProvider);
    await onSaveSetting('llm_api_key', llmApiKey);
    await onSaveSetting('llm_model', llmModel);
    await onSaveSetting('llm_key_gemini', currentKeys.gemini || '');
    await onSaveSetting('llm_key_deepseek', currentKeys.deepseek || '');
    await onSaveSetting('llm_key_openrouter', currentKeys.openrouter || '');
    await onSaveSetting('llm_key_groq', currentKeys.groq || '');
    await onSaveSetting('llm_model_gemini', currentModels.gemini || 'gemini-3.6-flash');
    await onSaveSetting('llm_model_deepseek', currentModels.deepseek || 'deepseek-chat');
    await onSaveSetting('llm_model_openrouter', currentModels.openrouter || 'meta-llama/llama-3.3-70b-instruct:free');
    await onSaveSetting('llm_model_groq', currentModels.groq || 'llama-3.3-70b-versatile');
    await onSaveSetting('agent_system_prompt', agentPrompt);
    await onSaveSetting('custom_contacts', contacts);
    await onSaveSetting('custom_portfolio_links', JSON.stringify(links));
    await onSaveSetting('search_queries', JSON.stringify(queries));

    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  const addQuery = () => {
    const defaultResumeId = hhResumes.length > 0 ? hhResumes[0].id : 'game_designer';
    setQueries([...queries, {
      id: `q_${Date.now()}`,
      name: 'Новый запрос',
      query: '"Поисковая фраза"',
      resume_key: defaultResumeId,
      salary_min: 100000,
      schedule: 'remote',
      enabled: true,
    }]);
  };

  const removeQuery = (id: string) => setQueries(queries.filter((q) => q.id !== id));

  const updateQuery = (id: string, field: keyof SearchQueryItem, val: any) =>
    setQueries(queries.map((q) => (q.id === id ? { ...q, [field]: val } : q)));

  return (
    <div className="flex-1 overflow-y-auto p-6 max-w-4xl mx-auto space-y-6">
      {/* Sub-tabs */}
      <div className="flex items-center gap-2 border-b border-planka-border/50 pb-3 flex-wrap">
        {([
          { id: 'search', icon: <Search className="w-4 h-4" />, label: 'Поиск и HH' },
          { id: 'llm', icon: <Key className="w-4 h-4" />, label: 'Нейросеть (LLM)' },
          { id: 'prompt', icon: <Bot className="w-4 h-4" />, label: 'Стиль и Тон ИИ' },
          { id: 'links', icon: <Link2 className="w-4 h-4" />, label: 'Портфолио' },
          { id: 'contacts', icon: <UserCheck className="w-4 h-4" />, label: 'Контакты' },
        ] as const).map(tab => (
          <button
            key={tab.id}
            onClick={() => setActiveTab(tab.id)}
            className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-all ${
              activeTab === tab.id
                ? 'bg-planka-accent text-white shadow-md shadow-indigo-950/40'
                : 'text-planka-textMuted hover:text-white hover:bg-planka-card'
            }`}
          >
            {tab.icon}
            <span>{tab.label}</span>
          </button>
        ))}
      </div>

      {/* Tab: Search & HH */}
      {activeTab === 'search' && (
        <div className="space-y-6">
          {/* HH Auth */}
          <div className="bg-planka-sidebar/70 border border-planka-border/50 rounded-xl p-5 shadow-sm">
            <div className="flex items-center justify-between mb-3">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 rounded-lg bg-rose-600 flex items-center justify-center font-bold text-white text-lg shadow-md shadow-rose-900/30">hh</div>
                <div>
                  <h3 className="text-base font-bold text-white">Авторизация в HeadHunter</h3>
                  <p className="text-xs text-planka-textMuted">Нажми кнопку — откроется окно входа, куки перехватятся автоматически. Резюме обновятся сразу после входа.</p>
                </div>
              </div>
              <button
                onClick={handleStartHhAuth}
                disabled={isAuthenticating}
                className="flex items-center gap-2 px-4 py-2 bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white rounded-lg transition-colors shadow-md shadow-rose-950/40 disabled:opacity-50"
              >
                <LogIn className="w-4 h-4" />
                {isAuthenticating ? 'Ожидание входа...' : 'Войти через HeadHunter'}
              </button>
            </div>

            <div className="pt-3 border-t border-planka-border/30 flex items-center justify-between text-xs">
              {hhStatus.authenticated ? (
                <div className="flex items-center gap-2 text-emerald-400 font-medium">
                  <CheckCircle2 className="w-4 h-4" />
                  <span>Сессия активна: {hhStatus.user || 'Пользователь HH'}</span>
                </div>
              ) : (
                <div className="flex items-center gap-2 text-amber-400 font-medium">
                  <AlertCircle className="w-4 h-4" />
                  <span>{hhStatus.error || 'Требуется авторизация'}</span>
                </div>
              )}
              <button
                onClick={() => setShowManualCookies(!showManualCookies)}
                className="text-[11px] text-planka-textMuted hover:text-white underline ml-auto"
              >
                {showManualCookies ? 'Скрыть ручной ввод' : 'Ввести токены вручную (резерв)'}
              </button>
            </div>

            {showManualCookies && (
              <div className="mt-3 p-3 bg-planka-card/60 border border-planka-border/50 rounded-lg space-y-3">
                <div className="text-[11px] text-planka-textMuted">
                  Скопируй куки <code className="text-rose-400 font-mono">hhtoken</code> и <code className="text-rose-400 font-mono">_xsrf</code> из браузера (F12 → Application → Cookies → hh.ru).
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="block text-[11px] font-semibold text-planka-textMuted mb-1 font-mono">hhtoken</label>
                    <input type="password" value={manualHhToken} onChange={(e) => setManualHhToken(e.target.value)} placeholder="E9naDk4..." className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2 text-xs text-white font-mono" />
                  </div>
                  <div>
                    <label className="block text-[11px] font-semibold text-planka-textMuted mb-1 font-mono">_xsrf</label>
                    <input type="password" value={manualXsrf} onChange={(e) => setManualXsrf(e.target.value)} placeholder="37f629..." className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2 text-xs text-white font-mono" />
                  </div>
                </div>
                <button
                  onClick={async () => { await onSaveSetting('hh_token', manualHhToken); await onSaveSetting('hh_xsrf', manualXsrf); await checkAuth(); }}
                  className="px-3 py-1.5 bg-planka-accent hover:bg-indigo-600 text-xs text-white rounded-lg font-medium"
                >
                  Применить токены
                </button>
              </div>
            )}
          </div>

          {/* HH Resumes */}
          <div className="bg-planka-sidebar/70 border border-planka-border/50 rounded-xl p-5 shadow-sm space-y-3">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <FileText className="w-5 h-5 text-rose-400" />
                <div>
                  <div className="flex items-center gap-2">
                    <h3 className="text-base font-bold text-white">Мои резюме на HeadHunter</h3>
                    {hhResumes.length > 0 && (
                      <span className="text-[11px] font-semibold px-2 py-0.5 rounded-full bg-rose-500/20 text-rose-300 border border-rose-500/30">
                        {hhResumes.length} {hhResumes.length === 1 ? 'резюме' : (hhResumes.length < 5 ? 'резюме' : 'резюме')}
                      </span>
                    )}
                  </div>
                  <p className="text-xs text-planka-textMuted">
                    Спарсены с твоего аккаунта. Используются для автооткликов и выбора в поисковых запросах.
                  </p>
                </div>
              </div>
              <button
                onClick={handleFetchResumes}
                disabled={isFetchingResumes}
                className="flex items-center gap-1.5 px-3.5 py-2 bg-rose-600 hover:bg-rose-500 text-xs font-semibold text-white rounded-lg transition-colors shadow-md shadow-rose-950/40 disabled:opacity-50 active:scale-95"
              >
                {isFetchingResumes ? (
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                ) : (
                  <RefreshCw className="w-3.5 h-3.5" />
                )}
                {isFetchingResumes ? 'Парсим с сайта...' : 'Обновить резюме'}
              </button>
            </div>

            {/* Error banner if fetch failed */}
            {fetchResumesError && (
              <div className="p-3 bg-rose-950/50 border border-rose-800/60 rounded-lg flex items-start gap-2.5 text-xs text-rose-200 animate-in fade-in">
                <AlertCircle className="w-4 h-4 text-rose-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1">
                  <div className="font-semibold text-rose-300">Ошибка получения резюме:</div>
                  <div className="text-[11px] mt-0.5 text-rose-200/90">{fetchResumesError}</div>
                </div>
              </div>
            )}

            {/* Success indicator */}
            {fetchResumesSuccess && (
              <div className="p-2.5 bg-emerald-950/40 border border-emerald-800/50 rounded-lg flex items-center gap-2 text-xs text-emerald-300 animate-in fade-in">
                <CheckCircle2 className="w-4 h-4 text-emerald-400" />
                <span>Успешно спарсено и сохранено <b>{hhResumes.length}</b> резюме с аккаунта HeadHunter!</span>
              </div>
            )}

            {/* Resumes List */}
            {hhResumes.length > 0 ? (
              <div className="space-y-2 pt-1">
                {hhResumes.map((r) => (
                  <div
                    key={r.id}
                    className="flex flex-col sm:flex-row sm:items-center justify-between gap-2 p-3 bg-planka-card/60 hover:bg-planka-card border border-planka-border/50 rounded-lg transition-colors"
                  >
                    <div className="flex items-center gap-2.5 flex-1 min-w-0">
                      <div className="w-2 h-2 rounded-full bg-emerald-400 flex-shrink-0" />
                      <span className="text-xs font-semibold text-white truncate" title={formatResumeTitle(r.title)}>
                        {formatResumeTitle(r.title)}
                      </span>
                      {r.status && (
                        <span className="text-[10px] px-2 py-0.5 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/20 font-medium">
                          {r.status}
                        </span>
                      )}
                    </div>

                    <div className="flex items-center gap-2 self-end sm:self-auto">
                      {/* Copy Hash ID Button */}
                      <button
                        onClick={() => handleCopyId(r.id)}
                        className="flex items-center gap-1 px-2 py-1 bg-planka-sidebar/80 hover:bg-planka-sidebar border border-planka-border/60 rounded text-[11px] text-planka-textMuted hover:text-white transition-colors font-mono"
                        title="Скопировать ID резюме (хэш)"
                      >
                        {copiedId === r.id ? (
                          <>
                            <Check className="w-3 h-3 text-emerald-400" />
                            <span className="text-emerald-400">Скопирован</span>
                          </>
                        ) : (
                          <>
                            <Copy className="w-3 h-3" />
                            <span className="truncate max-w-[120px]">{r.id.substring(0, 12)}...</span>
                          </>
                        )}
                      </button>

                      {/* Direct HH link */}
                      <a
                        href={r.url || `https://hh.ru/resume/${r.id}`}
                        target="_blank"
                        rel="noreferrer"
                        className="flex items-center gap-1 px-2.5 py-1 bg-rose-600/20 hover:bg-rose-600/30 text-rose-300 border border-rose-500/30 rounded text-[11px] font-medium transition-colors"
                        title="Открыть резюме на сайте HeadHunter"
                      >
                        <ExternalLink className="w-3 h-3" />
                        <span>На сайт HH</span>
                      </a>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className="text-xs text-planka-textMuted italic py-3 text-center bg-planka-card/30 rounded-lg border border-dashed border-planka-border/40">
                Резюме пока не загружены. Войдите в аккаунт выше и нажмите кнопку <b>«Обновить резюме»</b>.
              </div>
            )}
          </div>

          {/* Search Queries */}
          <div className="bg-planka-sidebar/70 border border-planka-border/50 rounded-xl p-5 shadow-sm space-y-4">
            <div className="flex items-center justify-between">
              <div className="flex items-center gap-2.5">
                <Search className="w-5 h-5 text-planka-accent" />
                <div>
                  <h3 className="text-base font-bold text-white">Поисковые роли и запросы</h3>
                  <p className="text-xs text-planka-textMuted">Какие профессии и ключевые слова сканируются на HH.</p>
                </div>
              </div>
              <button onClick={addQuery} className="flex items-center gap-1.5 px-3 py-1.5 bg-planka-card hover:bg-planka-cardHover border border-planka-border text-xs font-medium text-white rounded-lg transition-colors">
                <Plus className="w-4 h-4 text-emerald-400" /> Добавить роль
              </button>
            </div>

            <div className="space-y-3">
              {queries.map((q) => (
                <div key={q.id} className="p-3.5 bg-planka-card/50 border border-planka-border/40 rounded-xl flex flex-col md:flex-row items-start md:items-center gap-3">
                  <div className="flex-1 grid grid-cols-1 md:grid-cols-12 gap-2.5 w-full">
                    <input type="text" value={q.name} onChange={(e) => updateQuery(q.id, 'name', e.target.value)} placeholder="Название роли" className="md:col-span-3 bg-planka-card border border-planka-border/60 rounded-lg p-2 text-xs text-white font-semibold" />
                    <input type="text" value={q.query} onChange={(e) => updateQuery(q.id, 'query', e.target.value)} placeholder='"ГД" OR "гейм"' className="md:col-span-4 bg-planka-card border border-planka-border/60 rounded-lg p-2 text-xs text-planka-text font-mono" />
                    <select value={q.resume_key} onChange={(e) => updateQuery(q.id, 'resume_key', e.target.value)} className="md:col-span-3 bg-planka-card border border-planka-border/60 rounded-lg p-2 text-xs text-planka-text">
                      {hhResumes.length > 0 ? (
                        hhResumes.map((r) => <option key={r.id} value={r.id}>{formatResumeTitle(r.title)}</option>)
                      ) : (
                        <>
                          <option value="game_designer">Гейм-дизайн</option>
                          <option value="narrative_designer">Нарратив</option>
                          <option value="3d_generalist">3D generalist</option>
                          <option value="actor">Актер</option>
                        </>
                      )}
                    </select>
                    <input type="number" value={q.salary_min} onChange={(e) => updateQuery(q.id, 'salary_min', Number(e.target.value))} placeholder="Мин. ЗП" className="md:col-span-2 bg-planka-card border border-planka-border/60 rounded-lg p-2 text-xs text-emerald-400 font-mono" />
                  </div>
                  <div className="flex items-center gap-2">
                    <input type="checkbox" checked={q.enabled} onChange={(e) => updateQuery(q.id, 'enabled', e.target.checked)} className="w-4 h-4 rounded cursor-pointer" title="Активен" />
                    <button onClick={() => removeQuery(q.id)} className="p-2 text-planka-textMuted hover:text-rose-400 transition-colors" title="Удалить">
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {/* Tab: LLM */}
      {activeTab === 'llm' && (
        <div className="bg-planka-sidebar/70 border border-planka-border/50 rounded-xl p-5 shadow-sm space-y-4">
          <div className="flex items-center gap-2.5">
            <Key className="w-5 h-5 text-purple-400" />
            <div>
              <h3 className="text-base font-bold text-white">Нейросеть для живых писем (LLM API)</h3>
              <p className="text-xs text-planka-textMuted">Ключ для генерации писем по твоим фактам и редполитике.</p>
            </div>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
            <div>
              <label className="block text-xs font-semibold text-planka-textMuted mb-1.5 uppercase">Провайдер</label>
              <select value={llmProvider} onChange={(e) => handleProviderChange(e.target.value)} className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-planka-accent font-semibold">
                <option value="gemini">Google Gemini (AI Studio)</option>
                <option value="deepseek">DeepSeek</option>
                <option value="openrouter">OpenRouter (бесплатные)</option>
                <option value="groq">Groq (Llama)</option>
              </select>
            </div>
            <div>
              <label className="block text-xs font-semibold text-planka-textMuted mb-1.5 uppercase">Модель</label>
              {llmProvider === 'gemini' ? (
                <select value={llmModel} onChange={(e) => { setLlmModel(e.target.value); setProviderModels({ ...providerModels, gemini: e.target.value }); }} className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-planka-accent font-mono">
                  <option value="gemini-3.6-flash">gemini-3.6-flash (Новейшая, Free)</option>
                  <option value="gemini-flash-latest">gemini-flash-latest (Free)</option>
                  <option value="gemini-2.5-pro">gemini-2.5-pro (Free)</option>
                  <option value="gemini-2.5-flash">gemini-2.5-flash (Legacy Free)</option>
                </select>
              ) : llmProvider === 'deepseek' ? (
                <select value={llmModel} onChange={(e) => { setLlmModel(e.target.value); setProviderModels({ ...providerModels, deepseek: e.target.value }); }} className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-planka-accent font-mono">
                  <option value="deepseek-chat">deepseek-chat (V3, Рекомендуется)</option>
                  <option value="deepseek-reasoner">deepseek-reasoner (R1)</option>
                </select>
              ) : llmProvider === 'openrouter' ? (
                <select value={llmModel} onChange={(e) => { setLlmModel(e.target.value); setProviderModels({ ...providerModels, openrouter: e.target.value }); }} className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-planka-accent font-mono">
                  <option value="meta-llama/llama-3.3-70b-instruct:free">Llama 3.3 70B (Free)</option>
                  <option value="google/gemini-2.0-flash-exp:free">Gemini 2.0 Flash (Free)</option>
                  <option value="deepseek/deepseek-r1:free">DeepSeek R1 (Free)</option>
                  <option value="qwen/qwen-2.5-72b-instruct:free">Qwen 2.5 72B (Free)</option>
                </select>
              ) : (
                <input type="text" value={llmModel} onChange={(e) => { setLlmModel(e.target.value); setProviderModels({ ...providerModels, [llmProvider]: e.target.value }); }} placeholder="llama-3.3-70b-versatile" className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-planka-accent font-mono" />
              )}
            </div>
            <div>
              <label className="block text-xs font-semibold text-planka-textMuted mb-1.5 uppercase">API-ключ</label>
              <input type="password" value={llmApiKey} onChange={(e) => { setLlmApiKey(e.target.value); setProviderKeys({ ...providerKeys, [llmProvider]: e.target.value }); }} placeholder={llmProvider === 'gemini' ? 'AIzaSy...' : llmProvider === 'deepseek' ? 'sk-...' : llmProvider === 'openrouter' ? 'sk-or-v1-...' : 'gsk_...'} className="w-full bg-planka-card border border-planka-border/60 rounded-lg p-2.5 text-xs text-white focus:outline-none focus:border-planka-accent font-mono" />
            </div>
          </div>

          <div className="pt-2 text-[11px] text-planka-textMuted border-t border-planka-border/30">
            {llmProvider === 'gemini' && <span>Бесплатный ключ: <a href="https://aistudio.google.com/app/apikey" target="_blank" rel="noreferrer" className="text-planka-accent hover:underline">aistudio.google.com</a></span>}
            {llmProvider === 'deepseek' && <span>Ключ: <a href="https://platform.deepseek.com/api_keys" target="_blank" rel="noreferrer" className="text-planka-accent hover:underline">platform.deepseek.com</a></span>}
            {llmProvider === 'openrouter' && <span>Ключ: <a href="https://openrouter.ai/keys" target="_blank" rel="noreferrer" className="text-planka-accent hover:underline">openrouter.ai/keys</a></span>}
            {llmProvider === 'groq' && <span>Ключ: <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer" className="text-planka-accent hover:underline">console.groq.com</a></span>}
          </div>
        </div>
      )}

      {activeTab === 'prompt' && (
        <AgentStyleSettings systemPrompt={agentPrompt} onSavePrompt={async (p) => { setAgentPrompt(p); await onSaveSetting('agent_system_prompt', p); }} />
      )}

      {activeTab === 'links' && (
        <PortfolioLinksSettings links={links} onSaveLinks={async (l) => { setLinks(l); await onSaveSetting('custom_portfolio_links', JSON.stringify(l)); }} />
      )}

      {activeTab === 'contacts' && (
        <ContactsSettings contacts={contacts} onSaveContacts={async (c) => { setContacts(c); await onSaveSetting('custom_contacts', c); }} />
      )}

      {/* Save */}
      <div className="flex items-center justify-end gap-3 pt-2">
        {saveSuccess && (
          <span className="text-xs text-emerald-400 font-medium flex items-center gap-1.5">
            <CheckCircle2 className="w-4 h-4" /> Настройки сохранены!
          </span>
        )}
        <button onClick={handleSaveAll} className="flex items-center gap-2 px-6 py-2.5 bg-planka-accent hover:bg-planka-accentHover text-xs font-bold text-white rounded-lg transition-all shadow-lg shadow-indigo-950/40 active:scale-95">
          <Save className="w-4 h-4" /> Сохранить все настройки
        </button>
      </div>
    </div>
  );
};
