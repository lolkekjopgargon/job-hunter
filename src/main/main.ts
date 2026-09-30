import { app, BrowserWindow, ipcMain } from 'electron';
import path from 'path';
import fs from 'fs';
import { spawn } from 'child_process';
import { openHeadHunterAuthWindow } from './hh_auth_window';
import { AppScheduler } from './scheduler';
import { createTray } from './tray';

let mainWindow: BrowserWindow | null = null;
let scheduler: AppScheduler | null = null;
let appTray: any = null;

function getEngineCliPath(): string {
  const unpackedPath = path.join(process.resourcesPath, 'app.asar.unpacked/src/engine/cli.py');
  if (fs.existsSync(unpackedPath)) {
    return unpackedPath;
  }
  const devPath = path.join(__dirname, '../../src/engine/cli.py');
  if (fs.existsSync(devPath)) {
    return devPath;
  }
  const distPath = path.join(__dirname, '../engine/cli.py');
  if (fs.existsSync(distPath)) {
    return distPath;
  }
  const packagedPath = path.join(process.resourcesPath, 'src/engine/cli.py');
  if (fs.existsSync(packagedPath)) {
    return packagedPath;
  }
  return devPath;
}

function callPythonEngine(actionPayload: Record<string, any>): Promise<any> {
  return new Promise((resolve, reject) => {
    const cliPath = getEngineCliPath();
    // Store DB in userData (AppData) — persists across app rebuilds and updates.
    // build/win-unpacked/ is recreated by npm run pack and would delete the DB.
    const dbPath = path.join(app.getPath('userData'), 'job_hunter.db');
    const cleanEnv: Record<string, string> = {
      ...(process.env as Record<string, string>),
      PYTHONIOENCODING: 'utf-8',
      PYTHONUTF8: '1',           // Force Python UTF-8 mode for all I/O
      JOB_HUNTER_DB: dbPath,
    };
    delete cleanEnv.PYTHONHOME;
    delete cleanEnv.PYTHONPATH;

    // Pass payload via stdin to avoid Windows ENAMETOOLONG for large strings (e.g. system prompts)
    const pyProcess = spawn('python', ['-E', cliPath], {
      env: cleanEnv,
      cwd: app.isPackaged ? path.dirname(app.getPath('exe')) : app.getAppPath(),
    });
    pyProcess.stdin.write(JSON.stringify(actionPayload) + '\n');
    pyProcess.stdin.end();

    let stdoutData = '';
    let stderrData = '';

    pyProcess.stdout.on('data', (chunk) => {
      const text = chunk.toString('utf-8');
      stdoutData += text;
      const lines = text.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed && !trimmed.startsWith('{"success":') && !trimmed.startsWith('{"authenticated":')) {
          mainWindow?.webContents.send('engine-log', {
            id: Math.random().toString(36).substring(2, 9),
            timestamp: new Date().toLocaleTimeString('ru-RU'),
            level: trimmed.includes('⚠️') || trimmed.includes('✗') ? 'error' : (trimmed.includes('✓') || trimmed.includes('🎯') ? 'success' : (trimmed.includes('🔍') || trimmed.includes('✨') ? 'hh' : 'info')),
            message: trimmed,
          });
        }
      }
    });

    pyProcess.stderr.on('data', (chunk) => {
      const text = chunk.toString('utf-8');
      stderrData += text;
      const lines = text.split('\n');
      for (const line of lines) {
        const trimmed = line.trim();
        if (trimmed) {
          const isErr = trimmed.includes('⚠️') || trimmed.includes('✗') || trimmed.toLowerCase().includes('traceback') || trimmed.toLowerCase().includes('error:');
          const isSucc = trimmed.includes('✓') || trimmed.includes('🎯');
          const isHh = trimmed.includes('🔍') || trimmed.includes('✨') || trimmed.includes('[HH]');
          mainWindow?.webContents.send('engine-log', {
            id: Math.random().toString(36).substring(2, 9),
            timestamp: new Date().toLocaleTimeString('ru-RU'),
            level: isErr ? 'error' : (isSucc ? 'success' : (isHh ? 'hh' : 'info')),
            message: trimmed,
          });
        }
      }
    });

    pyProcess.on('close', (code) => {
      if (code !== 0 && !stdoutData.includes('{"success":')) {
        console.error('Python error:', stderrData);
        return reject(new Error(stderrData || `Python process exited with code ${code}`));
      }
      try {
        const lines = stdoutData.trim().split('\n');
        let parsed: any = null;
        for (let i = lines.length - 1; i >= 0; i--) {
          const l = lines[i].trim();
          if (l.startsWith('{') && l.endsWith('}')) {
            try {
              parsed = JSON.parse(l);
              break;
            } catch (_) {}
          }
        }
        if (!parsed) {
          parsed = JSON.parse(stdoutData.trim());
        }
        resolve(parsed);
      } catch (err) {
        console.error('JSON parse error:', stdoutData);
        reject(new Error(`Failed to parse Python response: ${stdoutData}`));
      }
    });

    pyProcess.on('error', (err) => {
      reject(err);
    });
  });
}

function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1360,
    height: 860,
    minWidth: 1024,
    minHeight: 700,
    title: 'Job Hunter',
    backgroundColor: '#1e2023',
    autoHideMenuBar: true,
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Load Vite dev server if explicitly provided, else load production index.html
  const devUrl = process.env.VITE_DEV_SERVER_URL;
  if (devUrl) {
    mainWindow.loadURL(devUrl);
  } else {
    mainWindow.loadFile(path.join(__dirname, '../renderer/index.html'));
  }

  mainWindow.once('ready-to-show', () => {
    mainWindow?.show();
    mainWindow?.focus();
  });

  mainWindow.on('close', (event) => {
    // Minimize to tray on close only if tray exists, otherwise close app
    if (!(app as any).isQuitting && appTray) {
      event.preventDefault();
      mainWindow?.hide();
    }
  });
}

// IPC Handlers
function setupIpcHandlers() {
  ipcMain.handle('get-vacancies', async (_event, listName) => {
    return callPythonEngine({ action: 'get_vacancies', list_name: listName });
  });

  ipcMain.handle('move-vacancy', async (_event, vacancyId, newList) => {
    return callPythonEngine({ action: 'move_vacancy', vacancy_id: vacancyId, new_list: newList });
  });

  ipcMain.handle('update-customization', async (_event, vacancyId, resumeId, materials, coverLetter) => {
    return callPythonEngine({
      action: 'update_customization',
      vacancy_id: vacancyId,
      resume_id: resumeId,
      materials,
      cover_letter: coverLetter,
    });
  });

  ipcMain.handle('apply-vacancy', async (_event, vacancyId) => {
    return callPythonEngine({ action: 'apply', vacancy_id: vacancyId });
  });

  ipcMain.handle('run-scan', async () => {
    return callPythonEngine({ action: 'scan' });
  });

  ipcMain.handle('check-negotiations', async () => {
    return callPythonEngine({ action: 'check_negotiations' });
  });

  ipcMain.handle('clear-archive', async () => {
    return callPythonEngine({ action: 'clear_archive' });
  });

  ipcMain.handle('get-settings', async () => {
    return callPythonEngine({ action: 'get_settings' });
  });

  ipcMain.handle('set-setting', async (_event, key, value) => {
    return callPythonEngine({ action: 'set_setting', key, value });
  });

  let lastAuthCheck = 0;
  let cachedAuthResult: any = null;

  ipcMain.handle('check-hh-auth', async (_event, force = false) => {
    const now = Date.now();
    if (!force && cachedAuthResult && (now - lastAuthCheck < 180000)) {
      return cachedAuthResult;
    }
    try {
      const res = await callPythonEngine({ action: 'check_hh_auth' });
      if (res && res.authenticated) {
        cachedAuthResult = res;
        lastAuthCheck = now;
      }
      return res;
    } catch (e: any) {
      if (cachedAuthResult) return cachedAuthResult;
      return { authenticated: false, error: e.message || 'Ошибка проверки авторизации' };
    }
  });

  ipcMain.handle('get-knowledge', async (_event, name) => {
    return callPythonEngine({ action: 'get_knowledge', name });
  });

  ipcMain.handle('save-knowledge', async (_event, name, content) => {
    return callPythonEngine({ action: 'save_knowledge', name, content });
  });

  ipcMain.handle('migrate-planka', async () => {
    return callPythonEngine({ action: 'migrate_planka' });
  });

  ipcMain.handle('generate-letter', async (_event, vacancyId, regenerate = false) => {
    return callPythonEngine({ action: 'generate_letter', vacancy_id: vacancyId, regenerate });
  });

  ipcMain.handle('apply-approved', async () => {
    return callPythonEngine({ action: 'apply_approved' });
  });

  ipcMain.handle('refetch-vacancy', async (_event, vacancyId) => {
    return callPythonEngine({ action: 'refetch_vacancy', vacancy_id: vacancyId });
  });

  ipcMain.handle('start-hh-auth', async () => {
    return new Promise((resolve) => {
      openHeadHunterAuthWindow(async ({ hhtoken, xsrf, cookieStr }: any) => {
        await callPythonEngine({ action: 'set_setting', key: 'hh_token', value: hhtoken });
        await callPythonEngine({ action: 'set_setting', key: 'hh_xsrf', value: xsrf });
        if (cookieStr) {
          await callPythonEngine({ action: 'set_setting', key: 'hh_cookie_str', value: cookieStr });
        }
        const checkRes = await callPythonEngine({ action: 'check_hh_auth', force: true });
        // Auto-fetch resumes after successful login
        try {
          await callPythonEngine({ action: 'fetch_hh_resumes' });
        } catch (_) { /* non-critical */ }
        resolve(checkRes);
      });
    });
  });

  ipcMain.handle('fetch-hh-resumes', async () => {
    return callPythonEngine({ action: 'fetch_hh_resumes' });
  });
}

app.whenReady().then(async () => {
  setupIpcHandlers();
  createWindow();

  // Initialize SQLite database
  try {
    await callPythonEngine({ action: 'init' });
  } catch (err) {
    console.error('Failed to initialize database:', err);
  }

  if (mainWindow) {
    appTray = createTray(mainWindow, () => {
      callPythonEngine({ action: 'scan' });
    });
  }

  // Start background scheduler
  scheduler = new AppScheduler({
    runDailyScan: () => callPythonEngine({ action: 'scan' }),
    runNegotiationsCheck: () => callPythonEngine({ action: 'check_negotiations' }),
  });
  scheduler.start();

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('before-quit', () => {
  (app as any).isQuitting = true;
  if (scheduler) scheduler.stop();
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    // Keep app running in tray unless explicit quit
  }
});
