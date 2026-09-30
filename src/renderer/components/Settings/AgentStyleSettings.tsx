import React, { useState, useEffect } from 'react';
import { Bot, Save, Check, Loader2 } from 'lucide-react';

interface AgentStyleSettingsProps {
  systemPrompt?: string;
  onSavePrompt?: (prompt: string) => Promise<void>;
}

export const AgentStyleSettings: React.FC<AgentStyleSettingsProps> = () => {

  const [innerTab, setInnerTab] = useState<'prompt' | 'facts'>('prompt');

  // --- Prompt state (loaded from application_rules.md in userData) ---
  const [prompt, setPrompt] = useState('');
  const [isLoadingPrompt, setIsLoadingPrompt] = useState(true);
  const [isSavingPrompt, setIsSavingPrompt] = useState(false);
  const [isSavedPrompt, setIsSavedPrompt] = useState(false);
  const [savePromptError, setSavePromptError] = useState('');

  // --- Facts state (loaded from candidate_facts.md in userData) ---
  const [facts, setFacts] = useState('');
  const [isLoadingFacts, setIsLoadingFacts] = useState(false);
  const [isSavingFacts, setIsSavingFacts] = useState(false);
  const [isSavedFacts, setIsSavedFacts] = useState(false);

  const electronAPI = (window as any).electronAPI;

  // Load prompt from application_rules.md
  useEffect(() => {
    const loadPrompt = async () => {
      if (electronAPI?.getKnowledge) {
        setIsLoadingPrompt(true);
        try {
          const res = await electronAPI.getKnowledge('rules');
          // If file exists — show its content. If not — empty (user writes their own).
          setPrompt(res?.content?.trim() ?? '');
        } catch {
          setPrompt('');
        } finally {
          setIsLoadingPrompt(false);
        }
      } else {
        setPrompt('');
        setIsLoadingPrompt(false);
      }
    };
    loadPrompt();
  }, []);

  // Load facts from candidate_facts.md
  useEffect(() => {
    const loadFacts = async () => {
      if (electronAPI?.getKnowledge) {
        setIsLoadingFacts(true);
        try {
          const res = await electronAPI.getKnowledge('facts');
          setFacts(res?.content ?? '');
        } finally {
          setIsLoadingFacts(false);
        }
      }
    };
    loadFacts();
  }, []);


  const handleSavePrompt = async () => {
    if (!electronAPI?.saveKnowledge) return;
    setIsSavingPrompt(true);
    setSavePromptError('');
    try {
      await electronAPI.saveKnowledge('rules', prompt);
      setIsSavedPrompt(true);
      setTimeout(() => setIsSavedPrompt(false), 2500);
    } catch (e: any) {
      setSavePromptError(e?.message || 'Ошибка сохранения');
    } finally {
      setIsSavingPrompt(false);
    }
  };

  const handleSaveFacts = async () => {
    if (!electronAPI?.saveKnowledge) return;
    setIsSavingFacts(true);
    try {
      await electronAPI.saveKnowledge('facts', facts);
      setIsSavedFacts(true);
      setTimeout(() => setIsSavedFacts(false), 2500);
    } finally {
      setIsSavingFacts(false);
    }
  };


  return (
    <div className="bg-planka-card/70 border border-planka-border/40 rounded-xl p-5 shadow-sm space-y-4">
      {/* Sub-tab switcher */}
      <div className="flex items-center justify-between border-b border-planka-border/40 pb-3">
        <div className="flex items-center gap-2">
          <button
            onClick={() => setInnerTab('prompt')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              innerTab === 'prompt'
                ? 'bg-purple-600 text-white shadow-sm shadow-purple-950/40'
                : 'text-planka-textMuted hover:text-white hover:bg-planka-bg'
            }`}
          >
            1. Правила стиля и редполитика
          </button>

          <button
            onClick={() => setInnerTab('facts')}
            className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all ${
              innerTab === 'facts'
                ? 'bg-purple-600 text-white shadow-sm shadow-purple-950/40'
                : 'text-planka-textMuted hover:text-white hover:bg-planka-bg'
            }`}
          >
            2. Опыт и факты кандидата
          </button>
        </div>

        {innerTab === 'prompt' ? (
          <div className="flex items-center gap-2">
            <button
              onClick={handleSavePrompt}
              disabled={isSavingPrompt || isLoadingPrompt}
              className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-purple-600 hover:bg-purple-500 text-white shadow-sm shadow-purple-900/40 active:scale-95 transition-all disabled:opacity-60"
            >
              {isSavedPrompt ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-300" />
                  <span>Сохранено!</span>
                </>
              ) : isSavingPrompt ? (
                <>
                  <Loader2 className="w-3.5 h-3.5 animate-spin" />
                  <span>Сохранение...</span>
                </>
              ) : (
                <>
                  <Save className="w-3.5 h-3.5" />
                  <span>Сохранить правила</span>
                </>
              )}
            </button>
          </div>
        ) : (
          <button
            onClick={handleSaveFacts}
            disabled={isSavingFacts || isLoadingFacts}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-900/40 active:scale-95 transition-all disabled:opacity-60"
          >
            {isSavedFacts ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-200" />
                <span>Факты сохранены!</span>
              </>
            ) : isSavingFacts ? (
              <>
                <Loader2 className="w-3.5 h-3.5 animate-spin" />
                <span>Сохранение...</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>Сохранить факты</span>
              </>
            )}
          </button>
        )}
      </div>

      {innerTab === 'prompt' ? (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-planka-textMuted">
            <Bot className="w-4 h-4 text-purple-400" />
            <span>Системный промпт для ИИ — сохраняется в <code className="font-mono text-purple-300">application_rules.md</code> и читается при каждой генерации письма</span>
          </div>
          {isLoadingPrompt ? (
            <div className="py-12 text-center text-xs text-planka-textMuted font-mono animate-pulse">
              Загрузка правил стиля...
            </div>
          ) : (
            <textarea
              value={prompt}
              onChange={(e) => setPrompt(e.target.value)}
              rows={12}
              className="w-full bg-planka-bg/80 border border-planka-border/60 rounded-xl p-3.5 text-xs text-slate-200 font-mono leading-relaxed resize-y focus:outline-none focus:border-purple-500/80 transition-colors"
              placeholder="Введите правила стиля и редполитики для ИИ..."
            />
          )}
          {savePromptError && (
            <p className="text-xs text-red-400 font-mono">{savePromptError}</p>
          )}
        </div>
      ) : (
        <div className="space-y-2">
          <div className="flex items-center gap-2 text-xs text-planka-textMuted">
            <Bot className="w-4 h-4 text-emerald-400" />
            <span>Единый источник правды: реальные проекты (Owlcat, VEA, CGF), образование и проверенный опыт, используемый ИИ</span>
          </div>
          {isLoadingFacts ? (
            <div className="py-12 text-center text-xs text-planka-textMuted font-mono animate-pulse">
              Загрузка фактов из candidate_facts.md...
            </div>
          ) : (
            <textarea
              value={facts}
              onChange={(e) => setFacts(e.target.value)}
              rows={16}
              className="w-full bg-planka-bg/80 border border-planka-border/60 rounded-xl p-3.5 text-xs text-slate-200 font-mono leading-relaxed resize-y focus:outline-none focus:border-emerald-500/80 transition-colors"
              placeholder="Введите проверенные факты опыта кандидата..."
            />
          )}
        </div>
      )}
    </div>
  );
};
