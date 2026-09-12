import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import useVoiceAssistant from '../hooks/useVoiceAssistant'
import { voiceScripts } from '../api/client'

const AppContext = createContext(null)
const STORE_KEY = 'pavhan.session.v1'

function loadSession() {
  try {
    const raw = localStorage.getItem(STORE_KEY)
    return raw ? JSON.parse(raw) : null
  } catch { return null }
}

export function AppProvider({ children }) {
  const saved = loadSession()
  const [role, setRole] = useState(saved?.role || null)
  const [lang, setLang] = useState(saved?.lang || 'hi')
  const [voiceOn, setVoiceOn] = useState(saved?.voiceOn ?? true)
  const [user, setUser] = useState(saved?.user || null)
  const [scripts, setScripts] = useState(null)
  const [toasts, setToasts] = useState([])
  const toastId = useRef(0)

  const assistant = useVoiceAssistant({ lang, enabled: voiceOn })

  useEffect(() => {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ role, lang, voiceOn, user }))
    } catch { /* private mode; the app still works, it just forgets */ }
  }, [role, lang, voiceOn, user])

  // Pull every script up front so the guide can speak with no round trip.
  useEffect(() => {
    let alive = true
    voiceScripts(lang)
      .then((data) => { if (alive) setScripts(data) })
      .catch(() => { if (alive) setScripts(null) })
    return () => { alive = false }
  }, [lang])

  const toast = useCallback((message, tone = 'ok', ms = 3600) => {
    const id = (toastId.current += 1)
    setToasts((list) => [...list, { id, message, tone }])
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), ms)
  }, [])

  /** Speak one of the server-provided screen scripts. */
  const say = useCallback((screen, opts = {}) => {
    if (!voiceOn) return
    const text = opts.text || scripts?.screens?.[screen]
    if (!text) return
    const filled = Object.entries(opts.fields || {}).reduce(
      (acc, [k, v]) => acc.replaceAll(`{${k}}`, String(v)),
      text,
    )
    assistant.speak(filled, { once: opts.once === false ? null : `${screen}:${lang}` })
  }, [assistant, scripts, voiceOn, lang])

  const sayRaw = useCallback((text, opts) => {
    if (!voiceOn || !text) return
    assistant.speak(text, opts)
  }, [assistant, voiceOn])

  const value = useMemo(() => ({
    role, setRole,
    lang, setLang,
    voiceOn, setVoiceOn,
    user, setUser,
    scripts,
    assistant,
    say, sayRaw,
    toast, toasts,
    t: (hi, en) => (lang === 'hi' ? hi : en),
  }), [role, lang, voiceOn, user, scripts, assistant, say, sayRaw, toast, toasts])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>')
  return ctx
}
