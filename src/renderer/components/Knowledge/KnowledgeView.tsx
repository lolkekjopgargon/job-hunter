import React, { useState, useEffect } from 'react';
import { FileText, ShieldAlert, FolderGit2, Save, CheckCircle2 } from 'lucide-react';

interface KnowledgeViewProps {
  onLoadFile: (name: string) => Promise<string>;
  onSaveFile: (name: string, content: string) => Promise<boolean>;
}

export const KnowledgeView: React.FC<KnowledgeViewProps> = ({ onLoadFile, onSaveFile }) => {
  const [activeTab, setActiveTab] = useState<'facts' | 'rules' | 'portfolio'>('facts');
  const [content, setContent] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [saveMessage, setSaveMessage] = useState<string | null>(null);

  const loadCurrentTab = async (tab: 'facts' | 'rules' | 'portfolio') => {
    setIsLoading(true);
    try {
      const text = await onLoadFile(tab);
      setContent(text);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    loadCurrentTab(activeTab);
  }, [activeTab]);

  const handleSave = async () => {
    setIsSaving(true);
    setSaveMessage(null);
    try {
      const ok = await onSaveFile(activeTab, content);
      if (ok) {
        setSaveMessage('✓ Файл успешно сохранен!');
        setTimeout(() => setSaveMessage(null), 3000);
      }
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden p-6 max-w-5xl mx-auto w-full">
      {/* Top Description & Tabs */}
      <div className="mb-4">
        <h2 className="text-lg font-bold text-white mb-1">Редактор базы знаний и редполитики ИИ</h2>
        <p className="text-xs text-planka-textMuted">
          Здесь можно прямо в приложении менять факты твоего опыта, примеры живого тона и реестр портфолио. ИИ сразу учитывает эти правки в следующих письмах.
        </p>

        <div className="flex items-center justify-between mt-4">
          <div className="flex gap-2">
            <button
              onClick={() => setActiveTab('facts')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors border ${
                activeTab === 'facts'
                  ? 'bg-planka-accent border-planka-accent text-white shadow-md'
                  : 'bg-planka-sidebar/70 border-planka-border/50 text-planka-textMuted hover:text-white hover:bg-planka-card'
              }`}
            >
              <FileText className="w-4 h-4" />
              Факты кандидата (candidate_facts.md)
            </button>

            <button
              onClick={() => setActiveTab('rules')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors border ${
                activeTab === 'rules'
                  ? 'bg-planka-accent border-planka-accent text-white shadow-md'
                  : 'bg-planka-sidebar/70 border-planka-border/50 text-planka-textMuted hover:text-white hover:bg-planka-card'
              }`}
            >
              <ShieldAlert className="w-4 h-4" />
              Редполитика и тон (application_rules.md)
            </button>

            <button
              onClick={() => setActiveTab('portfolio')}
              className={`flex items-center gap-2 px-3.5 py-2 rounded-lg text-xs font-semibold transition-colors border ${
                activeTab === 'portfolio'
                  ? 'bg-planka-accent border-planka-accent text-white shadow-md'
                  : 'bg-planka-sidebar/70 border-planka-border/50 text-planka-textMuted hover:text-white hover:bg-planka-card'
              }`}
            >
              <FolderGit2 className="w-4 h-4" />
              Ссылки портфолио (portfolio_index.md)
            </button>
          </div>

          <div className="flex items-center gap-3">
            {saveMessage && (
              <span className="text-xs text-emerald-400 font-medium flex items-center gap-1">
                <CheckCircle2 className="w-4 h-4" /> {saveMessage}
              </span>
            )}
            <button
              onClick={handleSave}
              disabled={isSaving || isLoading}
              className="flex items-center gap-2 px-4 py-2 bg-emerald-600 hover:bg-emerald-500 text-xs font-bold text-white rounded-lg transition-colors shadow-md shadow-emerald-950/40 disabled:opacity-50"
            >
              <Save className="w-4 h-4" />
              {isSaving ? 'Сохранение...' : 'Сохранить изменения'}
            </button>
          </div>
        </div>
      </div>

      {/* Editor Box */}
      <div className="flex-1 bg-planka-sidebar/80 border border-planka-border/60 rounded-xl overflow-hidden flex flex-col shadow-inner">
        {isLoading ? (
          <div className="flex-1 flex items-center justify-center text-xs text-planka-textMuted">
            Загрузка файла...
          </div>
        ) : (
          <textarea
            value={content}
            onChange={(e) => setContent(e.target.value)}
            className="w-full flex-1 p-4 bg-transparent text-xs text-white leading-relaxed resize-none focus:outline-none font-mono selection:bg-planka-accent selection:text-white"
            placeholder="Содержимое файла..."
          />
        )}
      </div>
    </div>
  );
};
