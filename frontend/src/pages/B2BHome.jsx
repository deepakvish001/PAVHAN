import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Bar, Empty, Loading, ProductImage, VoiceOrb, rupees, useScreenVoice } from '../components/ui'
import { buyerRecommendations, listBuyers } from '../api/client'

/**
 * The B2B side. A bulk buyer picks the profile that matches their business and
 * immediately sees artisan pieces ranked by fit against THEIR sourcing rules —
 * the mirror image of the artisan's buyer-matching screen.
 */
export default function B2BHome() {
  const navigate = useNavigate()
  const { t, lang, L } = useApp()
  const [buyers, setBuyers] = useState([])
  const [active, setActive] = useState(null)
  const [recs, setRecs] = useState(null)
  const [loading, setLoading] = useState(true)

  useScreenVoice('b2b_home')

  useEffect(() => {
    listBuyers().then((rows) => {
      setBuyers(rows)
      if (rows.length) setActive(rows[0])
    }).catch(() => {}).finally(() => setLoading(false))
  }, [])

  useEffect(() => {
    if (!active) return
    setRecs(null)
    buyerRecommendations(active.id).then(setRecs).catch(() => {})
  }, [active])

  if (loading) return (<><TopBar title="PAVHAN B2B" /><Screen><Loading /></Screen></>)

  return (
    <>
      <TopBar
        title={t('थोक ख़रीद', 'Bulk sourcing')}
        subtitle={active ? `${active.name}` : ''}
      />
      <Screen>
        <div className="page stack">
          <div>
            <div className="section-title" lang={lang}>
              {t('आपका व्यापार किस तरह का है?', 'Which buyer profile fits you?')}
            </div>
            <div className="section-sub" style={{ marginBottom: 10 }} lang={lang}>
              {t('चुनिए — सामान आपके नियमों के हिसाब से छाँटा जाएगा।',
                 'Pick one and the catalogue is ranked against your sourcing rules.')}
            </div>
            <div className="scroll-x">
              {buyers.map((b) => (
                <button
                  key={b.id}
                  onClick={() => setActive(b)}
                  className="card"
                  style={{
                    width: 152, flexShrink: 0, textAlign: 'left', padding: 12,
                    borderColor: active?.id === b.id ? 'var(--indigo)' : 'var(--line)',
                    borderWidth: active?.id === b.id ? 2 : 1,
                  }}
                >
                  <div style={{ fontSize: 'calc(21px * var(--font-scale))' }}>{b.logo}</div>
                  <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))', marginTop: 5, lineHeight: 1.3 }}>
                    {b.name}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginTop: 3 }}>
                    {L(b.org_type)} · {L(b.city)}
                  </div>
                </button>
              ))}
            </div>
          </div>

          {active && (
            <div className="card tinted">
              <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 8 }}>
                {active.logo} {active.name}
              </div>
              <p className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.6, margin: '0 0 11px' }}>
                {active.notes}
              </p>
              {[
                [t('बजट', 'Budget'), `${rupees(active.budget_min)} – ${rupees(active.budget_max)}`],
                [t('सामान्य मात्रा', 'Typical order'), `${active.typical_order_qty} ${t('पीस', 'pcs')}`],
                [t('अधिकतम समय', 'Max lead time'), `${active.max_lead_time_days} ${t('दिन', 'days')}`],
                [t('श्रेणियाँ', 'Categories'), active.categories.map(L).join(', ')],
                [t('पसंदीदा क्षेत्र', 'Regions'),
                 active.preferred_regions.map(L).join(', ') || t('कोई भी', 'Any')],
                [t('प्रमाणपत्र', 'Certifications'), active.certifications.join(', ') || '—'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="row-between"
                  style={{ fontSize: 'calc(12px * var(--font-scale))', padding: '6px 0', borderTop: '1px solid var(--line)' }}
                >
                  <span className="muted">{label}</span>
                  <span style={{ fontWeight: 600, textAlign: 'right', maxWidth: '60%' }}>{value}</span>
                </div>
              ))}
              <div className="row" style={{ gap: 12, marginTop: 11 }}>
                <div style={{ flex: 1 }}>
                  <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginBottom: 4 }}>
                    🌱 {t('पर्यावरण को महत्व', 'Sustainability weight')}
                  </div>
                  <Bar value={active.values_sustainability} tone="var(--leaf)" height={5} />
                </div>
                <div style={{ flex: 1 }}>
                  <div className="muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginBottom: 4 }}>
                    🏅 {t('जीआई को महत्व', 'GI weight')}
                  </div>
                  <Bar value={active.values_gi_tag} tone="var(--marigold)" height={5} />
                </div>
              </div>
            </div>
          )}

          <div className="row-between">
            <div className="section-title" lang={lang}>
              {t('आपके लिए छाँटा हुआ', 'Ranked for you')}
            </div>
            <button className="btn btn-soft btn-sm" onClick={() => navigate('/search')}>
              {t('खोजिए', 'Search')}
            </button>
          </div>

          {!recs ? (
            <Loading label={t('मिलान किया जा रहा है…', 'Matching the catalogue…')} />
          ) : recs.results.length === 0 ? (
            <Empty title={t('कुछ नहीं मिला', 'No matches')} />
          ) : (
            recs.results.map((r) => (
              <button
                key={r.product_id}
                className="card row fade-up"
                style={{ gap: 12, textAlign: 'left', width: '100%' }}
                onClick={() => navigate(`/product/${r.product_id}`)}
              >
                <ProductImage product={{ images: [r.image] }} height={74} style={{ width: 74 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.3 }}>{r.title}</div>
                  <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', margin: '3px 0 6px' }}>
                    {L(r.craft_type)} · {L(r.region)} · MOQ {r.moq}
                  </div>
                  <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                    <span className="pill gold mono">{rupees(r.unit_price)}/{t('पीस', 'pc')}</span>
                    <span className="pill">{r.suggested_quantity} {t('पीस', 'pcs')}</span>
                  </div>
                </div>
                <div className="center" style={{ width: 44 }}>
                  <div
                    className="mono"
                    style={{
                      fontSize: 'calc(16px * var(--font-scale))', fontWeight: 800,
                      color: r.score >= 82 ? 'var(--leaf)' : r.score >= 68 ? 'var(--marigold)' : 'var(--muted)',
                    }}
                  >
                    {r.score}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(8.5px * var(--font-scale))', textTransform: 'uppercase' }}>
                    {t('मेल', 'fit')}
                  </div>
                </div>
              </button>
            ))
          )}
        </div>
        <VoiceOrb script="b2b_home" />
      </Screen>
    </>
  )
}
