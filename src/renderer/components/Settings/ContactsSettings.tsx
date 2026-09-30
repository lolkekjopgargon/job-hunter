import React, { useState, useEffect } from 'react';
import { UserCheck, Save, Check, RotateCcw } from 'lucide-react';

interface ContactsSettingsProps {
  contacts: string;
  onSaveContacts: (contacts: string) => Promise<void>;
}

const DEFAULT_CONTACTS = `Павел Тэхэда Кардэнас
lol.kek.jopgargon@gmail.com
Telegram: @Pasha_tejeda`;

export const ContactsSettings: React.FC<ContactsSettingsProps> = ({
  contacts,
  onSaveContacts,
}) => {
  const [value, setValue] = useState(contacts || DEFAULT_CONTACTS);
  const [isSaved, setIsSaved] = useState(false);
  const [isSaving, setIsSaving] = useState(false);

  useEffect(() => {
    if (contacts) setValue(contacts);
  }, [contacts]);

  const handleSave = async () => {
    setIsSaving(true);
    await onSaveContacts(value);
    setIsSaving(false);
    setIsSaved(true);
    setTimeout(() => setIsSaved(false), 2000);
  };

  const handleReset = () => {
    setValue(DEFAULT_CONTACTS);
  };

  return (
    <div className="bg-planka-card/70 border border-planka-border/40 rounded-xl p-5 shadow-sm space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2.5">
          <div className="w-8 h-8 rounded-lg bg-emerald-500/20 text-emerald-400 flex items-center justify-center border border-emerald-500/30">
            <UserCheck className="w-4 h-4" />
          </div>
          <div>
            <h3 className="text-sm font-bold text-white">Контакты и подпись в конце письма</h3>
            <p className="text-xs text-planka-textMuted">
              Текст подписи, который автоматически подставляется в конец сгенерированного письма
            </p>
          </div>
        </div>

        <div className="flex items-center gap-2">
          <button
            onClick={handleReset}
            className="flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-xs font-medium bg-planka-bg/70 hover:bg-planka-bg text-planka-textMuted hover:text-white border border-planka-border/50 transition-colors"
            title="Восстановить стандартные контакты"
          >
            <RotateCcw className="w-3.5 h-3.5" />
            <span>По умолчанию</span>
          </button>

          <button
            onClick={handleSave}
            disabled={isSaving}
            className="flex items-center gap-1.5 px-3.5 py-1.5 rounded-lg text-xs font-semibold bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm shadow-emerald-900/40 active:scale-95 transition-all"
          >
            {isSaved ? (
              <>
                <Check className="w-3.5 h-3.5 text-emerald-200" />
                <span>Сохранено!</span>
              </>
            ) : (
              <>
                <Save className="w-3.5 h-3.5" />
                <span>{isSaving ? 'Сохранение...' : 'Сохранить контакты'}</span>
              </>
            )}
          </button>
        </div>
      </div>

      <div>
        <textarea
          value={value}
          onChange={(e) => setValue(e.target.value)}
          rows={4}
          className="w-full bg-planka-bg/80 border border-planka-border/60 rounded-xl p-3.5 text-xs text-slate-200 font-sans leading-relaxed resize-y focus:outline-none focus:border-emerald-500/80 transition-colors"
          placeholder="Введите контакты и подпись..."
        />
      </div>
    </div>
  );
};
