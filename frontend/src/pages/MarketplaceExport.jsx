import { useEffect, useState } from 'react'
import { useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Bar, Loading, ScoreRing } from '../components/ui'
import {
  exportDownloadUrl, exportFormats, exportPackage, exportReadiness, getProduct,
} from '../api/client'

/**
 * Getting a listing onto a government e-marketplace.
 *
 * The honest position, stated on the screen itself: everything up to the
 * submission is done here — field mapping, HSN classification, the statutory
 * declarations — and the final push needs a registered seller account that is
 * granted to an organisation, not issued to an app. What this removes from
 * the artisan is the part they could never do alone.
 */
export default function MarketplaceExport() {
  const { id } = useParams()
  const { t, lang, toast } = useApp()
  const [product, setProduct] = useState(null)
  const [report, setReport] = useState(null)
  const [formats, setFormats] = useState([])
  const [preview, setPreview] = useState(null)
  const [active, setActive] = useState('gem')
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      getProduct(id).catch(() => null),
      exportReadiness(id).catch(() => null),
      exportFormats().catch(() => ({ formats: [] })),
    ]).then(([p, r, f]) => {
      setProduct(p); setReport(r); setFormats(f.formats || []); setLoading(false)
    })
  }, [id])

  useEffect(() => {
    if (active === 'csv') { setPreview(null); return }
    exportPackage(id, active).then(setPreview).catch(() => setPreview(null))
  }, [id, active])

  if (loading) return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)

  const blocking = report?.blocking || []
  const warnings = report?.warnings || []

  return (
    <>
      <TopBar
        title={t('सरकारी बाज़ार', 'Government marketplace')}
        subtitle={product?.title}
        back
      />
      <Screen>
        <div className="page stack">
          <div className="card">
            <div className="row" style={{ gap: 13, alignItems: 'flex-start' }}>
              <ScoreRing value={report?.score ?? 0} label={t('तैयारी', 'ready')} />
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 700, fontSize: 'calc(14.5px * var(--font-scale))' }} lang={lang}>
                  {report?.ready
                    ? t('यह सामान भेजने लायक तैयार है', 'This listing is submission-ready')
                    : t('कुछ जानकारी बाकी है', 'A few things are still missing')}
                </div>
                <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 4 }}>
                  {t(`एचएसएन कोड ${report?.hsn_code} — ${report?.hsn_description}`,
                     `HSN ${report?.hsn_code} — ${report?.hsn_description}`)}
                </div>
              </div>
            </div>
          </div>

          {blocking.length > 0 && (
            <div className="card" style={{ background: 'var(--marigold-soft)',
                                           borderColor: 'var(--line)' }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 8 }} lang={lang}>
                {t('इनके बिना पोर्टल स्वीकार नहीं करेगा', 'The portal will reject it without these')}
              </div>
              {blocking.map((b) => (
                <div key={b.field} className="row" style={{ gap: 8, alignItems: 'flex-start',
                                                            marginBottom: 7 }}>
                  <span>⚠️</span>
                  <div>
                    <div style={{ fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 600 }}>{b.field}</div>
                    <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.5 }} lang={lang}>
                      {lang === 'hi' ? b.reason_hi : b.reason}
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )}

          {warnings.length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 8 }} lang={lang}>
                💡 {t('ये जोड़ने से बिक्री बढ़ेगी', 'These would help it sell')}
              </div>
              {warnings.map((w) => (
                <div key={w.field} className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.6 }}
                     lang={lang}>
                  • {lang === 'hi' ? w.reason_hi : w.reason}
                </div>
              ))}
            </div>
          )}

          <div>
            <div className="section-title" lang={lang}>{t('प्रारूप चुनिए', 'Choose a format')}</div>
            <div className="chiprow" style={{ marginTop: 9 }}>
              {formats.map((f) => (
                <button key={f.key} className={`chip ${active === f.key ? 'active' : ''}`}
                        onClick={() => setActive(f.key)}>
                  {f.name}
                </button>
              ))}
            </div>
            <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 8 }}
                 lang={lang}>
              {(() => {
                const f = formats.find((x) => x.key === active)
                return f ? (lang === 'hi' ? f.description_hi : f.description) : ''
              })()}
            </div>
          </div>

          <a
            className="btn btn-primary btn-block"
            href={exportDownloadUrl(id, active)}
            download
            style={{ padding: 15, textDecoration: 'none' }}
            onClick={() => toast(t('फ़ाइल डाउनलोड हो रही है।', 'Downloading the package.'), 'ok')}
          >
            ⬇ {t('पैकेज डाउनलोड कीजिए', 'Download the package')}
          </a>

          {preview && (
            <div className="card">
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
                {t('क्या भेजा जाएगा', 'What gets submitted')}
              </div>
              <pre
                style={{
                  fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.6, overflowX: 'auto', margin: 0,
                  background: 'var(--paper-2)', padding: 12, borderRadius: 10,
                  maxHeight: 320, color: 'var(--ink-soft)',
                }}
              >
                {JSON.stringify(preview, null, 2).slice(0, 2600)}
              </pre>
            </div>
          )}

          <div className="card tinted">
            <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))', marginBottom: 6 }} lang={lang}>
              {t('साफ़-साफ़ बात', 'Being straight with you')}
            </div>
            <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.7, color: 'var(--ink-soft)' }} lang={lang}>
              {lang === 'hi' ? report?.note_hi : report?.note}
            </div>
          </div>
        </div>
      </Screen>
    </>
  )
}
