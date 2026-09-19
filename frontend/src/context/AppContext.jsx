import { createContext, useCallback, useContext, useEffect, useMemo, useRef, useState } from 'react'
import useVoiceAssistant from '../hooks/useVoiceAssistant'
import usePwa from '../hooks/usePwa'
import { useOutboxCount } from '../hooks/useOutboxCount'
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
  const [theme, setTheme] = useState(saved?.theme || 'light')
  const [fontScale, setFontScale] = useState(saved?.fontScale || 1)
  const [contrast, setContrast] = useState(saved?.contrast || 'normal')
  // The voice the listener picked on this device. Accent is a matter of taste
  // and of which engine happens to be installed, so the scoring table yields
  // to an explicit choice.
  const [voiceName, setVoiceName] = useState(saved?.voiceName || '')
  const [token, setToken] = useState(saved?.token || null)
  const [lang, setLang] = useState(saved?.lang || 'hi')
  const [voiceOn, setVoiceOn] = useState(saved?.voiceOn ?? true)
  const [user, setUser] = useState(saved?.user || null)
  const [scripts, setScripts] = useState(null)
  const [labels, setLabels] = useState(null)
  const [toasts, setToasts] = useState([])
  const toastId = useRef(0)

  const assistant = useVoiceAssistant({ lang, enabled: voiceOn, voiceName })
  const pwa = usePwa()
  // Mounting this here is what starts the outbox watching for the connection
  // to return, app-wide — a listing recorded in a field with no signal sends
  // itself the moment the phone finds a tower.
  const outboxCount = useOutboxCount()

  useEffect(() => {
    try {
      localStorage.setItem(STORE_KEY, JSON.stringify({ role, lang, voiceOn, user, theme, token, fontScale, contrast, voiceName}))
    } catch { /* private mode; the app still works, it just forgets */ }
  }, [role, lang, voiceOn, user, theme, token, fontScale, contrast, voiceName])

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

  /**
   * Product text in the reader's own language.
   *
   * Every listing carries both halves — `title` and `title_hi`, `story` and
   * `story_hi` — and for a long time the app generated the Hindi, stored it,
   * and then showed the English to everybody. An artisan who set the
   * interface to Hindi still browsed a catalogue written in the one language
   * this project exists to spare them.
   *
   * The fallback is deliberate and one-way: an empty Hindi field shows the
   * English rather than nothing, because a blank title is worse than a
   * foreign one, and listings imported or created before the Hindi generator
   * existed still have to render.
   */
  const P = useCallback((product, field) => {
    if (!product) return ''
    const english = product[field] || ''
    if (lang !== 'hi') return english
    return product[`${field}_hi`] || english
  }, [lang])

  /** Speak something that must survive the next navigation and must not be
   *  talked over by the screen it lands on. */
  const protectedUntil = useRef(0)
  const sayProtected = useCallback((text, { onDone } = {}) => {
    if (!voiceOn || !text) {
      onDone?.()                       // muted: do not strand the caller
      return () => {}
    }
    // Hold the floor for roughly as long as the line takes to read, rather
    // than trusting `speaking` — some engines never fire onstart at all.
    const words = text.trim().split(/\s+/).length
    const estimate = Math.min(22000, Math.max(4000, words * 420))
    protectedUntil.current = Date.now() + estimate

    let finished = false
    const finish = () => {
      if (finished) return
      finished = true
      protectedUntil.current = 0
      onDone?.()
    }
    // ...and release it the moment the utterance genuinely ends, so whatever
    // is queued behind it does not wait out the estimate. The timer is the
    // backstop for engines that never fire onend at all.
    const backstop = setTimeout(finish, estimate + 800)
    assistant.speak(text, { onEnd: () => { clearTimeout(backstop); finish() } })
    return () => { clearTimeout(backstop); finish() }   // caller can skip ahead
  }, [assistant, voiceOn])

  const cancelUnlessProtected = useCallback(() => {
    if (Date.now() < protectedUntil.current) return
    assistant.cancel()
  }, [assistant])

  // The theme lives on <html> so CSS variables cascade over everything,
  // including portals and the scrollbar.
  useEffect(() => {
    // Both live on <html> so every CSS variable cascades, including into the
    // scrollbar and any portal.
    document.documentElement.style.setProperty('--font-scale', String(fontScale))
    document.documentElement.setAttribute('data-contrast', contrast)
  }, [fontScale, contrast])

  useEffect(() => {
    document.documentElement.setAttribute('data-theme', theme)
    const meta = document.querySelector('meta[name="theme-color"]')
    if (meta) meta.setAttribute('content', theme === 'dark' ? '#0b0a0d' : '#161B33')
  }, [theme])

  // Pinned at runtime so a tab that previously held another app cannot keep
  // showing its title.
  useEffect(() => { document.title = 'PAVHAN — AI-Powered Growth for Artisan Craft' }, [])

  const toggleTheme = useCallback(() => {
    setTheme((current) => (current === 'dark' ? 'light' : 'dark'))
  }, [])

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
    theme, setTheme, toggleTheme,
    fontScale, setFontScale, contrast, setContrast,
    token, setToken,
    voiceOn, setVoiceOn,
    user, setUser,
    scripts,
    labels, L,
    pwa, outboxCount, P, voiceName, setVoiceName,
    assistant,
    say, sayRaw, sayProtected, cancelUnlessProtected,
    toast, toasts,
    t: (hi, en) => (lang === 'hi' ? hi : en),
  }), [role, lang, voiceOn, user, theme, token, toggleTheme, fontScale, contrast,
       scripts, labels, L, P, pwa, outboxCount, voiceName, assistant, say, sayRaw, sayProtected,
       cancelUnlessProtected, toast, toasts])

  return <AppContext.Provider value={value}>{children}</AppContext.Provider>
}

export function useApp() {
  const ctx = useContext(AppContext)
  if (!ctx) throw new Error('useApp must be used inside <AppProvider>')
  return ctx
}
