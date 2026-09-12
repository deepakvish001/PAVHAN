import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import useVoiceAssistant from '../hooks/useVoiceAssistant'
import { voiceLabels, voiceScripts } from '../api/client'

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
  const [labels, setLabels] = useState(null)
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

  // Hindi names for the data itself (craft types, categories, materials,
  // regions, colours). Without these a "Hindi" screen still reads
  // "Pottery & Ceramics · Varanasi", which is the half-translated feeling.
  useEffect(() => {
    let alive = true
    if (lang !== 'hi') { setLabels(null); return () => { alive = false } }
    voiceLabels('hi')
      .then((data) => { if (alive) setLabels(data.labels || null) })
      .catch(() => { if (alive) setLabels(null) })
    return () => { alive = false }
  }, [lang])

  /** Translate one value coming back from the API. Falls through unchanged
   *  when there is no Hindi name for it, so nothing ever renders blank. */
  const L = useCallback((value) => {
    if (!value || lang !== 'hi' || !labels) return value
    const key = String(value)
    for (const group of Object.values(labels)) {
      if (group[key]) return group[key]
    }
    return value
  }, [labels, lang])

  /** Speak something that must survive the next navigation and must not be
   *  talked over by the screen it lands on. */
  const protectedUntil = useRef(0)
  const sayProtected = useCallback((text) => {
    if (!voiceOn || !text) return
    // Hold the floor for roughly as long as the line takes to read, rather
    // than trusting `speaking` — some engines never fire onstart at all.
    const words = text.trim().split(/\s+/).length
    protectedUntil.current = Date.now() + Math.min(22000, Math.max(4000, words * 420))
    // ...and release it the moment the utterance genuinely ends, so whatever
    // is queued behind it does not wait out the estimate.
    assistant.speak(text, { onEnd: () => { protectedUntil.current = 0 } })
  }, [assistant, voiceOn])

  const cancelUnlessProtected = useCallback(() => {
    if (Date.now() < protectedUntil.current) return
    assistant.cancel()
  }, [assistant])

  const toast = useCallback((message, tone = 'ok', ms = 3600) => {
    const id = (toastId.current += 1)
    setToasts((list) => [...list, { id, message, tone }])
    setTimeout(() => setToasts((list) => list.filter((t) => t.id !== id)), ms)
  }, [])

  /** Speak one of the server-provided screen scripts.
   *
   * Screen scripts must never talk over a protected greeting — that was what
   * made the welcome sound like it was being cut off mid-sentence. If one is
   * still playing, the screen script waits its turn instead of interrupting.
   */
  const pending = useRef(null)
  const say = useCallback((screen, opts = {}) => {
    if (!voiceOn) return
    const text = opts.text || scripts?.screens?.[screen]
    if (!text) return
    const filled = Object.entries(opts.fields || {}).reduce(
      (acc, [k, v]) => acc.replaceAll(`{${k}}`, String(v)),
      text,
    )
    const once = opts.once === false ? null : `${screen}:${lang}`

    const speakNow = () => assistant.speak(filled, { once })

    if (Date.now() < protectedUntil.current) {
      // Wait for the greeting to finish, then say our piece. Bounded so a
      // stuck utterance can never leave the app silent forever.
      clearTimeout(pending.current)
      const deadline = Date.now() + 24000
      const waitTurn = () => {
        if (Date.now() > deadline) return
        if (Date.now() < protectedUntil.current) {
          pending.current = setTimeout(waitTurn, 350)
          return
        }
        speakNow()
      }
      pending.current = setTimeout(waitTurn, 400)
      return
    }
    speakNow()
  }, [assistant, scripts, voiceOn, lang])

  useEffect(() => () => clearTimeout(pending.current), [])

  /** Speak an arbitrary line right now — used for deliberate actions like
   *  "read this pitch to me", which should interrupt anything in progress. */
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
    labels, L,
    assistant,
    say, sayRaw, sayProtected, cancelUnlessProtected,
    toast, toasts,
    t: (hi, en) => (lang === 'hi' ? hi : en),
  }), [role, lang, voiceOn, user, scripts, labels, L, assistant, say, sayRaw,
       sayProtected, cancelUnlessProtected, toast, toasts])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>')
  return ctx
}
