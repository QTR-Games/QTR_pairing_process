import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import './index.css'
import App from './App.tsx'

/*
 * Take a new build on the first open, not the second.
 *
 * Left to itself the service worker updates in the background, but the page that
 * triggered the update has already been served from the old cache -- so a push
 * only appears on the *next* launch. Measured: fifteen seconds still showing the
 * old build, then correct after a second reload. If a fix goes out on event
 * morning and the app is opened once in the car, that is the launch that
 * matters, and it is the one that misses it.
 *
 * `controllerchange` fires when a newly activated worker claims this page, which
 * under `registerType: 'autoUpdate'` is the moment the new build is ready to be
 * served. Reloading then picks it up immediately.
 *
 * The `hadController` guard matters: on a first-ever visit the worker also
 * claims the page, but that page is already running the newest code, and
 * reloading there would be a pointless flash on the very first launch.
 *
 * Reloading at all is only safe because the round in progress is persisted (see
 * `saveLive` in model/board.ts). Without that, this would trade a stale build
 * for a lost round, which is the worse of the two.
 */
if ('serviceWorker' in navigator) {
  const hadController = !!navigator.serviceWorker.controller
  let reloading = false
  navigator.serviceWorker.addEventListener('controllerchange', () => {
    if (!hadController || reloading) return
    reloading = true
    window.location.reload()
  })
}

/*
 * Bring the store up before the UI.
 *
 * On the desktop build the model must persist to SQLite, not localStorage, and
 * that store hydrates from disk asynchronously. So the very first render waits
 * for the desktop store to be installed on the seam -- otherwise the first board
 * read would race the hydrate and briefly see an empty app. On the web
 * `isDesktop()` is false and this is a straight-through render with no delay. If
 * the desktop store fails to open we log and fall through to the default
 * localStorage backend, so a database problem never stops the app from opening.
 */
async function boot() {
  const {
    isDesktop,
    initDesktopStore,
    initDesktopAffordances,
    initDesktopUpdates,
  } = await import('./desktop/bootstrap')
  const desktop = isDesktop()
  if (desktop) {
    try {
      await initDesktopStore()
    } catch (err) {
      console.error('desktop SQLite store unavailable, using localStorage', err)
    }
    try {
      await initDesktopAffordances()
    } catch (err) {
      console.error('desktop menu and dialogs unavailable', err)
    }
  }

  createRoot(document.getElementById('root')!).render(
    <StrictMode>
      <App />
    </StrictMode>,
  )

  // After the first paint, not before it: an update check must never delay the
  // app opening. Fire-and-forget -- initDesktopUpdates swallows its own errors.
  if (desktop) {
    void initDesktopUpdates()
  }
}

void boot()
