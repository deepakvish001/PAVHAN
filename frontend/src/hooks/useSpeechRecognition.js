import { useCallback, useEffect, useRef, useState } from 'react'

/**
 * Speech-to-text that actually starts.
 *
 * The old prototype's mic "did nothing" for the usual four reasons, and this
 * hook handles all of them explicitly instead of failing silently:
 *
 *  1. Not a secure context. getUserMedia and SpeechRecognition are disabled
 *     outside https:// and localhost, with no error the user can see.
 *  2. Permission never actually requested. Calling recognition.start() alone
 *     shows no prompt on some Chrome builds — so we call getUserMedia first,
 *     which reliably raises the prompt AND gives us a live level meter, so the
 *     artisan can SEE that the mic is picking them up.
 *  3. Chrome ends the session after a few seconds of silence. An artisan
 *     pauses to think, `onend` fires, and everything stops. We restart while
 *     the user still intends to be recording.
 *  4. Every error was swallowed. Each one is now mapped to a sentence in the
 *     artisan's own language.
 */

const ERRORS = {
  'not-allowed': {
    hi: 'माइक की अनुमति नहीं मिली। ब्राउज़र में माइक चालू कीजिए या नीचे लिखकर बताइए।',
    en: 'Microphone permission was denied. Allow it in your browser, or type below.',
  },
  'service-not-allowed': {
    hi: 'इस ब्राउज़र ने बोलकर लिखने की सुविधा रोक दी है। क्रोम में खोलिए।',
    en: 'Your browser blocked speech recognition. Try opening PAVHAN in Chrome.',
  },
  'no-speech': {
    hi: 'कुछ सुनाई नहीं दिया। माइक के थोड़ा पास आकर दोबारा बोलिए।',
    en: 'I did not hear anything. Move a little closer and speak again.',
  },
  'audio-capture': {
    hi: 'माइक नहीं मिला। जाँचिए कि कोई और ऐप माइक इस्तेमाल तो नहीं कर रहा।',
    en: 'No microphone found. Check that another app is not using it.',
  },
  network: {
    hi: 'इंटरनेट की दिक्कत है। बोलकर लिखने के लिए नेट चाहिए।',
    en: 'Network problem — speech recognition needs an internet connection.',
  },
  aborted: { hi: '', en: '' }, // user stopped on purpose; not worth reporting
}

const LANGS = { hi: 'hi-IN', en: 'en-IN' }

function getRecognition() {
  if (typeof window === 'undefined') return null
  const Impl = window.SpeechRecognition || window.webkitSpeechRecognition
  return Impl ? new Impl() : null
}

export function speechSupport() {
  if (typeof window === 'undefined') return { supported: false, reason: 'ssr' }
  const secure = window.isSecureContext || ['localhost', '127.0.0.1'].includes(location.hostname)
  if (!secure) return { supported: false, reason: 'insecure' }
  const hasApi = !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  if (!hasApi) return { supported: false, reason: 'unsupported' }
  return { supported: true, reason: null }
}

/**
 * Why can't this browser hear me? Answer it precisely, before the user
 * presses anything, because "the mic doesn't work" is almost never the mic.
 */
export async function micDiagnostics() {
  if (typeof window === 'undefined') return null
  const host = location.hostname
  const localhost = ['localhost', '127.0.0.1', '[::1]'].includes(host)
  const secure = window.isSecureContext || localhost
  const hasApi = !!(window.SpeechRecognition || window.webkitSpeechRecognition)
  const hasMedia = !!navigator.mediaDevices?.getUserMedia
  const ua = navigator.userAgent
  const browser = /Edg\//.test(ua) ? 'Edge'
    : /OPR\//.test(ua) ? 'Opera'
    : /Chrome\//.test(ua) ? 'Chrome'
    : /Firefox\//.test(ua) ? 'Firefox'
    : /Safari\//.test(ua) ? 'Safari'
    : 'this browser'

  let permission = 'unknown'
  try {
    const status = await navigator.permissions?.query({ name: 'microphone' })
    if (status) permission = status.state
  } catch { /* Firefox and Safari do not expose the microphone permission */ }

  let devices = null
  try {
    const list = await navigator.mediaDevices?.enumerateDevices()
    if (list) devices = list.filter((d) => d.kind === 'audioinput').length
  } catch { /* needs permission on some browsers */ }

  // The first blocker in this list is the one actually stopping them.
  let blocker = null
  if (!secure) blocker = 'insecure'
  else if (!hasMedia) blocker = 'nomedia'
  else if (!hasApi) blocker = 'noapi'
  else if (permission === 'denied') blocker = 'denied'
  else if (devices === 0) blocker = 'nodevice'

  return {
    origin: location.origin, host, localhost, secure, hasApi, hasMedia,
    browser, permission, devices, blocker,
  }
}

export default function useSpeechRecognition({ lang = 'hi', onFinal } = {}) {
  const [listening, setListening] = useState(false)
  const [finalText, setFinalText] = useState('')
  const [interim, setInterim] = useState('')
  const [level, setLevel] = useState(0)
  const [error, setError] = useState(null)
  const [permission, setPermission] = useState('prompt')

  const recogRef = useRef(null)
  const wantRef = useRef(false)       // does the user still intend to record?
  const finalRef = useRef('')
  const streamRef = useRef(null)
  const audioRef = useRef(null)
  const rafRef = useRef(null)
  const onFinalRef = useRef(onFinal)
  const langRef = useRef(lang)

  useEffect(() => { onFinalRef.current = onFinal }, [onFinal])
  useEffect(() => { langRef.current = lang }, [lang])

  const support = speechSupport()

  // ---- live input level, so the UI can prove the mic is working ----------
  const startMeter = useCallback((stream) => {
    try {
      const Ctx = window.AudioContext || window.webkitAudioContext
      if (!Ctx) return
      const ctx = new Ctx()
      audioRef.current = ctx
      const source = ctx.createMediaStreamSource(stream)
      const analyser = ctx.createAnalyser()
      analyser.fftSize = 512
      source.connect(analyser)
      const buf = new Uint8Array(analyser.frequencyBinCount)
      const tick = () => {
        analyser.getByteTimeDomainData(buf)
        let peak = 0
        for (let i = 0; i < buf.length; i += 1) {
          const v = Math.abs(buf[i] - 128) / 128
          if (v > peak) peak = v
        }
        setLevel((prev) => prev * 0.7 + Math.min(1, peak * 2.2) * 0.3)
        rafRef.current = requestAnimationFrame(tick)
      }
      tick()
    } catch {
      /* the meter is a nicety — never let it break recording */
    }
  }, [])

  const stopMeter = useCallback(() => {
    if (rafRef.current) cancelAnimationFrame(rafRef.current)
    rafRef.current = null
    if (audioRef.current) { audioRef.current.close().catch(() => {}); audioRef.current = null }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((t) => t.stop())
      streamRef.current = null
    }
    setLevel(0)
  }, [])

  const buildRecognition = useCallback(() => {
    const recog = getRecognition()
    if (!recog) return null
    recog.lang = LANGS[langRef.current] || LANGS.hi
    recog.continuous = true
    recog.interimResults = true
    recog.maxAlternatives = 1

    recog.onresult = (event) => {
      let live = ''
      for (let i = event.resultIndex; i < event.results.length; i += 1) {
        const result = event.results[i]
        const text = result[0].transcript
        if (result.isFinal) {
          finalRef.current = `${finalRef.current} ${text}`.replace(/\s+/g, ' ').trim()
          setFinalText(finalRef.current)
          onFinalRef.current?.(finalRef.current)
        } else {
          live += text
        }
      }
      setInterim(live)
    }

    recog.onerror = (event) => {
      const mapped = ERRORS[event.error]
      if (event.error === 'not-allowed' || event.error === 'service-not-allowed') {
        setPermission('denied')
        wantRef.current = false
      }
      // 'no-speech' is recoverable — Chrome restarts happily, so don't stop.
      if (mapped && mapped[langRef.current]) setError(mapped[langRef.current])
      else if (mapped && mapped.en && event.error !== 'aborted') setError(mapped.en)
    }

    recog.onend = () => {
      // Chrome ends the session on a pause. If the artisan is still speaking
      // their mind, start it again rather than dropping the rest of the note.
      if (wantRef.current) {
        try { recog.start() } catch { /* already starting; ignore */ }
      } else {
        setListening(false)
        setInterim('')
        stopMeter()
      }
    }
    return recog
  }, [stopMeter])

  const start = useCallback(async ({ reset = false } = {}) => {
    setError(null)
    const state = speechSupport()
    if (!state.supported) {
      setError(
        state.reason === 'insecure'
          ? (langRef.current === 'hi'
              ? 'माइक के लिए सुरक्षित पता (https) चाहिए। localhost पर यह काम करेगा।'
              : 'The microphone needs a secure (https) address. It works on localhost.')
          : (langRef.current === 'hi'
              ? 'इस ब्राउज़र में बोलकर लिखना नहीं चलता। क्रोम खोलिए या नीचे लिखिए।'
              : 'This browser cannot do speech to text. Use Chrome, or type below.'),
      )
      return false
    }

    if (reset) { finalRef.current = ''; setFinalText(''); }
    setInterim('')

    // Ask for the mic explicitly. This is what makes the prompt appear.
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      })
      streamRef.current = stream
      setPermission('granted')
      startMeter(stream)
    } catch {
      setPermission('denied')
      setError(ERRORS['not-allowed'][langRef.current] || ERRORS['not-allowed'].en)
      return false
    }

    const recog = buildRecognition()
    if (!recog) { setError(ERRORS['service-not-allowed'][langRef.current]); stopMeter(); return false }
    recogRef.current = recog
    wantRef.current = true
    try {
      recog.start()
      setListening(true)
      return true
    } catch {
      // start() throws if a previous session is still closing — retry once.
      setTimeout(() => { try { recog.start(); setListening(true) } catch { /* give up quietly */ } }, 260)
      return true
    }
  }, [buildRecognition, startMeter, stopMeter])

  const stop = useCallback(() => {
    wantRef.current = false
    setListening(false)
    setInterim('')
    try { recogRef.current?.stop() } catch { /* not running */ }
    stopMeter()
  }, [stopMeter])

  const toggle = useCallback(
    (opts) => (listening ? (stop(), false) : start(opts)),
    [listening, start, stop],
  )

  const reset = useCallback(() => {
    finalRef.current = ''
    setFinalText('')
    setInterim('')
    setError(null)
  }, [])

  const setText = useCallback((text) => {
    finalRef.current = text
    setFinalText(text)
  }, [])

  useEffect(() => () => { wantRef.current = false; try { recogRef.current?.abort() } catch {} ; stopMeter() }, [stopMeter])

  return {
    supported: support.supported,
    unsupportedReason: support.reason,
    listening, finalText, interim, level, error, permission,
    start, stop, toggle, reset, setText,
    transcript: `${finalText}${interim ? ` ${interim}` : ''}`.trim(),
  }
}
