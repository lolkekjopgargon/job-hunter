import { Notification } from 'electron';

export interface SchedulerCallbacks {
  runDailyScan: () => Promise<any>;
  runNegotiationsCheck: () => Promise<any>;
}

export class AppScheduler {
  private scanTimer: NodeJS.Timeout | null = null;
  private negotiationsTimer: NodeJS.Timeout | null = null;
  private callbacks: SchedulerCallbacks;

  constructor(callbacks: SchedulerCallbacks) {
    this.callbacks = callbacks;
  }

  start() {
    this.scheduleNextDailyScan();
    this.startNegotiationsPolling();
  }

  stop() {
    if (this.scanTimer) clearTimeout(this.scanTimer);
    if (this.negotiationsTimer) clearInterval(this.negotiationsTimer);
  }

  private scheduleNextDailyScan() {
    const now = new Date();
    const nextScan = new Date();
    nextScan.setHours(11, 0, 0, 0);

    // If 11:00 has already passed today, schedule for tomorrow 11:00
    if (now.getTime() >= nextScan.getTime()) {
      nextScan.setDate(nextScan.getDate() + 1);
    }

    const msUntilScan = nextScan.getTime() - now.getTime();
    console.log(`[Scheduler] Следующий скан запланирован на: ${nextScan.toLocaleString()} (через ${Math.round(msUntilScan / 1000 / 60)} мин)`);

    this.scanTimer = setTimeout(async () => {
      try {
        console.log('[Scheduler] Запуск ежедневного авто-сбора в 11:00...');
        const res = await this.callbacks.runDailyScan();
        if (Notification.isSupported()) {
          new Notification({
            title: 'Job Hunter: Сбор завершен',
            body: `Найдено ${res.found || 0} вакансий. Добавлено в Бэклог: ${res.added || 0}`,
          }).show();
        }
      } catch (e) {
        console.error('[Scheduler] Ошибка авто-сканирования:', e);
      } finally {
        this.scheduleNextDailyScan();
      }
    }, msUntilScan);
  }

  private startNegotiationsPolling(intervalMinutes: number = 30) {
    // Run initial check after 10 seconds
    setTimeout(async () => {
      await this.checkNegotiationsOnce();
    }, 10000);

    // Regular interval
    this.negotiationsTimer = setInterval(async () => {
      await this.checkNegotiationsOnce();
    }, intervalMinutes * 60 * 1000);
  }

  private async checkNegotiationsOnce() {
    try {
      const res = await this.callbacks.runNegotiationsCheck();
      const updates = res.updated || [];
      for (const u of updates) {
        if (Notification.isSupported()) {
          const isInterview = u.new_status.includes('Приглашение');
          new Notification({
            title: isInterview ? '🎉 Приглашение на интервью!' : 'Статус вакансии изменен',
            body: `${u.employer} — ${u.title}: ${u.new_status}`,
          }).show();
        }
      }
    } catch (e) {
      console.error('[Scheduler] Ошибка проверки переговоров:', e);
    }
  }
}
