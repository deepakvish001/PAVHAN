import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { aiStatus, health, lookupPincode, platformStats, priceModelCard, updateUser, voiceLanguages } from '../api/client'

export default function Profile() {
  const navigate = useNavigate()
  const { t, lang, setLang, role, setRole, user, voiceOn, setVoiceOn, assistant,
          sayRaw, L, pwa, theme, toggleTheme, fontScale, setFontScale,
          contrast, setContrast, voiceName, setVoiceName } = useApp()
  const [status, setStatus] = useState(null)
  const { setUser, toast } = useApp()
  const [stats, setStats] = useState(null)
  const [modelCard, setModelCard] = useState(null)
  const [langCount, setLangCount] = useState(0)

  useEffect(() => {
    Promise.all([
      aiStatus().catch(() => null),
      platformStats().catch(() => null),
      health().catch(() => null),
      priceModelCard().catch(() => null),
      voiceLanguages().catch(() => null),
    ]).then(([ai, st, , model, langs]) => {
      setStatus(ai); setStats(st); setModelCard(model)
      setLangCount(langs?.languages?.length || 0)
    })
  }, [])

  const ROLES = [
    ['artisan', '🧵', t('कारीगर', 'Artisan'), '/artisan'],
    ['customer', '🛍️', t('ख़रीदार', 'Shopper'), '/shop'],
    ['b2b', '🏬', t('थोक ख़रीदार', 'Bulk buyer'), '/b2b'],
    ['exporter', '🌍', t('निर्यातक', 'Exporter'), '/b2b'],
  ]

  return (
    <>
      <TopBar title={t('खाता और सेटिंग', 'Account & settings')} />
      <Screen>
        <div className="page stack">
          <div className="card row" style={{ gap: 13 }}>
            <div
              style={{
                width: 52, height: 52, borderRadius: 16, background: 'var(--paper-2)',
                display: 'grid', placeItems: 'center', fontSize: 'calc(26px * var(--font-scale))',
              }}
            >
              {user?.avatar || '👤'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(15.5px * var(--font-scale))' }}>
                {user?.name || t('मेहमान', 'Guest')}
              </div>
              <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 2 }}>
                {L(user?.craft_focus) || ''} {user?.region ? `· ${L(user.region)}` : ''}
              </div>
            </div>
          </div>

          {role === 'artisan' && user?.id && (
            <PincodeCard user={user} setUser={setUser} t={t} lang={lang} toast={toast} />
          )}

          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
              {t('मैं यहाँ किस काम से हूँ', 'What I am here for')}
            </div>
            <div className="grid-2">
              {ROLES.map(([key, icon, label, path]) => (
                <button
                  key={key}
                  className={`chip ${role === key ? 'active' : ''}`}
                  style={{ padding: '12px 10px', justifyContent: 'center', display: 'flex', gap: 7 }}
                  onClick={() => { setRole(key); navigate(path) }}
                >
                  <span>{icon}</span> {label}
                </button>
              ))}
            </div>
          </div>

          {/* Installing matters more than it sounds: an icon on the home
              screen is what turns this from "a website someone showed me"
              into something an artisan opens on their own next week. */}
          {(pwa.canInstall || pwa.installed) && (
            <div className="card" style={{ background: 'var(--marigold-soft)',
                                           borderColor: 'var(--line)' }}>
              <div className="row-between">
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
                    📲 {pwa.installed
                      ? t('ऐप इंस्टॉल है', 'Installed as an app')
                      : t('फ़ोन में ऐप की तरह लगाइए', 'Install it like an app')}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 3 }}
                       lang={lang}>
                    {pwa.installed
                      ? t('बिना इंटरनेट भी खुलेगा और सहेजा काम दिखेगा।',
                           'It opens without internet and shows your saved work.')
                      : t('होम स्क्रीन पर आइकॉन आ जाएगा, इंटरनेट न हो तब भी खुलेगा।',
                           'You get an icon on your home screen, and it opens offline.')}
                  </div>
                </div>
                {!pwa.installed && (
                  <button className="btn btn-gold btn-sm" onClick={pwa.install}>
                    {t('लगाइए', 'Install')}
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="card">
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
                  🗣️ {t('आवाज़ वाली मदद', 'Voice guide')}
                </div>
                <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 2, lineHeight: 1.5 }} lang={lang}>
                  {t('हर पन्ने पर बोलकर बताती है कि क्या करना है।',
                     'Explains every screen out loud as you go.')}
                </div>
              </div>
              <button
                className={`btn btn-sm ${voiceOn ? 'btn-gold' : 'btn-soft'}`}
                onClick={() => { if (voiceOn) assistant.cancel(); setVoiceOn(!voiceOn) }}
              >
                {voiceOn ? t('चालू', 'On') : t('बंद', 'Off')}
              </button>
            </div>

            <HindiVoiceNote assistant={assistant} t={t} lang={lang} sayRaw={sayRaw}
                            voiceName={voiceName} setVoiceName={setVoiceName} />

            <div className="row-between" style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
                {theme === 'dark' ? '🌙' : '☀️'} {t('रंग-रूप', 'Appearance')}
              </div>
              <div className="row" style={{ gap: 7 }}>
                <button className={`chip ${theme === 'light' ? 'active' : ''}`}
                        onClick={() => theme === 'dark' && toggleTheme()}>
                  {t('उजला', 'Light')}
                </button>
                <button className={`chip ${theme === 'dark' ? 'active' : ''}`}
                        onClick={() => theme === 'light' && toggleTheme()}>
                  {t('गहरा', 'Dark')}
                </button>
              </div>
            </div>
            <div className="row-between">
              <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
                🌐 {t('भाषा', 'Language')}
              </div>
              <div className="row" style={{ gap: 7 }}>
                <button
                  className={`chip ${lang === 'hi' ? 'active' : ''}`}
                  onClick={() => setLang('hi')}
                >
                  हिंदी
                </button>
                <button
                  className={`chip ${lang === 'en' ? 'active' : ''}`}
                  onClick={() => setLang('en')}
                >
                  English
                </button>
              </div>
            </div>
            {voiceOn && (
              <button
                className="btn btn-soft btn-sm btn-block"
                style={{ marginTop: 12 }}
                onClick={() => sayRaw(
                  t('नमस्ते! मैं पवन की आवाज़ हूँ। मैं हर कदम पर आपकी मदद करूँगा।',
                    'Hello! I am the PAVHAN voice guide. I will help you at every step.'),
                )}
              >
                🔊 {t('आवाज़ जाँचिए', 'Test the voice')}
              </button>
            )}
          </div>

          {/* MoSJE's beneficiaries include Divyangjan, and the problem
              statement asks for accessible layouts in as many words. */}
          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 12 }} lang={lang}>
              ♿ {t('पढ़ने में आसानी', 'Easier to read')}
            </div>
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div style={{ fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 600 }} lang={lang}>
                {t('अक्षरों का आकार', 'Text size')}
              </div>
              <div className="row" style={{ gap: 7 }}>
                {[['A', 0.9], ['A', 1], ['A', 1.2], ['A', 1.45]].map(([letter, scale], i) => (
                  <button
                    key={scale}
                    className={`chip ${fontScale === scale ? 'active' : ''}`}
                    onClick={() => setFontScale(scale)}
                    aria-label={`${t('अक्षर आकार', 'Text size')} ${i + 1}`}
                    style={{ fontSize: `${11 + i * 3}px`, fontWeight: 700,
                             minWidth: 40, justifyContent: 'center' }}
                  >
                    {letter}
                  </button>
                ))}
              </div>
            </div>
            <div className="row-between">
              <div style={{ flex: 1 }}>
                <div style={{ fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 600 }} lang={lang}>
                  {t('ज़्यादा साफ़ रंग', 'High contrast')}
                </div>
                <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.5, marginTop: 2 }}
                     lang={lang}>
                  {t('कम दिखाई देने पर या तेज़ धूप में', 'For low vision or bright sunlight')}
                </div>
              </div>
              <button
                className={`btn btn-sm ${contrast === 'high' ? 'btn-gold' : 'btn-soft'}`}
                onClick={() => setContrast(contrast === 'high' ? 'normal' : 'high')}
                aria-pressed={contrast === 'high'}
              >
                {contrast === 'high' ? t('चालू', 'On') : t('बंद', 'Off')}
              </button>
            </div>
          </div>

          {status && (
            <div className="card">
              <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
                ⚙️ {t('कौन सा इंजन चल रहा है', 'Which engines are live')}
              </div>
              {[
                [t('विवरण लिखना', 'Listing copy'), status.llm_model],
                [t('फोटो पढ़ना', 'Image understanding'), status.vision],
                [t('आवाज़ से लिखना', 'Speech to text'), status.speech_to_text],
                [t('ज्ञात शिल्प', 'Crafts known'), status.crafts_known],
                [t('बोलने की भाषाएँ', 'Spoken languages'), langCount || '—'],
                [t('दाम का मॉडल', 'Pricing model'),
                 modelCard?.available ? `${modelCard.metrics.median_abs_pct}% median error` : '—'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="row-between"
                  style={{ fontSize: 'calc(12px * var(--font-scale))', padding: '7px 0', borderTop: '1px solid var(--line)' }}
                >
                  <span className="muted">{label}</span>
                  <span className="mono" style={{ fontWeight: 600 }}>{value}</span>
                </div>
              ))}
              <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 9 }} lang={lang}>
                {status.llm === 'claude'
                  ? t('Claude API जुड़ा है — विवरण और फोटो दोनों उसी से पढ़े जा रहे हैं।',
                       'Claude API is connected — copy and image understanding both run through it.')
                  : t('बिना किसी API key के चल रहा है। ANTHROPIC_API_KEY डालते ही Claude अपने आप जुड़ जाएगा।',
                       'Running fully on-device with no API key. Set ANTHROPIC_API_KEY and Claude is used automatically.')}
              </div>
            </div>
          )}

          {stats && (
            <div className="card tinted row" style={{ gap: 14 }}>
              {[
                [stats.artisans, t('कारीगर', 'artisans')],
                [stats.products, t('सामान', 'listings')],
                [stats.regions_covered, t('क्षेत्र', 'clusters')],
              ].map(([n, label]) => (
                <div key={label} style={{ flex: 1 }}>
                  <div className="mono" style={{ fontSize: 'calc(17px * var(--font-scale))', fontWeight: 800 }}>{n}</div>
                  <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase' }}>{label}</div>
                </div>
              ))}
            </div>
          )}

          <button
            className="btn btn-ghost btn-block"
            onClick={() => { localStorage.removeItem('pavhan.session.v1'); window.location.href = '/' }}
          >
            {t('शुरू से शुरू कीजिए', 'Start over')}
          </button>

          <div className="center muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.7, paddingTop: 6 }}>
            PAVHAN · AI-Powered Growth for Artisan Craft<br />
            Smart India Hackathon · PS 26090
          </div>
        </div>
      </Screen>
    </>
  )
}


/**
 * The artisan's own pincode, which is where every shipment starts.
 *
 * It sits in Profile rather than buried in the despatch flow because it is
 * asked for once and used for ever, and because an artisan who first meets
 * this question while a buyer is waiting will guess. Confirming the state
 * back to them is the check: somebody who sees "Uttar Pradesh" when they live
 * in Bihar has caught a typo that would otherwise have mis-priced every
 * parcel they ever send.
 */
function PincodeCard({ user, setUser, t, lang, toast }) {
  const [value, setValue] = useState(user.pincode || '')
  const [place, setPlace] = useState(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    const pin = value.trim()
    if (pin.length !== 6) { setPlace(null); return }
    const timer = setTimeout(() => {
      lookupPincode(pin).then(setPlace).catch(() => setPlace(null))
    }, 300)
    return () => clearTimeout(timer)
  }, [value])

  const save = async () => {
    setSaving(true)
    try {
      const updated = await updateUser(user.id, { pincode: value.trim() })
      setUser(updated)
      toast(t('पिनकोड सुरक्षित कर लिया।', 'Pincode saved.'), 'ok')
    } catch (err) {
      toast(err.message, 'err')
    } finally { setSaving(false) }
  }

  const dirty = value.trim() !== (user.pincode || '') && value.trim().length === 6

  return (
    <div className="card" style={{ borderColor: user.pincode ? 'var(--line)' : 'var(--marigold)' }}>
      <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
        {t('आपका पिनकोड', 'Your pincode')}
      </div>
      <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 4, lineHeight: 1.5 }}
           lang={lang}>
        {t('कूरियर का दाम यहीं से निकलता है। एक बार डाल दीजिए, हर बार काम आएगा।',
           'Shipping rates are worked out from here. Enter it once and it is used every time.')}
      </div>
      <div className="row" style={{ gap: 8, marginTop: 10 }}>
        <input className="input" value={value} inputMode="numeric" maxLength={6}
               placeholder="221001" style={{ flex: 1 }}
               onChange={(e) => setValue(e.target.value.replace(/\D/g, ''))} />
        <button className="btn btn-soft btn-sm" onClick={save} disabled={!dirty || saving}>
          {saving ? <span className="spinner dark" /> : t('सहेजें', 'Save')}
        </button>
      </div>
      {place && (
        <div style={{
          fontSize: 'calc(12px * var(--font-scale))', marginTop: 7, lineHeight: 1.45,
          color: place.valid ? 'var(--ink-soft)' : 'var(--madder)',
        }} lang={lang}>
          {place.valid
            ? `\u2713 ${place.state}${place.remote ? ` \u00b7 ${lang === 'hi' ? place.note_hi : place.note}` : ''}`
            : (lang === 'hi' ? place.reason_hi : place.reason)}
        </div>
      )}
    </div>
  )
}


/**
 * What this particular device can do with the Hindi voice.
 *
 * The most common support question about this app is "the Hindi voice does
 * not work, the English one does", and the answer is almost never in the
 * code: the machine has no Hindi voice installed. Windows does not ship one
 * unless somebody added the Hindi language pack, and a borrowed demo laptop
 * never has. Saying so on screen turns a mystery into a one-line
 * explanation — and shows that the app kept speaking Hindi anyway.
 */
function HindiVoiceNote({ assistant, t, lang, sayRaw, voiceName, setVoiceName }) {
  const [info, setInfo] = useState(null)

  useEffect(() => {
    if (!assistant?.hindiVoice) return undefined
    const read = () => setInfo(assistant.hindiVoice())
    read()
    // Voices load asynchronously and often arrive after the first render.
    const timer = setTimeout(read, 900)
    return () => clearTimeout(timer)
  }, [assistant])

  if (!info) return null

  const MODES = {
    native: {
      icon: '✅',
      title: t('हिंदी आवाज़ मौजूद है', 'A Hindi voice is installed'),
      body: t('यह डिवाइस देवनागरी पढ़ सकता है, इसलिए सब कुछ असली हिंदी आवाज़ में बोला जाएगा।',
              'This device can read Devanagari, so everything is spoken in a real Hindi voice.'),
    },
    indic: {
      icon: '✅',
      title: t('भारतीय भाषा की आवाज़ मौजूद है', 'An Indic voice is installed'),
      body: t('देवनागरी पढ़ने वाली आवाज़ मिल गई है।',
              'A voice that can read Devanagari was found.'),
    },
    romanised: {
      icon: 'ℹ️',
      title: t('इस डिवाइस में हिंदी आवाज़ नहीं है', 'This device has no Hindi voice'),
      body: t('कोई बात नहीं — हिंदी रोमन में लिखकर भारतीय अंग्रेज़ी आवाज़ से बोली जाएगी, ' +
              'जैसे "yeh haath se banee hai"। सुनने में हिंदी ही लगेगी। ' +
              'असली हिंदी आवाज़ चाहिए तो फ़ोन की सेटिंग में हिंदी भाषा जोड़ लीजिए।',
              'That is fine — the Hindi is written in Roman and read by an Indian-English ' +
              'voice, like "yeh haath se banee hai". It still sounds like Hindi. ' +
              'For a true Hindi voice, add Hindi in your device language settings.'),
    },
    none: {
      icon: '⚠️',
      title: t('इस ब्राउज़र में कोई आवाज़ नहीं मिली', 'No voices found in this browser'),
      body: t('क्रोम या एज में खोलिए — वहाँ आवाज़ काम करेगी।',
              'Open PAVHAN in Chrome or Edge, where speech works.'),
    },
  }
  const mode = MODES[info.mode] || MODES.none

  return (
    <div style={{
      marginBottom: 12, padding: '10px 11px', borderRadius: 12,
      background: 'var(--paper-2)', lineHeight: 1.5,
    }}>
      <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))' }} lang={lang}>
        {mode.icon} {mode.title}
      </div>
      <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 4 }}
           lang={lang}>
        {mode.body}
      </div>
      {info.voice && (
        <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', marginTop: 5 }}>
          {t('आवाज़', 'Voice')}: {info.voice} ({info.lang})
          {info.quality === 'natural' && ` · ${t('बढ़िया गुणवत्ता', 'natural quality')}`}
          {info.quality === 'basic' && ` · ${t('बुनियादी गुणवत्ता', 'basic quality')}`}
        </div>
      )}
      {info.quality === 'basic' && (
        <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 5, lineHeight: 1.5 }}
             lang={lang}>
          {t('इस डिवाइस पर सिर्फ़ रोबोट जैसी आवाज़ मिली है। क्रोम ब्राउज़र में खोलने पर बेहतर आवाज़ मिलेगी।',
             'Only a robotic voice was found on this device. Opening PAVHAN in Chrome usually gives a better one.')}
        </div>
      )}
      <button className="btn btn-soft btn-sm" style={{ marginTop: 9 }}
              onClick={() => sayRaw(SAMPLE, { lang: 'hi' })}>
        🔊 {t('हिंदी आवाज़ सुनकर देखिए', 'Test the Hindi voice')}
      </button>

      {/* Accent is a matter of taste, and which engine is installed differs
          on every machine. Rather than insisting the scoring table knows
          best, offer what is actually on this device and let the listener
          decide — with a sample of each, because nobody can pick a voice
          from a name. */}
      {info.choices?.length > 1 && (
        <div style={{ marginTop: 11, paddingTop: 10, borderTop: '1px solid var(--line)' }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
            {t('आवाज़ खुद चुनिए', 'Choose the voice yourself')}
          </div>
          <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 3, lineHeight: 1.45 }}
               lang={lang}>
            {t('हर आवाज़ सुनकर देखिए, जो सबसे अच्छी लगे वही रख लीजिए।',
               'Listen to each one and keep whichever sounds best to you.')}
          </div>

          <div className="stack" style={{ gap: 7, marginTop: 9 }}>
            {info.choices.map((choice) => {
              const active = voiceName
                ? choice.name === voiceName
                : choice.name === info.voice
              return (
                <div key={choice.name} className="row" style={{ gap: 7, alignItems: 'center' }}>
                  <button
                    className="btn btn-soft btn-sm"
                    style={{ minWidth: 44, padding: '0 10px' }}
                    aria-label={t(`${choice.name} सुनिए`, `Listen to ${choice.name}`)}
                    onClick={() => { setVoiceName(choice.name); sayRaw(SAMPLE, { lang: 'hi' }) }}
                  >
                    🔊
                  </button>
                  <button
                    onClick={() => setVoiceName(choice.name)}
                    className="card"
                    style={{
                      flex: 1, minWidth: 0, textAlign: 'left', padding: '8px 10px',
                      borderColor: active ? 'var(--indigo)' : 'var(--line)',
                    }}
                  >
                    <div style={{ fontWeight: active ? 800 : 600,
                                  fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.35 }}>
                      {active && '✓ '}{choice.name}
                    </div>
                    <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginTop: 2 }}
                         lang={lang}>
                      {choice.lang}
                      {choice.readsHindi
                        ? ` · ${t('हिंदी में बोलेगी', 'speaks Hindi')}`
                        : ` · ${t('रोमन में बोलेगी', 'speaks romanised')}`}
                      {choice.quality === 'natural' && ` · ${t('बढ़िया', 'natural')}`}
                      {choice.quality === 'basic' && ` · ${t('बुनियादी', 'basic')}`}
                    </div>
                  </button>
                </div>
              )
            })}
          </div>

          {voiceName && (
            <button className="btn btn-ghost btn-sm btn-block" style={{ marginTop: 8 }}
                    onClick={() => setVoiceName('')}>
              {t('अपने आप चुनने दीजिए', 'Let PAVHAN choose again')}
            </button>
          )}
        </div>
      )}
    </div>
  )
}

// Long enough to judge an accent by, short enough to listen to four times.
const SAMPLE = 'नमस्ते! यह पावहन की हिंदी आवाज़ है। आपका सामान पूरे भारत में दिखेगा, '
  + 'और पूरा दाम सीधे आपके पास आएगा।'
