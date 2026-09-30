import React, { useState } from 'react';
import { Vacancy, AppSettings } from '../../types';
import { VacancyCard } from './VacancyCard';
import { CardModal } from './CardModal';
import { Inbox, Star, Send, MessageSquare, Archive, RefreshCw, Trash2, Loader2 } from 'lucide-react';

interface KanbanBoardProps {
  vacancies: Vacancy[];
  settings?: AppSettings;
  onRefresh: () => void;
  onMoveVacancy: (vacancyId: string, newList: Vacancy['list_name']) => Promise<void>;
  onUpdateCustomization: (vacancyId: string, resumeId: string, materials: string[], letter: string) => Promise<void>;
  onApplyVacancy: (vacancyId: string) => Promise<void>;
}

const COLUMNS: { id: Vacancy['list_name']; title: string; icon: any; color: string }[] = [
  { id: 'backlog', title: 'Найдено (Бэклог)', icon: Inbox, color: 'text-summer-sky border-sky-500/40' },
  { id: 'approved', title: 'Одобрено мной', icon: Star, color: 'text-amber-400 border-amber-500/40' },
  { id: 'applied', title: 'Отклик отправлен', icon: Send, color: 'text-emerald-400 border-emerald-500/40' },
  { id: 'interview', title: 'Интервью / Созвон', icon: MessageSquare, color: 'text-purple-400 border-purple-500/40' },
  { id: 'archive', title: 'Отказ / Архив', icon: Archive, color: 'text-zinc-400 border-zinc-600/40' },
];

export const KanbanBoard: React.FC<KanbanBoardProps> = ({
  vacancies,
  settings,
  onRefresh,
  onMoveVacancy,
  onUpdateCustomization,
  onApplyVacancy,
}) => {
  const [selectedVacancy, setSelectedVacancy] = useState<Vacancy | null>(null);
  const [generatingIds, setGeneratingIds] = useState<Record<string, boolean>>({});
  const [isClearingArchive, setIsClearingArchive] = useState(false);

  const electronAPI = (window as any).electronAPI;

  const handleClearArchive = async () => {
    if (!electronAPI?.clearArchive) return;
    const confirmed = window.confirm(
      'Очистить колонку «Отказ / Архив»?\n\nКарточки исчезнут с доски, но навсегда останутся в базе исключений — сканер HeadHunter больше никогда не предложит эти вакансии снова.'
    );
    if (!confirmed) return;

    setIsClearingArchive(true);
    try {
      const res = await electronAPI.clearArchive();
      if (res?.success) {
        onRefresh();
      } else {
        alert(`Ошибка очистки: ${res?.error || 'Не удалось очистить архив'}`);
      }
    } catch (e: any) {
      alert(`Ошибка: ${e.message || e}`);
    } finally {
      setIsClearingArchive(false);
    }
  };

  const handleStartGenerateLetter = async (vacancyId: string, regenerate = false) => {
    setGeneratingIds(prev => ({ ...prev, [vacancyId]: true }));
    try {
      if (electronAPI?.generateLetter) {
        const res = await electronAPI.generateLetter(vacancyId, regenerate);
        if (res.success && res.cover_letter) {
          // Update selected vacancy if open
          setSelectedVacancy(prev => {
            if (prev && prev.id === vacancyId) {
              return { ...prev, cover_letter: res.cover_letter };
            }
            return prev;
          });
          onRefresh();
        } else {
          alert(`Не удалось сгенерировать: ${res.error || 'Проверьте настройки ИИ'}`);
        }
      }
    } catch (e: any) {
      alert(`Ошибка генерации: ${e.message || e}`);
    } finally {
      setGeneratingIds(prev => ({ ...prev, [vacancyId]: false }));
    }
  };

  return (
    <div className="flex-1 flex flex-col overflow-hidden">
      {/* Columns Container */}
      <div className="flex-1 overflow-x-auto p-4 flex gap-4 items-start select-none">
        {COLUMNS.map((col) => {
          const colVacancies = vacancies.filter((v) => v.list_name === col.id);
          const IconComponent = col.icon;

          return (
            <div
              key={col.id}
              className="w-80 flex-shrink-0 bg-planka-sidebar/70 border border-planka-border/40 rounded-xl flex flex-col max-h-[85vh] shadow-lg shadow-black/20"
            >
              {/* Column Header */}
              <div className="p-3.5 border-b border-planka-border/30 flex items-center justify-between">
                <div className="flex items-center gap-2">
                  <IconComponent className={`w-4 h-4 ${col.color.split(' ')[0]}`} />
                  <span className="text-xs font-bold text-white tracking-wide uppercase">{col.title}</span>
                </div>
                <div className="flex items-center gap-2">
                  {col.id === 'archive' && colVacancies.length > 0 && (
                    <button
                      onClick={handleClearArchive}
                      disabled={isClearingArchive}
                      title="Очистить архив (все вакансии навсегда сохраняются в базе исключений)"
                      className="flex items-center gap-1 px-2 py-0.5 text-[11px] font-medium text-zinc-400 hover:text-rose-300 hover:bg-rose-950/40 rounded border border-zinc-700/50 hover:border-rose-800/60 transition-all active:scale-95 disabled:opacity-50"
                    >
                      {isClearingArchive ? (
                        <Loader2 className="w-3 h-3 animate-spin text-rose-400" />
                      ) : (
                        <Trash2 className="w-3 h-3 text-rose-400" />
                      )}
                      <span>Очистить</span>
                    </button>
                  )}
                  <span className="text-xs font-mono font-semibold bg-planka-card px-2 py-0.5 rounded-full text-planka-textMuted border border-planka-border/40">
                    {colVacancies.length}
                  </span>
                </div>
              </div>

              {/* Cards List */}
              <div className="flex-1 overflow-y-auto p-2.5">
                {colVacancies.length === 0 ? (
                  <div className="h-32 flex items-center justify-center text-xs text-planka-textMuted/60 italic border-2 border-dashed border-planka-border/20 rounded-lg m-1">
                    Нет вакансий
                  </div>
                ) : (
                  colVacancies.map((vac) => (
                    <VacancyCard
                      key={vac.id}
                      vacancy={vac}
                      isGenerating={Boolean(generatingIds[vac.id])}
                      onClick={() => setSelectedVacancy(vac)}
                      onMoveQuick={async (target) => {
                        await onMoveVacancy(vac.id, target);
                        onRefresh();
                      }}
                    />
                  ))
                )}
              </div>
            </div>
          );
        })}
      </div>

      {/* Selected Card Modal */}
      {selectedVacancy && (
        <CardModal
          vacancy={selectedVacancy}
          settings={settings}
          isGeneratingLetter={Boolean(generatingIds[selectedVacancy.id])}
          onGenerateLetter={(regen) => handleStartGenerateLetter(selectedVacancy.id, regen)}
          onClose={() => setSelectedVacancy(null)}
          onSave={async (resumeId, materials, letter) => {
            await onUpdateCustomization(selectedVacancy.id, resumeId, materials, letter);
            setSelectedVacancy({
              ...selectedVacancy,
              selected_resume_id: resumeId,
              selected_materials: materials,
              cover_letter: letter,
            });
            onRefresh();
          }}
          onApply={async () => {
            await onApplyVacancy(selectedVacancy.id);
            setSelectedVacancy({
              ...selectedVacancy,
              list_name: 'applied',
            });
            onRefresh();
          }}
          onMove={async (targetList) => {
            await onMoveVacancy(selectedVacancy.id, targetList);
            setSelectedVacancy({
              ...selectedVacancy,
              list_name: targetList,
            });
            onRefresh();
          }}
        />
      )}
    </div>
  );
};
