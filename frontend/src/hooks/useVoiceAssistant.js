import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * The PAVHAN voice guide.
 *
 * Speech synthesis has two traps that make assistants feel broken:
 *   - voices load asynchronously, so the first utterance often speaks Hindi
 *     text in an English voice;
 *   - browsers block speech until the user has interacted with the page, and
 *     the rejection is silent.
 * Both are handled here, and anything spoken before the first tap is queued
 * and released the moment the user touches the screen.
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

    const utter = new SpeechSynthesisUtterance(text)
    const voice = pickVoice(voicesRef.current, opts.lang || lang)
    if (voice) utter.voice = voice
    utter.lang = voice?.lang || ((opts.lang || lang) === 'hi' ? 'hi-IN' : 'en-IN')
    // Slightly slow: these are instructions, and many users are hearing a
    // screen read to them for the first time.
    utter.rate = rate ?? ((opts.lang || lang) === 'hi' ? 0.92 : 0.98)
    utter.pitch = 1
    utter.volume = 1
    utter.onstart = () => setSpeaking(true)
    utter.onend = () => { setSpeaking(false); onEnd?.() }
    utter.onerror = () => { setSpeaking(false); onEnd?.() }
    try { window.speechSynthesis.speak(utter) } catch { setSpeaking(false); onEnd?.() }
  }, [supported, enabled, lang])

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

  return { speak, cancel, speaking, supported, ready, forgetOnce }
}
