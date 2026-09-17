import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Bar, Empty, Loading, Money, ProductCard, ScoreRing, VoiceOrb, useScreenVoice } from '../components/ui'
import { artisanEnquiries, dashboard, listUsers, marketContext } from '../api/client'

export default function ArtisanHome() {
  const navigate = useNavigate()
  const { t, lang, user, setUser, scripts, sayRaw, L, P } = useApp()
  const [data, setData] = useState(null)
  const [enquiries, setEnquiries] = useState([])
  const [market, setMarket] = useState(null)
  const [loading, setLoading] = useState(true)

  useScreenVoice('artisan_home')

  useEffect(() => {
    let alive = true
    async function load() {
      try {
        // A demo opens straight into a real artisan's account rather than an
        // empty one, so the dashboard has something to say from second one.
        let artisanId = user?.id
        if (!artisanId) {
          const artisans = await listUsers('artisan')
          artisanId = artisans[0]?.id
          if (alive && artisans[0]) setUser({ ...artisans[0] })
        }
        if (!artisanId) return
        const [dash, enq, mkt] = await Promise.all([
          dashboard(artisanId),
          artisanEnquiries(artisanId).catch(() => ({ enquiries: [] })),
          marketContext().catch(() => null),
        ])
        if (!alive) return
        setData(dash)
        setEnquiries(enq.enquiries || [])
        setMarket(mkt)
      } finally {
        if (alive) setLoading(false)
      }
    }
    load()
    return () => { alive = false }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return (
      <>
        <TopBar title="PAVHAN" subtitle={t('कारीगर खाता', 'Artisan account')} />
        <Screen><Loading /></Screen>
      </>
    )
  }

  const s = data?.stats
  const tips = scripts?.tips?.artisan || []

  return (
    <>
      <TopBar
        title={data?.artisan?.name || 'PAVHAN'}
        subtitle={`${L(data?.artisan?.craft_focus) || ''} · ${L(data?.artisan?.region) || ''}`}
      />
      <Screen>
        <div className="page stack">
          {/* Earnings — the number that matters most to an artisan */}
          <div
            className="card fade-up"
            style={{
              background: 'linear-gradient(150deg, var(--ink) 0%, var(--ink-2) 100%)',
              color: '#fff', border: 0,
            }}
          >
            <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', color: '#b0b8d8', fontWeight: 600 }} lang={lang}>
              {t('अब तक आपकी कमाई', 'Your earnings so far')}
            </div>
            <div className="mono" style={{ fontSize: 'calc(31px * var(--font-scale))', fontWeight: 800, margin: '3px 0 8px' }}>
              <Money value={s?.earnings} />
            </div>
            {s?.extra_vs_middleman > 0 && (
              <div
                style={{
                  fontSize: 'calc(12px * var(--font-scale))', background: 'rgba(224,146,47,0.16)', color: 'var(--marigold)',
                  padding: '7px 11px', borderRadius: 10, lineHeight: 1.5, fontWeight: 600,
                }}
                lang={lang}
              >
                {t(
                  `बिचौलिये के मुक़ाबले ₹${Math.round(s.extra_vs_middleman).toLocaleString('en-IN')} ज़्यादा — यानी ${Math.round(s.uplift_percent)}% बढ़त।`,
                  `${Math.round(s.uplift_percent)}% more than a middleman would have paid — ₹${Math.round(s.extra_vs_middleman).toLocaleString('en-IN')} extra.`,
                )}
              </div>
            )}
            <div className="row" style={{ gap: 18, marginTop: 14 }}>
              {[
                [s?.products, t('सामान', 'listings')],
                [s?.orders, t('ऑर्डर', 'orders')],
                [s?.total_views, t('देखा गया', 'views')],
                [s?.open_enquiries, t('पूछताछ', 'enquiries')],
              ].map(([n, label]) => (
                <div key={label}>
                  <div className="mono" style={{ fontSize: 'calc(17px * var(--font-scale))', fontWeight: 800 }}>{n ?? 0}</div>
                  <div style={{ fontSize: 'calc(9.5px * var(--font-scale))', color: '#98a0c0', textTransform: 'uppercase' }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          </div>

          {/* Primary action */}
          <button
            className="btn btn-primary btn-block fade-up"
            style={{ padding: '17px', fontSize: 'calc(16px * var(--font-scale))' }}
            onClick={() => navigate('/add')}
          >
            🎤 {t('बोलकर नया सामान डालिए', 'Add a product by voice')}
          </button>

          <button
            className="card row fade-up"
            style={{ gap: 12, width: '100%', textAlign: 'left' }}
            onClick={() => navigate('/assistant')}
          >
            <div style={{ width: 42, height: 42, borderRadius: 13, flexShrink: 0,
                          background: 'var(--marigold-soft)', display: 'grid',
                          placeItems: 'center', fontSize: 'calc(21px * var(--font-scale))' }}>🪡</div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))' }} lang={lang}>
                {t('पवन सहायक से पूछिए', 'Ask the PAVHAN assistant')}
              </div>
              <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 2 }} lang={lang}>
                {t('दाम, कमाई, फोटो — कुछ भी पूछिए', 'Prices, earnings, photos — ask anything')}
              </div>
            </div>
            <span style={{ color: 'var(--muted)' }}>›</span>
          </button>

          {market && (
            <div className="card tinted fade-up">
              <div className="row-between">
                <div>
                  <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))' }} lang={lang}>
                    {t('अभी बाज़ार कैसा है', "This month's market")}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 2 }}>
                    {market.season_label}
                  </div>
                </div>
                <div className="pill gold mono">{market.demand_index}×</div>
              </div>
              <div style={{ marginTop: 10 }}>
                <Bar
                  value={Math.min(100, (market.demand_index - 0.85) * 240)}
                  tone="var(--marigold)"
                />
              </div>
              <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 7, lineHeight: 1.5 }} lang={lang}>
                {market.demand_index >= 1.05
                  ? t('माँग ऊपर है — अभी सामान डालने का सही समय है।',
                       'Demand is up — this is a good month to list.')
                  : t('माँग सामान्य है। त्योहार से पहले दाम बेहतर मिलेंगे।',
                       'Demand is steady. Prices strengthen closer to the festival season.')}
              </div>
            </div>
          )}

          {enquiries.length > 0 && (
            <div className="stack" style={{ gap: 9 }}>
              <div className="row-between">
                <div className="section-title" lang={lang}>
                  {t('खरीदारों की पूछताछ', 'Buyer enquiries')}
                </div>
                <button className="btn btn-soft btn-sm" onClick={() => navigate('/artisan/buyers')}>
                  {t('सब देखिए', 'See all')}
                </button>
              </div>
              {enquiries.slice(0, 2).map((e) => (
                <div key={e.id} className="card row fade-up" style={{ gap: 11 }}>
                  <div style={{ fontSize: 'calc(24px * var(--font-scale))' }}>{e.buyer.logo}</div>
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }}>{e.buyer.name}</div>
                    <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))' }}>
                      {e.quantity} × {P(e.product, 'title').slice(0, 26)}…
                    </div>
                  </div>
                  <div className="pill leaf mono"><Money value={e.estimated_value} /></div>
                </div>
              ))}
            </div>
          )}

          {/* Everything an artisan does between listings. */}
          <div className="grid-2">
            {[
              ['/earnings', '💰', t('मेरी कमाई', 'My earnings')],
              ['/requirements', '📋', t('खरीदारों की माँग', 'Buyer requirements')],
              ['/pooling', '👥', t('मिलकर ऑर्डर लीजिए', 'Take an order together')],
              ['/artisan/buyers', '🤝', t('मेल खाते खरीदार', 'Matched buyers')],
              ['/fairs', '🎪', t('मेला मोड', 'Fair mode')],
              ['/impact', '🏛️', t('योजना का असर', 'Scheme impact')],
            ].map(([to, icon, label]) => (
              <button key={to} className="card fade-up" onClick={() => navigate(to)}
                      style={{ textAlign: 'left', padding: '13px 12px' }}>
                <div style={{ fontSize: 'calc(21px * var(--font-scale))' }}>{icon}</div>
                <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))', marginTop: 6, lineHeight: 1.35 }}
                     lang={lang}>
                  {label}
                </div>
              </button>
            ))}
          </div>

          <div className="row-between" style={{ marginTop: 4 }}>
            <div className="section-title" lang={lang}>{t('आपका सामान', 'Your products')}</div>
            <button className="btn btn-soft btn-sm" onClick={() => navigate('/artisan/products')}>
              {t('सब देखिए', 'See all')}
            </button>
          </div>

          {data?.top_products?.length ? (
            <div className="stack" style={{ gap: 10 }}>
              {data.top_products.slice(0, 3).map((p) => (
                <button
                  key={p.id}
                  className="card row fade-up"
                  style={{ gap: 12, textAlign: 'left', width: '100%' }}
                  onClick={() => navigate(`/product/${p.id}`)}
                >
                  <ScoreRing value={p.quality_score} size={46} label={t('गुण', 'quality')} />
                  <div style={{ flex: 1, minWidth: 0 }}>
                    <div lang={lang} style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.3 }}>{P(p, 'title')}</div>
                    <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 3 }}>
                      👁 {p.views} · <Money value={p.price} />
                    </div>
                  </div>
                  <span style={{ color: 'var(--muted)' }}>›</span>
                </button>
              ))}
            </div>
          ) : (
            <Empty
              title={t('अभी कुछ नहीं डाला', 'Nothing listed yet')}
              body={t('बोलकर अपना पहला सामान डालिए — दो मिनट लगेंगे।',
                      'Add your first product by voice — it takes two minutes.')}
              action={
                <button className="btn btn-primary" onClick={() => navigate('/add')}>
                  🎤 {t('शुरू कीजिए', 'Start')}
                </button>
              }
            />
          )}

          {tips.length > 0 && (
            <div className="card tinted fade-up">
              <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 8 }} lang={lang}>
                💡 {t('ज़्यादा बेचने के लिए', 'To sell more')}
              </div>
              <div className="stack" style={{ gap: 8 }}>
                {tips.slice(0, 3).map((tip) => (
                  <button
                    key={tip}
                    onClick={() => sayRaw(tip)}
                    style={{
                      background: 'none', border: 0, padding: 0, textAlign: 'left',
                      fontSize: 'calc(12.5px * var(--font-scale))', lineHeight: 1.55, color: 'var(--ink-soft)',
                      display: 'flex', gap: 7,
                    }}
                    lang={lang}
                  >
                    <span style={{ color: 'var(--marigold)' }}>▸</span>
                    <span>{tip}</span>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
        <VoiceOrb script="artisan_home" />
      </Screen>
    </>
  )
}
