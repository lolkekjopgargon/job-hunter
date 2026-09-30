import React, { useState, useEffect } from 'react';
import { PortfolioLink } from '../../types';
import { Link2, Plus, Trash2, ExternalLink, Save, Check, ArrowUp, ArrowDown, RotateCcw } from 'lucide-react';

interface PortfolioLinksSettingsProps {
  links: PortfolioLink[];
  onSaveLinks: (links: PortfolioLink[]) => Promise<void>;
}

export const DEFAULT_PORTFOLIO_LINKS: PortfolioLink[] = [
  { id: 'gd_spec', title: 'Game Design Specification (GDD / Notion)', url: 'https://drive.google.com/file/d/1rgMxRtjwmq1XIpI5rt32LeBj8ZRrS93r/view?usp=drive_link', category: 'game_design' },
  { id: 'combat_balance', title: 'Combat Balance & Data Architecture (Sheets)', url: 'https://drive.google.com/file/d/1RO46ycLAckr803ahy8ULLimjzwcHr4Bx/view?usp=drive_link', category: 'game_design' },
  { id: 'rpg_tracker', title: 'RPG Life Tracker / Dynamic Quest Engine Demo', url: 'https://youtu.be/_teOplLx3QY', category: 'game_design' },
  { id: 'artstation', title: 'ArtStation Portfolio (3D / UE5)', url: 'https://www.artstation.com/tejedakardenas', category: '3d_art' },
  { id: 'ue5_previs', title: 'Unreal Engine 5 Previs Reel (Cinematics)', url: 'https://youtu.be/II82L2EZ8g0', category: '3d_art' },
  { id: 'narrative_sample', title: 'Narrative Sample (Dialogue & Lore)', url: 'https://drive.google.com/file/d/1xvJnbGAKg970oqK4wQ2VGYpVNMDA6G/view?usp=drive_link', category: 'narrative' },
  { id: 'game_promo', title: 'Game Promo / Investor Presentation', url: 'https://drive.google.com/file/d/1npzQUk5a0eNipXLLN-9YJZGS1n8MUcIt/view?usp=drivesdk', category: 'game_design' },
  { id: 'acting_reel', title: 'Актерская визитка / Шоурил', url: 'https://youtu.be/5f1FLQ6sHr8', category: 'voice' }
];

export const CATEGORY_OPTIONS = [
  { value: 'game_design', label: 'Гейм-дизайн' },
  { value: 'narrative', label: 'Нарратив' },
  { value: '3d_art', label: '3D и UE5' },
  { value: 'voice', label: 'Озвучка / Шоурил' },
  { value: 'general', label: 'Общее' },
];

export const PortfolioLinksSettings: React.FC<PortfolioLinksSettingsProps> = ({
  links,
  onSaveLinks,
}) => {
  const [items, setItems] = useState<PortfolioLink[]>(() => {
    return Array.isArray(links) && links.length > 0 ? links : DEFAULT_PORTFOLIO_LINKS;
  });
  const [newTitle, setNewTitle] = useState('');
  const [newUrl, setNewUrl] = useState('');
  const [newCat, setNewCat] = useState('game_design');
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);

  useEffect(() => {
    if (links && Array.isArray(links) && links.length > 0) {
      setItems(links);
    }
  }, [links]);

  const handleAdd = () => {
    if (!newTitle.trim() || !newUrl.trim()) return;
    const newItem: PortfolioLink = {
      id: 'link_' + Date.now().toString(36) + '_' + Math.random().toString(36).substring(2, 6),
      title: newTitle.trim(),
      url: newUrl.trim(),
      category: newCat,
    };
    const updated = [...items, newItem];
    setItems(updated);
    setNewTitle('');
    setNewUrl('');
    setHasChanges(true);
  };

  const handleUpdateItem = (id: string, field: keyof PortfolioLink, value: string) => {
    setItems((prev) =>
      prev.map((it) => (it.id === id ? { ...it, [field]: value } : it))
    );
    setHasChanges(true);
  };

  const handleDelete = (id: string) => {
    setItems((prev) => prev.filter((it) => it.id !== id));
    setHasChanges(true);
  };

  const handleMove = (index: number, direction: 'up' | 'down') => {
    const targetIndex = direction === 'up' ? index - 1 : index + 1;
    if (targetIndex < 0 || targetIndex >= items.length) return;
    const newItems = [...items];
    const temp = newItems[index];
    newItems[index] = newItems[targetIndex];
    newItems[targetIndex] = temp;
    setItems(newItems);
    setHasChanges(true);
  };

  const handleResetToDefaults = () => {
    if (window.confirm('Восстановить стандартный набор из 8 материалов портфолио? Ваши текущие правки будут заменены.')) {
      setItems(DEFAULT_PORTFOLIO_LINKS);
      setHasChanges(true);
    }
  };

  const handleSave = async () => {
    setIsSaving(true);
    try {
      await onSaveLinks(items);
      setIsSaved(true);
      setHasChanges(false);
      setTimeout(() => setIsSaved(false), 2500);
    } finally {
      setIsSaving(false);
    }
  };

  return (
    <div className="bg-planka-sidebar/70 border border-planka-border/50 rounded-xl p-5 shadow-sm space-y-5">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-3 border-b border-planka-border/40">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 rounded-lg bg-indigo-500/20 text-indigo-400 flex items-center justify-center border border-indigo-500/30 flex-shrink-0 shadow-sm">
            <Link2 className="w-5 h-5" />
          </div>
          <div>
            <h3 className="text-base font-bold text-white flex items-center gap-2">
              Портфолио и материалы для откликов
              {hasChanges && (
                <span className="text-[10px] font-semibold uppercase bg-amber-500/20 text-amber-300 border border-amber-500/30 px-2 py-0.5 rounded-full">
                  Есть несохраненные правки
                </span>
              )}
            </h3>
            <p className="text-xs text-planka-textMuted">
              Здесь вы можете редактировать названия, ссылки и категории. Именно эти ссылки подхватываются в чекбоксах карточки при формировании отклика.
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2 flex-shrink-0">
          <button
            onClick={handleResetToDefaults}
            className="flex items-center gap-1.5 px-3 py-2 rounded-lg text-xs font-medium bg-planka-card/80 hover:bg-planka-card text-planka-textMuted hover:text-white border border-planka-border/50 transition-colors"
            title="Восстановить исходные ссылки"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span className="hidden sm:inline">Сброс</span>
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className={`flex items-center gap-2 px-4 py-2 rounded-lg text-xs font-bold transition-all shadow-md active:scale-95 ${
              isSaved
                ? 'bg-emerald-600 text-white shadow-emerald-950/40'
                : hasChanges
                ? 'bg-planka-accent hover:bg-planka-accentHover text-white shadow-indigo-950/50 animate-pulse'
                : 'bg-planka-accent hover:bg-planka-accentHover text-white shadow-indigo-950/50'
            }`}
          >
            {isSaved ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Сохранено!</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>{isSaving ? 'Сохранение...' : 'Сохранить ссылки'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      {/* Add New Link Card */}
      <div className="bg-planka-card/60 border border-planka-border/60 rounded-xl p-4 space-y-3">
        <h4 className="text-xs font-bold text-white uppercase tracking-wider flex items-center gap-1.5">
          <Plus className="w-4 h-4 text-emerald-400" /> Добавить новую ссылку в портфолио
        </h4>
        <div className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-center">
          <div className="sm:col-span-4">
            <label className="block text-[10px] text-planka-textMuted uppercase font-semibold mb-1">
              Название материала
            </label>
            <input
              type="text"
              placeholder="Напр. Дизайн-документ (Notion)"
              value={newTitle}
              onChange={(e) => setNewTitle(e.target.value)}
              className="w-full bg-planka-bg/80 border border-planka-border/70 rounded-lg px-3 py-2 text-xs text-white placeholder-slate-500 focus:outline-none focus:border-planka-accent font-medium"
            />
          </div>
          <div className="sm:col-span-5">
            <label className="block text-[10px] text-planka-textMuted uppercase font-semibold mb-1">
              URL адрес
            </label>
            <input
              type="url"
              placeholder="https://..."
              value={newUrl}
              onChange={(e) => setNewUrl(e.target.value)}
              className="w-full bg-planka-bg/80 border border-planka-border/70 rounded-lg px-3 py-2 text-xs text-white font-mono placeholder-slate-500 focus:outline-none focus:border-planka-accent"
            />
          </div>
          <div className="sm:col-span-2">
            <label className="block text-[10px] text-planka-textMuted uppercase font-semibold mb-1">
              Категория
            </label>
            <select
              value={newCat}
              onChange={(e) => setNewCat(e.target.value)}
              className="w-full bg-planka-bg/80 border border-planka-border/70 rounded-lg px-2.5 py-2 text-xs text-white focus:outline-none focus:border-planka-accent font-medium"
            >
              {CATEGORY_OPTIONS.map((c) => (
                <option key={c.value} value={c.value}>
                  {c.label}
                </option>
              ))}
            </select>
          </div>
          <div className="sm:col-span-1 flex items-end justify-end pt-5">
            <button
              onClick={handleAdd}
              disabled={!newTitle.trim() || !newUrl.trim()}
              className="w-full sm:w-auto p-2 bg-emerald-600 hover:bg-emerald-500 disabled:opacity-40 text-white rounded-lg transition-all flex items-center justify-center shadow-sm shadow-emerald-950/40"
              title="Добавить ссылку"
            >
              <Plus className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Editable Links List */}
      <div className="space-y-2.5">
        <div className="flex items-center justify-between text-xs text-planka-textMuted px-1">
          <span>Список активных материалов ({items.length})</span>
          <span className="text-[11px] italic">Все поля можно редактировать и переименовывать прямо в строках</span>
        </div>

        {items.length === 0 ? (
          <div className="text-center py-8 text-xs text-planka-textMuted bg-planka-card/30 rounded-xl border border-dashed border-planka-border/40">
            Список ссылок пуст. Добавьте свои ссылки выше или нажмите «Сброс» для стандартного набора.
          </div>
        ) : (
          items.map((it, idx) => (
            <div
              key={it.id || idx}
              className="p-3 bg-planka-card/50 hover:bg-planka-card/80 border border-planka-border/40 hover:border-planka-border/80 rounded-xl transition-all space-y-2 group shadow-sm"
            >
              {/* Row 1: Title, Category, Reorder, Actions */}
              <div className="flex items-center gap-2">
                {/* Reorder Buttons */}
                <div className="flex flex-col gap-0.5 text-planka-textMuted flex-shrink-0">
                  <button
                    onClick={() => handleMove(idx, 'up')}
                    disabled={idx === 0}
                    className="p-0.5 hover:text-white disabled:opacity-20 transition-colors"
                    title="Поднять выше"
                  >
                    <ArrowUp className="w-3 h-3" />
                  </button>
                  <button
                    onClick={() => handleMove(idx, 'down')}
                    disabled={idx === items.length - 1}
                    className="p-0.5 hover:text-white disabled:opacity-20 transition-colors"
                    title="Опустить ниже"
                  >
                    <ArrowDown className="w-3 h-3" />
                  </button>
                </div>

                {/* Editable Title */}
                <div className="flex-1">
                  <input
                    type="text"
                    value={it.title}
                    onChange={(e) => handleUpdateItem(it.id, 'title', e.target.value)}
                    placeholder="Название материала"
                    className="w-full bg-planka-bg/60 border border-planka-border/50 rounded-lg px-3 py-1.5 text-xs font-semibold text-white focus:outline-none focus:border-planka-accent focus:bg-planka-bg transition-colors"
                    title="Нажмите для переименования"
                  />
                </div>

                {/* Category Select */}
                <div className="w-36 flex-shrink-0">
                  <select
                    value={it.category || 'general'}
                    onChange={(e) => handleUpdateItem(it.id, 'category', e.target.value)}
                    className="w-full bg-planka-bg/60 border border-planka-border/50 rounded-lg px-2 py-1.5 text-xs text-planka-text focus:outline-none focus:border-planka-accent"
                  >
                    {CATEGORY_OPTIONS.map((c) => (
                      <option key={c.value} value={c.value}>
                        {c.label}
                      </option>
                    ))}
                  </select>
                </div>

                {/* Actions: Open external URL & Delete */}
                <div className="flex items-center gap-1 flex-shrink-0">
                  {it.url && (
                    <a
                      href={it.url}
                      target="_blank"
                      rel="noreferrer"
                      className="p-1.5 text-planka-textMuted hover:text-indigo-300 hover:bg-indigo-950/40 rounded-lg transition-colors"
                      title="Открыть ссылку в браузере"
                    >
                      <ExternalLink className="w-3.5 h-3.5" />
                    </a>
                  )}
                  <button
                    onClick={() => handleDelete(it.id)}
                    className="p-1.5 text-planka-textMuted hover:text-rose-400 hover:bg-rose-950/40 rounded-lg transition-colors"
                    title="Удалить материал"
                  >
                    <Trash2 className="w-3.5 h-3.5" />
                  </button>
                </div>
              </div>

              {/* Row 2: Editable URL */}
              <div className="pl-6">
                <input
                  type="url"
                  value={it.url}
                  onChange={(e) => handleUpdateItem(it.id, 'url', e.target.value)}
                  placeholder="https://..."
                  className="w-full bg-planka-bg/40 border border-planka-border/30 rounded-lg px-3 py-1 text-xs font-mono text-indigo-300 placeholder-slate-600 focus:outline-none focus:border-planka-accent focus:bg-planka-bg transition-colors"
                  title="URL адрес материала"
                />
              </div>
            </div>
          ))
        )}
      </div>

      {/* Bottom Save Trigger */}
      {items.length > 0 && (
        <div className="pt-2 flex justify-end">
          <button
            onClick={handleSave}
            disabled={isSaving}
            className={`flex items-center gap-2 px-5 py-2.5 rounded-lg text-xs font-bold transition-all shadow-md active:scale-95 ${
              isSaved
                ? 'bg-emerald-600 text-white shadow-emerald-950/40'
                : hasChanges
                ? 'bg-planka-accent hover:bg-planka-accentHover text-white shadow-indigo-950/50'
                : 'bg-planka-card hover:bg-planka-cardHover text-white border border-planka-border'
            }`}
          >
            {isSaved ? (
              <>
                <Check className="w-4 h-4 text-white" />
                <span>Ссылки сохранены!</span>
              </>
            ) : (
              <>
                <Save className="w-4 h-4" />
                <span>{isSaving ? 'Сохранение...' : 'Сохранить изменения ссылок'}</span>
              </>
            )}
          </button>
        </div>
      )}
    </div>
  );
};
