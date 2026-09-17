import { useCallback, useEffect, useRef, useState } from 'react'
import { hasDevanagari, hasIndicVoice, toLatin } from '../lib/devanagari'

/**
 * The PAVHAN voice guide.
 *
 * Speech synthesis has three traps that make assistants feel broken:
 *   - voices load asynchronously, so the first utterance often speaks Hindi
 *     text in an English voice;
 *   - browsers block speech until the user has interacted with the page, and
 *     the rejection is silent;
 *   - **most machines have no Hindi voice at all.** Android usually ships
 *     one; Windows does not unless somebody installed the Hindi language
 *     pack, and a demo laptop or a cloud VM almost never has. On those
 *     machines `getVoices()` returns English only, the app hands an English
 *     voice a string of Devanagari, and nothing comes out — while the English
 *     assistant on the same page works perfectly. That asymmetry is not a
 *     Hindi bug in the app; it is a missing voice in the operating system,
 *     and it is the single most common reason "the Hindi voice is not
 *     working".
 *
 * All three are handled here. For the third, when no Indic voice exists the
 * Hindi is transliterated to Roman and read by the best Indian-English voice
 * available: "yeh madhubani mein haath se banee hai" is understood instantly
 * by the person this app is for, and silence is not. A real Hindi voice is
 * always preferred when the device has one.
 */

const HINDI_VOICE_HINTS = ['hi-IN', 'hi_IN', 'hindi']
const ENGLISH_VOICE_HINTS = ['en-IN', 'en_IN', 'en-GB', 'en-US']

function pickVoice(voices, lang) {
  if (!voices.length) return null
  const hints = lang === 'hi' ? HINDI_VOICE_HINTS : ENGLISH_VOICE_HINTS
  for (const hint of hints) {
    const match = voices.find(
      (v) => v.lang?.toLowerCase().includes(hint.toLowerCase())
        || v.name?.toLowerCase().includes(hint.toLowerCase()),
    )
    if (match) return match
  }
  // An Indian-English voice reads Hinglish far better than a US one.
  return voices.find((v) => v.lang?.startsWith('en-IN'))
      || voices.find((v) => v.lang?.startsWith('en'))
      || voices[0]
}

export default function useVoiceAssistant({ lang = 'hi', enabled = true } = {}) {
  const [speaking, setSpeaking] = useState(false)
  const [ready, setReady] = useState(false)
  const [supported] = useState(() => typeof window !== 'undefined' && 'speechSynthesis' in window)
  const voicesRef = useRef([])
  const queueRef = useRef(null)
  const unlockedRef = useRef(false)
  const spokenRef = useRef(new Set())

  useEffect(() => {
    if (!supported) return undefined
    const load = () => {
      voicesRef.current = window.speechSynthesis.getVoices() || []
      if (voicesRef.current.length) setReady(true)
    }
    load()
    window.speechSynthesis.addEventListener?.('voiceschanged', load)
    const timer = setTimeout(load, 600)
    return () => {
      window.speechSynthesis.removeEventListener?.('voiceschanged', load)
      clearTimeout(timer)
    }
  }, [supported])

  const cancel = useCallback(() => {
    if (!supported) return
    try { window.speechSynthesis.cancel() } catch { /* nothing playing */ }
    setSpeaking(false)
  }, [supported])

  const speak = useCallback((text, opts = {}) => {
    if (!supported || !enabled || !text) return
    const { interrupt = true, rate, once, onEnd } = opts

    if (once) {
      if (spokenRef.current.has(once)) return
      spokenRef.current.add(once)
    }

    // Before the first user gesture the browser will refuse to speak, so hold
    // the line and say it as soon as they touch something.
    if (!unlockedRef.current) { queueRef.current = { text, opts: { ...opts, once: null } }; return }

    if (interrupt) { try { window.speechSynthesis.cancel() } catch {} }

    const target = opts.lang || lang
    const voices = voicesRef.current
    let spokenText = text

    // Hindi text, and nothing on this device can read the script. Rather than
    // playing silence, hand an English voice something it can pronounce.
    if (target === 'hi' && hasDevanagari(text) && !hasIndicVoice(voices)) {
      spokenText = toLatin(text)
    }

    const utter = new SpeechSynthesisUtterance(spokenText)
    const voice = pickVoice(voices, target)
    // Wrapped, because assigning a voice can throw: the list is refreshed on
    // `voiceschanged` and a handle taken before that event can be rejected as
    // stale. An exception here would silence the assistant for the rest of
    // the session, and the utterance still speaks in the default voice with
    // `lang` alone set.
    if (voice) { try { utter.voice = voice } catch { /* stale handle */ } }
    // When the text was transliterated the voice is an English one, and
    // telling it the language is Hindi makes it try — and fail — to apply
    // Hindi phonology to Roman letters. Let it read the Roman as Indian
    // English, which is exactly what we want it to sound like.
    const transliterated = spokenText !== text
    utter.lang = transliterated ? (voice?.lang || 'en-IN')
      : (voice?.lang || (target === 'hi' ? 'hi-IN' : 'en-IN'))
    // Slightly slow: these are instructions, and many users are hearing a
    // screen read to them for the first time.
    utter.rate = rate ?? (target === 'hi' ? 0.92 : 0.98)
    utter.pitch = 1
    utter.volume = 1
    utter.onstart = () => setSpeaking(true)
    utter.onend = () => { setSpeaking(false); onEnd?.() }
    utter.onerror = () => { setSpeaking(false); onEnd?.() }
    try { window.speechSynthesis.speak(utter) } catch { setSpeaking(false); onEnd?.() }
  }, [supported, enabled, lang])

  /** What this device can actually do with Hindi, in plain terms. */
  const hindiVoice = useCallback(() => {
    const voices = voicesRef.current
    const indic = voices.find((v) => {
      const tag = `${v.lang || ''} ${v.name || ''}`.toLowerCase()
      return /\bhi[-_]/.test(tag) || tag.includes('hindi')
    })
    if (indic) return { mode: 'native', voice: indic.name, lang: indic.lang }
    if (hasIndicVoice(voices)) {
      const other = voices.find((v) => hasIndicVoice([v]))
      return { mode: 'indic', voice: other?.name || '', lang: other?.lang || '' }
    }
    const english = voices.find((v) => v.lang?.startsWith('en-IN'))
      || voices.find((v) => v.lang?.startsWith('en'))
    return {
      mode: voices.length ? 'romanised' : 'none',
      voice: english?.name || '', lang: english?.lang || '',
    }
  }, [])

  // Release anything queued the first time the user touches the screen.
  useEffect(() => {
    if (!supported) return undefined
    const unlock = () => {
      if (unlockedRef.current) return
      unlockedRef.current = true
      const queued = queueRef.current
      queueRef.current = null
      if (queued && enabled) setTimeout(() => speak(queued.text, queued.opts), 180)
    }
    const events = ['pointerdown', 'keydown', 'touchstart']
    events.forEach((e) => window.addEventListener(e, unlock, { once: true, passive: true }))
    return () => events.forEach((e) => window.removeEventListener(e, unlock))
  }, [supported, enabled, speak])

  useEffect(() => { if (!enabled) cancel() }, [enabled, cancel])

  const forgetOnce = useCallback((key) => { spokenRef.current.delete(key) }, [])

  return { speak, cancel, speaking, supported, ready, forgetOnce, hindiVoice }
}
