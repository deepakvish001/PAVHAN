import { useCallback, useEffect, useState } from 'react'

/**
 * Install and connectivity state.
 *
 * Two things matter to an artisan on a cheap phone and a patchy line: that
 * the app can live on the home screen like any other app, and that it says
 * plainly when it is working from saved data rather than pretending
 * everything is fine.
 */
export default function usePwa() {
  const [installEvent, setInstallEvent] = useState(null)
  const [installed, setInstalled] = useState(false)
  const [online, setOnline] = useState(
    typeof navigator === 'undefined' ? true : navigator.onLine,
  )
  const [updateReady, setUpdateReady] = useState(false)

  useEffect(() => {
    if (!('serviceWorker' in navigator)) return undefined
    // Registered after load so it never competes with the first paint.
    const register = () => {
      navigator.serviceWorker.register('/sw.js').then((reg) => {
        reg.addEventListener('updatefound', () => {
          const next = reg.installing
          next?.addEventListener('statechange', () => {
            if (next.state === 'installed' && navigator.serviceWorker.controller) {
              setUpdateReady(true)
            }
          })
        })
      }).catch(() => { /* http:// on a LAN address; the app still works */ })
    }
    if (document.readyState === 'complete') register()
    else window.addEventListener('load', register)
    return () => window.removeEventListener('load', register)
  }, [])

  useEffect(() => {
    const standalone = window.matchMedia?.('(display-mode: standalone)').matches
      || window.navigator.standalone === true
    setInstalled(!!standalone)

    const onPrompt = (e) => { e.preventDefault(); setInstallEvent(e) }
    const onInstalled = () => { setInstalled(true); setInstallEvent(null) }
    const goOnline = () => setOnline(true)
    const goOffline = () => setOnline(false)

    window.addEventListener('beforeinstallprompt', onPrompt)
    window.addEventListener('appinstalled', onInstalled)
    window.addEventListener('online', goOnline)
    window.addEventListener('offline', goOffline)
    return () => {
      window.removeEventListener('beforeinstallprompt', onPrompt)
      window.removeEventListener('appinstalled', onInstalled)
      window.removeEventListener('online', goOnline)
      window.removeEventListener('offline', goOffline)
    }
  }, [])

  const install = useCallback(async () => {
    if (!installEvent) return false
    installEvent.prompt()
    const { outcome } = await installEvent.userChoice
    if (outcome === 'accepted') setInstalled(true)
    setInstallEvent(null)
    return outcome === 'accepted'
  }, [installEvent])

  const applyUpdate = useCallback(() => window.location.reload(), [])

  return {
    canInstall: !!installEvent && !installed,
    installed,
    install,
    online,
    updateReady,
    applyUpdate,
  }
}
