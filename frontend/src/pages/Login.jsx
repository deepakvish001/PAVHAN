import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Toasts } from '../components/Shell'
import { completeProfile, requestOtp, verifyOtp } from '../api/client'

const HOME_FOR = { artisan: '/artisan', customer: '/shop', b2b: '/b2b', exporter: '/b2b' }

const CRAFTS = [
  ['Banarasi Handloom Silk', 'बनारसी रेशम', '🥻'],
  ['Jaipur Blue Pottery', 'ब्लू पॉटरी', '🏺'],
  ['Terracotta Pottery', 'टेराकोटा', '🪔'],
  ['Bamboo & Cane Craft', 'बाँस और बेंत', '🧺'],
  ['Madhubani Painting', 'मधुबनी', '🎨'],
  ['Dhokra Metal Craft', 'ढोकरा', '🔔'],
  ['Kashmiri Pashmina', 'पश्मीना', '🧣'],
  ['Lucknawi Chikankari', 'चिकनकारी', '🪡'],
]

/**
 * Mobile-number sign-in.
 *
 * An artisan has a phone number and usually no email address, so the number
 * is the identity and the only thing they have to type is ten digits they
 * already know by heart. Every step is spoken aloud, because this is the
 * first screen a low-literacy user meets and a wall of text loses them here.
 */
export default function Login() {
  const navigate = useNavigate()
  const {
    t, lang, setLang, role, setRole, setUser, setToken,
    voiceOn, setVoiceOn, theme, toggleTheme, assistant, sayRaw,
  } = useApp()

  const [step, setStep] = useState('phone')      // phone | otp | profile
  const [phone, setPhone] = useState('')
  const [code, setCode] = useState('')
  const [demoCode, setDemoCode] = useState(null)
  const [demoNote, setDemoNote] = useState('')
  const [name, setName] = useState('')
  const [craft, setCraft] = useState('')
  const [region, setRegion] = useState('')
  const [session, setSession] = useState(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const spoken = useRef(new Set())

  const LINES = {
    phone: {
      hi: 'अपना मोबाइल नंबर डालिए। हम उस पर एक छोटा कोड भेजेंगे, बस उतना ही करना है। '
        + 'कोई पासवर्ड याद रखने की ज़रूरत नहीं।',
      en: 'Enter your mobile number. We will send a short code to it — that is all you '
        + 'need. There is no password to remember.',
    },
    otp: {
      hi: 'अब वह छह अंकों का कोड डालिए। डेमो में कोड यहीं स्क्रीन पर दिख रहा है।',
      en: 'Now enter the six-digit code. In this demo the code is shown on the screen.',
    },
    profile: {
      hi: 'आख़िरी बात — अपना नाम और अपना काम बता दीजिए, ताकि खरीदार जान सकें कि यह किसने बनाया।',
      en: 'Last thing — your name and your craft, so buyers know who made the piece.',
    },
  }

  useEffect(() => {
    if (!voiceOn || spoken.current.has(step)) return
    spoken.current.add(step)
    const timer = setTimeout(() => sayRaw(LINES[step][lang] || LINES[step].en), 550)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [step, voiceOn])

  const digits = phone.replace(/\D/g, '')

  const sendCode = async () => {
    setError('')
    if (digits.length < 10) {
      setError(t('पूरा दस अंकों का नंबर डालिए।', 'Enter the full 10-digit number.'))
      return
    }
    setBusy(true)
    try {
      const res = await requestOtp(digits)
      setDemoCode(res.demo_code || null)
      setDemoNote(lang === 'hi' ? res.demo_note_hi || '' : res.demo_note || '')
      if (res.name) setName(res.name)
      setStep('otp')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const verify = async () => {
    setError('')
    setBusy(true)
    try {
      const res = await verifyOtp({
        phone: digits, code: code.trim(), name: name || undefined,
        role: role || 'artisan', language: lang,
      })
      setToken(res.token)
      setUser(res.user)
      setSession(res)
      if (res.needs_onboarding) {
        setName(res.user.name === 'PAVHAN user' ? '' : res.user.name)
        setStep('profile')
      } else {
        setRole(res.user.role)
        navigate(HOME_FOR[res.user.role] || '/shop')
      }
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  const finish = async () => {
    setBusy(true)
    try {
      const user = await completeProfile({
        token: session.token,
        name: name || t('कारीगर', 'Artisan'),
        craft_focus: craft,
        region,
        language: lang,
        role: role || 'artisan',
      })
      setUser(user)
      setRole(user.role)
      navigate(HOME_FOR[user.role] || '/artisan')
    } catch (err) {
      setError(err.message)
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <div
        className="app-body no-nav"
        style={{ background: 'var(--ink)', color: '#fff', padding: 0,
                 display: 'flex', flexDirection: 'column' }}
      >
        <div style={{ padding: '24px 20px 18px' }}>
          <div className="row-between">
            <div className="row" style={{ gap: 9 }}>
              <div style={{ width: 36, height: 36, borderRadius: 11, background: 'var(--marigold)',
                            display: 'grid', placeItems: 'center', fontSize: 18 }}>🪡</div>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 19, fontWeight: 700,
                              letterSpacing: '0.02em' }}>PAVHAN</div>
                <div style={{ fontSize: 9, color: '#a9b1cf', letterSpacing: '0.07em',
                              textTransform: 'uppercase' }}>
                  {t('आपका बिज़नेस मैनेजर', 'Your business manager')}
                </div>
              </div>
            </div>
            <div className="row" style={{ gap: 7 }}>
              <button className="topbar-btn" onClick={toggleTheme}>
                {theme === 'dark' ? '☀️' : '🌙'}
              </button>
              <button className="topbar-btn" style={{ fontSize: 12, fontWeight: 700 }}
                      onClick={() => setLang(lang === 'hi' ? 'en' : 'hi')}>
                {lang === 'hi' ? 'अ' : 'A'}
              </button>
              <button className={`topbar-btn ${voiceOn ? 'on' : ''}`}
                      onClick={() => { if (voiceOn) assistant.cancel(); setVoiceOn(!voiceOn) }}>
                {voiceOn ? '🔊' : '🔇'}
              </button>
            </div>
          </div>
        </div>

        <div style={{ background: 'var(--paper)', color: 'var(--ink)',
                      borderRadius: '28px 28px 0 0', padding: '26px 18px 34px',
                      flex: 1, display: 'flex', flexDirection: 'column' }}>
          <div className="row" style={{ gap: 6, marginBottom: 16 }}>
            {['phone', 'otp', 'profile'].map((s) => (
              <div key={s} style={{ flex: 1, height: 4, borderRadius: 99,
                background: ['phone', 'otp', 'profile'].indexOf(step) >= ['phone', 'otp', 'profile'].indexOf(s)
                  ? 'var(--madder)' : 'var(--line)' }} />
            ))}
          </div>

          {step === 'phone' && (
            <div className="stack fade-up">
              <h2 style={{ fontSize: 23 }} lang={lang}>
                {t('स्वागत है', 'Welcome')}
              </h2>
              <p className="section-sub" lang={lang} style={{ marginTop: -6 }}>
                {t('अपना मोबाइल नंबर डालिए — पासवर्ड की ज़रूरत नहीं।',
                   'Enter your mobile number. No password needed.')}
              </p>
              <div className="field">
                <label>{t('मोबाइल नंबर', 'Mobile number')}</label>
                <div className="row card" style={{ gap: 8, padding: '4px 12px' }}>
                  <span style={{ fontWeight: 700, color: 'var(--muted)' }}>+91</span>
                  <input
                    className="input" inputMode="numeric" autoComplete="tel"
                    style={{ border: 0, fontSize: 19, letterSpacing: '0.09em', padding: '12px 0' }}
                    placeholder="98765 43210" value={phone} maxLength={11}
                    onChange={(e) => setPhone(e.target.value.replace(/[^\d ]/g, ''))}
                    onKeyDown={(e) => e.key === 'Enter' && sendCode()}
                  />
                </div>
              </div>
              {error && <div className="pill madder" style={{ whiteSpace: 'normal' }}>{error}</div>}
              <button className="btn btn-primary btn-block" onClick={sendCode}
                      disabled={busy} style={{ padding: 16 }}>
                {busy ? <span className="spinner" /> : t('कोड भेजिए', 'Send code')}
              </button>
              <button className="btn btn-ghost btn-block btn-sm" onClick={() => navigate('/')}>
                {t('अभी नहीं — पहले ऐप देखिए', 'Not now — look around first')}
              </button>
            </div>
          )}

          {step === 'otp' && (
            <div className="stack fade-up">
              <h2 style={{ fontSize: 23 }} lang={lang}>{t('कोड डालिए', 'Enter the code')}</h2>
              <p className="section-sub" lang={lang} style={{ marginTop: -6 }}>
                {t(`+91 ${digits} पर भेजा गया`, `Sent to +91 ${digits}`)}
              </p>
              {demoCode && (
                <div className="card" style={{ background: 'var(--marigold-soft)',
                                               borderColor: '#eccf9e' }}>
                  <div style={{ fontSize: 11.5, lineHeight: 1.6 }} lang={lang}>{demoNote}</div>
                  <div className="mono center" style={{ fontSize: 30, fontWeight: 800,
                       letterSpacing: '0.2em', marginTop: 8 }}>{demoCode}</div>
                  <button className="btn btn-soft btn-sm btn-block" style={{ marginTop: 10 }}
                          onClick={() => setCode(demoCode)}>
                    {t('यही भर दीजिए', 'Fill it in')}
                  </button>
                </div>
              )}
              <div className="field">
                <label>{t('छह अंकों का कोड', 'Six-digit code')}</label>
                <input className="input mono" inputMode="numeric" maxLength={6}
                       style={{ fontSize: 26, letterSpacing: '0.42em', textAlign: 'center' }}
                       value={code} placeholder="------"
                       onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
                       onKeyDown={(e) => e.key === 'Enter' && verify()} />
              </div>
              {error && <div className="pill madder" style={{ whiteSpace: 'normal' }}>{error}</div>}
              <button className="btn btn-primary btn-block" onClick={verify}
                      disabled={busy || code.length < 6} style={{ padding: 16 }}>
                {busy ? <span className="spinner" /> : t('आगे बढ़िए', 'Continue')}
              </button>
              <button className="btn btn-ghost btn-block btn-sm"
                      onClick={() => { setStep('phone'); setCode(''); setError('') }}>
                {t('नंबर बदलिए', 'Change number')}
              </button>
            </div>
          )}

          {step === 'profile' && (
            <div className="stack fade-up">
              <h2 style={{ fontSize: 23 }} lang={lang}>{t('आपका परिचय', 'About you')}</h2>
              <p className="section-sub" lang={lang} style={{ marginTop: -6 }}>
                {t('यह खरीदारों को दिखेगा — इसी से वे जानेंगे कि सामान किसने बनाया।',
                   'Buyers see this — it is how they know who made the piece.')}
              </p>
              <div className="field">
                <label>{t('आपका नाम', 'Your name')}</label>
                <input className="input" value={name} placeholder={t('जैसे: सीता देवी', 'e.g. Sita Devi')}
                       onChange={(e) => setName(e.target.value)} />
              </div>
              <div className="field">
                <label>{t('आप क्या बनाते हैं?', 'What do you make?')}</label>
                <div className="row" style={{ gap: 7, flexWrap: 'wrap' }}>
                  {CRAFTS.map(([key, hi, icon]) => (
                    <button key={key} className={`chip ${craft === key ? 'active' : ''}`}
                            style={{ padding: '9px 12px' }} onClick={() => setCraft(key)} lang={lang}>
                      {icon} {lang === 'hi' ? hi : key}
                    </button>
                  ))}
                </div>
              </div>
              <div className="field">
                <label>{t('आपका गाँव या शहर', 'Your town or district')}</label>
                <input className="input" value={region} placeholder={t('जैसे: बांकुड़ा', 'e.g. Bankura')}
                       onChange={(e) => setRegion(e.target.value)} />
              </div>
              {error && <div className="pill madder" style={{ whiteSpace: 'normal' }}>{error}</div>}
              <button className="btn btn-primary btn-block" onClick={finish}
                      disabled={busy} style={{ padding: 16 }}>
                {busy ? <span className="spinner" /> : t('मेरा खाता बनाइए', 'Create my account')}
              </button>
            </div>
          )}

          <div className="spacer" />
          <p className="center muted" style={{ fontSize: 11, lineHeight: 1.6, marginTop: 20 }} lang={lang}>
            🔊 {t('हर पन्ना बोलकर समझाया जाता है — सुनते रहिए।',
                  'Every screen is explained out loud — just listen.')}
          </p>
        </div>
      </div>
      <Toasts />
    </>
  )
}
