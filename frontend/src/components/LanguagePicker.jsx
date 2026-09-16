import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { voiceLanguages } from '../api/client'

/**
 * Which language the artisan will SPEAK.
 *
 * Deliberately separate from the interface language. A Tamil weaver may well
 * read the app in English but describe her work in Tamil, and forcing one
 * choice to serve both would make her pick the wrong one. Whatever goes in,
 * the listing comes out in English and Hindi.
 */
export default function LanguagePicker({ value, onChange, compact = false }) {
  const { t, lang } = useApp()
  const [languages, setLanguages] = useState([])
  const [open, setOpen] = useState(false)

  useEffect(() => {
    voiceLanguages().then((d) => setLanguages(d.languages || [])).catch(() => {})
  }, [])

  const current = languages.find((l) => l.code === value)

  if (compact) {
    return (
      <select
        className="select"
        value={value}
        onChange={(e) => onChange(e.target.value)}
        style={{ width: 'auto', padding: '8px 10px', fontSize: 13 }}
        aria-label={t('बोलने की भाषा', 'Speaking language')}
      >
        {languages.map((l) => (
          <option key={l.code} value={l.code}>{l.native}</option>
        ))}
      </select>
    )
  }

  return (
    <div className="card">
      <button
        onClick={() => setOpen(!open)}
        style={{ background: 'none', border: 0, padding: 0, width: '100%',
                 textAlign: 'left', display: 'flex', alignItems: 'center', gap: 10 }}
      >
        <span style={{ fontSize: 20 }}>🗣️</span>
        <div style={{ flex: 1 }}>
          <div style={{ fontSize: 11.5, fontWeight: 700, color: 'var(--ink-soft)' }} lang={lang}>
            {t('आप किस भाषा में बोलेंगे?', 'Which language will you speak?')}
          </div>
          <div style={{ fontSize: 15, fontWeight: 700, marginTop: 2 }}>
            {current?.native || '—'}
            {current && current.code !== 'en' && (
              <span className="muted" style={{ fontSize: 12, fontWeight: 500 }}>
                {'  '}· {current.name}
              </span>
            )}
          </div>
        </div>
        <span style={{ color: 'var(--muted)' }}>{open ? '▾' : '▸'}</span>
      </button>

      {open && (
        <div className="fade-up" style={{ marginTop: 11 }}>
          <div className="row" style={{ gap: 7, flexWrap: 'wrap' }}>
            {languages.map((l) => (
              <button
                key={l.code}
                className={`chip ${value === l.code ? 'active' : ''}`}
                style={{ padding: '9px 13px', fontSize: 13.5 }}
                onClick={() => { onChange(l.code); setOpen(false) }}
              >
                {l.native}
              </button>
            ))}
          </div>
          <div className="muted" style={{ fontSize: 11, lineHeight: 1.6, marginTop: 10 }} lang={lang}>
            {t('किसी भी भाषा में बोलिए — विवरण अंग्रेज़ी और हिंदी, दोनों में बनेगा।',
               'Speak in any of these — your listing is written in English and Hindi either way.')}
          </div>
        </div>
      )}
    </div>
  )
}
