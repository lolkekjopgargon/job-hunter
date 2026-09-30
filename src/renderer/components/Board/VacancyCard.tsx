import React from 'react';
import { Vacancy } from '../../types';
import { Building2, DollarSign, Wifi, Bot, AlertTriangle, FileText, ChevronRight } from 'lucide-react';

interface VacancyCardProps {
  vacancy: Vacancy;
  onClick: () => void;
  onMoveQuick?: (targetList: Vacancy['list_name']) => void;
  isGenerating?: boolean;
}

export const VacancyCard: React.FC<VacancyCardProps> = ({ vacancy, onClick, onMoveQuick, isGenerating }) => {
  const hasLetter = Boolean(vacancy.cover_letter && vacancy.cover_letter.trim().length > 0);

  return (
    <div
      onClick={onClick}
      className="bg-planka-card hover:bg-planka-cardHover border border-planka-border/40 rounded-lg p-3.5 mb-2.5 cursor-pointer transition-all duration-150 shadow-sm hover:shadow-md group relative"
    >
      {/* Title & Employer */}
      <div className="flex items-start justify-between gap-2 mb-2">
        <h4 className="text-sm font-semibold text-white group-hover:text-planka-accent transition-colors leading-snug">
          {vacancy.title}
        </h4>
      </div>

      <div className="flex items-center text-xs text-planka-textMuted mb-2.5 gap-1.5">
        <Building2 className="w-3.5 h-3.5 flex-shrink-0" />
        <span className="truncate font-medium">{vacancy.employer}</span>
      </div>

      {/* Badges / Labels */}
      <div className="flex flex-wrap gap-1.5 mb-3">
        {vacancy.salary && vacancy.salary !== 'Не указана' && (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-950/60 text-emerald-300 border border-emerald-800/40 px-2 py-0.5 rounded">
            <DollarSign className="w-3 h-3" />
            {vacancy.salary}
          </span>
        )}

        {vacancy.is_remote ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-cyan-950/60 text-cyan-300 border border-cyan-800/40 px-2 py-0.5 rounded">
            <Wifi className="w-3 h-3" />
            Удаленка
          </span>
        ) : null}

        {isGenerating ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-semibold bg-purple-900/70 text-purple-200 border border-purple-500/60 px-2 py-0.5 rounded animate-pulse shadow-sm">
            <Bot className="w-3 h-3 animate-spin text-purple-300" />
            ИИ пишет...
          </span>
        ) : hasLetter ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-emerald-950/70 text-emerald-300 border border-emerald-700/50 px-2 py-0.5 rounded shadow-sm">
            <Bot className="w-3 h-3 text-emerald-400" />
            ✓ Письмо готово
          </span>
        ) : null}

        {vacancy.has_questionnaire ? (
          <span className="inline-flex items-center gap-1 text-[11px] font-medium bg-amber-950/60 text-amber-300 border border-amber-800/40 px-2 py-0.5 rounded">
            <AlertTriangle className="w-3 h-3" />
            Анкета
          </span>
        ) : null}
      </div>

      {/* Footer / Quick action */}
      <div className="flex items-center justify-between pt-2 border-t border-planka-border/30 text-[11px] text-planka-textMuted">
        <span className="font-mono text-[10px]">ID: {vacancy.id}</span>
        {onMoveQuick && vacancy.list_name === 'backlog' && (
          <button
            onClick={(e) => {
              e.stopPropagation();
              onMoveQuick('approved');
            }}
            className="flex items-center gap-1 text-planka-accent hover:text-white font-medium hover:underline px-1.5 py-0.5 rounded"
          >
            В одобренные
            <ChevronRight className="w-3 h-3" />
          </button>
        )}
      </div>
    </div>
  );
};
