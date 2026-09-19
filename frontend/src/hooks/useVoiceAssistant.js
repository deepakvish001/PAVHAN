import { useCallback, useEffect, useRef, useState } from 'react'
import { hasDevanagari, toLatin } from '../lib/devanagari'
import { speakNumbersInHindi } from '../lib/hindiNumbers'
import { chooseVoice, offerableVoices } from '../lib/voices'
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


export default function useVoiceAssistant({ lang = 'hi', enabled = true, voiceName = '' } = {}) {
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
    if (keepAliveRef.current) {
      clearTimeout(keepAliveRef.current)
      clearInterval(keepAliveRef.current)
      keepAliveRef.current = null
    }
  }, [])

  const startKeepAlive = useCallback(() => {
    stopKeepAlive()
    // Deliberately delayed, not immediate. pause()/resume() on a voice that
    // is mid-word produces an audible click, and on some engines a small
    // stutter — so running it every nine seconds from the start made every
    // sentence in the app worse in order to rescue the few that run past
    // Chrome's limit. It now waits until the passage is already longer than
    // anything that limit would have cut, and only then keeps nudging.
    keepAliveRef.current = setTimeout(() => {
      keepAliveRef.current = setInterval(() => {
        const synth = window.speechSynthesis
        if (!synth) return
        if (!synth.speaking && !synth.pending) { stopKeepAlive(); return }
        try { synth.pause(); synth.resume() } catch { /* not all engines have it */ }
      }, 9000)
    }, 12000)
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
    const { voice, romanise } = chooseVoice(voicesRef.current, target, voiceName)
    if (target !== 'hi' || !romanise || !hasDevanagari(text)) {
      return { spoken: text, romanised: false, voice }
    }
    // Romanise, then say the numbers the way a Hindi speaker says them. An
    // Indian-English voice reads "4249" as "four thousand two hundred
    // forty-nine" — English digits landing in the middle of a Hindi sentence,
    // and landing exactly where it matters, because the numbers in this app
    // are what the artisan is being paid.
    return { spoken: speakNumbersInHindi(toLatin(text)), romanised: true, voice }
  }, [voiceName])

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

      // Pace. A Hindi voice is already tuned by its vendor to sound natural
      // at its own defaults, and every step away from them costs something:
      // 0.88 dragged, and a raised pitch made a warm voice sound thin. Both
      // were changed to "improve" the sound and both made it worse. The only
      // adjustment kept is a small slowdown, because these are instructions
      // to somebody who may be hearing a screen read aloud for the first
      // time — and a touch more of it on the romanised path, where the voice
      // is guessing at unfamiliar spellings.
      utter.rate = rate ?? (target === 'hi' ? (romanised ? 0.93 : 0.95) : 0.98)
      utter.pitch = 1
      utter.volume = 1

      utter.onstart = () => setSpeaking(true)
      utter.onend = () => {
        if (run !== runRef.current) return
        // Hand the next piece straight to the engine. The previous version
        // waited 240ms between sentences to "sound natural"; in practice the
        // synthesiser already leaves its own pause at a full stop, and adding
        // another on top is what made a flowing passage sound like it was
        // being read one line at a time.
        sayPiece()
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

    // Only guard against Chrome's cut-off when the passage is long enough to
    // reach it. Most of what this app says is one or two sentences and is
    // finished well inside the window.
    if (pieces.length > 1) startKeepAlive()
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
    const { voice, romanise, quality, picked } = chooseVoice(voices, 'hi', voiceName)
    const tag = `${voice?.lang || ''} ${voice?.name || ''}`.toLowerCase()
    const mode = romanise ? 'romanised'
      : (/\bhi[-_]/.test(tag) || tag.includes('hindi')) ? 'native' : 'indic'
    return {
      mode, voice: voice?.name || '', lang: voice?.lang || '',
      quality, picked: !!picked, choices: offerableVoices(voices),
    }
  }, [voiceName])

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
