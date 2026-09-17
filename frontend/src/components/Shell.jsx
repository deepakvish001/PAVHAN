import { useLocation, useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'

export function TopBar({ title, subtitle, back, right, onBack }) {
  const navigate = useNavigate()
  const { lang, setLang, voiceOn, setVoiceOn, assistant, theme, toggleTheme } = useApp()

  return (
    <header className="topbar">
      {back && (
        <button
          className="topbar-btn"
          onClick={() => (onBack ? onBack() : navigate(-1))}
          aria-label={lang === 'hi' ? 'पीछे जाइए' : 'Go back'}
        >
          ←
        </button>
      )}
      <div style={{ flex: 1, minWidth: 0 }}>
        <h1 style={{ overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {title}
        </h1>
        {subtitle && <div className="sub">{subtitle}</div>}
      </div>
      {right}
      <button
        className="topbar-btn"
        onClick={toggleTheme}
        aria-label={theme === 'dark' ? 'Switch to light mode' : 'Switch to dark mode'}
        title={theme === 'dark' ? 'Light mode' : 'Dark mode'}
      >
        {theme === 'dark' ? '☀️' : '🌙'}
      </button>
      <button
        className="topbar-btn"
        onClick={() => setLang(lang === 'hi' ? 'en' : 'hi')}
        aria-label="Switch language"
        title={lang === 'hi' ? 'Switch to English' : 'हिंदी में बदलिए'}
        style={{ fontSize: 'calc(12px * var(--font-scale))', fontWeight: 700 }}
      >
        {lang === 'hi' ? 'अ' : 'A'}
      </button>
      <button
        className={`topbar-btn ${voiceOn ? 'on' : ''}`}
        onClick={() => { if (voiceOn) assistant.cancel(); setVoiceOn(!voiceOn) }}
        aria-label={voiceOn ? 'Mute the voice guide' : 'Unmute the voice guide'}
        title={voiceOn ? 'Voice guide on' : 'Voice guide off'}
      >
        {voiceOn ? (assistant.speaking ? '🔊' : '🔉') : '🔇'}
      </button>
    </header>
  )
}

const NAV = {
  artisan: [
    { to: '/artisan', icon: '🏠', label_hi: 'घर', label_en: 'Home' },
    { to: '/artisan/products', icon: '📦', label_hi: 'मेरा सामान', label_en: 'Products' },
    { to: '/add', icon: '🎤', label_hi: 'नया', label_en: 'Add', primary: true },
    { to: '/orders', icon: '📦', label_hi: 'ऑर्डर', label_en: 'Orders' },
    { to: '/profile', icon: '👤', label_hi: 'खाता', label_en: 'Profile' },
  ],
  customer: [
    { to: '/shop', icon: '🏠', label_hi: 'घर', label_en: 'Home' },
    { to: '/search', icon: '🔍', label_hi: 'खोजें', label_en: 'Search' },
    { to: '/profile', icon: '👤', label_hi: 'खाता', label_en: 'Profile' },
  ],
  b2b: [
    { to: '/b2b', icon: '🏬', label_hi: 'घर', label_en: 'Home' },
    { to: '/search', icon: '🔍', label_hi: 'खोजें', label_en: 'Sourcing' },
    { to: '/profile', icon: '👤', label_hi: 'खाता', label_en: 'Profile' },
  ],
}
NAV.exporter = NAV.b2b

export function BottomNav() {
  const { role, lang } = useApp()
  const navigate = useNavigate()
  const { pathname } = useLocation()
  const items = NAV[role] || NAV.customer

  return (
    <nav className="bottomnav">
      {items.map((item) => {
        const active = pathname === item.to
          || (item.to !== '/' && pathname.startsWith(item.to) && !item.primary)
        return (
          <button
            key={item.to}
            className={`${active ? 'active' : ''} ${item.primary ? 'primary' : ''}`}
            onClick={() => navigate(item.to)}
          >
            <span className="ico">{item.icon}</span>
            <span>{lang === 'hi' ? item.label_hi : item.label_en}</span>
          </button>
        )
      })}
    </nav>
  )
}

export function Toasts() {
  const { toasts } = useApp()
  if (!toasts.length) return null
  return (
    <div className="toast-wrap" role="status" aria-live="polite">
      {toasts.map((t) => (
        <div key={t.id} className={`toast ${t.tone}`}>{t.message}</div>
      ))}
    </div>
  )
}

/** A quiet strip that only appears when there is something to say. */
export function StatusStrip() {
  const { pwa, lang, t, outboxCount } = useApp()
  const navigate = useNavigate()

  // Offline with work waiting is the case worth naming precisely. "It will
  // sync" is a promise the app can only keep because the outbox exists, so
  // the strip says how many pieces are waiting and opens the queue.
  if (!pwa.online && outboxCount > 0) {
    return (
      <button
        onClick={() => navigate('/outbox')}
        style={{
          padding: '7px 14px', fontSize: 'calc(11.5px * var(--font-scale))', fontWeight: 700,
          textAlign: 'center', width: '100%', border: 0,
          background: 'var(--marigold)', color: 'var(--ink)',
        }}
        lang={lang}
        role="status"
      >
        {t(`इंटरनेट नहीं — ${outboxCount} सामान भेजने बाकी। सिग्नल आते ही चले जाएँगे ›`,
           `No internet — ${outboxCount} item${outboxCount === 1 ? '' : 's'} waiting. They go when the signal returns ›`)}
      </button>
    )
  }

  if (pwa.online && outboxCount > 0) {
    return (
      <button
        onClick={() => navigate('/outbox')}
        style={{
          padding: '7px 14px', fontSize: 'calc(11.5px * var(--font-scale))', fontWeight: 700,
          textAlign: 'center', width: '100%', border: 0,
          background: 'var(--indigo)', color: '#fff',
        }}
        lang={lang}
        role="status"
      >
        {t(`${outboxCount} सामान भेजे जा रहे हैं ›`,
           `Sending ${outboxCount} item${outboxCount === 1 ? '' : 's'} ›`)}
      </button>
    )
  }

  if (pwa.online && !pwa.updateReady) return null
  return (
    <div
      style={{
        padding: '7px 14px', fontSize: 'calc(11.5px * var(--font-scale))', fontWeight: 600, textAlign: 'center',
        background: pwa.online ? 'var(--leaf)' : 'var(--clay)', color: '#fff',
      }}
      lang={lang}
      role="status"
    >
      {pwa.online
        ? (
          <button onClick={pwa.applyUpdate}
                  style={{ background: 'none', border: 0, color: '#fff', fontWeight: 700 }}>
            {t('नया संस्करण तैयार है — दबाकर चालू कीजिए', 'A new version is ready — tap to load it')}
          </button>
        )
        : t('इंटरनेट नहीं है — सहेजी हुई जानकारी दिख रही है। काम करते रहिए।',
             'No internet — showing saved data. Keep working; it will sync.')}
    </div>
  )
}

export function Screen({ children, nav = true, className = '' }) {
  return (
    <>
      <StatusStrip />
      <main id="main" className={`app-body ${nav ? '' : 'no-nav'} ${className}`}>
        {children}
      </main>
      {nav && <BottomNav />}
      <Toasts />
    </>
  )
}
