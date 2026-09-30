import { BrowserWindow, session } from 'electron';

export function openHeadHunterAuthWindow(onSuccess: (tokens: { hhtoken: string; xsrf: string; cookieStr?: string }) => void) {
  const customUa = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0.0.0 Safari/537.36';

  const authSession = session.fromPartition('persist:hh_auth_session');
  authSession.setUserAgent(customUa);

  const authWindow = new BrowserWindow({
    width: 640,
    height: 800,
    title: 'Авторизация в HeadHunter',
    autoHideMenuBar: true,
    backgroundColor: '#ffffff',
    webPreferences: {
      session: authSession,
      nodeIntegration: false,
      contextIsolation: true,
    },
  });

  authWindow.loadURL('https://hh.ru/account/login', {
    userAgent: customUa,
    extraHeaders: 'Accept-Language: ru-RU,ru;q=0.9,en-US;q=0.8,en;q=0.7\n',
  });

  const checkCookies = async () => {
    try {
      const cookies = await authSession.cookies.get({ domain: '.hh.ru' });
      const hhtokenCookie = cookies.find((c) => c.name === 'hhtoken');
      const xsrfCookie = cookies.find((c) => c.name === '_xsrf');

      if (hhtokenCookie && xsrfCookie && hhtokenCookie.value && xsrfCookie.value) {
        const fullCookieStr = cookies.map(c => `${c.name}=${c.value}`).join('; ');
        onSuccess({
          hhtoken: hhtokenCookie.value,
          xsrf: xsrfCookie.value,
          cookieStr: fullCookieStr,
        });
        if (!authWindow.isDestroyed()) {
          authWindow.close();
        }
      }
    } catch (e) {
      console.error('Error checking cookies:', e);
    }
  };

  // passedLoginPage — guard against stale session cookies auto-closing the window.
  // Only start checking for auth cookies once the user has actually submitted the login form
  // and hh.ru has navigated away from the login page.
  let passedLoginPage = false;

  authWindow.webContents.on('did-navigate', (_event, url) => {
    if (!url.includes('/account/login') && url !== 'about:blank') {
      passedLoginPage = true;
      checkCookies();
    }
  });

  // Interval for SMS/2FA flows where the URL stays the same but cookies get set
  const intervalId = setInterval(() => {
    if (authWindow.isDestroyed()) {
      clearInterval(intervalId);
      return;
    }
    if (passedLoginPage) {
      checkCookies();
    }
  }, 3000);

  authWindow.on('closed', () => {
    clearInterval(intervalId);
  });
}
