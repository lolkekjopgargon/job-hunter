import React, { useState, useEffect } from 'react';
import { Vacancy, PortfolioLink, AppSettings } from '../../types';
import { X, ExternalLink, Send, CheckSquare, Square, FileText, AlertCircle, Sparkles, Building2, DollarSign, RefreshCw, Layers } from 'lucide-react';
import { formatResumeTitle } from '../../utils/resumeFormatter';

interface CardModalProps {
  vacancy: Vacancy;
  settings?: AppSettings;
  onClose: () => void;
  onSave: (resumeId: string, materials: string[], letter: string) => Promise<void>;
  onApply: () => Promise<void>;
  onMove: (targetList: Vacancy['list_name']) => Promise<void>;
  isGeneratingLetter?: boolean;
  onGenerateLetter?: (regenerate?: boolean) => void;
}

// Hardcoded fallback — used only when user hasn't logged in to HH yet
const FALLBACK_RESUMES = [
  { id: 'game_designer', title: 'Гейм-дизайнер' },
  { id: 'narrative_designer', title: 'Нарративный дизайнер' },
  { id: '3d_generalist', title: '3D generalist' },
  { id: 'actor', title: 'Актер' },
];

const DEFAULT_MATERIALS = [
  { title: 'Game Design Specification (GDD / Notion)', url: 'https://drive.google.com/file/d/1rgMxRtjwmq1XIpI5rt32LeBj8ZRrS93r/view?usp=drive_link', category: 'game_design' },
  { title: 'Combat Balance & Data Architecture (Sheets)', url: 'https://drive.google.com/file/d/1RO46ycLAckr803ahy8ULLimjzwcHr4Bx/view?usp=drive_link', category: 'game_design' },
  { title: 'RPG Life Tracker / Dynamic Quest Engine (Web/YouTube)', url: 'https://youtu.be/_teOplLx3QY', category: 'game_design' },
  { title: 'ArtStation Portfolio (3D / UE5)', url: 'https://www.artstation.com/tejedakardenas', category: '3d_art' },
  { title: 'Unreal Engine 5 Previs Reel (Cinematics)', url: 'https://youtu.be/II82L2EZ8g0', category: '3d_art' },
  { title: 'Narrative Sample (Dialogue & Lore)', url: 'https://drive.google.com/file/d/1xvJnbGAKg970oqK4wQ2VGYpVNMDA6G/view?usp=drive_link', category: 'narrative' },
  { title: 'Game Promo / Investor Presentation', url: 'https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk', category: 'game_design' },
  { title: 'Актерская визитка / Шоурил', url: 'https://youtu.be/5f1FLQ6sHr8', category: 'voice' }
];

const CATEGORY_LABELS: Record<string, string> = {
  game_design: 'Гейм-дизайн',
  narrative: 'Нарратив',
  '3d_art': '3D и UE5',
  voice: 'Озвучка',
  general: 'Общее',
  'Game Design': 'Гейм-дизайн',
  '3D & Art': '3D и UE5',
  'Narrative': 'Нарратив',
  'VO & Acting': 'Озвучка',
};

export const CardModal: React.FC<CardModalProps> = ({
  vacancy,
  settings,
  onClose,
  onSave,
  onApply,
  onMove,
  isGeneratingLetter = false,
  onGenerateLetter,
}) => {
  const [resumes, setResumes] = useState<Array<{ id: string; title: string }>>(FALLBACK_RESUMES);
  const [selectedResume, setSelectedResume] = useState(vacancy.selected_resume_id || FALLBACK_RESUMES[0].id);
  const [selectedMaterials, setSelectedMaterials] = useState<string[]>(vacancy.selected_materials || []);

  const getInitialMaterials = (): Array<{ id?: string; title: string; url: string; category?: string }> => {
    if (settings?.custom_portfolio_links) {
      try {
        const parsed = JSON.parse(settings.custom_portfolio_links);
        if (Array.isArray(parsed) && parsed.length > 0) return parsed;
      } catch {}
    }
    return DEFAULT_MATERIALS;
  };

  const [availableMaterials, setAvailableMaterials] = useState<Array<{ id?: string; title: string; url: string; category?: string }>>(getInitialMaterials);
  const [letterText, setLetterText] = useState(vacancy.cover_letter || '');
  const [userContacts, setUserContacts] = useState(settings?.custom_contacts?.trim() || '');
  const [includeContacts, setIncludeContacts] = useState(true);
  const [fullDescription, setFullDescription] = useState(vacancy.full_description || '');
  const [isApplying, setIsApplying] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [isRefetchingDesc, setIsRefetchingDesc] = useState(false);
  const [applyResult, setApplyResult] = useState<string | null>(null);

  const electronAPI = (window as any).electronAPI;

  useEffect(() => {
    if (vacancy.cover_letter) {
      setLetterText(vacancy.cover_letter);
    }
  }, [vacancy.cover_letter]);

  // Sync settings when passed via props
  useEffect(() => {
    if (settings?.custom_portfolio_links) {
      try {
        const parsed = JSON.parse(settings.custom_portfolio_links);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setAvailableMaterials(parsed);
        }
      } catch {}
    }
    if (settings?.custom_contacts) {
      setUserContacts(settings.custom_contacts.trim());
    }
    if (settings?.hh_resumes) {
      try {
        const parsed = JSON.parse(settings.hh_resumes);
        if (Array.isArray(parsed) && parsed.length > 0) {
          setResumes(parsed);
          if (!vacancy.selected_resume_id) setSelectedResume(parsed[0].id);
        }
      } catch {}
    }
  }, [settings]);

  useEffect(() => {
    const loadSettings = async () => {
      if (!electronAPI?.getSettings) return;
      try {
        const s = await electronAPI.getSettings();
        const cfg = (s?.success && s.settings) ? s.settings : s;
        if (!cfg) return;

        if (cfg.custom_portfolio_links) {
          try {
            const parsed = JSON.parse(cfg.custom_portfolio_links);
            if (Array.isArray(parsed) && parsed.length > 0) setAvailableMaterials(parsed);
          } catch {}
        }
        if (cfg.custom_contacts) setUserContacts(cfg.custom_contacts.trim());

        if (cfg.hh_resumes) {
          try {
            const parsed = JSON.parse(cfg.hh_resumes);
            if (Array.isArray(parsed) && parsed.length > 0) {
              setResumes(parsed);
              if (!vacancy.selected_resume_id) setSelectedResume(parsed[0].id);
            }
          } catch {}
        }
      } catch (e) {
        console.error('Failed to load settings in modal', e);
      }
    };
    loadSettings();
  }, []);

  const toggleContacts = () => {
    const nextVal = !includeContacts;
    setIncludeContacts(nextVal);
    if (!nextVal) {
      // Remove contacts signature from letterText if present
      const lines = userContacts.split('\n').map(l => l.trim()).filter(Boolean);
      let updated = letterText;
      for (const line of lines) {
        updated = updated.split('\n').filter(l => !l.includes(line)).join('\n');
      }
      setLetterText(updated.trim());
    } else {
      // Append contacts signature to letterText if not already in text
      if (userContacts && !letterText.includes(userContacts.split('\n')[0])) {
        setLetterText(prev => prev.trim() + '\n\n' + userContacts);
      }
    }
  };

  const toggleMaterial = (url: string, title: string) => {
    const isCurrentlyChecked = selectedMaterials.includes(url) || (Boolean(url) && letterText.includes(url));
    if (isCurrentlyChecked) {
      const nextMaterials = selectedMaterials.filter((m) => m !== url);
      setSelectedMaterials(nextMaterials);
      // Remove URL and title line from letterText
      const cleaned = letterText
        .split('\n')
        .filter(line => !line.includes(url) && !(title && line.includes(title)))
        .join('\n')
        .replace(/\n{3,}/g, '\n\n')
        .trim();
      setLetterText(cleaned);
    } else {
      const nextMaterials = selectedMaterials.includes(url) ? selectedMaterials : [...selectedMaterials, url];
      setSelectedMaterials(nextMaterials);
      // Append URL with title if not already in letter
      if (!letterText.includes(url)) {
        const toAppend = `\n\n${title}:\n${url}`;
        setLetterText(prev => prev.trim() + toAppend);
      }
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    await onSave(selectedResume, selectedMaterials, letterText);
    setIsSaving(false);
  };

  const handleGenerateLetter = async (regenerate = false) => {
    if (onGenerateLetter) {
      onGenerateLetter(regenerate);
      return;
    }
    if (electronAPI?.generateLetter) {
      const res = await electronAPI.generateLetter(vacancy.id, regenerate);
      if (res.success && res.cover_letter) {
        setLetterText(res.cover_letter);
      } else {
        alert(`Не удалось сгенерировать: ${res.error || 'Проверьте API-ключ в Настройках'}`);
      }
    }
  };

  const handleRefetchDescription = async () => {
    setIsRefetchingDesc(true);
    try {
      if (electronAPI?.refetchVacancy) {
        const res = await electronAPI.refetchVacancy(vacancy.id);
        if (res.success && res.vacancy) {
          setFullDescription(res.vacancy.full_description);
        } else {
          alert(`Ошибка обновления: ${res.error || 'Не удалось забрать страницу с HH'}`);
        }
      }
    } catch (e: any) {
      alert(`Ошибка: ${e.message || e}`);
    } finally {
      setIsRefetchingDesc(false);
    }
  };

  const handleApplyNow = async () => {
    setIsApplying(true);
    setApplyResult(null);
    try {
      await onSave(selectedResume, selectedMaterials, letterText);
      await onApply();
      setApplyResult('✓ Отклик успешно отправлен на HeadHunter!');
    } catch (e: any) {
      setApplyResult(`⚠️ Ошибка: ${e.message || e}`);
    } finally {
      setIsApplying(false);
    }
  };

  return (
    <div className="fixed inset-0 z-50 bg-black/70 backdrop-blur-sm flex items-center justify-center p-3 md:p-6 overflow-hidden">
      <div className="bg-planka-column border border-planka-border w-full max-w-6xl h-[90vh] rounded-xl flex flex-col shadow-2xl overflow-hidden animate-in fade-in zoom-in-95 duration-150">
        
        {/* Modal Header */}
        <div className="p-4 md:p-5 border-b border-planka-border/60 bg-planka-sidebar/50 flex items-start justify-between flex-shrink-0">
          <div className="space-y-1.5 flex-1 pr-4">
            <div className="flex items-center gap-2">
              <span className="text-xs font-mono px-2 py-0.5 rounded bg-planka-accent/20 text-planka-accent border border-planka-accent/30 uppercase font-semibold">
                {vacancy.role_category}
              </span>
              {vacancy.is_remote ? (
                <span className="text-xs px-2 py-0.5 rounded bg-emerald-950/60 text-emerald-300 border border-emerald-800/40">
                  Удаленно
                </span>
              ) : null}
            </div>
            <h2 className="text-lg font-bold text-white tracking-tight flex items-center gap-2">
              {vacancy.title}
            </h2>
            <div className="flex items-center gap-4 text-xs text-planka-textMuted flex-wrap">
              <span className="flex items-center gap-1">
                <Building2 className="w-3.5 h-3.5" />
                {vacancy.employer}
              </span>
              <span className="flex items-center gap-1 font-medium text-emerald-400">
                <DollarSign className="w-3.5 h-3.5" />
                {vacancy.salary}
              </span>
              <a
                href={vacancy.url}
                target="_blank"
                rel="noreferrer"
                className="flex items-center gap-1 text-planka-accent hover:underline ml-2"
              >
                Открыть на HH <ExternalLink className="w-3 h-3" />
              </a>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-1.5 rounded-lg hover:bg-planka-card text-planka-textMuted hover:text-white transition-colors flex-shrink-0"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Body: 2 Columns */}
        <div className="grid grid-cols-1 lg:grid-cols-12 flex-1 overflow-hidden min-h-0">
          
          {/* Left Column: Full Vacancy Description */}
          <div className="lg:col-span-6 p-4 md:p-5 overflow-y-auto border-r border-planka-border/50 flex flex-col min-h-0">
            <div className="flex items-center justify-between mb-2 flex-shrink-0">
              <h3 className="font-bold text-sm text-white flex items-center gap-2">
                <FileText className="w-4 h-4 text-planka-accent" />
                Полное описание вакансии
              </h3>
              <button
                onClick={handleRefetchDescription}
                disabled={isRefetchingDesc}
                className="flex items-center gap-1 px-2.5 py-1 text-[11px] bg-planka-card hover:bg-slate-700 text-planka-textMuted hover:text-white rounded border border-planka-border/50 transition-colors"
                title="Загрузить 100% свежее описание с HeadHunter"
              >
                <RefreshCw className={`w-3 h-3 ${isRefetchingDesc ? 'animate-spin text-planka-accent' : ''}`} />
                <span>{isRefetchingDesc ? 'Загрузка...' : 'Обновить с HH'}</span>
              </button>
            </div>
            
            {vacancy.has_questionnaire ? (
              <div className="mb-4 p-3 bg-amber-950/40 border border-amber-800/40 rounded-lg flex items-start gap-2.5 text-xs text-amber-200">
                <AlertCircle className="w-4 h-4 text-amber-400 flex-shrink-0 mt-0.5" />
                <div>
                  <div className="font-semibold text-amber-300">Внимание: Требуется анкета / ответы на вопросы!</div>
                  На странице HH работодатель требует ответить на вопросы перед откликом.
                </div>
              </div>
            ) : null}

            <div className="text-xs leading-relaxed text-planka-text/90 whitespace-pre-line font-sans bg-planka-card/50 p-4 rounded-lg border border-planka-border/30 select-text">
              {fullDescription}
            </div>
          </div>

          {/* Right Column: Customization (Resume -> Letter [AI] -> Materials) */}
          <div className="lg:col-span-6 p-4 md:p-5 flex flex-col gap-4 overflow-y-auto min-h-0 bg-planka-sidebar/30">
            
            {/* 1. Resume Selector */}
            <div className="flex-shrink-0">
              <label className="block text-xs font-semibold uppercase tracking-wider text-planka-textMuted mb-2">
                📄 Резюме для отклика
              </label>
              <div className="grid grid-cols-2 gap-2">
                {resumes.map((res) => (
                  <button
                    key={res.id}
                    onClick={() => setSelectedResume(res.id)}
                    className={`text-left text-xs p-2.5 rounded-lg border transition-all ${
                      selectedResume === res.id
                        ? 'bg-planka-accent/20 border-planka-accent text-white font-medium shadow-sm'
                        : 'bg-planka-card/60 border-planka-border/40 text-planka-textMuted hover:text-white hover:bg-planka-card'
                    }`}
                  >
                    {formatResumeTitle(res.title)}
                  </button>
                ))}
              </div>
            </div>

            {/* 2. Tailored Living Cover Letter with AI Button */}
            <div className="flex flex-col flex-1 min-h-[220px]">
              <div className="flex items-center justify-between mb-2 flex-wrap gap-2 flex-shrink-0">
                <label className="text-xs font-semibold uppercase tracking-wider text-planka-textMuted flex items-center gap-1.5">
                  <Sparkles className="w-3.5 h-3.5 text-purple-400" />
                  Живое авторское письмо
                </label>
                <div className="flex items-center gap-1.5">
                  {letterText.trim().length > 0 && (
                    <button
                      onClick={() => handleGenerateLetter(true)}
                      disabled={isGeneratingLetter}
                      className="flex items-center gap-1 px-2.5 py-1 bg-slate-800 hover:bg-slate-700 text-purple-300 border border-purple-500/30 rounded-md text-[11px] font-medium transition-all shadow-sm active:scale-95 disabled:opacity-50"
                      title="Перегенерировать письмо с другим углом подачи"
                    >
                      <RefreshCw className={`w-3 h-3 ${isGeneratingLetter ? 'animate-spin text-purple-400' : ''}`} />
                      <span>Другой вариант</span>
                    </button>
                  )}
                  <button
                    onClick={() => handleGenerateLetter(false)}
                    disabled={isGeneratingLetter}
                    className="flex items-center gap-1.5 px-3 py-1 bg-purple-600/30 hover:bg-purple-600/50 text-purple-300 border border-purple-500/40 rounded-md text-[11px] font-medium transition-all shadow-sm active:scale-95 disabled:opacity-50"
                    title="Сгенерировать живое письмо через онлайн LLM"
                  >
                    <Sparkles className={`w-3 h-3 ${isGeneratingLetter ? 'animate-spin' : ''}`} />
                    <span>{isGeneratingLetter ? 'Пишет ИИ...' : (letterText.trim().length > 0 ? 'Переписать ИИ' : 'Сгенерировать ИИ')}</span>
                  </button>
                </div>
              </div>

              <textarea
                value={letterText}
                onChange={(e) => setLetterText(e.target.value)}
                className="w-full flex-1 min-h-[140px] p-3 bg-planka-card border border-planka-border/50 rounded-lg text-xs text-white leading-relaxed resize-y focus:outline-none focus:border-planka-accent font-sans"
                placeholder={isGeneratingLetter ? "Генерация текста нейросетью в фоне..." : "Текст живого сопроводительного письма (нажмите «Сгенерировать ИИ» или введите вручную)..."}
                rows={7}
              />

              {/* Contacts inclusion checkbox with clean wrap */}
              <div
                onClick={toggleContacts}
                className={`mt-2.5 flex items-start gap-2.5 p-2.5 rounded-lg cursor-pointer text-xs transition-colors border flex-shrink-0 ${
                  includeContacts
                    ? 'bg-emerald-950/40 border-emerald-800/40 text-emerald-300 font-medium'
                    : 'bg-planka-card/40 border-planka-border/40 text-planka-textMuted hover:text-white'
                }`}
              >
                {includeContacts ? (
                  <CheckSquare className="w-4 h-4 text-emerald-400 flex-shrink-0 mt-0.5" />
                ) : (
                  <Square className="w-4 h-4 text-planka-border flex-shrink-0 mt-0.5" />
                )}
                <div className="flex flex-col min-w-0 flex-1">
                  <span className="font-semibold leading-tight">Включить блок контактов и подписи в письмо</span>
                  <span className="text-[11px] text-planka-textMuted font-mono mt-1 break-words whitespace-normal leading-normal">
                    {userContacts.split('\n').join(' • ')}
                  </span>
                </div>
              </div>
            </div>

            {/* 3. Portfolio Materials Checklists */}
            <div className="flex-shrink-0">
              <label className="block text-xs font-semibold uppercase tracking-wider text-planka-textMuted mb-2 flex items-center gap-1.5">
                <Layers className="w-3.5 h-3.5 text-planka-accent" />
                Прикрепленные материалы ({selectedMaterials.length})
              </label>
              <div className="space-y-1.5 max-h-48 overflow-y-auto pr-1 scrollbar-thin">
                {availableMaterials.map((mat, index) => {
                  const isChecked = selectedMaterials.includes(mat.url) || (Boolean(mat.url) && letterText.includes(mat.url));
                  return (
                    <div
                      key={mat.id || mat.url || index}
                      onClick={() => toggleMaterial(mat.url, mat.title)}
                      className={`flex items-start gap-2.5 p-2.5 rounded-lg cursor-pointer text-xs transition-colors border ${
                        isChecked
                          ? 'bg-planka-card border-planka-accent/50 text-white shadow-sm'
                          : 'bg-planka-card/30 border-planka-border/30 text-planka-textMuted hover:bg-planka-card/60 hover:text-white'
                      }`}
                    >
                      {isChecked ? (
                        <CheckSquare className="w-4 h-4 text-planka-accent flex-shrink-0 mt-0.5" />
                      ) : (
                        <Square className="w-4 h-4 text-planka-border flex-shrink-0 mt-0.5" />
                      )}
                      <div className="min-w-0 flex-1 break-words">
                        <div className="flex items-center gap-2 flex-wrap">
                          <span className="font-semibold text-white">{mat.title}</span>
                          {mat.category && (
                            <span className="text-[10px] text-planka-accent bg-planka-accent/15 border border-planka-accent/30 px-1.5 py-0.2 rounded font-medium">
                              {CATEGORY_LABELS[mat.category] || mat.category}
                            </span>
                          )}
                        </div>
                        <span className="text-[11px] text-indigo-400 font-mono block truncate mt-0.5 select-all" title={mat.url}>
                          {mat.url}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {applyResult && (
              <div className={`p-2.5 rounded-lg text-xs font-medium border flex-shrink-0 ${
                applyResult.startsWith('✓') ? 'bg-emerald-950/50 border-emerald-800 text-emerald-300' : 'bg-rose-950/50 border-rose-800 text-rose-300'
              }`}>
                {applyResult}
              </div>
            )}

          </div>

        </div>

        {/* Modal Footer */}
        <div className="p-4 bg-planka-sidebar border-t border-planka-border/50 flex items-center justify-between">
          <div className="flex items-center gap-2">
            <span className="text-xs text-planka-textMuted">Переместить в:</span>
            <select
              value={vacancy.list_name}
              onChange={(e) => onMove(e.target.value as Vacancy['list_name'])}
              className="bg-planka-card border border-planka-border/60 rounded px-2.5 py-1 text-xs text-white focus:outline-none focus:border-planka-accent"
            >
              <option value="backlog">📥 Найдено (Бэклог)</option>
              <option value="approved">⭐ Одобрено мной</option>
              <option value="applied">🚀 Отклик отправлен</option>
              <option value="interview">💬 Приглашение на интервью</option>
              <option value="archive">❌ Отказ / Архив</option>
            </select>
          </div>

          <div className="flex items-center gap-3">
            <button
              onClick={handleSave}
              disabled={isSaving}
              className="px-4 py-2 bg-planka-card hover:bg-slate-700 text-white rounded-lg text-xs font-semibold border border-planka-border/50 transition-colors"
            >
              {isSaving ? 'Сохранение...' : 'Сохранить изменения'}
            </button>

            <button
              onClick={handleApplyNow}
              disabled={isApplying}
              className="flex items-center gap-2 px-5 py-2 bg-emerald-600 hover:bg-emerald-500 text-white rounded-lg text-xs font-bold shadow-md shadow-emerald-950/50 transition-all active:scale-95 disabled:opacity-50"
            >
              <Send className="w-3.5 h-3.5" />
              <span>{isApplying ? 'Отправка...' : 'Отправить отклик на HH'}</span>
            </button>
          </div>
        </div>

      </div>
    </div>
  );
};
