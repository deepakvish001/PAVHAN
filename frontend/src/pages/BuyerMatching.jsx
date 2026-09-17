import { useEffect, useState } from 'react'
import { useSearchParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, Loading, ProductImage, VoiceOrb, rupees, useScreenVoice } from '../components/ui'
import { BuyerMatchCard } from './AddProduct'
import { listProducts, listUsers, matchBuyers, sendEnquiry } from '../api/client'

/**
 * The screen that used to say "select a product" and then show nothing.
 * Now it always has a product selected, and every match is scored against it.
 */
export default function BuyerMatching() {
  const [params] = useSearchParams()
  const { t, lang, user, setUser, toast, P } = useApp()
  const [products, setProducts] = useState([])
  const [selected, setSelected] = useState(params.get('product') || null)
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [sent, setSent] = useState({})

  useScreenVoice('buyer_match')

  useEffect(() => {
    let alive = true
    async function load() {
      let id = user?.id
      if (!id) {
        const artisans = await listUsers('artisan').catch(() => [])
        id = artisans[0]?.id
        if (artisans[0]) setUser(artisans[0])
      }
      const rows = await listProducts({ artisan_id: id, limit: 40 }).catch(() => [])
      if (!alive) return
      setProducts(rows)
      // Never leave the screen empty: pick the first product automatically.
      if (!selected && rows.length) setSelected(rows[0].id)
      if (!rows.length) setLoading(false)
    }
    load()
    return () => { alive = false }
  }, []) // eslint-disable-line

  useEffect(() => {
    if (!selected) return
    setLoading(true)
    matchBuyers(selected, { limit: 10 })
      .then(setData)
      .catch((err) => toast(err.message, 'err'))
      .finally(() => setLoading(false))
  }, [selected]) // eslint-disable-line

  const enquire = async (match) => {
    try {
      await sendEnquiry({
        product_id: selected, buyer_id: match.buyer_id,
        quantity: match.suggested_quantity, message: match.pitch,
      })
      setSent((s) => ({ ...s, [`${selected}:${match.buyer_id}`]: true }))
      toast(t(`${match.name} को संदेश भेज दिया।`, `Enquiry sent to ${match.name}.`), 'ok')
    } catch (err) {
      toast(err.message, 'err')
    }
  }

  return (
    <>
      <TopBar
        title={t('खरीदार मिलान', 'Buyer matching')}
        subtitle={data ? `${data.summary.buyers_scored} ${t('खरीदार परखे', 'buyers scored')}` : ''}
      />
      <Screen>
        <div className="page stack">
          {products.length === 0 && !loading ? (
            <Empty
              icon="🤝"
              title={t('पहले कुछ सामान डालिए', 'List something first')}
              body={t('खरीदार आपके सामान के हिसाब से ही ढूँढे जाते हैं।',
                      'Buyers are matched against a specific piece, so we need one first.')}
            />
          ) : (
            <>
              <div>
                <div className="section-title" lang={lang}>
                  {t('किस सामान के लिए?', 'Which piece?')}
                </div>
                <div className="scroll-x" style={{ marginTop: 9 }}>
                  {products.map((p) => (
                    <button
                      key={p.id}
                      onClick={() => setSelected(p.id)}
                      className="card flush"
                      style={{
                        width: 118, flexShrink: 0, textAlign: 'left',
                        borderColor: selected === p.id ? 'var(--madder)' : 'var(--line)',
                        borderWidth: selected === p.id ? 2 : 1,
                      }}
                    >
                      <ProductImage product={p} height={72} radius={0} style={{ width: '100%' }} />
                      <div style={{ padding: '7px 8px 9px' }}>
                        <div style={{ fontSize: 'calc(10.5px * var(--font-scale))', fontWeight: 700, lineHeight: 1.35, minHeight: 28 }}>
                          {(() => { const ttl = P(p, 'title')
                            return ttl.length > 30 ? `${ttl.slice(0, 28)}…` : ttl })()}
                        </div>
                        <div className="mono muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginTop: 3 }}>
                          {rupees(p.price)}
                        </div>
                      </div>
                    </button>
                  ))}
                </div>
              </div>

              {loading ? (
                <Loading label={t('खरीदार परखे जा रहे हैं…', 'Scoring buyers…')} />
              ) : data ? (
                <>
                  <div className="card tinted row" style={{ gap: 14 }}>
                    {[
                      [data.summary.strong_matches, t('पक्के मेल', 'strong')],
                      [data.summary.best_score, t('सबसे अच्छा अंक', 'best score')],
                      [rupees(data.summary.total_opportunity), t('कुल मौका', 'opportunity')],
                    ].map(([n, label]) => (
                      <div key={label} style={{ flex: 1 }}>
                        <div className="mono" style={{ fontSize: 'calc(15px * var(--font-scale))', fontWeight: 800 }}>{n}</div>
                        <div className="muted" style={{ fontSize: 'calc(9px * var(--font-scale))', textTransform: 'uppercase', lineHeight: 1.3 }}>
                          {label}
                        </div>
                      </div>
                    ))}
                  </div>

                  {data.categories?.length > 0 && (
                    <div className="card">
                      <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
                        {t('खरीदारों की श्रेणियाँ', 'Buyer categories')}
                      </div>
                      {data.categories.map((g) => (
                        <div
                          key={g.category}
                          className="row-between"
                          style={{ fontSize: 'calc(12.5px * var(--font-scale))', padding: '7px 0', borderTop: '1px solid var(--line)' }}
                        >
                          <span style={{ fontWeight: 600 }}>{g.category}</span>
                          <span className="row" style={{ gap: 7 }}>
                            <span className="muted">{g.count}</span>
                            <span className="pill mono">{g.best_score}</span>
                          </span>
                        </div>
                      ))}
                    </div>
                  )}

                  <div className="section-title" lang={lang}>
                    {t('मेल खाते खरीदार', 'Matched buyers')}
                  </div>
                  {data.matches.map((m) => (
                    <BuyerMatchCard
                      key={m.buyer_id}
                      match={m}
                      sent={sent[`${selected}:${m.buyer_id}`]}
                      onEnquire={() => enquire(m)}
                    />
                  ))}
                </>
              ) : null}
            </>
          )}
        </div>
        <VoiceOrb script="buyer_match" />
      </Screen>
    </>
  )
}
