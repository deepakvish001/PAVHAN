import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { voiceRoles, voiceWelcome, platformStats } from '../api/client'
import { Toasts } from '../components/Shell'

const HOME_FOR = { artisan: '/artisan', customer: '/shop', b2b: '/b2b', exporter: '/b2b' }

/**
 * First open. Two jobs: say who PAVHAN is for, and find out which of the four
 * people is holding the phone — because an artisan, a shopper and a bulk buyer
 * need three different apps behind the same front door.
 */
export default function Welcome() {
  const navigate = useNavigate()
  const { lang, setLang, setRole, setUser, voiceOn, setVoiceOn, sayRaw, sayProtected, assistant } = useApp()
  const [roles, setRoles] = useState([])
  const [prompt, setPrompt] = useState('')
  const [stats, setStats] = useState(null)
  const [picked, setPicked] = useState(null)
  const [greeting, setGreeting] = useState(null)   // {text, skip}

  useEffect(() => {
    voiceRoles(lang).then((d) => { setRoles(d.roles || []); setPrompt(d.prompt || '') }).catch(() => {})
    greetingRef.current = greeting
    platformStats().then(setStats).catch(() => {})
  }, [lang])

  useEffect(() => { greetingRef.current = greeting }, [greeting])

  // The opening line, spoken once the moment the app opens.
  const greeted = useRef(false)
  const greetingRef = useRef(null)
  useEffect(() => {
    if (!voiceOn || !prompt || greeted.current) return undefined
    greeted.current = true
    const timer = setTimeout(() => sayRaw(prompt), 700)
    return () => clearTimeout(timer)
  }, [voiceOn, prompt, sayRaw])

  const choose = async (roleKey) => {
    setPicked(roleKey)
    setRole(roleKey)
    setUser((u) => u || { name: lang === 'hi' ? 'मेहमान' : 'Guest', role: roleKey })

    const go = () => navigate(HOME_FOR[roleKey] || '/shop')

    let welcome = null
    try {
      welcome = await voiceWelcome(roleKey, lang)
    } catch { /* the app works without the greeting */ }

    if (!welcome?.text || !voiceOn) { go(); return }

    // Navigate when the greeting FINISHES, not on a timer. Racing a timer
    // against speech is what made the app cut itself off after "welcome to".
    // The whole line is shown on screen meanwhile, with a way to skip.
    const skip = sayProtected(welcome.text, { onDone: go })
    setGreeting({ text: welcome.text, skip })
  }

  // Leaving the screen must not leave a half-spoken greeting behind.
  useEffect(() => () => { greetingRef.current?.skip?.() }, [])

  return (
    <>
      <div
        className="app-body no-nav"
        style={{
          background: 'var(--ink)', color: '#fff', padding: 0,
          display: 'flex', flexDirection: 'column',
        }}
      >
        <div style={{ padding: '26px 20px 20px' }}>
          <div className="row-between" style={{ marginBottom: 26 }}>
            <div className="row" style={{ gap: 9 }}>
              <div
                style={{
                  width: 38, height: 38, borderRadius: 11, background: 'var(--marigold)',
                  display: 'grid', placeItems: 'center', fontSize: 'calc(19px * var(--font-scale))',
                }}
              >
                🪡
              </div>
              <div>
                <div style={{ fontFamily: 'var(--font-display)', fontSize: 'calc(20px * var(--font-scale))', fontWeight: 700, letterSpacing: '0.02em' }}>
                  PAVHAN
                </div>
                <div style={{ fontSize: 'calc(9.5px * var(--font-scale))', color: '#a9b1cf', letterSpacing: '0.08em', textTransform: 'uppercase' }}>
                  AI-Powered Growth for Artisan Craft
                </div>
              </div>
            </div>
            <div className="row" style={{ gap: 7 }}>
              <button
                className="topbar-btn"
                onClick={() => setLang(lang === 'hi' ? 'en' : 'hi')}
                style={{ fontSize: 'calc(12px * var(--font-scale))', fontWeight: 700 }}
              >
                {lang === 'hi' ? 'अ' : 'A'}
              </button>
              <button
                className={`topbar-btn ${voiceOn ? 'on' : ''}`}
                onClick={() => { if (voiceOn) assistant.cancel(); setVoiceOn(!voiceOn) }}
              >
                {voiceOn ? '🔊' : '🔇'}
              </button>
            </div>
          </div>

          <h2
            style={{ fontSize: 'calc(27px * var(--font-scale))', lineHeight: 1.24, color: '#fff', marginBottom: 10 }}
            lang={lang}
          >
            {lang === 'hi' ? (
              <>आपकी कारीगरी,<br /><span style={{ color: 'var(--marigold)' }}>आपका पूरा दाम।</span></>
            ) : (
              <>Your craft.<br /><span style={{ color: 'var(--marigold)' }}>Your full price.</span></>
            )}
          </h2>
          <p style={{ fontSize: 'calc(13.5px * var(--font-scale))', color: '#b9c0dc', lineHeight: 1.65, margin: '0 0 4px' }} lang={lang}>
            {lang === 'hi'
              ? 'बस बोलिए और एक फोटो खींचिए। विवरण, सही कीमत और खरीदार — तीनों हम तैयार कर देंगे।'
              : 'Just speak and take one photo. The listing, a fair price and matched buyers all follow.'}
          </p>

          {stats && (
            <div className="row" style={{ gap: 16, marginTop: 18, flexWrap: 'wrap' }}>
              {[
                [stats.artisans, lang === 'hi' ? 'कारीगर' : 'artisans'],
                [stats.products, lang === 'hi' ? 'सामान' : 'listings'],
                [stats.regions_covered, lang === 'hi' ? 'क्षेत्र' : 'clusters'],
                [`${stats.artisan_share_percent}%`, lang === 'hi' ? 'कारीगर को' : 'to the maker'],
              ].map(([n, label]) => (
                <div key={label}>
                  <div className="mono" style={{ fontSize: 'calc(19px * var(--font-scale))', fontWeight: 800, color: 'var(--marigold)' }}>
                    {n}
                  </div>
                  <div style={{ fontSize: 'calc(10px * var(--font-scale))', color: '#98a0c0', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div
          style={{
            background: 'var(--paper)', color: 'var(--ink)',
            borderRadius: '28px 28px 0 0', padding: '22px 16px 34px',
            flex: 1, minHeight: 380,
          }}
        >
          <div className="section-title" lang={lang}>
            {lang === 'hi' ? 'आप यहाँ किस काम से आए हैं?' : 'What brings you here?'}
          </div>
          <div className="section-sub" style={{ marginBottom: 15 }} lang={lang}>
            {prompt || (lang === 'hi'
              ? 'अपना चुनाव कीजिए — ऐप उसी हिसाब से चलेगा।'
              : 'Pick one — the whole app adapts to your answer.')}
          </div>

          <div className="stack">
            {roles.map((r, i) => (
              <button
                key={r.key}
                onClick={() => choose(r.key)}
                className="card fade-up"
                style={{
                  display: 'flex', alignItems: 'center', gap: 13, textAlign: 'left',
                  animationDelay: `${i * 60}ms`,
                  borderColor: picked === r.key ? r.accent : 'var(--line)',
                  borderWidth: picked === r.key ? 2 : 1,
                  boxShadow: picked === r.key ? `0 6px 22px ${r.accent}33` : 'var(--shadow-1)',
                }}
              >
                <div
                  style={{
                    width: 46, height: 46, borderRadius: 14, display: 'grid',
                    placeItems: 'center', fontSize: 'calc(23px * var(--font-scale))', background: `${r.accent}1a`,
                  }}
                >
                  {r.icon}
                </div>
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(15px * var(--font-scale))' }} lang={lang}>
                    {lang === 'hi' ? r.title_hi : r.title}
                  </div>
                  <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', color: 'var(--muted)', marginTop: 2 }} lang={lang}>
                    {lang === 'hi' ? r.subtitle_hi : r.subtitle}
                  </div>
                </div>
                <div style={{ color: r.accent, fontSize: 'calc(19px * var(--font-scale))' }}>
                  {picked === r.key ? '✓' : '→'}
                </div>
              </button>
            ))}
          </div>

          <button
            className="btn btn-soft btn-block"
            style={{ marginTop: 16 }}
            onClick={() => navigate('/login')}
          >
            📱 {lang === 'hi' ? 'मोबाइल नंबर से खाता बनाइए' : 'Sign in with your mobile number'}
          </button>

          <p
            className="center muted"
            style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 14, lineHeight: 1.6 }}
            lang={lang}
          >
            {lang === 'hi'
              ? '🔊 आवाज़ वाली मदद चालू है — हर पन्ने पर मैं बताता रहूँगा कि क्या करना है।'
              : '🔊 The voice guide is on — it explains every screen as you go.'}
          </p>
        </div>
      </div>
      {greeting && (
        <div
          style={{
            position: 'absolute', inset: 0, zIndex: 120,
            background: 'rgba(11, 10, 13, 0.93)', color: '#fff',
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            justifyContent: 'center', padding: '32px 28px', textAlign: 'center',
          }}
        >
          <div style={{ fontSize: 'calc(44px * var(--font-scale))', marginBottom: 18, animation: 'floaty 2.6s ease-in-out infinite' }}>
            🗣️
          </div>
          <p
            lang={lang}
            style={{
              fontSize: 'calc(16px * var(--font-scale))', lineHeight: 1.85, maxWidth: 360, margin: '0 0 26px',
              fontFamily: lang === 'hi' ? 'var(--font-hi)' : 'var(--font-ui)',
            }}
          >
            {greeting.text}
          </p>
          <button
            className="btn btn-gold"
            onClick={() => { greeting.skip?.() }}
            style={{ minWidth: 170 }}
          >
            {lang === 'hi' ? 'आगे बढ़िए →' : 'Continue →'}
          </button>
          <div style={{ fontSize: 'calc(11px * var(--font-scale))', color: '#9aa0bd', marginTop: 14 }} lang={lang}>
            {lang === 'hi' ? 'सुनकर अपने आप आगे बढ़ जाएगा' : 'It continues on its own when the line ends'}
          </div>
        </div>
      )}
      <Toasts />
    </>
  )
}
