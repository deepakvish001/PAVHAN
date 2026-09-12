import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { TopBar, Toasts } from '../components/Shell'
import { Bar, Money, ScoreRing, Stepper, VoiceOrb, rupees } from '../components/ui'
import useSpeechRecognition from '../hooks/useSpeechRecognition'
import {
  analyzeImage, coach, createProduct, generateListing, listUsers,
  matchBuyers, sendEnquiry, transcribeAudio,
} from '../api/client'

const SAMPLES = {
  hi: [
    'यह बनारसी हथकरघा रेशमी साड़ी है। इसे हमने हाथ से बुना है। इसमें लाल और सुनहरी ज़री का काम है। वज़न लगभग 450 ग्राम और लंबाई साढ़े पाँच मीटर है। बनाने में बारह दिन लगे। केवल ड्राई क्लीन।',
    'मैंने मिट्टी का दीया बनाया है, रंग भूरा और लाल है, वज़न दो सौ ग्राम, चार इंच का है, बनाने में दो दिन लगे, मैं बांकुड़ा से हूँ, प्राकृतिक रंग लगाए हैं।',
    'यह जयपुर की ब्लू पॉटरी का गुलदस्ता है, नीला और सफ़ेद रंग, सिरेमिक का बना है, आठ सौ ग्राम, नौ इंच ऊँचा, तीन दिन लगे।',
  ],
  en: [
    'This is a handwoven Banarasi silk saree. We wove it by hand. It has red and golden zari work. Weight is around 450 gram and length is 5.5 metre. It took twelve days to make. Dry clean only.',
    'I made a terracotta diya from clay, brown and red colour, 200 gram, four inch, took two days, I am from Bankura, used natural colours.',
    'This is a Jaipur blue pottery vase, blue and white, made of ceramic, 800 gram, nine inch tall, took three days.',
  ],
}

export default function AddProduct() {
  const navigate = useNavigate()
  const { t, lang, say, sayRaw, toast, user, setUser } = useApp()
  const [step, setStep] = useState(0)

  // step state
  const [imageId, setImageId] = useState(null)
  const [imageUrl, setImageUrl] = useState(null)
  const [vision, setVision] = useState(null)
  const [analysing, setAnalysing] = useState(false)
  const [listing, setListing] = useState(null)
  const [generating, setGenerating] = useState(false)
  const [saved, setSaved] = useState(null)
  const [matches, setMatches] = useState(null)

  const steps = [
    t('फोटो', 'Photo'), t('बोलिए', 'Speak'), t('जाँचिए', 'Review'),
    t('दाम', 'Price'), t('खरीदार', 'Buyers'), t('हो गया', 'Done'),
  ]

  const goto = (n) => { setStep(n); document.querySelector('.app-body')?.scrollTo({ top: 0 }) }

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
          <PhotoStep
            {...{ imageUrl, vision, analysing, setAnalysing, setImageId, setImageUrl, setVision }}
            onNext={() => goto(1)}
          />
        )}
        {step === 1 && (
          <VoiceStep
            imageId={imageId}
            onGenerated={(data) => { setListing(data); goto(2) }}
            generating={generating}
            setGenerating={setGenerating}
          />
        )}
        {step === 2 && listing && (
          <ReviewStep listing={listing} setListing={setListing} onNext={() => goto(3)} />
        )}
        {step === 3 && listing && (
          <PriceStep listing={listing} setListing={setListing} onNext={() => goto(4)} />
        )}
        {step === 4 && listing && (
          <PublishStep
            listing={listing}
            saved={saved}
            setSaved={setSaved}
            matches={matches}
            setMatches={setMatches}
            onDone={() => goto(5)}
          />
        )}
        {step === 5 && <DoneStep product={saved} />}
      </div>
      <Toasts />
      <VoiceOrb
        script={['capture_photo', 'voice_record', 'listing_review', 'pricing', 'buyer_match', 'published'][step]}
        fields={{ hours: listing?.pricing_meta?.breakdown?.[1]?.amount ? '' : '' }}
      />
    </>
  )

  // ---------------------------------------------------------------- step 0
  function PhotoStep({ imageUrl, vision, analysing, setAnalysing, setImageId, setImageUrl, setVision, onNext }) {
    const fileRef = useRef(null)
    const cameraRef = useRef(null)
    useVoiceOnce('capture_photo')

    const handle = async (file) => {
      if (!file) return
      setAnalysing(true)
      setImageUrl(URL.createObjectURL(file))
      try {
        const res = await analyzeImage(file)
        setImageId(res.image_id)
        setVision(res.vision)
        const tips = lang === 'hi' ? res.vision.photo_tips_hi : res.vision.photo_tips
        const tip = tips?.[0] || res.vision.photo_tips?.[0]
        if (tip) sayRaw(t(`फोटो देख ली। ${tip}`, `I have looked at your photo. ${tip}`))
      } catch (err) {
        toast(err.message, 'err')
        setImageUrl(null)
      } finally {
        setAnalysing(false)
      }
    }

    return (
      <div className="page stack">
        <div>
          <h2 style={{ fontSize: 21 }} lang={lang}>
            {t('पहले सामान की फोटो लीजिए', 'First, photograph your piece')}
          </h2>
          <p className="section-sub" style={{ marginTop: 6 }} lang={lang}>
            {t('दिन की रोशनी में, सादे कपड़े पर, पूरा सामान फ्रेम में।',
               'Daylight, plain cloth behind it, the whole piece inside the frame.')}
          </p>
        </div>

        <div
          className="card flush"
          style={{
            minHeight: 210, display: 'grid', placeItems: 'center',
            background: imageUrl ? '#000' : 'var(--paper-2)', position: 'relative',
            borderStyle: imageUrl ? 'solid' : 'dashed', borderWidth: imageUrl ? 1 : 2,
          }}
        >
          {imageUrl ? (
            <>
              <img
                src={imageUrl}
                alt=""
                style={{ width: '100%', maxHeight: 300, objectFit: 'contain', display: 'block' }}
              />
              {analysing && (
                <div
                  style={{
                    position: 'absolute', inset: 0, background: 'rgba(22,27,51,0.62)',
                    display: 'grid', placeItems: 'center', color: '#fff',
                  }}
                >
                  <div className="center">
                    <div className="spinner" style={{ margin: '0 auto 10px' }} />
                    <div style={{ fontSize: 13 }} lang={lang}>
                      {t('फोटो पढ़ी जा रही है…', 'Reading your photo…')}
                    </div>
                  </div>
                </div>
              )}
            </>
          ) : (
            <div className="center muted" style={{ padding: 30 }}>
              <div style={{ fontSize: 40, marginBottom: 8 }}>📷</div>
              <div style={{ fontSize: 13 }} lang={lang}>
                {t('अभी कोई फोटो नहीं', 'No photo yet')}
              </div>
            </div>
          )}
        </div>

        <input
          ref={cameraRef} type="file" accept="image/*" capture="environment"
          hidden onChange={(e) => handle(e.target.files?.[0])}
        />
        <input
          ref={fileRef} type="file" accept="image/*"
          hidden onChange={(e) => handle(e.target.files?.[0])}
        />

        <div className="grid-2">
          <button className="btn btn-ink" onClick={() => cameraRef.current?.click()}>
            📷 {t('कैमरा', 'Camera')}
          </button>
          <button className="btn btn-soft" onClick={() => fileRef.current?.click()}>
            🖼️ {t('गैलरी', 'Gallery')}
          </button>
        </div>

        {vision && <PhotoReport vision={vision} />}

        <button
          className="btn btn-primary btn-block"
          disabled={analysing}
          onClick={onNext}
          style={{ marginTop: 4 }}
        >
          {imageUrl
            ? t('आगे — अब बोलिए', 'Next — now speak')
            : t('फोटो के बिना आगे बढ़िए', 'Continue without a photo')}
        </button>
        <p className="center muted" style={{ fontSize: 11, lineHeight: 1.55 }} lang={lang}>
          {t('फोटो से रंग, बनावट और बारीकी अपने आप पढ़ी जाती है — इसी से दाम तय होता है।',
             "The photo's colour, texture and intricacy are measured automatically — they feed your price.")}
        </p>
      </div>
    )
  }

  function PhotoReport({ vision }) {
    return (
      <div className="card fade-up">
        <div className="row" style={{ gap: 12, alignItems: 'flex-start' }}>
          <ScoreRing value={vision.photo_quality} label={t('फोटो', 'photo')} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 13.5, marginBottom: 5 }} lang={lang}>
              {t('फोटो से क्या पढ़ा गया', 'What the photo told us')}
            </div>
            <div className="row" style={{ gap: 5, flexWrap: 'wrap', marginBottom: 8 }}>
              {(vision.palette || []).slice(0, 5).map((c) => (
                <span
                  key={c.hex + c.name}
                  title={`${c.name} · ${Math.round(c.share * 100)}%`}
                  style={{
                    width: 22, height: 22, borderRadius: 7, background: c.hex,
                    border: '1px solid rgba(0,0,0,0.12)',
                  }}
                />
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
        {(vision.photo_tips_hi || vision.photo_tips)?.length > 0 && (
          <div
            style={{
              marginTop: 11, paddingTop: 11, borderTop: '1px solid var(--line)',
              fontSize: 12, lineHeight: 1.6, color: 'var(--ink-soft)',
            }}
          >
            {(lang === 'hi' ? vision.photo_tips_hi : vision.photo_tips).map((tip) => (
              <div key={tip} className="row" style={{ gap: 7, alignItems: 'flex-start' }}>
                <span>{vision.photo_quality >= 85 ? '✅' : '💡'}</span>
                <span>{tip}</span>
              </div>
            ))}
          </div>
        )}
      </div>
    )
  }

  // ---------------------------------------------------------------- step 1
  function VoiceStep({ imageId, onGenerated, generating, setGenerating }) {
    const [text, setText] = useState('')
    const [tips, setTips] = useState(null)
    const [sampleIdx, setSampleIdx] = useState(0)
    const [recorderFallback, setRecorderFallback] = useState(false)
    const mediaRef = useRef(null)
    const chunksRef = useRef([])
    useVoiceOnce('voice_record')

    const mic = useSpeechRecognition({
      lang,
      onFinal: (full) => setText(full),
    })

    // Live coaching: as the artisan speaks, work out what is still missing.
    useEffect(() => {
      const value = text.trim()
      if (value.length < 8) { setTips(null); return undefined }
      const timer = setTimeout(() => {
        coach(value, lang).then(setTips).catch(() => {})
      }, 750)
      return () => clearTimeout(timer)
    }, [text])

    const toggleMic = async () => {
      if (mic.listening) { mic.stop(); return }
      const ok = await mic.start({ reset: !text })
      if (ok) sayRaw(t('मैं सुन रहा हूँ। बोलिए।', 'I am listening. Go ahead.'), { rate: 1.05 })
    }

    // If the browser has no speech recognition at all, record audio instead
    // and let the server transcribe it — the artisan still only has to speak.
    const recordAudio = async () => {
      if (mediaRef.current?.state === 'recording') {
        mediaRef.current.stop()
        return
      }
      try {
        const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
        const rec = new MediaRecorder(stream)
        chunksRef.current = []
        rec.ondataavailable = (e) => chunksRef.current.push(e.data)
        rec.onstop = async () => {
          stream.getTracks().forEach((tr) => tr.stop())
          const blob = new Blob(chunksRef.current, { type: 'audio/webm' })
          try {
            const res = await transcribeAudio(new File([blob], 'note.webm'), lang)
            setText(res.transcript)
          } catch (err) {
            toast(err.message, 'warn')
          }
          setRecorderFallback(false)
        }
        mediaRef.current = rec
        rec.start()
        setRecorderFallback(true)
      } catch {
        toast(t('माइक नहीं मिला।', 'Microphone unavailable.'), 'err')
      }
    }

    const generate = async () => {
      const value = text.trim()
      if (!value && !imageId) {
        toast(t('पहले बोलिए या फोटो डालिए।', 'Speak or add a photo first.'), 'warn')
        return
      }
      mic.stop()
      setGenerating(true)
      try {
        const data = await generateListing({
          transcript: value, image_id: imageId || '', language: lang, use_llm: 'true',
        })
        onGenerated(data)
      } catch (err) {
        toast(err.message, 'err')
      } finally {
        setGenerating(false)
      }
    }

    const useSample = () => {
      const list = SAMPLES[lang] || SAMPLES.en
      const next = list[sampleIdx % list.length]
      setText(next)
      setSampleIdx((i) => i + 1)
      mic.setText(next)
    }

    const live = `${text}${mic.interim ? ` ${mic.interim}` : ''}`.trim()

    return (
      <div className="page stack">
        <div>
          <h2 style={{ fontSize: 21 }} lang={lang}>
            {t('अब बस बोलिए', 'Now just speak')}
          </h2>
          <p className="section-sub" style={{ marginTop: 6 }} lang={lang}>
            {t('अपनी भाषा में बताइए — यह क्या है, किस चीज़ से बना है, कितना बड़ा है, कितने दिन लगे।',
               'In your own language: what it is, what it is made of, how big it is, how long it took.')}
          </p>
        </div>

        <MicButton mic={mic} onToggle={toggleMic} />

        {mic.error && (
          <div
            className="card"
            style={{ borderColor: '#f0cbc6', background: '#fdf4f3', fontSize: 12.5, lineHeight: 1.6 }}
            lang={lang}
          >
            ⚠️ {mic.error}
            {!mic.supported && (
              <button className="btn btn-soft btn-sm btn-block" style={{ marginTop: 10 }} onClick={recordAudio}>
                {recorderFallback
                  ? t('⏹ रिकॉर्डिंग रोकिए', '⏹ Stop recording')
                  : t('🎙️ आवाज़ रिकॉर्ड कीजिए (सर्वर पर लिखा जाएगा)',
                       '🎙️ Record audio instead (transcribed on the server)')}
              </button>
            )}
          </div>
        )}

        <div className="field">
          <div className="row-between">
            <label htmlFor="transcript">
              {t('आपने जो बोला (बदल भी सकते हैं)', 'What you said — editable')}
            </label>
            {live && (
              <button
                className="btn btn-sm btn-soft"
                onClick={() => { setText(''); mic.reset(); setTips(null) }}
              >
                {t('मिटाइए', 'Clear')}
              </button>
            )}
          </div>
          <textarea
            id="transcript"
            className="textarea"
            lang={lang}
            rows={5}
            value={live}
            placeholder={t('माइक दबाइए, या यहाँ सीधे लिख दीजिए…',
                           'Press the mic, or type here directly…')}
            onChange={(e) => { setText(e.target.value); mic.setText(e.target.value) }}
          />
        </div>

        {tips && <CoachCard tips={tips} />}

        <button className="btn btn-soft btn-block btn-sm" onClick={useSample}>
          {t('नमूना भर दीजिए (डेमो के लिए)', 'Fill a sample (for demo)')}
        </button>

        <button
          className="btn btn-primary btn-block"
          onClick={generate}
          disabled={generating}
          style={{ padding: 16 }}
        >
          {generating
            ? <><span className="spinner" /> {t('विवरण बनाया जा रहा है…', 'Writing your listing…')}</>
            : `✨ ${t('मेरा विवरण बनाइए', 'Create my listing')}`}
        </button>
      </div>
    )
  }

  function MicButton({ mic, onToggle }) {
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
            color: '#fff', fontSize: 38,
            boxShadow: mic.listening
              ? `0 0 0 ${8 + mic.level * 26}px rgba(176,57,43,${0.1 + mic.level * 0.14})`
              : 'var(--shadow-2)',
            transform: `scale(${mic.listening ? scale : 1})`,
            transition: 'transform 0.09s linear, box-shadow 0.09s linear',
          }}
        >
          {mic.listening ? '⏹' : '🎤'}
        </button>
        <div
          style={{ fontSize: 13, marginTop: 12, fontWeight: 600, color: mic.listening ? 'var(--madder)' : 'var(--muted)' }}
          lang={lang}
        >
          {mic.listening
            ? t('सुन रहा हूँ… बोलते रहिए', 'Listening… keep speaking')
            : t('माइक दबाकर बोलिए', 'Tap the mic and speak')}
        </div>
        {mic.listening && (
          <div style={{ width: 150, margin: '9px auto 0' }}>
            <Bar value={Math.max(4, mic.level * 100)} tone="var(--madder)" height={5} />
            <div className="muted" style={{ fontSize: 10, marginTop: 5 }} lang={lang}>
              {mic.level > 0.06
                ? t('आवाज़ आ रही है ✓', 'Picking up your voice ✓')
                : t('थोड़ा ज़ोर से बोलिए', 'Speak a little louder')}
            </div>
          </div>
        )}
        {!mic.supported && !mic.error && (
          <div className="muted" style={{ fontSize: 11, marginTop: 8, lineHeight: 1.5 }} lang={lang}>
            {t('इस ब्राउज़र में बोलकर लिखना नहीं चलता — नीचे लिखकर बता दीजिए।',
               'This browser has no speech-to-text — please type below.')}
          </div>
        )}
      </div>
    )
  }

  function CoachCard({ tips }) {
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
          <div style={{ fontWeight: 700, fontSize: 13 }} lang={lang}>
            {t('अब तक समझ आया', 'Understood so far')}
          </div>
          <span className="pill mono">{tips.completeness}%</span>
        </div>
        <Bar
          value={tips.completeness}
          tone={tips.completeness >= 80 ? 'var(--leaf)' : 'var(--marigold)'}
        />
        {chips.length > 0 && (
          <div className="row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 10 }}>
            {chips.map((c) => <span key={c} className="pill leaf">✓ {c}</span>)}
          </div>
        )}
        {tips.next_question && (
          <button
            onClick={() => sayRaw(tips.next_question)}
            style={{
              marginTop: 11, background: 'none', border: 0, padding: 0, textAlign: 'left',
              fontSize: 12.5, color: 'var(--madder-dark)', fontWeight: 600, lineHeight: 1.5,
              display: 'flex', gap: 7,
            }}
            lang={lang}
          >
            <span>🗣️</span><span>{tips.next_question}</span>
          </button>
        )}
      </div>
    )
  }

  // ---------------------------------------------------------------- step 2
  function ReviewStep({ listing, setListing, onNext }) {
    useVoiceOnce('listing_review')
    const set = (key) => (e) => setListing({ ...listing, [key]: e.target.value })
    const meta = listing.ai_meta || {}

    return (
      <div className="page stack">
        <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
          <span className="pill gold">
            ✨ {meta.engine === 'claude-enriched' ? 'Claude' : t('पवन इंजन', 'PAVHAN engine')}
          </span>
          <span className="pill ink">
            {t('पहचान', 'Identified')} {meta.craft_confidence}%
          </span>
          <span className="pill">{listing.took_ms?.toFixed?.(0)}ms</span>
        </div>

        <div className="card tinted">
          <div className="row" style={{ gap: 11, alignItems: 'flex-start' }}>
            <ScoreRing value={listing.quality_score} label={t('पूर्णता', 'complete')} />
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 14 }}>{listing.craft_type}</div>
              <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.5, marginTop: 3 }}>
                {(meta.craft_evidence || []).slice(0, 2).join(' · ')}
              </div>
            </div>
          </div>
          {meta.improvement_tips?.length > 0 && (
            <div style={{ marginTop: 11, paddingTop: 10, borderTop: '1px solid var(--line)' }}>
              <div style={{ fontSize: 11.5, fontWeight: 700, marginBottom: 6 }} lang={lang}>
                {t('इन्हें जोड़ेंगे तो और बिकेगा', 'Add these to sell more')}
              </div>
              {meta.improvement_tips.slice(0, 3).map((tip) => (
                <div
                  key={tip}
                  className="row"
                  style={{ gap: 7, fontSize: 12, lineHeight: 1.55, color: 'var(--ink-soft)', alignItems: 'flex-start' }}
                >
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
          <textarea className="textarea" rows={2} value={listing.short_description} onChange={set('short_description')} />
        </div>
        <div className="field">
          <label>{t('पूरा विवरण', 'Detailed description')}</label>
          <textarea className="textarea" rows={5} value={listing.detailed_description} onChange={set('detailed_description')} />
        </div>

        <div className="grid-2">
          {[
            ['material', t('सामग्री', 'Material')], ['technique', t('तकनीक', 'Technique')],
            ['colour', t('रंग', 'Colour')], ['region', t('कहाँ से', 'Origin')],
            ['size', t('नाप', 'Size')], ['weight', t('वज़न', 'Weight')],
          ].map(([key, label]) => (
            <div className="field" key={key}>
              <label>{label}</label>
              <input
                className="input"
                value={listing[key] || ''}
                onChange={set(key)}
                placeholder={t('— खाली है —', '— not stated —')}
              />
            </div>
          ))}
        </div>

        <div className="field">
          <label>{t('रख-रखाव', 'Care instructions')}</label>
          <input className="input" value={listing.care || ''} onChange={set('care')} />
        </div>

        {listing.story && (
          <div className="card" style={{ background: 'var(--marigold-soft)', borderColor: '#eccf9e' }}>
            <div style={{ fontWeight: 700, fontSize: 12.5, marginBottom: 5 }} lang={lang}>
              📖 {t('आपकी कहानी — खरीदार यही दोबारा सुनाते हैं', 'Your story — this is what buyers retell')}
            </div>
            <div style={{ fontSize: 12.5, lineHeight: 1.65, color: '#5e4413' }}>{listing.story}</div>
          </div>
        )}

        <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
          {(listing.tags || []).slice(0, 10).map((tag) => (
            <span key={tag} className="pill">#{tag}</span>
          ))}
        </div>

        <button className="btn btn-primary btn-block" onClick={onNext} style={{ padding: 16 }}>
          {t('ठीक है — अब दाम देखिए', 'Looks right — see the price')} →
        </button>
      </div>
    )
  }

  // ---------------------------------------------------------------- step 3
  function PriceStep({ listing, setListing, onNext }) {
    const p = listing.pricing_meta || {}
    const [chosen, setChosen] = useState(listing.price)
    useVoiceOnce('pricing')

    const tiers = [
      { key: 'floor', label: t('कम से कम', 'Floor'), value: p.floor, note: t('इससे नीचे घाटा', 'Below this you lose') },
      { key: 'recommended', label: t('हमारी सलाह', 'Recommended'), value: p.recommended, note: t('सबसे अच्छा संतुलन', 'Best balance') },
      { key: 'premium', label: t('प्रीमियम', 'Premium'), value: p.premium, note: t('धीरे बिकेगा', 'Sells slower') },
    ]

    const apply = (value) => {
      setChosen(value)
      setListing({ ...listing, price: value })
    }

    return (
      <div className="page stack">
        <div>
          <h2 style={{ fontSize: 21 }} lang={lang}>{t('आपका सही दाम', 'Your fair price')}</h2>
          <p className="section-sub" style={{ marginTop: 6 }} lang={lang}>
            {t('मेहनत, माल और बाज़ार — तीनों जोड़कर।',
               'Your labour, your material and the live market, added up.')}
          </p>
        </div>

        <div className="row" style={{ gap: 9 }}>
          {tiers.map((tier) => (
            <button
              key={tier.key}
              onClick={() => apply(tier.value)}
              className="card"
              style={{
                flex: 1, textAlign: 'center', padding: '13px 7px',
                borderColor: chosen === tier.value ? 'var(--madder)' : 'var(--line)',
                borderWidth: chosen === tier.value ? 2 : 1,
                background: chosen === tier.value ? '#fff8f7' : '#fff',
              }}
            >
              <div className="muted" style={{ fontSize: 10, fontWeight: 700, textTransform: 'uppercase' }}>
                {tier.label}
              </div>
              <div className="mono" style={{ fontSize: 16, fontWeight: 800, margin: '5px 0 3px' }}>
                {rupees(tier.value)}
              </div>
              <div className="muted" style={{ fontSize: 9.5, lineHeight: 1.35 }}>{tier.note}</div>
            </button>
          ))}
        </div>

        <div className="card" style={{ background: 'var(--ink)', color: '#fff', border: 0 }}>
          <div className="row-between">
            <div>
              <div style={{ fontSize: 11.5, color: '#b0b8d8' }} lang={lang}>
                {t('इस दाम पर आपको मिलेगा', 'You take home')}
              </div>
              <div className="mono" style={{ fontSize: 26, fontWeight: 800, marginTop: 3 }}>
                {rupees(chosen * 0.95 - 70)}
              </div>
            </div>
            <ScoreRing value={p.confidence} size={52} label={t('भरोसा', 'confidence')} tone="var(--marigold)" />
          </div>
          {p.effective_hourly_wage > 0 && (
            <div
              style={{
                marginTop: 11, fontSize: 12, background: 'rgba(224,146,47,0.16)',
                color: 'var(--marigold)', padding: '8px 11px', borderRadius: 10, lineHeight: 1.5, fontWeight: 600,
              }}
              lang={lang}
            >
              {t(`यानी आपकी मेहनत के ₹${Math.round(p.effective_hourly_wage)} प्रति घंटे।`,
                 `That works out to ₹${Math.round(p.effective_hourly_wage)} an hour for your work.`)}
            </div>
          )}
        </div>

        {((lang === 'hi' ? p.warnings_hi : p.warnings) || p.warnings || []).map((w) => (
          <div
            key={w}
            className="card"
            style={{ background: '#fdf6ee', borderColor: '#e8d3b4', fontSize: 12.5, lineHeight: 1.6 }}
          >
            ⚠️ {w}
          </div>
        ))}

        <div className="card">
          <div style={{ fontWeight: 700, fontSize: 13.5, marginBottom: 10 }} lang={lang}>
            🧾 {t('पूरा हिसाब — किसी को भी दिखाइए', 'The full arithmetic — show it to anyone')}
          </div>
          {(p.breakdown || []).map((line) => (
            <div key={line.label} style={{ marginBottom: 9 }}>
              <div className="row-between" style={{ fontSize: 13 }}>
                <span style={{ fontWeight: 600 }}>{lang === 'hi' ? line.label_hi : line.label}</span>
                <span className="mono" style={{ fontWeight: 700 }}>{rupees(line.amount)}</span>
              </div>
              {(lang === 'hi' ? line.note_hi || line.note : line.note) && (
                <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.45, marginTop: 2 }} lang={lang}>
                  {lang === 'hi' ? line.note_hi || line.note : line.note}
                </div>
              )}
            </div>
          ))}
          <div className="divider" />
          <div className="row-between" style={{ fontSize: 14, fontWeight: 800 }}>
            <span lang={lang}>{t('कुल सलाह', 'Recommended')}</span>
            <span className="mono">{rupees(p.recommended)}</span>
          </div>
        </div>

        {p.comparables?.length > 0 && (
          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 13.5, marginBottom: 10 }} lang={lang}>
              📊 {t('और जगह यही चीज़ किस दाम पर', 'What the same piece fetches elsewhere')}
            </div>
            {p.comparables.map((c) => (
              <div key={c.label} style={{ marginBottom: 10 }}>
                <div className="row-between" style={{ fontSize: 12.5, marginBottom: 4 }}>
                  <span lang={lang}>{lang === 'hi' ? c.label_hi || c.label : c.label}</span>
                  <span className="mono" style={{ fontWeight: 700 }}>{rupees(c.price)}</span>
                </div>
                <Bar
                  value={Math.min(100, (c.price / Math.max(...p.comparables.map((x) => x.price))) * 100)}
                  tone={c.delta_percent < 0 ? 'var(--madder)' : 'var(--leaf)'}
                  height={5}
                />
              </div>
            ))}
            <div className="muted" style={{ fontSize: 11, lineHeight: 1.55, marginTop: 8 }} lang={lang}>
              {t('सबसे ऊपर वाली पट्टी बताती है कि आपकी मेहनत का असली मोल क्या है।',
                 'The top bar is what your work is really worth downstream.')}
            </div>
          </div>
        )}

        {(p.rationale_hi || p.rationale) && (
          <div className="card tinted">
            <div style={{ fontWeight: 700, fontSize: 13, marginBottom: 8 }} lang={lang}>
              {t('यह दाम कैसे निकला', 'How we got here')}
            </div>
            {(lang === 'hi' ? p.rationale_hi : p.rationale).map((line) => (
              <div
                key={line}
                className="row"
                style={{ gap: 7, fontSize: 12, lineHeight: 1.6, marginBottom: 6, alignItems: 'flex-start' }}
              >
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

  // ---------------------------------------------------------------- step 4
  function PublishStep({ listing, saved, setSaved, matches, setMatches, onDone }) {
    const [busy, setBusy] = useState(false)
    const [sent, setSent] = useState({})
    useVoiceOnce('buyer_match')

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
        sayRaw(
          t(`आपका सामान डल गया। ${m.summary.strong_matches} खरीदार इससे अच्छी तरह मेल खाते हैं।`,
             `Your listing is live. ${m.summary.strong_matches} buyers are a strong match.`),
        )
      } catch (err) {
        toast(err.message, 'err')
      } finally {
        setBusy(false)
      }
    }, [listing])

    useEffect(() => { if (!saved && !busy) publish() }, []) // eslint-disable-line

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
          <div style={{ fontSize: 14, fontWeight: 600 }} lang={lang}>
            {t('खरीदार ढूँढे जा रहे हैं…', 'Finding buyers for this piece…')}
          </div>
          <div className="muted" style={{ fontSize: 12, marginTop: 6 }} lang={lang}>
            {t('हर खरीदार को सात बातों पर परखा जा रहा है।',
               'Scoring every buyer on seven signals.')}
          </div>
        </div>
      )
    }

    return (
      <div className="page stack">
        <div className="card" style={{ background: 'var(--leaf-soft)', borderColor: '#bcdbd1' }}>
          <div className="row" style={{ gap: 10 }}>
            <div style={{ fontSize: 26 }}>✅</div>
            <div>
              <div style={{ fontWeight: 700, fontSize: 14 }} lang={lang}>
                {t('आपका सामान अब सबको दिख रहा है', 'Your listing is live')}
              </div>
              <div style={{ fontSize: 12, color: '#145244', marginTop: 2 }}>{saved?.title}</div>
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
                <div className="mono" style={{ fontSize: 16, fontWeight: 800 }}>{n}</div>
                <div className="muted" style={{ fontSize: 9.5, textTransform: 'uppercase' }}>{label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="section-title" lang={lang}>
          {t('ये खरीदार आपके सामान से मेल खाते हैं', 'Buyers matched to this piece')}
        </div>

        {matches.matches.map((m) => (
          <BuyerMatchCard
            key={m.buyer_id}
            match={m}
            sent={sent[m.buyer_id]}
            onEnquire={() => enquire(m)}
          />
        ))}

        <button className="btn btn-ink btn-block" onClick={onDone} style={{ padding: 15 }}>
          {t('हो गया', 'Done')} →
        </button>
      </div>
    )
  }

  // ---------------------------------------------------------------- step 5
  function DoneStep({ product }) {
    useVoiceOnce('published')
    return (
      <div className="page center" style={{ paddingTop: 46 }}>
        <div style={{ fontSize: 58, animation: 'floaty 3s ease-in-out infinite' }}>🎉</div>
        <h2 style={{ fontSize: 22, margin: '14px 0 8px' }} lang={lang}>
          {t('शाबाश!', 'Well done!')}
        </h2>
        <p className="muted" style={{ fontSize: 13.5, lineHeight: 1.65, marginBottom: 22 }} lang={lang}>
          {t('आपका सामान पूरे भारत के खरीदारों को दिख रहा है। पूछताछ आने पर हम बता देंगे।',
             'Your piece is visible to buyers across India. We will tell you the moment an enquiry arrives.')}
        </p>
        <div className="stack">
          {product && (
            <button className="btn btn-soft btn-block" onClick={() => navigate(`/product/${product.id}`)}>
              {t('अपना सामान देखिए', 'View my listing')}
            </button>
          )}
          <button className="btn btn-primary btn-block" onClick={() => window.location.reload()}>
            🎤 {t('एक और डालिए', 'Add another')}
          </button>
          <button className="btn btn-ghost btn-block" onClick={() => navigate('/artisan')}>
            {t('घर वापस', 'Back home')}
          </button>
        </div>
      </div>
    )
  }

  function useVoiceOnce(screen) {
    const fired = useRef(false)
    useEffect(() => {
      if (fired.current) return undefined
      fired.current = true
      const timer = setTimeout(() => say(screen, { once: false }), 480)
      return () => clearTimeout(timer)
    }, [screen])
  }
}

export function BuyerMatchCard({ match, sent, onEnquire, compact }) {
  const { t, lang, sayRaw } = useApp()
  const [open, setOpen] = useState(false)
  const tone = match.score >= 82 ? 'var(--leaf)' : match.score >= 68 ? 'var(--marigold)' : 'var(--muted)'

  return (
    <div className="card fade-up">
      <div className="row" style={{ gap: 11, alignItems: 'flex-start' }}>
        <div
          style={{
            width: 44, height: 44, borderRadius: 13, background: 'var(--paper-2)',
            display: 'grid', placeItems: 'center', fontSize: 21, flexShrink: 0,
          }}
        >
          {match.logo}
        </div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div className="row-between">
            <div style={{ fontWeight: 700, fontSize: 14 }}>{match.name}</div>
            <span className="pill mono" style={{ background: `${tone}1a`, color: tone, borderColor: `${tone}44` }}>
              {match.score}
            </span>
          </div>
          <div className="muted" style={{ fontSize: 11.5, marginTop: 2 }}>
            {match.org_type} · {match.city}, {match.country}
          </div>
          <div style={{ fontSize: 11.5, color: tone, fontWeight: 700, marginTop: 4 }} lang={lang}>
            {lang === 'hi' ? match.fit_label_hi || match.fit_label : match.fit_label}
          </div>
        </div>
      </div>

      <div
        className="row"
        style={{
          gap: 8, marginTop: 11, padding: '9px 11px', background: 'var(--paper-2)',
          borderRadius: 11, flexWrap: 'wrap',
        }}
      >
        <div style={{ flex: 1 }}>
          <div className="muted" style={{ fontSize: 9.5, textTransform: 'uppercase', fontWeight: 700 }}>
            {t('मात्रा', 'Quantity')}
          </div>
          <div className="mono" style={{ fontSize: 13.5, fontWeight: 700 }}>{match.suggested_quantity}</div>
        </div>
        <div style={{ flex: 1 }}>
          <div className="muted" style={{ fontSize: 9.5, textTransform: 'uppercase', fontWeight: 700 }}>
            {t('प्रति पीस', 'Unit')}
          </div>
          <div className="mono" style={{ fontSize: 13.5, fontWeight: 700 }}>{rupees(match.suggested_unit_price)}</div>
        </div>
        <div style={{ flex: 1.2 }}>
          <div className="muted" style={{ fontSize: 9.5, textTransform: 'uppercase', fontWeight: 700 }}>
            {t('कुल', 'Order value')}
          </div>
          <div className="mono" style={{ fontSize: 13.5, fontWeight: 800, color: 'var(--leaf)' }}>
            {rupees(match.estimated_order_value)}
          </div>
        </div>
      </div>

      <button
        onClick={() => setOpen(!open)}
        className="btn btn-sm"
        style={{ background: 'none', padding: '9px 0 0', fontSize: 12, color: 'var(--indigo)', fontWeight: 700 }}
      >
        {open ? '▾' : '▸'} {t('यह मेल क्यों खाता है', 'Why this is a match')}
      </button>

      {open && (
        <div className="fade-up" style={{ marginTop: 8 }}>
          {match.factors.map((f) => (
            <div key={f.label} style={{ marginBottom: 9 }}>
              <div className="row-between" style={{ fontSize: 11.5, marginBottom: 3 }}>
                <span style={{ fontWeight: 600 }} lang={lang}>
                  {lang === 'hi' ? f.label_hi || f.label : f.label}
                </span>
                <span className="mono muted">{Math.round(f.score * 100)}%</span>
              </div>
              <Bar
                value={f.score * 100}
                height={4}
                tone={f.score > 0.7 ? 'var(--leaf)' : f.score > 0.4 ? 'var(--marigold)' : 'var(--madder)'}
              />
              <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.45, marginTop: 3 }} lang={lang}>
                {lang === 'hi' ? f.detail_hi || f.detail : f.detail}
              </div>
            </div>
          ))}
          {(lang === 'hi' ? match.gaps_hi : match.gaps)?.length > 0 && (
            <div
              style={{
                background: '#fdf6ee', border: '1px solid #e8d3b4', borderRadius: 10,
                padding: '8px 10px', fontSize: 11, lineHeight: 1.5, marginTop: 6,
              }}
            >
              <strong>{t('ध्यान दीजिए: ', 'Watch out: ')}</strong>
              {(lang === 'hi' ? match.gaps_hi : match.gaps).join('. ')}
            </div>
          )}
          <div
            style={{
              marginTop: 10, padding: '10px 11px', background: 'var(--marigold-soft)',
              borderRadius: 11, fontSize: 11.5, lineHeight: 1.6, color: '#5e4413',
            }}
            lang={lang}
          >
            <div style={{ fontWeight: 700, marginBottom: 4 }}>
              💬 {t('आपके लिए लिखा हुआ संदेश', 'Your message, already written')}
            </div>
            {lang === 'hi' ? match.pitch_hi : match.pitch}
            <button
              className="btn btn-sm btn-soft"
              style={{ marginTop: 8 }}
              onClick={() => sayRaw(lang === 'hi' ? match.pitch_hi : match.pitch)}
            >
              🔊 {t('सुनिए', 'Read it to me')}
            </button>
          </div>
        </div>
      )}

      {onEnquire && (
        <button
          className={`btn btn-block btn-sm ${sent ? 'btn-soft' : 'btn-gold'}`}
          style={{ marginTop: 11 }}
          onClick={onEnquire}
          disabled={sent}
        >
          {sent ? `✓ ${t('भेज दिया', 'Sent')}` : `📨 ${t('पूछताछ भेजिए', 'Send enquiry')}`}
        </button>
      )}
    </div>
  )
}
