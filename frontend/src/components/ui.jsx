import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'

export const rupees = (n) =>
  `₹${Number(n || 0).toLocaleString('en-IN', { maximumFractionDigits: 0 })}`

export function Money({ value, className = '' }) {
  return <span className={`mono ${className}`}>{rupees(value)}</span>
}

export function Loading({ label }) {
  const { t } = useApp()
  return (
    <div className="center" style={{ padding: '46px 18px', color: 'var(--muted)' }}>
      <div className="spinner dark" style={{ margin: '0 auto 12px' }} />
      <div style={{ fontSize: 'calc(13.5px * var(--font-scale))' }}>{label || t('एक पल…', 'One moment…')}</div>
    </div>
  )
}

export function SkeletonCard() {
  return (
    <div className="card" style={{ display: 'flex', gap: 12 }}>
      <div className="skeleton" style={{ width: 82, height: 82, borderRadius: 14 }} />
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: 8, paddingTop: 4 }}>
        <div className="skeleton" style={{ height: 15, width: '80%' }} />
        <div className="skeleton" style={{ height: 12, width: '55%' }} />
        <div className="skeleton" style={{ height: 12, width: '35%' }} />
      </div>
    </div>
  )
}

export function Empty({ icon = '🪡', title, body, action }) {
  return (
    <div className="center" style={{ padding: '48px 22px' }}>
      <div style={{ fontSize: 'calc(44px * var(--font-scale))', marginBottom: 10, animation: 'floaty 3.4s ease-in-out infinite' }}>
        {icon}
      </div>
      <h3 style={{ fontSize: 'calc(17px * var(--font-scale))', marginBottom: 6 }}>{title}</h3>
      {body && (
        <p className="muted" style={{ fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.6, margin: '0 0 16px' }}>
          {body}
        </p>
      )}
      {action}
    </div>
  )
}

export function ErrorNote({ error, onRetry }) {
  const { t } = useApp()
  if (!error) return null
  return (
    <div className="card" style={{ borderColor: '#f0cbc6', background: '#fdf4f3' }}>
      <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))', color: 'var(--madder-dark)', marginBottom: 4 }}>
        {t('कुछ गड़बड़ हुई', 'Something went wrong')}
      </div>
      <div style={{ fontSize: 'calc(13px * var(--font-scale))', lineHeight: 1.55, color: 'var(--ink-soft)' }}>
        {String(error.message || error)}
      </div>
      {onRetry && (
        <button className="btn btn-soft btn-sm" style={{ marginTop: 11 }} onClick={onRetry}>
          {t('दोबारा कोशिश', 'Try again')}
        </button>
      )}
    </div>
  )
}

/** Gauge used for quality / match / confidence scores. */
export function ScoreRing({ value, size = 54, label, tone }) {
  const pct = Math.max(0, Math.min(100, Number(value) || 0))
  const colour = tone
    || (pct >= 80 ? 'var(--leaf)' : pct >= 55 ? 'var(--marigold)' : 'var(--madder)')
  return (
    <div style={{ width: size, textAlign: 'center' }}>
      <div
        style={{
          width: size, height: size, borderRadius: '50%',
          background: `conic-gradient(${colour} ${pct * 3.6}deg, var(--paper-2) 0deg)`,
          display: 'grid', placeItems: 'center',
        }}
      >
        <div
          style={{
            width: size - 11, height: size - 11, borderRadius: '50%', background: '#fff',
            display: 'grid', placeItems: 'center',
            fontSize: size > 48 ? 14 : 12, fontWeight: 800, color: colour,
          }}
          className="mono"
        >
          {Math.round(pct)}
        </div>
      </div>
      {label && (
        <div style={{ fontSize: 'calc(9.5px * var(--font-scale))', marginTop: 4, color: 'var(--muted)', fontWeight: 700 }}>
          {label}
        </div>
      )}
    </div>
  )
}

export function Bar({ value, tone = 'var(--indigo)', height = 6 }) {
  return (
    <div style={{ background: 'var(--paper-2)', borderRadius: 99, height, overflow: 'hidden' }}>
      <div
        style={{
          width: `${Math.max(2, Math.min(100, value))}%`, height: '100%',
          background: tone, borderRadius: 99, transition: 'width 0.5s cubic-bezier(.2,.8,.2,1)',
        }}
      />
    </div>
  )
}

export function Stepper({ steps, current }) {
  return (
    <div style={{ display: 'flex', gap: 5, padding: '11px 16px 3px' }}>
      {steps.map((s, i) => (
        <div key={s} style={{ flex: 1 }}>
          <div
            style={{
              height: 4, borderRadius: 99,
              background: i < current ? 'var(--marigold)'
                : i === current ? 'var(--madder)' : 'var(--line)',
              transition: 'background 0.3s',
            }}
          />
          <div
            style={{
              fontSize: 'calc(9px * var(--font-scale))', marginTop: 5, fontWeight: 700, textAlign: 'center',
              color: i === current ? 'var(--madder)' : 'var(--muted)',
              overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap',
            }}
          >
            {s}
          </div>
        </div>
      ))}
    </div>
  )
}

/** Product artwork with a graceful, craft-coloured fallback. */
export function ProductImage({ product, height = 96, radius = 14, style = {} }) {
  const [failed, setFailed] = useState(false)
  const src = product?.images?.[0]
  const swatch = product?.palette?.[0]?.hex || '#c9b89a'

  if (!src || failed) {
    return (
      <div
        style={{
          height, borderRadius: radius, flexShrink: 0,
          background: `linear-gradient(140deg, ${swatch} 0%, #f3ece0 100%)`,
          display: 'grid', placeItems: 'center', fontSize: height > 120 ? 38 : 24,
          ...style,
        }}
      >
        🪡
      </div>
    )
  }
  return (
    <img
      src={src}
      alt={product?.title || ''}
      loading="lazy"
      onError={() => setFailed(true)}
      style={{
        height, borderRadius: radius, objectFit: 'cover', flexShrink: 0,
        background: 'var(--paper-2)', ...style,
      }}
    />
  )
}

export function ProductCard({ product, onClick, compact = false }) {
  const navigate = useNavigate()
  const { t, L, P, lang } = useApp()
  const go = onClick || (() => navigate(`/product/${product.id}`))
  // The card is where most people meet a listing, so it is the first place
  // that has to be in their language.
  const title = P(product, 'title')

  if (compact) {
    return (
      <button
        onClick={go}
        className="card flush fade-up"
        style={{ width: 158, textAlign: 'left', flexShrink: 0, border: '1px solid var(--line)' }}
      >
        <ProductImage product={product} height={116} radius={0} style={{ width: '100%' }} />
        <div style={{ padding: '9px 10px 11px' }}>
          <div lang={lang} style={{ fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 700, lineHeight: 1.35, minHeight: 34 }}>
            {title.length > 38 ? `${title.slice(0, 36)}…` : title}
          </div>
          <div style={{ fontSize: 'calc(10.5px * var(--font-scale))', color: 'var(--muted)', margin: '3px 0 6px' }}>
            {L(product.region)}
          </div>
          <Money value={product.price} className="" />
        </div>
      </button>
    )
  }

  return (
    <button
      onClick={go}
      className="card fade-up"
      style={{ display: 'flex', gap: 12, textAlign: 'left', width: '100%', alignItems: 'stretch' }}
    >
      <ProductImage product={product} height={86} style={{ width: 86 }} />
      <div style={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column', gap: 4 }}>
        <div lang={lang} style={{ fontWeight: 700, fontSize: 'calc(14.5px * var(--font-scale))', lineHeight: 1.3 }}>{title}</div>
        <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', color: 'var(--muted)' }}>
          {L(product.craft_type)} · {L(product.region)}
        </div>
        <div className="row" style={{ gap: 6, flexWrap: 'wrap', marginTop: 'auto' }}>
          <span className="pill gold"><Money value={product.price} /></span>
          {product.gi_tagged && <span className="pill leaf">GI</span>}
          {product.stock <= 3 && product.stock > 0 && (
            <span className="pill madder">
              {t(`बस ${product.stock} बचे`, `${product.stock} left`)}
            </span>
          )}
        </div>
      </div>
    </button>
  )
}

/** Floating voice-guide button — the assistant is reachable on every screen. */
export function VoiceOrb({ script, fields, text }) {
  const { say, sayRaw, assistant, voiceOn, t, scripts } = useApp()
  const [hint, setHint] = useState(false)

  const replay = () => {
    if (assistant.speaking) { assistant.cancel(); return }
    if (text) sayRaw(text)
    else if (script) say(script, { fields, once: false })
    setHint(true)
    setTimeout(() => setHint(false), 2400)
  }

  if (!assistant.supported) return null
  const available = text || scripts?.screens?.[script]
  if (!available) return null

  return (
    <div style={{ position: 'absolute', right: 14, bottom: 'calc(var(--nav-h) + 18px)', zIndex: 60 }}>
      {hint && (
        <div
          className="fade-up"
          style={{
            position: 'absolute', right: 60, bottom: 8, background: 'var(--ink)', color: '#fff',
            padding: '7px 11px', borderRadius: 11, fontSize: 'calc(11.5px * var(--font-scale))', whiteSpace: 'nowrap',
            boxShadow: 'var(--shadow-2)',
          }}
        >
          {t('सुनिए…', 'Listening guide…')}
        </div>
      )}
      <button
        onClick={replay}
        aria-label={t('मदद सुनिए', 'Hear the guide')}
        style={{
          width: 50, height: 50, borderRadius: '50%', border: '3px solid var(--paper)',
          background: voiceOn ? 'var(--ink)' : 'var(--muted)', color: '#fff', fontSize: 'calc(20px * var(--font-scale))',
          boxShadow: 'var(--shadow-2)',
          animation: assistant.speaking ? 'pulseRing 1.5s infinite' : 'none',
        }}
      >
        {assistant.speaking ? '⏸' : '🗣️'}
      </button>
    </div>
  )
}

/** Speak a screen's script once, when the screen mounts. */
export function useScreenVoice(screen, fields, deps = []) {
  const { say, scripts } = useApp()
  const fired = useRef(false)
  useEffect(() => {
    if (!scripts || fired.current) return
    fired.current = true
    const timer = setTimeout(() => say(screen, { fields }), 520)
    return () => clearTimeout(timer)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [scripts, screen, ...deps])
}
