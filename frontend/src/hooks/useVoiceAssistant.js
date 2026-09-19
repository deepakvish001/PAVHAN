import { useCallback, useEffect, useRef, useState } from 'react'
import { hasDevanagari, toLatin } from '../lib/devanagari'
import { speakNumbersInHindi } from '../lib/hindiNumbers'
import { chooseVoice } from '../lib/voices'
import { MAX_CHUNK, chunkForSpeech } from '../lib/speech'

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


export default function useVoiceAssistant({ lang = 'hi', enabled = true } = {}) {
  const [speaking, setSpeaking] = useState(false)
  const [ready, setReady] = useState(false)
  const [supported] = useState(() => typeof window !== 'undefined' && 'speechSynthesis' in window)
  const voicesRef = useRef([])
  const queueRef = useRef(null)
  const unlockedRef = useRef(false)
  const spokenRef = useRef(new Set())
  // Increments on every new passage. A chunk that finishes after something
  // newer has started checks this and stops, so a cancelled greeting cannot
  // resume over the screen the user has already moved to.
  const runRef = useRef(0)
  const keepAliveRef = useRef(null)

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

  /**
   * Keep Chrome's queue alive.
   *
   * Chrome stops speaking after roughly fifteen seconds and fires no `onend`,
   * so the assistant simply goes quiet in the middle of a sentence and never
   * recovers. It is a decade-old bug with one known workaround: pause and
   * immediately resume while speech is in flight. Harmless on every other
   * engine, and the difference between a greeting that finishes and one that
   * dies halfway through in front of a judge.
   */
  const stopKeepAlive = useCallback(() => {
    if (keepAliveRef.current) { clearInterval(keepAliveRef.current); keepAliveRef.current = null }
  }, [])

  const startKeepAlive = useCallback(() => {
    stopKeepAlive()
    keepAliveRef.current = setInterval(() => {
      const synth = window.speechSynthesis
      if (!synth) return
      if (!synth.speaking && !synth.pending) { stopKeepAlive(); return }
      try { synth.pause(); synth.resume() } catch { /* not all engines have it */ }
    }, 9000)
  }, [stopKeepAlive])

  const cancel = useCallback(() => {
    if (!supported) return
    // Bump the run id first: any chunk already in flight will see it changed
    // in its `onend` and stop rather than queueing the next piece.
    runRef.current += 1
    stopKeepAlive()
    try { window.speechSynthesis.cancel() } catch { /* nothing playing */ }
    setSpeaking(false)
  }, [supported, stopKeepAlive])

  /**
   * Prepare the text this device can actually pronounce well.
   *
   * Returns the string to speak plus whether it had to be romanised, because
   * that decides the utterance's language tag further down.
   */
  const prepare = useCallback((text, target) => {
    const { voice, romanise } = chooseVoice(voicesRef.current, target)
    if (target !== 'hi' || !romanise || !hasDevanagari(text)) {
      return { spoken: text, romanised: false, voice }
    }
    // Romanise, then say the numbers the way a Hindi speaker says them. An
    // Indian-English voice reads "4249" as "four thousand two hundred
    // forty-nine" — English digits landing in the middle of a Hindi sentence,
    // and landing exactly where it matters, because the numbers in this app
    // are what the artisan is being paid.
    return { spoken: speakNumbersInHindi(toLatin(text)), romanised: true, voice }
  }, [])

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

    if (interrupt) {
      try { window.speechSynthesis.cancel() } catch { /* nothing playing */ }
    }

    const target = opts.lang || lang
    const { spoken, romanised, voice } = prepare(text, target)
    const pieces = chunkForSpeech(spoken)
    if (!pieces.length) { onEnd?.(); return }

    // A running id, so a cancelled passage cannot resume from its own
    // `onend` after something newer has started speaking.
    runRef.current += 1
    const run = runRef.current
    let index = 0

    const sayPiece = () => {
      if (run !== runRef.current) return          // superseded
      if (index >= pieces.length) {
        setSpeaking(false)
        stopKeepAlive()
        onEnd?.()
        return
      }
      const piece = pieces[index]
      index += 1

      const utter = new SpeechSynthesisUtterance(piece)
      // Wrapped, because assigning a voice can throw: the list is refreshed
      // on `voiceschanged` and a handle taken before that event can be
      // rejected as stale. An exception here would silence the assistant for
      // the rest of the session, and the utterance still speaks in the
      // default voice with `lang` alone set.
      if (voice) { try { utter.voice = voice } catch { /* stale handle */ } }
      // When the text was romanised the voice is an English one, and telling
      // it the language is Hindi makes it try — and fail — to apply Hindi
      // phonology to Roman letters. Let it read the Roman as Indian English,
      // which is exactly what it should sound like.
      utter.lang = romanised ? (voice?.lang || 'en-IN')
        : (voice?.lang || (target === 'hi' ? 'hi-IN' : 'en-IN'))

      // Pace. Hindi carries more syllables per idea than English, and these
      // are instructions to somebody who may be hearing a screen read aloud
      // for the first time. Romanised Hindi is slowed a little further: the
      // voice is guessing at unfamiliar spellings and rushing them is what
      // makes it sound like gibberish rather than an accent.
      const base = target === 'hi' ? (romanised ? 0.88 : 0.92) : 0.98
      utter.rate = rate ?? base
      // A touch above neutral carries better on a phone speaker in a noisy
      // room, which is where this is actually used.
      utter.pitch = target === 'hi' ? 1.05 : 1
      utter.volume = 1

      utter.onstart = () => setSpeaking(true)
      utter.onend = () => {
        if (run !== runRef.current) return
        // A short gap between pieces is what turns a wall of speech into
        // sentences. Longer after a full stop than after a comma.
        setTimeout(sayPiece, /[।.!?]\s*$/.test(piece) ? 240 : 120)
      }
      utter.onerror = () => {
        if (run !== runRef.current) return
        setSpeaking(false)
        stopKeepAlive()
        onEnd?.()
      }

      try { window.speechSynthesis.speak(utter) } catch {
        setSpeaking(false); stopKeepAlive(); onEnd?.()
      }
    }

    startKeepAlive()
    sayPiece()
  }, [supported, enabled, lang, prepare, startKeepAlive, stopKeepAlive])

  /**
   * What this device can actually do with Hindi, in plain terms.
   *
   * Deliberately asks `chooseVoice` — the same function the speaking path
   * uses — rather than repeating the logic. A diagnostic that disagrees with
   * the behaviour it is diagnosing is worse than none.
   */
  const hindiVoice = useCallback(() => {
    const voices = voicesRef.current
    if (!voices.length) return { mode: 'none', voice: '', lang: '', quality: 'none' }
    const { voice, romanise, quality } = chooseVoice(voices, 'hi')
    const tag = `${voice?.lang || ''} ${voice?.name || ''}`.toLowerCase()
    const mode = romanise ? 'romanised'
      : (/\bhi[-_]/.test(tag) || tag.includes('hindi')) ? 'native' : 'indic'
    return { mode, voice: voice?.name || '', lang: voice?.lang || '', quality }
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
  useEffect(() => stopKeepAlive, [stopKeepAlive])

  const forgetOnce = useCallback((key) => { spokenRef.current.delete(key) }, [])

  return { speak, cancel, speaking, supported, ready, forgetOnce, hindiVoice }
}
