import React, { useState, useEffect, useRef } from 'react';
import { LogEntry } from '../../types';
import { Terminal, X, Copy, Trash2, ArrowDown, Check, Search, ShieldAlert, Sparkles, Globe } from 'lucide-react';

interface LogModalProps {
  isOpen: boolean;
  onClose: () => void;
  logs: LogEntry[];
  onClearLogs: () => void;
}

export const LogModal: React.FC<LogModalProps> = ({
  isOpen,
  onClose,
  logs,
  onClearLogs,
}) => {
  const [filter, setFilter] = useState<'all' | 'hh' | 'error' | 'success'>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [autoScroll, setAutoScroll] = useState(true);
  const [copied, setCopied] = useState(false);
  const logContainerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (autoScroll && logContainerRef.current) {
      logContainerRef.current.scrollTop = logContainerRef.current.scrollHeight;
    }
  }, [logs, autoScroll]);

  if (!isOpen) return null;

  const filteredLogs = logs.filter((l) => {
    if (filter === 'hh' && l.level !== 'hh') return false;
    if (filter === 'error' && l.level !== 'error') return false;
    if (filter === 'success' && l.level !== 'success') return false;
    if (searchQuery) {
      return l.message.toLowerCase().includes(searchQuery.toLowerCase());
    }
    return true;
  });

  const handleCopyAll = () => {
    const fullText = logs.map((l) => `[${l.timestamp}] [${l.level.toUpperCase()}] ${l.message}`).join('\n');
    navigator.clipboard.writeText(fullText);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const getBadgeStyle = (level: LogEntry['level']) => {
    switch (level) {
      case 'error':
        return 'text-rose-400 bg-rose-950/60 border-rose-800/50';
      case 'success':
        return 'text-emerald-400 bg-emerald-950/60 border-emerald-800/50';
      case 'hh':
        return 'text-sky-400 bg-sky-950/60 border-sky-800/50';
      default:
        return 'text-slate-400 bg-slate-800/60 border-slate-700/50';
    }
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/75 backdrop-blur-sm p-4 animate-in fade-in duration-150">
      <div className="bg-[#181a1e] border border-planka-border w-full max-w-4xl h-[85vh] rounded-2xl shadow-2xl flex flex-col overflow-hidden text-planka-text">
        
        {/* Modal Header */}
        <div className="px-5 py-3.5 border-b border-planka-border/60 bg-[#1e2025] flex items-center justify-between flex-shrink-0">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 rounded-lg bg-indigo-950/80 border border-indigo-700/50 flex items-center justify-center text-indigo-400">
              <Terminal className="w-4 h-4" />
            </div>
            <div>
              <div className="flex items-center gap-2">
                <h3 className="font-bold text-sm text-white">Журнал работы скриптов и парсера</h3>
                <span className="flex h-2 w-2 relative">
                  <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-emerald-400 opacity-75"></span>
                  <span className="relative inline-flex rounded-full h-2 w-2 bg-emerald-500"></span>
                </span>
              </div>
              <p className="text-[11px] text-planka-textMuted">
                Потоковый вывод консоли Python (поиск HeadHunter, LLM генерация, пакетная отправка)
              </p>
            </div>
          </div>

          <div className="flex items-center gap-2">
            <button
              onClick={handleCopyAll}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-planka-card hover:bg-slate-700 text-planka-text border border-planka-border/50 transition-colors"
              title="Скопировать все строки"
            >
              {copied ? <Check className="w-3.5 h-3.5 text-emerald-400" /> : <Copy className="w-3.5 h-3.5" />}
              <span>{copied ? 'Скопировано' : 'Копировать'}</span>
            </button>

            <button
              onClick={onClearLogs}
              className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-planka-card hover:bg-rose-950/40 hover:text-rose-300 text-planka-text border border-planka-border/50 transition-colors"
              title="Очистить журнал"
            >
              <Trash2 className="w-3.5 h-3.5" />
              <span>Очистить</span>
            </button>

            <button
              onClick={onClose}
              className="p-1.5 rounded-lg hover:bg-planka-card text-planka-textMuted hover:text-white transition-colors ml-1"
            >
              <X className="w-5 h-5" />
            </button>
          </div>
        </div>

        {/* Toolbar & Filters */}
        <div className="px-5 py-2.5 bg-[#141619] border-b border-planka-border/40 flex items-center justify-between gap-4 flex-shrink-0 text-xs">
          <div className="flex items-center gap-1.5">
            <button
              onClick={() => setFilter('all')}
              className={`px-2.5 py-1 rounded-md font-medium transition-all ${
                filter === 'all'
                  ? 'bg-planka-accent text-white shadow-sm'
                  : 'text-planka-textMuted hover:text-white hover:bg-planka-card'
              }`}
            >
              Все ({logs.length})
            </button>
            <button
              onClick={() => setFilter('hh')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition-all ${
                filter === 'hh'
                  ? 'bg-sky-600 text-white shadow-sm'
                  : 'text-planka-textMuted hover:text-sky-300 hover:bg-planka-card'
              }`}
            >
              <Globe className="w-3 h-3" />
              HH Поиск ({logs.filter((l) => l.level === 'hh').length})
            </button>
            <button
              onClick={() => setFilter('success')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition-all ${
                filter === 'success'
                  ? 'bg-emerald-600 text-white shadow-sm'
                  : 'text-planka-textMuted hover:text-emerald-300 hover:bg-planka-card'
              }`}
            >
              <Sparkles className="w-3 h-3" />
              Успех ({logs.filter((l) => l.level === 'success').length})
            </button>
            <button
              onClick={() => setFilter('error')}
              className={`flex items-center gap-1 px-2.5 py-1 rounded-md font-medium transition-all ${
                filter === 'error'
                  ? 'bg-rose-600 text-white shadow-sm'
                  : 'text-planka-textMuted hover:text-rose-300 hover:bg-planka-card'
              }`}
            >
              <ShieldAlert className="w-3 h-3" />
              Ошибки ({logs.filter((l) => l.level === 'error').length})
            </button>
          </div>

          <div className="flex items-center gap-3">
            <div className="relative w-48">
              <Search className="w-3.5 h-3.5 absolute left-2.5 top-1/2 -translate-y-1/2 text-planka-textMuted" />
              <input
                type="text"
                placeholder="Фильтр по тексту..."
                value={searchQuery}
                onChange={(e) => setSearchQuery(e.target.value)}
                className="w-full pl-8 pr-2.5 py-1 bg-black/40 border border-planka-border/50 rounded-md text-xs text-white placeholder-planka-textMuted focus:outline-none focus:border-planka-accent"
              />
            </div>

            <label className="flex items-center gap-1.5 text-planka-textMuted hover:text-white cursor-pointer select-none">
              <input
                type="checkbox"
                checked={autoScroll}
                onChange={(e) => setAutoScroll(e.target.checked)}
                className="rounded border-planka-border bg-black/40 text-planka-accent focus:ring-0 w-3.5 h-3.5"
              />
              <ArrowDown className="w-3 h-3" />
              <span>Автоскролл</span>
            </label>
          </div>
        </div>

        {/* Console Output Terminal */}
        <div
          ref={logContainerRef}
          className="flex-1 bg-[#0d0e11] p-4 overflow-y-auto font-mono text-xs leading-relaxed space-y-1 select-text scrollbar-thin scrollbar-thumb-zinc-700"
        >
          {filteredLogs.length === 0 ? (
            <div className="h-full flex flex-col items-center justify-center text-planka-textMuted space-y-2">
              <Terminal className="w-10 h-10 opacity-30" />
              <p>Логов пока нет. Нажмите «Сканировать HH» или запустите отправку.</p>
            </div>
          ) : (
            filteredLogs.map((log) => (
              <div key={log.id} className="flex items-start gap-2.5 hover:bg-white/[0.02] px-1.5 py-0.5 rounded">
                <span className="text-zinc-500 flex-shrink-0 select-none">
                  [{log.timestamp}]
                </span>
                <span
                  className={`text-[10px] px-1.5 py-0.5 rounded border flex-shrink-0 font-sans uppercase font-bold tracking-wider select-none ${getBadgeStyle(
                    log.level
                  )}`}
                >
                  {log.level}
                </span>
                <span className="text-zinc-200 whitespace-pre-wrap break-words flex-1">
                  {log.message}
                </span>
              </div>
            ))
          )}
        </div>

        {/* Modal Footer */}
        <div className="px-5 py-2.5 bg-[#181a1e] border-t border-planka-border/40 flex items-center justify-between text-[11px] text-planka-textMuted flex-shrink-0">
          <span>Показано: {filteredLogs.length} из {logs.length} сообщений</span>
          <span>Job Hunter Sidecar IPC</span>
        </div>

      </div>
    </div>
  );
};
