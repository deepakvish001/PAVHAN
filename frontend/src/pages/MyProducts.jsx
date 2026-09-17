import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, Money, ProductImage, ScoreRing, SkeletonCard, rupees } from '../components/ui'
import { listProducts, listUsers, priceForProduct } from '../api/client'

export default function MyProducts() {
  const navigate = useNavigate()
  const { t, lang, user, setUser, L, P } = useApp()
  const [products, setProducts] = useState(null)
  const [repriced, setRepriced] = useState({})

  useEffect(() => {
    let alive = true
    async function load() {
      let id = user?.id
      if (!id) {
        const artisans = await listUsers('artisan').catch(() => [])
        id = artisans[0]?.id
        if (artisans[0]) setUser(artisans[0])
      }
      const rows = await listProducts({ artisan_id: id, limit: 60 }).catch(() => [])
      if (alive) setProducts(rows)
    }
    load()
    return () => { alive = false }
  }, []) // eslint-disable-line

  const checkPrice = async (product) => {
    try {
      const res = await priceForProduct(product.id)
      setRepriced((r) => ({ ...r, [product.id]: res }))
    } catch { /* the listing still works without a re-check */ }
  }

  return (
    <>
      <TopBar title={t('मेरा सामान', 'My products')} subtitle={products ? `${products.length}` : ''} />
      <Screen>
        <div className="page stack">
          {!products ? (
            <><SkeletonCard /><SkeletonCard /><SkeletonCard /></>
          ) : products.length === 0 ? (
            <Empty
              title={t('अभी कुछ नहीं डाला', 'Nothing listed yet')}
              body={t('बोलकर अपना पहला सामान डालिए।', 'Add your first piece by voice.')}
              action={
                <button className="btn btn-primary" onClick={() => navigate('/add')}>
                  🎤 {t('शुरू कीजिए', 'Start')}
                </button>
              }
            />
          ) : (
            products.map((p) => {
              const rp = repriced[p.id]
              return (
                <div key={p.id} className="card fade-up">
                  <button
                    className="row"
                    style={{ gap: 12, width: '100%', textAlign: 'left', background: 'none', border: 0, padding: 0 }}
                    onClick={() => navigate(`/product/${p.id}`)}
                  >
                    <ProductImage product={p} height={78} style={{ width: 78 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div lang={lang} style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))', lineHeight: 1.3 }}>{P(p, 'title')}</div>
                      <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', margin: '3px 0 6px' }}>
                        {L(p.material)} · {L(p.region)}
                      </div>
                      <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                        <span className="pill gold"><Money value={p.price} /></span>
                        <span className="pill">👁 {p.views}</span>
                        <span className="pill">{t('बचे', 'stock')} {p.stock}</span>
                      </div>
                    </div>
                    <ScoreRing value={p.quality_score} size={44} />
                  </button>

                  {rp ? (
                    <div
                      style={{
                        marginTop: 11, padding: '10px 12px', borderRadius: 11,
                        background: Math.abs(rp.delta_percent) < 5 ? 'var(--leaf-soft)' : '#fdf6ee',
                        border: `1px solid ${Math.abs(rp.delta_percent) < 5 ? '#bcdbd1' : '#e8d3b4'}`,
                        fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.55,
                      }}
                      lang={lang}
                    >
                      {Math.abs(rp.delta_percent) < 5
                        ? t('✅ आपका दाम अभी भी सही है।', '✅ Your price is still right.')
                        : t(
                            `📈 अभी बाज़ार ${rupees(rp.recommended)} कह रहा है (${rp.delta_percent > 0 ? '+' : ''}${rp.delta_percent}%). ${rp.season_label_hi || rp.season_label}।`,
                            `📈 The market now says ${rupees(rp.recommended)} (${rp.delta_percent > 0 ? '+' : ''}${rp.delta_percent}%). ${rp.season_label}.`,
                          )}
                    </div>
                  ) : (
                    <button
                      className="btn btn-soft btn-sm btn-block"
                      style={{ marginTop: 10 }}
                      onClick={() => checkPrice(p)}
                    >
                      📈 {t('दाम अब भी सही है? जाँचिए', 'Is my price still right?')}
                    </button>
                  )}
                </div>
              )
            })
          )}
        </div>
      </Screen>
    </>
  )
}
