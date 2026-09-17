import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { TopBar, Toasts } from '../components/Shell'
import { Bar, ScoreRing, Stepper, VoiceOrb, rupees } from '../components/ui'
import useSpeechRecognition, { micDiagnostics } from '../hooks/useSpeechRecognition'
import LanguagePicker from '../components/LanguagePicker'
import {
  coach, createProduct, enhancePhoto, generateListing, listUsers,
  matchBuyers, recommendPrice, sendEnquiry, transcribeAudio,
} from '../api/client'
import { enqueue as queueCapture } from '../lib/outbox'

/**
 * Every step below is declared at module level on purpose.
 *
 * They used to live inside AddProduct, which meant React saw a brand-new
 * component type on every parent render and threw away the step's state — so
 * switching language mid-flow, or any re-render at all, silently wiped the
 * photo and the transcript the artisan had just recorded.
 */

// Demo fallbacks across six different crafts. The point of offering a choice
// is that the demo must not look like it only knows one saree.
const SAMPLES = [
  {
    key: 'saree', icon: '🥻', label_hi: 'बनारसी साड़ी', label_en: 'Banarasi saree',
    hi: 'यह बनारसी हथकरघा रेशमी साड़ी है। इसे हमने हाथ से बुना है। इसमें लाल और सुनहरी ज़री का काम है। वज़न लगभग साढ़े चार सौ ग्राम और लंबाई साढ़े पाँच मीटर है। बनाने में बारह दिन लगे। केवल ड्राई क्लीन।',
    en: 'This is a handwoven Banarasi silk saree. We wove it by hand. It has red and golden zari work. Weight is around 450 gram and length is 5.5 metre. It took twelve days to make. Dry clean only.',
  },
  {
    key: 'pottery', icon: '🏺', label_hi: 'ब्लू पॉटरी', label_en: 'Blue pottery',
    hi: 'यह जयपुर की ब्लू पॉटरी का गुलदस्ता है। नीला और सफ़ेद रंग है, सिरेमिक का बना है। वज़न आठ सौ ग्राम, नौ इंच ऊँचा है। बनाने में तीन दिन लगे। हाथ से धोइए।',
    en: 'This is a Jaipur blue pottery vase. Blue and white, made of quartz ceramic. It weighs 800 gram and is nine inch tall. It took three days to make. Hand wash only.',
  },
  {
    key: 'diya', icon: '🪔', label_hi: 'मिट्टी का दीया', label_en: 'Terracotta diya',
    hi: 'मैंने मिट्टी से टेराकोटा दीया बनाया है। रंग भूरा और लाल है। वज़न दो सौ ग्राम, चार इंच का है। दो दिन लगे। मैं बांकुड़ा से हूँ और प्राकृतिक रंग लगाए हैं।',
    en: 'I made a terracotta diya from clay. Brown and red in colour. It weighs 200 gram and is four inch wide. It took two days. I am from Bankura and I used natural colours.',
  },
  {
    key: 'basket', icon: '🧺', label_hi: 'बाँस की टोकरी', label_en: 'Bamboo basket',
    hi: 'यह बाँस और बेंत की टोकरी है, असम से। रंग भूरा है, चौदह इंच की है, वज़न चार सौ ग्राम। बनाने में एक दिन लगा। सूखी जगह पर रखिए।',
    en: 'This is a bamboo and cane storage basket from Assam. Beige in colour, fourteen inch wide, weighs 400 gram. It took one day to make. Keep it in a dry place.',
  },
  {
    key: 'madhubani', icon: '🎨', label_hi: 'मधुबनी चित्र', label_en: 'Madhubani painting',
    hi: 'यह मधुबनी चित्रकला है, हाथ से बनाई है। कागज़ पर लाल और पीला रंग है। नाप चौबीस गुणा छत्तीस इंच, वज़न तीन सौ ग्राम। आठ दिन लगे। मैं मधुबनी से हूँ।',
    en: 'This is a hand-painted Madhubani artwork on handmade paper. Red and yellow. Size twenty four by thirty six inch, weighs 300 gram. It took eight days. I am from Madhubani.',
  },
  {
    key: 'pashmina', icon: '🧣', label_hi: 'पश्मीना शॉल', label_en: 'Pashmina shawl',
    hi: 'यह कश्मीरी पश्मीना शॉल है। क्रीम रंग की है, ऊन से बनी है। वज़न दो सौ दस ग्राम, लंबाई दो मीटर। बनाने में चौदह दिन लगे। केवल ड्राई क्लीन।',
    en: 'This is a Kashmiri pashmina shawl. Cream coloured, made of pashmina wool. It weighs 210 gram and is two metre long. It took fourteen days. Dry clean only.',
  },
]

const STEP_SCRIPTS = [
  'capture_photo', 'voice_record', 'listing_review', 'pricing', 'buyer_match', 'published',
]

/** Speak a screen's script once when that step appears. */
function useStepVoice(screen, say) {
  const fired = useRef(false)
  useEffect(() => {
    if (fired.current) return undefined
    fired.current = true
    const timer = setTimeout(() => say(screen, { once: false }), 480)
    return () => clearTimeout(timer)
  }, [screen]) // eslint-disable-line react-hooks/exhaustive-deps
}

// ===========================================================================
// Step 0 — photograph
// ===========================================================================
const BACKDROPS = [
  { key: 'white', label_hi: 'सफ़ेद', label_en: 'White', swatch: '#ffffff' },
  { key: 'studio', label_hi: 'स्टूडियो', label_en: 'Studio', swatch: 'linear-gradient(160deg,#fcfaf6,#e2dcd0)' },
  { key: 'transparent', label_hi: 'पारदर्शी', label_en: 'Transparent', swatch: 'repeating-conic-gradient(#ccc 0 25%, #fff 0 50%) 50%/12px 12px' },
  { key: 'original', label_hi: 'जैसी है', label_en: 'Original', swatch: 'linear-gradient(160deg,#b08a5a,#6d5637)' },
]

function PhotoStep({ studio, working, backdrop, setBackdrop, onPick, onNext }) {
  const { t, lang, say } = useApp()
  const fileRef = useRef(null)
  const cameraRef = useRef(null)
  const [compare, setCompare] = useState(false)
  useStepVoice('capture_photo', say)

  const report = studio?.report

  return (
    <div className="page stack">
      <div>
        <h2 style={{ fontSize: 'calc(21px * var(--font-scale))' }} lang={lang}>
          {t('पहले सामान की फोटो लीजिए', 'First, photograph your piece')}
        </h2>
        <p className="section-sub" style={{ marginTop: 6 }} lang={lang}>
          {t('दिन की रोशनी में, सादे कपड़े पर। बाकी सुधार मैं कर दूँगा।',
             'Daylight, plain cloth behind it. I will fix the rest.')}
        </p>
      </div>

      <div
        className="card flush"
        style={{
          minHeight: 210, display: 'grid', placeItems: 'center', position: 'relative',
          background: studio ? 'var(--paper-2)' : 'var(--paper-2)',
          borderStyle: studio ? 'solid' : 'dashed', borderWidth: studio ? 1 : 2,
        }}
      >
        {studio ? (
          <>
            <img
              src={compare ? studio.before_url : studio.after_url}
              alt=""
              style={{ width: '100%', maxHeight: 320, objectFit: 'contain', display: 'block',
                       background: compare ? '#000' : 'transparent' }}
            />
            <div style={{ position: 'absolute', top: 10, left: 10 }}>
              <span className="pill" style={{ background: compare ? 'var(--ink)' : 'var(--leaf)',
                                              color: '#fff', border: 0 }}>
                {compare ? t('पहले', 'Before') : t('बाद में', 'After')}
              </span>
            </div>
            <button
              onMouseDown={() => setCompare(true)} onMouseUp={() => setCompare(false)}
              onMouseLeave={() => setCompare(false)}
              onTouchStart={() => setCompare(true)} onTouchEnd={() => setCompare(false)}
              className="btn btn-sm"
              style={{ position: 'absolute', bottom: 10, right: 10, background: 'rgba(0,0,0,0.62)',
                       color: '#fff', backdropFilter: 'blur(4px)' }}
            >
              👁 {t('दबाकर पहले वाली देखिए', 'Hold to see before')}
            </button>
          </>
        ) : (
          <div className="center muted" style={{ padding: 30 }}>
            <div style={{ fontSize: 'calc(40px * var(--font-scale))', marginBottom: 8 }}>📷</div>
            <div style={{ fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>{t('अभी कोई फोटो नहीं', 'No photo yet')}</div>
          </div>
        )}
        {working && (
          <div style={{ position: 'absolute', inset: 0, background: 'rgba(22,27,51,0.72)',
                        display: 'grid', placeItems: 'center', color: '#fff' }}>
            <div className="center">
              <div className="spinner" style={{ margin: '0 auto 10px' }} />
              <div style={{ fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
                {t('स्टूडियो में सुधारा जा रहा है…', 'Cleaning it up in the studio…')}
              </div>
              <div style={{ fontSize: 'calc(11px * var(--font-scale))', color: '#b9c0da', marginTop: 5 }} lang={lang}>
                {t('बैकग्राउंड, रोशनी, नाप', 'Background, lighting, framing')}
              </div>
            </div>
          </div>
        )}
      </div>

      <input ref={cameraRef} type="file" accept="image/*" capture="environment" hidden
             onChange={(e) => onPick(e.target.files?.[0])} />
      <input ref={fileRef} type="file" accept="image/*" hidden
             onChange={(e) => onPick(e.target.files?.[0])} />

      <div className="grid-2">
        <button className="btn btn-ink" onClick={() => cameraRef.current?.click()}>
          📷 {t('कैमरा', 'Camera')}
        </button>
        <button className="btn btn-soft" onClick={() => fileRef.current?.click()}>
          🖼️ {t('गैलरी', 'Gallery')}
        </button>
      </div>

      {studio && (
        <>
          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
              {t('बैकग्राउंड चुनिए', 'Choose a backdrop')}
            </div>
            <div className="row" style={{ gap: 9 }}>
              {BACKDROPS.map((b) => (
                <button key={b.key} onClick={() => setBackdrop(b.key)}
                        style={{ flex: 1, border: backdrop === b.key ? '2px solid var(--madder)'
                                                                     : '1px solid var(--line)',
                                 borderRadius: 12, padding: 6, background: 'var(--card)' }}>
                  <div style={{ height: 34, borderRadius: 8, background: b.swatch,
                                border: '1px solid var(--line)' }} />
                  <div style={{ fontSize: 'calc(10px * var(--font-scale))', fontWeight: 700, marginTop: 5 }} lang={lang}>
                    {lang === 'hi' ? b.label_hi : b.label_en}
                  </div>
                </button>
              ))}
            </div>
          </div>

          <StudioReport report={report} />
        </>
      )}

      <button className="btn btn-primary btn-block" disabled={working} onClick={onNext}
              style={{ marginTop: 4 }}>
        {studio ? t('आगे — अब बोलिए', 'Next — now speak')
                : t('फोटो के बिना आगे बढ़िए', 'Continue without a photo')}
      </button>
      <p className="center muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.55 }} lang={lang}>
        {t('बैकग्राउंड, रोशनी और नाप अपने आप ठीक होते हैं — बिना इंटरनेट के भी।',
           'Background, lighting and framing are fixed automatically — even offline.')}
      </p>
    </div>
  )
}

function StudioReport({ report }) {
  const { t, lang } = useApp()
  if (!report) return null
  const lift = report.brightness_after - report.brightness_before
  return (
    <div className="card fade-up">
      <div className="row-between" style={{ marginBottom: 9 }}>
        <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
          ✨ {t('स्टूडियो ने क्या किया', 'What the studio did')}
        </div>
        {report.background_removed && (
          <span className="pill leaf">{report.segmentation_confidence}%</span>
        )}
      </div>
      {report.steps.map((s) => (
        <div key={s.key} className="row" style={{ gap: 8, alignItems: 'flex-start',
                                                  marginBottom: 7 }}>
          <span style={{ flexShrink: 0 }}>{s.applied ? '✅' : '⚠️'}</span>
          <div>
            <div style={{ fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 600 }} lang={lang}>
              {lang === 'hi' ? s.label_hi : s.label}
            </div>
            <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.5 }} lang={lang}>
              {lang === 'hi' ? s.detail_hi || s.detail : s.detail}
            </div>
          </div>
        </div>
      ))}
      <div className="row" style={{ gap: 8, flexWrap: 'wrap', marginTop: 10,
                                    paddingTop: 10, borderTop: '1px solid var(--line)' }}>
        {lift > 4 && (
          <span className="pill gold">
            ☀️ {t(`रोशनी +${Math.round(lift)}`, `Light +${Math.round(lift)}`)}
          </span>
        )}
        <span className="pill ink">{report.width}×{report.height}</span>
        <span className="pill">{report.engine.includes('OpenCV') ? 'OpenCV GrabCut' : 'on-device'}</span>
      </div>
    </div>
  )
}

function PhotoReport({ vision }) {
  const { t, lang } = useApp()
  const tips = (lang === 'hi' ? vision.photo_tips_hi : vision.photo_tips) || vision.photo_tips || []
  return (
    <div className="card fade-up">
      <div className="row" style={{ gap: 12, alignItems: 'flex-start' }}>
        <ScoreRing value={vision.photo_quality} label={t('फोटो', 'photo')} />
        <div style={{ flex: 1 }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 5 }} lang={lang}>
            {t('फोटो से क्या पढ़ा गया', 'What the photo told us')}
          </div>
          <div className="row" style={{ gap: 5, flexWrap: 'wrap', marginBottom: 8 }}>
            {(vision.palette || []).slice(0, 5).map((c) => (
              <span key={c.hex + c.name} title={`${c.name} · ${Math.round(c.share * 100)}%`}
                    style={{ width: 22, height: 22, borderRadius: 7, background: c.hex,
                             border: '1px solid rgba(0,0,0,0.12)' }} />
            ))}
          </div>
          <div className="row" style={{ gap: 5, flexWrap: 'wrap' }}>
            <span className="pill">{vision.dominant_colour}</span>
            <span className="pill">{vision.motif_density}</span>
            <span className="pill">{vision.surface}</span>
            <span className="pill ink">{vision.complexity}× {t('बारीकी', 'intricacy')}</span>
          </div>
        </div>
      </div>
      {tips.length > 0 && (
        <div style={{ marginTop: 11, paddingTop: 11, borderTop: '1px solid var(--line)',
                      fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.6, color: 'var(--ink-soft)' }}>
          {tips.map((tip) => (
            <div key={tip} className="row" style={{ gap: 7, alignItems: 'flex-start' }} lang={lang}>
              <span>{vision.photo_quality >= 85 ? '✅' : '💡'}</span><span>{tip}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}

// ===========================================================================
// Step 1 — speak
// ===========================================================================
function VoiceStep({ imageId, rawFile, text, setText, spokenLang, setSpokenLang, onGenerated, onQueued }) {
  const { t, lang, say, sayRaw, toast, user } = useApp()
  const [tips, setTips] = useState(null)
  const [generating, setGenerating] = useState(false)
  // Re-read on every connection change rather than once on mount: the whole
  // point of this screen is that the signal comes and goes while it is open.
  const [online, setOnline] = useState(navigator.onLine)
  useEffect(() => {
    const sync = () => setOnline(navigator.onLine)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)
    return () => {
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
    }
  }, [])
  const [showSamples, setShowSamples] = useState(false)
  const [diag, setDiag] = useState(null)
  const [recording, setRecording] = useState(false)
  const mediaRef = useRef(null)
  const chunksRef = useRef([])
  useStepVoice('voice_record', say)

  // The recogniser listens in the language the artisan chose, not the
  // language the interface happens to be in.
  const mic = useSpeechRecognition({ lang: spokenLang, onFinal: (full) => setText(full) })

  // Work out up front why the mic might not work, so the artisan is told
  // before they tap it rather than after it silently fails.
  useEffect(() => { micDiagnostics().then(setDiag).catch(() => {}) }, [])

  // Live coaching while they speak.
  useEffect(() => {
    const value = text.trim()
    if (value.length < 8) { setTips(null); return undefined }
    const timer = setTimeout(() => { coach(value, lang).then(setTips).catch(() => {}) }, 750)
    return () => clearTimeout(timer)
  }, [text, lang])

  const toggleMic = async () => {
    if (mic.listening) { mic.stop(); return }
    const ok = await mic.start({ reset: !text })
    if (ok) sayRaw(t('मैं सुन रहा हूँ। बोलिए।', 'I am listening. Go ahead.'), { rate: 1.05 })
  }

  // If speech recognition is unavailable, record audio and let the server
  // transcribe it — the artisan still only has to speak.
  const recordAudio = async () => {
    if (mediaRef.current?.state === 'recording') { mediaRef.current.stop(); return }
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const rec = new MediaRecorder(stream)
      chunksRef.current = []
      rec.ondataavailable = (e) => chunksRef.current.push(e.data)
      rec.onstop = async () => {
        stream.getTracks().forEach((tr) => tr.stop())
        setRecording(false)
        const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
        try {
          const res = await transcribeAudio(new File([blob], 'note.webm'), spokenLang)
          setText(res.transcript)
        } catch (err) { toast(err.message, 'warn') }
      }
      mediaRef.current = rec
      rec.start()
      setRecording(true)
    } catch {
      toast(t('माइक नहीं मिला।', 'Microphone unavailable.'), 'err')
    }
  }

  /** Prove the microphone hears them, without starting a whole recording. */
  const testMic = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      const Ctx = window.AudioContext || window.webkitAudioContext
      const ctx = new Ctx()
      const analyser = ctx.createAnalyser()
      ctx.createMediaStreamSource(stream).connect(analyser)
      const buf = new Uint8Array(analyser.frequencyBinCount)
      let peak = 0
      const started = Date.now()
      sayRaw(t('कुछ बोलिए… मैं जाँच रहा हूँ।', 'Say something — I am checking.'))
      const tick = () => {
        analyser.getByteTimeDomainData(buf)
        for (const v of buf) peak = Math.max(peak, Math.abs(v - 128) / 128)
        if (Date.now() - started < 3200) { requestAnimationFrame(tick); return }
        stream.getTracks().forEach((t2) => t2.stop())
        ctx.close().catch(() => {})
        micDiagnostics().then(setDiag).catch(() => {})
        toast(
          peak > 0.05
            ? t('माइक ठीक है — आपकी आवाज़ आ रही है ✓', 'Your mic works — I can hear you ✓')
            : t('कुछ सुनाई नहीं दिया। माइक के पास आकर दोबारा बोलिए।',
                 'I heard nothing. Move closer and try again.'),
          peak > 0.05 ? 'ok' : 'warn', 4200,
        )
      }
      tick()
    } catch {
      toast(t('माइक की अनुमति नहीं मिली।', 'Microphone permission was refused.'), 'err')
      micDiagnostics().then(setDiag).catch(() => {})
    }
  }

  const generate = async () => {
    const value = text.trim()
    if (!value && !imageId && !rawFile) {
      toast(t('पहले बोलिए या फोटो डालिए।', 'Speak or add a photo first.'), 'warn')
      return
    }
    mic.stop()

    // Offline, there is no pipeline to run: the craft identification, the
    // description and the price all live on the server. Rather than failing
    // and losing what the artisan just recorded, the capture is held on the
    // phone and the whole flow runs on send.
    if (!navigator.onLine) {
      setGenerating(true)
      try {
        await queueCapture({
          photo: rawFile, transcript: value, language: spokenLang,
          artisanId: user?.id || '', label: value.slice(0, 60),
        })
        onQueued?.()
      } catch (err) {
        toast(err.message, 'err')
      } finally {
        setGenerating(false)
      }
      return
    }

    setGenerating(true)
    try {
      const data = await generateListing({
        transcript: value, image_id: imageId || '', language: spokenLang, use_llm: 'true',
      })
      onGenerated(data)
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setGenerating(false)
    }
  }

  const pickSample = (sample) => {
    const value = sample[spokenLang] || sample[lang] || sample.en
    setText(value)
    mic.setText(value)
    setShowSamples(false)
  }

  // NOT trimmed. This string is the textarea's controlled value, and trimming
  // it deletes the space the moment the user presses the spacebar — which made
  // typing come out as "thisisthetshirtwhich". Trim only when sending.
  const live = mic.interim ? `${text} ${mic.interim}` : text

  return (
    <div className="page stack">
      <div>
        <h2 style={{ fontSize: 'calc(21px * var(--font-scale))' }} lang={lang}>{t('अब बस बोलिए', 'Now just speak')}</h2>
        <p className="section-sub" style={{ marginTop: 6 }} lang={lang}>
          {t('अपनी भाषा में बताइए — यह क्या है, किस चीज़ से बना है, कितना बड़ा है, कितने दिन लगे।',
             'In your own language: what it is, what it is made of, how big it is, how long it took.')}
        </p>
      </div>

      <LanguagePicker value={spokenLang} onChange={setSpokenLang} />

      <MicButton mic={mic} onToggle={toggleMic} />

      {mic.error && (
        <div className="card" style={{ borderColor: '#f0cbc6', background: '#fdf4f3',
                                       fontSize: 'calc(12.5px * var(--font-scale))', lineHeight: 1.6 }} lang={lang}>
          ⚠️ {mic.error}
        </div>
      )}

      <MicHelp diag={diag} onRecord={recordAudio} recording={recording} onTest={testMic} />

      <div className="field">
        <div className="row-between">
          <label htmlFor="transcript">
            {t('आपने जो बोला (बदल भी सकते हैं)', 'What you said — editable')}
          </label>
          {live && (
            <button className="btn btn-sm btn-soft"
                    onClick={() => { setText(''); mic.reset(); setTips(null) }}>
              {t('मिटाइए', 'Clear')}
            </button>
          )}
        </div>
        <textarea
          id="transcript" className="textarea" lang={lang} rows={5} value={live}
          placeholder={t('माइक दबाइए, या यहाँ सीधे लिख दीजिए…',
                         'Press the mic, or type here directly…')}
          onChange={(e) => { setText(e.target.value); mic.setText(e.target.value) }}
        />
      </div>

      {tips && <CoachCard tips={tips} />}

      {/* A choice of samples, not one hardcoded saree. */}
      <div className="card tinted">
        <button
          onClick={() => setShowSamples(!showSamples)}
          style={{ background: 'none', border: 0, padding: 0, width: '100%',
                   textAlign: 'left', fontSize: 'calc(13px * var(--font-scale))', fontWeight: 700 }}
          lang={lang}
        >
          {showSamples ? '▾' : '▸'} {t('बोल नहीं पा रहे? तैयार नमूना चुनिए',
                                        'Cannot speak right now? Pick a ready sample')}
        </button>
        {showSamples && (
          <>
            <div className="row" style={{ gap: 7, flexWrap: 'wrap', marginTop: 10 }}>
              {SAMPLES.map((sample) => (
                <button key={sample.key} className="chip" onClick={() => pickSample(sample)}
                        style={{ padding: '8px 12px' }} lang={lang}>
                  {sample.icon} {lang === 'hi' ? sample.label_hi : sample.label_en}
                </button>
              ))}
            </div>
            <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.55, marginTop: 9 }} lang={lang}>
              {t('हर नमूना अलग शिल्प का है — विवरण, दाम और खरीदार भी अलग बनेंगे।',
                 'Each sample is a different craft — the listing, the price and the buyers all change.')}
            </div>
          </>
        )}
      </div>

      {!online && (
        <div className="card" style={{ borderColor: 'var(--marigold)', marginBottom: 10 }}>
          <div style={{ fontWeight: 800, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
            📵 {t('अभी सिग्नल नहीं है', 'No signal right now')}
          </div>
          <div className="muted" style={{ fontSize: 'calc(12.5px * var(--font-scale))', marginTop: 4, lineHeight: 1.5 }}
               lang={lang}>
            {t('कोई बात नहीं। आपकी फोटो और आपकी बात फ़ोन में रख ली जाएगी, और सिग्नल आते ही पूरा विवरण और दाम बन जाएगा।',
               'That is fine. Your photo and your words are kept on the phone, and the full listing and price are made the moment the signal returns.')}
          </div>
        </div>
      )}

      <button className="btn btn-primary btn-block" onClick={generate} disabled={generating}
              style={{ padding: 16 }}>
        {generating
          ? <><span className="spinner" /> {online
              ? t('विवरण बनाया जा रहा है…', 'Writing your listing…')
              : t('फ़ोन में रखा जा रहा है…', 'Saving to your phone…')}</>
          : online
            ? `✨ ${t('मेरा विवरण बनाइए', 'Create my listing')}`
            : `📥 ${t('फ़ोन में रखिए, बाद में भेजेंगे', 'Keep it on my phone, send later')}`}
      </button>
    </div>
  )
}

function MicButton({ mic, onToggle }) {
  const { t, lang } = useApp()
  const scale = 1 + mic.level * 0.32
  return (
    <div className="center" style={{ padding: '10px 0 4px' }}>
      <button
        onClick={onToggle}
        aria-label={mic.listening ? t('रोकिए', 'Stop') : t('बोलिए', 'Speak')}
        style={{
          width: 104, height: 104, borderRadius: '50%', border: 0,
          background: mic.listening
            ? 'linear-gradient(150deg, var(--madder) 0%, var(--madder-dark) 100%)'
            : 'linear-gradient(150deg, var(--ink) 0%, var(--ink-2) 100%)',
          color: '#fff', fontSize: 'calc(38px * var(--font-scale))',
          boxShadow: mic.listening
            ? `0 0 0 ${8 + mic.level * 26}px rgba(176,57,43,${0.1 + mic.level * 0.14})`
            : 'var(--shadow-2)',
          transform: `scale(${mic.listening ? scale : 1})`,
          transition: 'transform 0.09s linear, box-shadow 0.09s linear',
        }}
      >
        {mic.listening ? '⏹' : '🎤'}
      </button>
      <div style={{ fontSize: 'calc(13px * var(--font-scale))', marginTop: 12, fontWeight: 600,
                    color: mic.listening ? 'var(--madder)' : 'var(--muted)' }} lang={lang}>
        {mic.listening ? t('सुन रहा हूँ… बोलते रहिए', 'Listening… keep speaking')
                       : t('माइक दबाकर बोलिए', 'Tap the mic and speak')}
      </div>
      {mic.listening && (
        <div style={{ width: 150, margin: '9px auto 0' }}>
          <Bar value={Math.max(4, mic.level * 100)} tone="var(--madder)" height={5} />
          <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginTop: 5 }} lang={lang}>
            {mic.level > 0.06 ? t('आवाज़ आ रही है ✓', 'Picking up your voice ✓')
                              : t('थोड़ा ज़ोर से बोलिए', 'Speak a little louder')}
          </div>
        </div>
      )}
    </div>
  )
}

/**
 * The panel that answers "why can't it hear me?" precisely.
 * Silence here is what made the old build feel broken.
 */
function MicHelp({ diag, onRecord, recording, onTest }) {
  const { t, lang } = useApp()
  const [open, setOpen] = useState(false)
  if (!diag) return null

  const FIXES = {
    insecure: {
      hi: <>माइक इस पते पर बंद है। ब्राउज़र सिर्फ़ <b>localhost</b> या <b>https://</b> पर माइक देता है।
          आप अभी <code>{diag.origin}</code> पर हैं। पता बदलकर <b>http://localhost:5173</b> कीजिए —
          माइक तुरंत चल जाएगा।</>,
      en: <>The browser blocks the microphone on this address. It only allows it on
          <b> localhost</b> or <b> https://</b>. You are on <code>{diag.origin}</code> —
          open <b>http://localhost:5173</b> instead and the mic will work immediately.</>,
    },
    noapi: {
      hi: <>{diag.browser} में बोलकर लिखने की सुविधा नहीं है। <b>Chrome</b> या <b>Edge</b> में
          खोलिए, या नीचे आवाज़ रिकॉर्ड कीजिए / लिखकर बताइए।</>,
      en: <>{diag.browser} does not support speech-to-text. Open PAVHAN in <b>Chrome</b> or
          <b> Edge</b>, or record audio below / type your description.</>,
    },
    nomedia: {
      hi: <>यह ब्राउज़र माइक तक पहुँचने नहीं देता। Chrome या Edge में खोलिए।</>,
      en: <>This browser does not expose microphone access. Try Chrome or Edge.</>,
    },
    denied: {
      hi: <>आपने पहले माइक की अनुमति मना कर दी थी। पते वाली पट्टी में <b>🔒 ताले</b> के निशान पर
          दबाइए → माइक → अनुमति दीजिए, फिर पन्ना ताज़ा कीजिए।</>,
      en: <>Microphone permission was denied earlier. Click the <b>🔒 lock</b> in the address bar
          → Microphone → Allow, then reload the page.</>,
    },
    nodevice: {
      hi: <>कोई माइक जुड़ा नहीं मिला। हेडफ़ोन या माइक लगाइए और पन्ना ताज़ा कीजिए।</>,
      en: <>No microphone was found. Plug one in (or a headset) and reload the page.</>,
    },
  }

  const fix = diag.blocker ? FIXES[diag.blocker] : null

  return (
    <div
      className="card"
      style={{
        background: fix ? '#fdf6ee' : 'var(--leaf-soft)',
        borderColor: fix ? '#e8d3b4' : '#bcdbd1',
      }}
    >
      <button
        onClick={() => setOpen(!open)}
        style={{ background: 'none', border: 0, padding: 0, width: '100%', textAlign: 'left',
                 fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 700, lineHeight: 1.5 }}
        lang={lang}
      >
        {fix
          ? <>⚠️ {t('माइक अभी नहीं चलेगा — क्यों, यह देखिए', 'The mic will not work here — see why')}</>
          : <>✅ {t('माइक तैयार है', 'Microphone is ready')} · {diag.browser}</>}
        <span style={{ float: 'right', color: 'var(--muted)' }}>{open ? '▾' : '▸'}</span>
      </button>

      {fix && (
        <div style={{ fontSize: 'calc(12.5px * var(--font-scale))', lineHeight: 1.7, marginTop: 9, color: 'var(--ink-soft)' }}
             lang={lang}>
          {lang === 'hi' ? fix.hi : fix.en}
        </div>
      )}

      {open && (
        <div style={{ marginTop: 11, paddingTop: 10, borderTop: '1px solid rgba(0,0,0,0.08)' }}>
          {[
            [t('पता', 'Address'), diag.origin],
            [t('सुरक्षित पता', 'Secure context'), diag.secure ? '✅' : '❌'],
            [t('बोलकर लिखना', 'Speech-to-text API'), diag.hasApi ? '✅' : '❌'],
            [t('माइक की अनुमति', 'Mic permission'), diag.permission],
            [t('माइक जुड़े हैं', 'Input devices'), diag.devices ?? '—'],
            [t('ब्राउज़र', 'Browser'), diag.browser],
          ].map(([label, value]) => (
            <div key={label} className="row-between"
                 style={{ fontSize: 'calc(11.5px * var(--font-scale))', padding: '4px 0' }}>
              <span className="muted" lang={lang}>{label}</span>
              <span className="mono" style={{ fontWeight: 600, maxWidth: '60%',
                                              overflow: 'hidden', textOverflow: 'ellipsis' }}>
                {String(value)}
              </span>
            </div>
          ))}
        </div>
      )}

      {/* Always offered, not only when something is broken. Chrome's speech
          service can fail mid-demo on a venue network, and the artisan should
          never be left with no way to speak. */}
      <div className="row" style={{ gap: 8, marginTop: 10 }}>
        <button className="btn btn-soft btn-sm" style={{ flex: 1 }} onClick={onRecord}>
          {recording ? t('⏹ रोकिए', '⏹ Stop')
                     : t('🎙️ आवाज़ रिकॉर्ड कीजिए', '🎙️ Record audio')}
        </button>
        <button className="btn btn-soft btn-sm" style={{ flex: 1 }} onClick={onTest}>
          🔎 {t('माइक जाँचिए', 'Test my mic')}
        </button>
      </div>
    </div>
  )
}

function CoachCard({ tips }) {
  const { t, lang, sayRaw } = useApp()
  const captured = tips.captured || {}
  const chips = [
    captured.product, captured.materials?.[0], captured.colours?.[0],
    captured.size, captured.weight,
    captured.making_days ? t(`${captured.making_days} दिन`, `${captured.making_days} days`) : null,
    captured.regions?.[0],
  ].filter(Boolean)

  return (
    <div className="card tinted fade-up">
      <div className="row-between" style={{ marginBottom: 8 }}>
        <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
          {t('अब तक समझ आया', 'Understood so far')}
        </div>
        <span className="pill mono">{tips.completeness}%</span>
      </div>
      <Bar value={tips.completeness}
           tone={tips.completeness >= 80 ? 'var(--leaf)' : 'var(--marigold)'} />
      {chips.length > 0 && (
        <div className="row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
          {chips.map((c) => <span key={c} className="pill leaf">✓ {c}</span>)}
        </div>
      )}
      {tips.next_question && (
        <button
          onClick={() => sayRaw(tips.next_question)}
          style={{ marginTop: 11, background: 'none', border: 0, padding: 0, textAlign: 'left',
                   fontSize: 'calc(12.5px * var(--font-scale))', color: 'var(--madder-dark)', fontWeight: 600,
                   lineHeight: 1.5, display: 'flex', gap: 7 }}
          lang={lang}
        >
          <span>🗣️</span><span>{tips.next_question}</span>
        </button>
      )}
    </div>
  )
}

// ===========================================================================
// Step 2 — review
// ===========================================================================
function ReviewStep({ listing, setListing, onNext }) {
  const { t, lang, say, L } = useApp()
  useStepVoice('listing_review', say)
  const set = (key) => (e) => setListing({ ...listing, [key]: e.target.value })
  const meta = listing.ai_meta || {}

  return (
    <div className="page stack">
      <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
        <span className="pill gold">
          ✨ {meta.engine === 'claude-enriched' ? 'Claude' : t('पवन इंजन', 'PAVHAN engine')}
        </span>
        <span className="pill ink">{t('पहचान', 'Identified')} {meta.craft_confidence}%</span>
        <span className="pill">{listing.took_ms?.toFixed?.(0)}ms</span>
      </div>

      <div className="card tinted">
        <div className="row" style={{ gap: 11, alignItems: 'flex-start' }}>
          <ScoreRing value={listing.quality_score} label={t('पूर्णता', 'complete')} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))' }}>{L(listing.craft_type)}</div>
            <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.5, marginTop: 3 }}>
              {(meta.craft_evidence || []).slice(0, 2).join(' · ')}
            </div>
          </div>
        </div>
        {meta.improvement_tips?.length > 0 && (
          <div style={{ marginTop: 11, paddingTop: 10, borderTop: '1px solid var(--line)' }}>
            <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', fontWeight: 700, marginBottom: 6 }} lang={lang}>
              {t('इन्हें जोड़ेंगे तो और बिकेगा', 'Add these to sell more')}
            </div>
            {meta.improvement_tips.slice(0, 3).map((tip) => (
              <div key={tip} className="row" style={{ gap: 7, fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.55,
                   color: 'var(--ink-soft)', alignItems: 'flex-start' }}>
                <span style={{ color: 'var(--marigold)' }}>▸</span><span>{tip}</span>
              </div>
            ))}
          </div>
        )}
      </div>

      <div className="field">
        <label>{t('नाम', 'Product name')}</label>
        <input className="input" value={listing.title} onChange={set('title')} />
      </div>
      <div className="field">
        <label>{t('छोटा विवरण', 'Short description')}</label>
        <textarea className="textarea" rows={2} value={listing.short_description}
                  onChange={set('short_description')} />
      </div>
      <div className="field">
        <label>{t('पूरा विवरण (अंग्रेज़ी)', 'Detailed description (English)')}</label>
        <textarea className="textarea" rows={5} value={listing.detailed_description}
                  onChange={set('detailed_description')} />
      </div>

      {/* The problem statement asks for both languages, and a buyer on a
          government marketplace may search in either. Both are editable. */}
      <div className="card" style={{ background: 'var(--paper-2)' }}>
        <div className="row-between" style={{ marginBottom: 9 }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
            🇮🇳 {t('हिंदी विवरण', 'Hindi listing')}
          </div>
          <span className="pill leaf">{t('अपने आप बना', 'auto-written')}</span>
        </div>
        <div className="field" style={{ marginBottom: 10 }}>
          <label>{t('हिंदी नाम', 'Hindi title')}</label>
          <input className="input" lang="hi" value={listing.title_hi || ''}
                 onChange={set('title_hi')} />
        </div>
        <div className="field" style={{ marginBottom: 10 }}>
          <label>{t('हिंदी में छोटा विवरण', 'Hindi short description')}</label>
          <textarea className="textarea" lang="hi" rows={2}
                    value={listing.short_description_hi || ''}
                    onChange={set('short_description_hi')} />
        </div>
        <div className="field">
          <label>{t('हिंदी में पूरा विवरण', 'Hindi detailed description')}</label>
          <textarea className="textarea" lang="hi" rows={5}
                    value={listing.detailed_description_hi || ''}
                    onChange={set('detailed_description_hi')} />
        </div>
      </div>

      <div className="grid-2">
        {[
          ['material', t('सामग्री', 'Material')], ['technique', t('तकनीक', 'Technique')],
          ['colour', t('रंग', 'Colour')], ['region', t('कहाँ से', 'Origin')],
          ['size', t('नाप', 'Size')], ['weight', t('वज़न', 'Weight')],
        ].map(([key, label]) => (
          <div className="field" key={key}>
            <label>{label}</label>
            <input className="input" value={listing[key] || ''} onChange={set(key)}
                   placeholder={t('— खाली है —', '— not stated —')} />
          </div>
        ))}
      </div>

      <div className="field">
        <label>{t('रख-रखाव', 'Care instructions')}</label>
        <input className="input" value={listing.care || ''} onChange={set('care')} />
      </div>

      {listing.story && (
        <div className="card" style={{ background: 'var(--marigold-soft)', borderColor: '#eccf9e' }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))', marginBottom: 5 }} lang={lang}>
            📖 {t('आपकी कहानी — खरीदार यही दोबारा सुनाते हैं',
                  'Your story — this is what buyers retell')}
          </div>
          <div style={{ fontSize: 'calc(12.5px * var(--font-scale))', lineHeight: 1.65, color: '#5e4413' }}>{listing.story}</div>
        </div>
      )}

      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
        {(listing.tags || []).slice(0, 10).map((tag) => <span key={tag} className="pill">#{tag}</span>)}
      </div>

      <button className="btn btn-primary btn-block" onClick={onNext} style={{ padding: 16 }}>
        {t('ठीक है — अब दाम देखिए', 'Looks right — see the price')} →
      </button>
    </div>
  )
}

// ===========================================================================
// Step 3 — price
// ===========================================================================
function PriceStep({ listing, setListing, onNext }) {
  const { t, lang, say, toast } = useApp()
  const p = listing.pricing_meta || {}
  const [chosen, setChosen] = useState(listing.price)
  const [costs, setCosts] = useState({
    material: '', labour: '', other: '', margin: '',
  })
  const [repricing, setRepricing] = useState(false)
  const [showCosts, setShowCosts] = useState(false)
  useStepVoice('pricing', say)

  const tiers = [
    { key: 'floor', label: t('कम से कम', 'Floor'), value: p.floor,
      note: t('इससे नीचे घाटा', 'Below this you lose') },
    { key: 'recommended', label: t('हमारी सलाह', 'Recommended'), value: p.recommended,
      note: t('सबसे अच्छा संतुलन', 'Best balance') },
    { key: 'premium', label: t('प्रीमियम', 'Premium'), value: p.premium,
      note: t('धीरे बिकेगा', 'Sells slower') },
  ]
  const apply = (value) => { setChosen(value); setListing({ ...listing, price: value }) }
  const warnings = (lang === 'hi' ? p.warnings_hi : p.warnings) || p.warnings || []
  const rationale = (lang === 'hi' ? p.rationale_hi : p.rationale) || []

  /** Re-price using what the artisan actually spent, not a craft-wide average. */
  const repriceWithCosts = async () => {
    const facts = listing.ai_meta?.transcript_facts || {}
    setRepricing(true)
    try {
      const fresh = await recommendPrice({
        craft_key: listing.craft_key,
        craft_type: listing.craft_type,
        complexity: listing.ai_meta?.vision?.complexity ?? 1.3,
        making_days: facts.making_days ?? null,
        making_hours: facts.making_hours ?? null,
        region: listing.region || '',
        quality_score: listing.quality_score,
        gi_tagged: listing.gi_tagged,
        natural_dye: !!facts.natural_dye,
        sustainability_score: listing.sustainability_score ?? 65,
        material_cost: costs.material === '' ? null : Number(costs.material),
        labour_cost: costs.labour === '' ? null : Number(costs.labour),
        other_cost: costs.other === '' ? null : Number(costs.other),
        desired_margin_percent: costs.margin === '' ? null : Number(costs.margin),
      })
      setListing({
        ...listing, pricing_meta: fresh, price: fresh.recommended,
        price_floor: fresh.floor, price_premium: fresh.premium,
      })
      setChosen(fresh.recommended)
      toast(t('आपके ख़र्च के हिसाब से दाम दोबारा निकाला।',
              'Re-priced using your actual costs.'), 'ok')
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setRepricing(false)
    }
  }

  return (
    <div className="page stack">
      <div>
        <h2 style={{ fontSize: 'calc(21px * var(--font-scale))' }} lang={lang}>{t('आपका सही दाम', 'Your fair price')}</h2>
        <p className="section-sub" style={{ marginTop: 6 }} lang={lang}>
          {t('मेहनत, माल और बाज़ार — तीनों जोड़कर।',
             'Your labour, your material and the live market, added up.')}
        </p>
      </div>

      <div className="row" style={{ gap: 9 }}>
        {tiers.map((tier) => (
          <button key={tier.key} onClick={() => apply(tier.value)} className="card"
                  style={{ flex: 1, textAlign: 'center', padding: '13px 7px',
                           borderColor: chosen === tier.value ? 'var(--madder)' : 'var(--line)',
                           borderWidth: chosen === tier.value ? 2 : 1,
                           background: chosen === tier.value ? 'var(--paper-2)' : 'var(--card)' }}>
            <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', fontWeight: 700,
                                            textTransform: 'uppercase' }} lang={lang}>
              {tier.label}
            </div>
            <div className="mono" style={{ fontSize: 'calc(16px * var(--font-scale))', fontWeight: 800, margin: '5px 0 3px' }}>
              {rupees(tier.value)}
            </div>
            <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', lineHeight: 1.35 }} lang={lang}>
              {tier.note}
            </div>
          </button>
        ))}
      </div>

      <div className="card" style={{ background: 'var(--ink)', color: '#fff', border: 0 }}>
        <div className="row-between">
          <div>
            <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', color: '#b0b8d8' }} lang={lang}>
              {t('इस दाम पर आपको मिलेगा', 'You take home')}
            </div>
            <div className="mono" style={{ fontSize: 'calc(26px * var(--font-scale))', fontWeight: 800, marginTop: 3 }}>
              {rupees(chosen * 0.95 - 70)}
            </div>
          </div>
          <ScoreRing value={p.confidence} size={52} label={t('भरोसा', 'confidence')}
                     tone="var(--marigold)" />
        </div>
        {p.effective_hourly_wage > 0 && (
          <div style={{ marginTop: 11, fontSize: 'calc(12px * var(--font-scale))', background: 'rgba(224,146,47,0.16)',
                        color: 'var(--marigold)', padding: '8px 11px', borderRadius: 10,
                        lineHeight: 1.5, fontWeight: 600 }} lang={lang}>
            {t(`यानी आपकी मेहनत के ₹${Math.round(p.effective_hourly_wage)} प्रति घंटे।`,
               `That works out to ₹${Math.round(p.effective_hourly_wage)} an hour for your work.`)}
          </div>
        )}
      </div>

      <MarketModelCard pricing={p} />

      {/* The artisan's own costs. A craft-wide average is the category's
          price, not theirs — and the problem statement names raw material
          cost explicitly. */}
      <div className="card">
        <button
          onClick={() => setShowCosts(!showCosts)}
          style={{ background: 'none', border: 0, padding: 0, width: '100%',
                   textAlign: 'left', fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }}
          lang={lang}
        >
          {showCosts ? '▾' : '▸'} 🧮 {t('अपना असली ख़र्च भरिए (दाम और सटीक होगा)',
                                         'Enter your real costs for a sharper price')}
        </button>
        {showCosts && (
          <div className="fade-up" style={{ marginTop: 12 }}>
            <div className="grid-2">
              {[
                ['material', t('कच्चा माल ₹', 'Raw material ₹'), t('जैसे 600', 'e.g. 600')],
                ['labour', t('मज़दूरी ₹', 'Labour ₹'), t('जैसे 900', 'e.g. 900')],
                ['other', t('अन्य ख़र्च ₹', 'Other costs ₹'), t('जैसे 100', 'e.g. 100')],
                ['margin', t('मुनाफ़ा %', 'Your margin %'), t('जैसे 25', 'e.g. 25')],
              ].map(([key, label, ph]) => (
                <div className="field" key={key}>
                  <label>{label}</label>
                  <input
                    className="input mono" inputMode="decimal" placeholder={ph}
                    value={costs[key]}
                    onChange={(e) => setCosts({
                      ...costs, [key]: e.target.value.replace(/[^\d.]/g, ''),
                    })}
                  />
                </div>
              ))}
            </div>
            <button className="btn btn-ink btn-block" style={{ marginTop: 12 }}
                    onClick={repriceWithCosts} disabled={repricing}>
              {repricing ? <span className="spinner" />
                         : t('इन ख़र्चों से दाम निकालिए', 'Re-price with these costs')}
            </button>
            <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.55, marginTop: 9 }}
                 lang={lang}>
              {t('जो खाली छोड़ेंगे उसके लिए आपके शिल्प का औसत लिया जाएगा।',
                 'Anything you leave blank falls back to the average for your craft.')}
            </div>
          </div>
        )}
      </div>

      {warnings.map((w) => (
        <div key={w} className="card" style={{ background: 'var(--marigold-soft)',
                                               borderColor: 'var(--line)',
                                               fontSize: 'calc(12.5px * var(--font-scale))', lineHeight: 1.6 }} lang={lang}>
          ⚠️ {w}
        </div>
      ))}

      <div className="card">
        <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
          🧾 {t('पूरा हिसाब — किसी को भी दिखाइए', 'The full arithmetic — show it to anyone')}
        </div>
        {(p.breakdown || []).map((line) => {
          const note = lang === 'hi' ? line.note_hi || line.note : line.note
          return (
            <div key={line.label} style={{ marginBottom: 9 }}>
              <div className="row-between" style={{ fontSize: 'calc(13px * var(--font-scale))' }}>
                <span style={{ fontWeight: 600 }} lang={lang}>
                  {lang === 'hi' ? line.label_hi : line.label}
                </span>
                <span className="mono" style={{ fontWeight: 700 }}>{rupees(line.amount)}</span>
              </div>
              {note && (
                <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.45, marginTop: 2 }}
                     lang={lang}>
                  {note}
                </div>
              )}
            </div>
          )
        })}
        <div className="divider" />
        <div className="row-between" style={{ fontSize: 'calc(14px * var(--font-scale))', fontWeight: 800 }}>
          <span lang={lang}>{t('कुल सलाह', 'Recommended')}</span>
          <span className="mono">{rupees(p.recommended)}</span>
        </div>
      </div>

      {p.comparables?.length > 0 && (
        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
            📊 {t('और जगह यही चीज़ किस दाम पर', 'What the same piece fetches elsewhere')}
          </div>
          {p.comparables.map((c) => (
            <div key={c.label} style={{ marginBottom: 10 }}>
              <div className="row-between" style={{ fontSize: 'calc(12.5px * var(--font-scale))', marginBottom: 4 }}>
                <span lang={lang}>{lang === 'hi' ? c.label_hi || c.label : c.label}</span>
                <span className="mono" style={{ fontWeight: 700 }}>{rupees(c.price)}</span>
              </div>
              <Bar value={Math.min(100, (c.price / Math.max(...p.comparables.map((x) => x.price))) * 100)}
                   tone={c.delta_percent < 0 ? 'var(--madder)' : 'var(--leaf)'} height={5} />
            </div>
          ))}
        </div>
      )}

      {rationale.length > 0 && (
        <div className="card tinted">
          <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 8 }} lang={lang}>
            {t('यह दाम कैसे निकला', 'How we got here')}
          </div>
          {rationale.map((line) => (
            <div key={line} className="row" style={{ gap: 7, fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.6,
                 marginBottom: 6, alignItems: 'flex-start' }}>
              <span style={{ color: 'var(--leaf)' }}>✓</span><span lang={lang}>{line}</span>
            </div>
          ))}
        </div>
      )}

      <button className="btn btn-primary btn-block" onClick={onNext} style={{ padding: 16 }}>
        {rupees(chosen)} {t('पर आगे बढ़िए', '— continue')} →
      </button>
    </div>
  )
}

/** The trained model's view, next to the cost-plus one. */
function MarketModelCard({ pricing }) {
  const { t, lang } = useApp()
  const ml = pricing?.ml
  const rec = pricing?.reconciliation
  const [open, setOpen] = useState(false)
  if (!ml) return null

  return (
    <div className="card">
      <div className="row-between" style={{ marginBottom: 10 }}>
        <div>
          <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
            🤖 {t('बाज़ार मॉडल का अनुमान', 'What the market model predicts')}
          </div>
          <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', marginTop: 2 }}>
            {ml.model} · {t('औसत चूक', 'median error')} {ml.median_error_percent}%
          </div>
        </div>
        <span className="pill leaf mono">{ml.confidence}%</span>
      </div>

      <div className="row" style={{ gap: 12, alignItems: 'flex-end' }}>
        <div>
          <div className="mono" style={{ fontSize: 'calc(22px * var(--font-scale))', fontWeight: 800 }}>{rupees(ml.price)}</div>
          <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))' }}>
            {rupees(ml.low)} – {rupees(ml.high)}
          </div>
        </div>
        <div className="spacer" />
        <div style={{ textAlign: 'right' }}>
          <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', textTransform: 'uppercase',
                                          fontWeight: 700 }} lang={lang}>
            {t('लागत से', 'from costs')}
          </div>
          <div className="mono" style={{ fontSize: 'calc(15px * var(--font-scale))', fontWeight: 700 }}>
            {rupees(pricing.recommended)}
          </div>
        </div>
      </div>

      {rec && (
        <div style={{ marginTop: 11, padding: '9px 11px', borderRadius: 10,
                      background: rec.source === 'blended' ? 'var(--leaf-soft)' : 'var(--marigold-soft)',
                      fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.6 }} lang={lang}>
          {lang === 'hi' ? rec.note_hi : rec.note}
        </div>
      )}

      {ml.drivers?.length > 0 && (
        <>
          <button onClick={() => setOpen(!open)} className="btn btn-sm"
                  style={{ background: 'none', padding: '9px 0 0', fontSize: 'calc(12px * var(--font-scale))',
                           color: 'var(--indigo)', fontWeight: 700 }} lang={lang}>
            {open ? '▾' : '▸'} {t('इस दाम को किसने बढ़ाया-घटाया', 'What moved this price')}
          </button>
          {open && (
            <div className="fade-up" style={{ marginTop: 8 }}>
              {ml.drivers.map((d) => (
                <div key={d.feature} style={{ marginBottom: 8 }}>
                  <div className="row-between" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginBottom: 3 }}>
                    <span style={{ fontWeight: 600 }} lang={lang}>
                      {lang === 'hi' ? d.label_hi : d.label}
                    </span>
                    <span className="mono" style={{ fontWeight: 700,
                          color: d.direction === 'up' ? 'var(--leaf)' : 'var(--madder)' }}>
                      {d.direction === 'up' ? '+' : '−'}{rupees(Math.abs(d.delta))}
                    </span>
                  </div>
                  <Bar value={Math.min(100, Math.abs(d.percent))}
                       tone={d.direction === 'up' ? 'var(--leaf)' : 'var(--madder)'} height={4} />
                </div>
              ))}
              <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 8 }}
                   lang={lang}>
                {t('यह इसी कृति के लिए है — हर सामान के लिए अलग होता है।',
                   'Measured for this piece specifically, not a generic chart.')}
              </div>
            </div>
          )}
        </>
      )}
    </div>
  )
}

// ===========================================================================
// Step 4 — publish and match buyers
// ===========================================================================
function PublishStep({ listing, saved, setSaved, matches, setMatches, onDone }) {
  const { t, lang, say, sayRaw, toast, user, setUser, P } = useApp()
  const [busy, setBusy] = useState(false)
  const [sent, setSent] = useState({})
  const started = useRef(false)
  useStepVoice('buyer_match', say)

  const publish = useCallback(async () => {
    setBusy(true)
    try {
      let artisanId = user?.id
      if (!artisanId) {
        const artisans = await listUsers('artisan')
        artisanId = artisans[0]?.id
        if (artisans[0]) setUser(artisans[0])
      }
      const payload = {
        title: listing.title,
        short_description: listing.short_description,
        detailed_description: listing.detailed_description,
        story: listing.story,
        title_hi: listing.title_hi || '',
        short_description_hi: listing.short_description_hi || '',
        detailed_description_hi: listing.detailed_description_hi || '',
        story_hi: listing.story_hi || '',
        care_hi: listing.care_hi || '',
        craft_type: listing.craft_type,
        category: listing.category,
        material: listing.material,
        colour: listing.colour,
        region: listing.region,
        size: listing.size,
        weight: listing.weight,
        care: listing.care,
        technique: listing.technique,
        price: listing.price,
        price_floor: listing.price_floor,
        price_premium: listing.price_premium,
        quality_score: listing.quality_score,
        sustainability_score: listing.sustainability_score,
        gi_tagged: listing.gi_tagged,
        tags: listing.tags,
        keywords: listing.keywords,
        images: listing.images,
        palette: listing.palette,
        ai_meta: listing.ai_meta,
        pricing_meta: listing.pricing_meta,
        lead_time_days: listing.lead_time_days,
        moq: listing.moq || 1,
        stock: 5,
        artisan_id: artisanId,
      }
      const product = await createProduct(payload)
      setSaved(product)
      const m = await matchBuyers(product.id, { limit: 8 })
      setMatches(m)
      sayRaw(t(`आपका सामान डल गया। ${m.summary.strong_matches} खरीदार इससे अच्छी तरह मेल खाते हैं।`,
               `Your listing is live. ${m.summary.strong_matches} buyers are a strong match.`))
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setBusy(false)
    }
  }, [listing]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => {
    if (started.current || saved) return
    started.current = true
    publish()
  }, []) // eslint-disable-line react-hooks/exhaustive-deps

  const enquire = async (match) => {
    try {
      await sendEnquiry({
        product_id: saved.id, buyer_id: match.buyer_id,
        quantity: match.suggested_quantity, message: match.pitch,
      })
      setSent((s) => ({ ...s, [match.buyer_id]: true }))
      toast(t(`${match.name} को संदेश भेज दिया।`, `Message sent to ${match.name}.`), 'ok')
    } catch (err) {
      toast(err.message, 'err')
    }
  }

  if (busy || !matches) {
    return (
      <div className="page center" style={{ paddingTop: 60 }}>
        <div className="spinner dark" style={{ margin: '0 auto 14px' }} />
        <div style={{ fontSize: 'calc(14px * var(--font-scale))', fontWeight: 600 }} lang={lang}>
          {t('खरीदार ढूँढे जा रहे हैं…', 'Finding buyers for this piece…')}
        </div>
        <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 6 }} lang={lang}>
          {t('हर खरीदार को सात बातों पर परखा जा रहा है।', 'Scoring every buyer on seven signals.')}
        </div>
      </div>
    )
  }

  return (
    <div className="page stack">
      <div className="card" style={{ background: 'var(--leaf-soft)', borderColor: '#bcdbd1' }}>
        <div className="row" style={{ gap: 10 }}>
          <div style={{ fontSize: 'calc(26px * var(--font-scale))' }}>✅</div>
          <div>
            <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))' }} lang={lang}>
              {t('आपका सामान अब सबको दिख रहा है', 'Your listing is live')}
            </div>
            <div lang={lang} style={{ fontSize: 'calc(12px * var(--font-scale))', color: '#145244', marginTop: 2 }}>
              {P(saved, 'title')}
            </div>
          </div>
        </div>
      </div>

      <div className="card tinted">
        <div className="row" style={{ gap: 16 }}>
          {[
            [matches.summary.matches_returned, t('मेल खाते', 'matches')],
            [matches.summary.strong_matches, t('पक्के', 'strong')],
            [rupees(matches.summary.total_opportunity), t('कुल मौका', 'opportunity')],
          ].map(([n, label]) => (
            <div key={label} style={{ flex: 1 }}>
              <div className="mono" style={{ fontSize: 'calc(16px * var(--font-scale))', fontWeight: 800 }}>{n}</div>
              <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase' }}
                   lang={lang}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      <div className="section-title" lang={lang}>
        {t('ये खरीदार आपके सामान से मेल खाते हैं', 'Buyers matched to this piece')}
      </div>

      {matches.matches.map((m) => (
        <BuyerMatchCard key={m.buyer_id} match={m} sent={sent[m.buyer_id]}
                        onEnquire={() => enquire(m)} />
      ))}

      <button className="btn btn-ink btn-block" onClick={onDone} style={{ padding: 15 }}>
        {t('हो गया', 'Done')} →
      </button>
    </div>
  )
}

// ===========================================================================
// Step 5 — done
// ===========================================================================
function DoneStep({ product, onRestart }) {
  const { t, lang, say } = useApp()
  const navigate = useNavigate()
  useStepVoice('published', say)
  return (
    <div className="page center" style={{ paddingTop: 46 }}>
      <div style={{ fontSize: 'calc(58px * var(--font-scale))', animation: 'floaty 3s ease-in-out infinite' }}>🎉</div>
      <h2 style={{ fontSize: 'calc(22px * var(--font-scale))', margin: '14px 0 8px' }} lang={lang}>{t('शाबाश!', 'Well done!')}</h2>
      <p className="muted" style={{ fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.65, marginBottom: 22 }} lang={lang}>
        {t('आपका सामान पूरे भारत के खरीदारों को दिख रहा है। पूछताछ आने पर हम बता देंगे।',
           'Your piece is visible to buyers across India. We will tell you the moment an enquiry arrives.')}
      </p>
      <div className="stack">
        {product && (
          <button className="btn btn-soft btn-block" onClick={() => navigate(`/product/${product.id}`)}>
            {t('अपना सामान देखिए', 'View my listing')}
          </button>
        )}
        <button className="btn btn-primary btn-block" onClick={onRestart}>
          🎤 {t('एक और डालिए', 'Add another')}
        </button>
        <button className="btn btn-ghost btn-block" onClick={() => navigate('/artisan')}>
          {t('घर वापस', 'Back home')}
        </button>
      </div>
    </div>
  )
}

// ===========================================================================
// Shared buyer card (also used by the standalone buyer-matching screen)
// ===========================================================================
export function BuyerMatchCard({ match, sent, onEnquire }) {
  const { t, lang, sayRaw, L } = useApp()
  const [open, setOpen] = useState(false)
  const tone = match.score >= 82 ? 'var(--leaf)' : match.score >= 68 ? 'var(--marigold)' : 'var(--muted)'
  const gaps = (lang === 'hi' ? match.gaps_hi : match.gaps) || match.gaps || []

  return (
    <div className="card fade-up">
      <div className="row" style={{ gap: 11, alignItems: 'flex-start' }}>
        <div style={{ width: 44, height: 44, borderRadius: 13, background: 'var(--paper-2)',
                      display: 'grid', placeItems: 'center', fontSize: 'calc(21px * var(--font-scale))', flexShrink: 0 }}>
          {match.logo}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row-between">
            <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))' }}>{match.name}</div>
            <span className="pill mono" style={{ background: `${tone}1a`, color: tone,
                                                 borderColor: `${tone}44` }}>
              {match.score}
            </span>
          </div>
          <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 2 }}>
            {L(match.org_type)} · {L(match.city)}, {L(match.country)}
          </div>
          <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', color: tone, fontWeight: 700, marginTop: 4 }} lang={lang}>
            {lang === 'hi' ? match.fit_label_hi || match.fit_label : match.fit_label}
          </div>
        </div>
      </div>

      <div className="row" style={{ gap: 8, marginTop: 11, padding: '9px 11px',
                                    background: 'var(--paper-2)', borderRadius: 11, flexWrap: 'wrap' }}>
        {[
          [t('मात्रा', 'Quantity'), match.suggested_quantity, 1, 'inherit'],
          [t('प्रति पीस', 'Unit'), rupees(match.suggested_unit_price), 1, 'inherit'],
          [t('कुल', 'Order value'), rupees(match.estimated_order_value), 1.2, 'var(--leaf)'],
        ].map(([label, value, flex, colour]) => (
          <div key={label} style={{ flex }}>
            <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase',
                                            fontWeight: 700 }} lang={lang}>{label}</div>
            <div className="mono" style={{ fontSize: 'calc(13.5px * var(--font-scale))', fontWeight: 700, color: colour }}>
              {value}
            </div>
          </div>
        ))}
      </div>

      <button onClick={() => setOpen(!open)} className="btn btn-sm"
              style={{ background: 'none', padding: '9px 0 0', fontSize: 'calc(12px * var(--font-scale))',
                       color: 'var(--indigo)', fontWeight: 700 }} lang={lang}>
        {open ? '▾' : '▸'} {t('यह मेल क्यों खाता है', 'Why this is a match')}
      </button>

      {open && (
        <div className="fade-up" style={{ marginTop: 8 }}>
          {match.factors.map((f) => (
            <div key={f.label} style={{ marginBottom: 9 }}>
              <div className="row-between" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginBottom: 3 }}>
                <span style={{ fontWeight: 600 }} lang={lang}>
                  {lang === 'hi' ? f.label_hi || f.label : f.label}
                </span>
                <span className="mono muted">{Math.round(f.score * 100)}%</span>
              </div>
              <Bar value={f.score * 100} height={4}
                   tone={f.score > 0.7 ? 'var(--leaf)' : f.score > 0.4 ? 'var(--marigold)' : 'var(--madder)'} />
              <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.45, marginTop: 3 }}
                   lang={lang}>
                {lang === 'hi' ? f.detail_hi || f.detail : f.detail}
              </div>
            </div>
          ))}
          {gaps.length > 0 && (
            <div style={{ background: '#fdf6ee', border: '1px solid #e8d3b4', borderRadius: 10,
                          padding: '8px 10px', fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.5, marginTop: 6 }}
                 lang={lang}>
              <strong>{t('ध्यान दीजिए: ', 'Watch out: ')}</strong>{gaps.join('. ')}
            </div>
          )}
          <div style={{ marginTop: 10, padding: '10px 11px', background: 'var(--marigold-soft)',
                        borderRadius: 11, fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.6, color: '#5e4413' }}
               lang={lang}>
            <div style={{ fontWeight: 700, marginBottom: 4 }}>
              💬 {t('आपके लिए लिखा हुआ संदेश', 'Your message, already written')}
            </div>
            {lang === 'hi' ? match.pitch_hi : match.pitch}
            <button className="btn btn-sm btn-soft" style={{ marginTop: 8 }}
                    onClick={() => sayRaw(lang === 'hi' ? match.pitch_hi : match.pitch)}>
              🔊 {t('सुनिए', 'Read it to me')}
            </button>
          </div>
        </div>
      )}

      {onEnquire && (
        <button className={`btn btn-block btn-sm ${sent ? 'btn-soft' : 'btn-gold'}`}
                style={{ marginTop: 11 }} onClick={onEnquire} disabled={sent}>
          {sent ? `✓ ${t('भेज दिया', 'Sent')}` : `📨 ${t('पूछताछ भेजिए', 'Send enquiry')}`}
        </button>
      )}
    </div>
  )
}

// ===========================================================================
// The flow itself — holds the state the steps read and write.
// ===========================================================================
export default function AddProduct() {
  const navigate = useNavigate()
  const { t, lang, sayRaw, toast } = useApp()
  const [step, setStep] = useState(0)

  const [imageId, setImageId] = useState(null)
  const [studio, setStudio] = useState(null)      // {before_url, after_url, report}
  const [rawFile, setRawFile] = useState(null)
  const [backdrop, setBackdrop] = useState('white')
  const [vision, setVision] = useState(null)
  const [analysing, setAnalysing] = useState(false)
  const [transcript, setTranscript] = useState('')
  // Separate from the interface language on purpose — see LanguagePicker.
  const [spokenLang, setSpokenLang] = useState(lang)
  const [listing, setListing] = useState(null)
  const [saved, setSaved] = useState(null)
  const [matches, setMatches] = useState(null)

  const steps = [
    t('फोटो', 'Photo'), t('बोलिए', 'Speak'), t('जाँचिए', 'Review'),
    t('दाम', 'Price'), t('खरीदार', 'Buyers'), t('हो गया', 'Done'),
  ]

  const goto = (n) => { setStep(n); document.querySelector('.app-body')?.scrollTo({ top: 0 }) }

  /** Run the photograph through the studio, then read the CLEANED image.
   *  Measuring colour through a tungsten cast describes the room, not the
   *  product, so the catalogue engine gets the corrected picture. */
  const runStudio = async (file, background = backdrop) => {
    if (!file) return
    setAnalysing(true)
    setRawFile(file)
    if (!navigator.onLine) {
      // No signal. The Product Studio runs on the server, so there is nothing
      // to enhance with — but the photograph itself is the artisan's work and
      // is kept. It goes to the outbox with the voice note and is processed in
      // full when the connection returns.
      setStudio(null); setImageId(null); setVision(null); setAnalysing(false)
      toast(t('सिग्नल नहीं है — फोटो रख ली है, बाद में भेज देंगे।',
              'No signal — the photo is saved and will be sent later.'), 'warn', 4200)
      return
    }
    try {
      const res = await enhancePhoto(file, background)
      setStudio(res)
      setImageId(res.image_id)
      setVision(res.vision)
      const spoken = res.report.background_removed
        ? t('फोटो साफ़ कर दी — बैकग्राउंड हटाकर रोशनी ठीक कर दी है।',
             'Photo cleaned up — background removed and the lighting corrected.')
        : (lang === 'hi' ? res.report.steps.find((x) => x.key === 'background')?.detail_hi
                         : res.report.steps.find((x) => x.key === 'background')?.detail)
      if (spoken) sayRaw(spoken)
    } catch (err) {
      toast(err.message, 'err')
      setStudio(null)
    } finally {
      setAnalysing(false)
    }
  }

  const changeBackdrop = async (next) => {
    setBackdrop(next)
    if (rawFile) await runStudio(rawFile, next)
  }

  const restart = () => {
    setImageId(null); setStudio(null); setRawFile(null); setVision(null)
    setTranscript(''); setListing(null); setSaved(null); setMatches(null)
    goto(0)
  }

  return (
    <>
      <TopBar
        title={t('बोलकर सामान डालिए', 'Voice Cataloguer')}
        subtitle={`${t('चरण', 'Step')} ${step + 1}/${steps.length}`}
        back
        onBack={() => (step === 0 ? navigate(-1) : goto(step - 1))}
      />
      <div className="app-body no-nav">
        <Stepper steps={steps} current={step} />

        {step === 0 && (
          <PhotoStep studio={studio} working={analysing} backdrop={backdrop}
                     setBackdrop={changeBackdrop} onPick={runStudio}
                     onNext={() => goto(1)} />
        )}
        {step === 1 && (
          <VoiceStep imageId={imageId} rawFile={rawFile}
                     text={transcript} setText={setTranscript}
                     spokenLang={spokenLang} setSpokenLang={setSpokenLang}
                     onGenerated={(data) => { setListing(data); goto(2) }}
                     onQueued={() => navigate('/outbox')} />
        )}
        {step === 2 && listing && (
          <ReviewStep listing={listing} setListing={setListing} onNext={() => goto(3)} />
        )}
        {step === 3 && listing && (
          <PriceStep listing={listing} setListing={setListing} onNext={() => goto(4)} />
        )}
        {step === 4 && listing && (
          <PublishStep listing={listing} saved={saved} setSaved={setSaved}
                       matches={matches} setMatches={setMatches} onDone={() => goto(5)} />
        )}
        {step === 5 && <DoneStep product={saved} onRestart={restart} />}
      </div>
      <Toasts />
      <VoiceOrb script={STEP_SCRIPTS[step]} />
    </>
  )
}
