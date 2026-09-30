import { Tray, Menu, nativeImage, app, BrowserWindow } from 'electron';
import path from 'path';
import fs from 'fs';

export function createTray(mainWindow: BrowserWindow, onScanNow: () => void): Tray | null {
  try {
    // Try to load from assets folder (packed or dev)
    const iconPaths = [
      path.join(process.resourcesPath, 'assets/icon.png'),
      path.join(process.resourcesPath, 'app.asar.unpacked/assets/icon.png'),
      path.join(app.getAppPath(), 'assets/icon.png'),
    ];

    let icon = nativeImage.createEmpty();
    for (const p of iconPaths) {
      if (fs.existsSync(p)) {
        icon = nativeImage.createFromPath(p).resize({ width: 16, height: 16 });
        break;
      }
    }

    if (icon.isEmpty()) {
      // Tiny fallback placeholder (red 16x16)
      const b64 = 'data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAABAAAAAQCAYAAAAf8/9hAAAABmJLR0QA/wD/AP+gvaeTAAAAMElEQVQ4y2NgGAWjgP7//48hjKHQAAAAASUVORK5CYII=';
      icon = nativeImage.createFromDataURL(b64);
    }

    const tray = new Tray(icon);
    tray.setToolTip('Job Hunter - Автономный поиск работы');

    const contextMenu = Menu.buildFromTemplate([
      {
        label: 'Открыть главное окно',
        click: () => {
          mainWindow.show();
          mainWindow.focus();
        },
      },
      {
        label: 'Запустить поиск вакансий сейчас',
        click: () => onScanNow(),
      },
      { type: 'separator' },
      {
        label: 'Выход',
        click: () => {
          (app as any).isQuitting = true;
          app.quit();
        },
      },
    ]);

    tray.setContextMenu(contextMenu);

    tray.on('double-click', () => {
      if (mainWindow.isVisible()) {
        mainWindow.hide();
      } else {
        mainWindow.show();
        mainWindow.focus();
      }
    });

    return tray;
  } catch (err) {
    console.warn('Tray creation skipped:', err);
    return null;
  }
}
