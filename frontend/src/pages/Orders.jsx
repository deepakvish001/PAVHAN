import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, Loading, ProductImage, rupees } from '../components/ui'
import { advanceOrder, artisanOrders, listUsers } from '../api/client'

/**
 * Orders, with the stage they are at.
 *
 * "Digitize their inventory" is only half done if an artisan can list a piece
 * but cannot see what happened to it afterwards. The timeline matters for a
 * second reason too: a buyer who can watch "being made → despatched" does not
 * telephone to ask, and the artisan gets their afternoon back.
 */
export default function Orders() {
  const { t, lang, user, setUser, toast, P } = useApp()
  const navigate = useNavigate()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(null)

  const load = async () => {
    let id = user?.id
    if (!id) {
      const artisans = await listUsers('artisan').catch(() => [])
      id = artisans[0]?.id
      if (artisans[0]) setUser(artisans[0])
    }
    if (!id) { setLoading(false); return }
    const rows = await artisanOrders(id).catch(() => null)
    setData(rows)
    setLoading(false)
  }

  useEffect(() => { load() }, []) // eslint-disable-line

  const advance = async (order, nextStage) => {
    setBusy(order.id)
    try {
      await advanceOrder(order.id, nextStage)
      toast(t('ऑर्डर की स्थिति बदल दी।', 'Order updated.'), 'ok')
      await load()
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setBusy(null)
    }
  }

  if (loading) return (<><TopBar title="…" /><Screen><Loading /></Screen></>)

  const stages = data?.stages || []
  const orders = data?.orders || []

  return (
    <>
      <TopBar
        title={t('ऑर्डर', 'Orders')}
        subtitle={data ? t(`${data.summary.open} चल रहे`, `${data.summary.open} open`) : ''}
      />
      <Screen>
        <div className="page stack">
          {data && (
            <div className="card tinted row" style={{ gap: 14 }}>
              {[
                [data.summary.total, t('कुल', 'total')],
                [data.summary.open, t('चल रहे', 'open')],
                [rupees(data.summary.earnings), t('कमाई', 'earned')],
              ].map(([n, label]) => (
                <div key={label} style={{ flex: 1 }}>
                  <div className="mono" style={{ fontSize: 'calc(16px * var(--font-scale))', fontWeight: 800 }}>{n}</div>
                  <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase' }}
                       lang={lang}>{label}</div>
                </div>
              ))}
            </div>
          )}

          {orders.length === 0 ? (
            <Empty icon="📦" title={t('अभी कोई ऑर्डर नहीं', 'No orders yet')}
                   body={t('सामान डालते रहिए — खरीदार आएँगे।',
                           'Keep listing; the buyers will come.')} />
          ) : (
            orders.map((o) => {
              const done = o.stage_index
              const nextStage = stages[done + 1]
              return (
                <div key={o.id} className="card fade-up">
                  <div className="row" style={{ gap: 12, alignItems: 'flex-start' }}>
                    <ProductImage product={{ images: [o.product?.image] }} height={62}
                                  style={{ width: 62 }} />
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div lang={lang} style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.3 }}>
                        {P(o.product, 'title') || t('सामान', 'Product')}
                      </div>
                      <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 3 }}>
                        {o.customer_name} · {o.quantity} {t('पीस', 'pcs')}
                        {o.channel === 'b2b' && ` · ${t('थोक', 'bulk')}`}
                      </div>
                      <div className="row" style={{ gap: 6, marginTop: 6, flexWrap: 'wrap' }}>
                        <span className="pill gold mono">{rupees(o.amount)}</span>
                        <span className="pill leaf mono">
                          {t('आपको', 'you get')} {rupees(o.artisan_payout)}
                        </span>
                      </div>
                    </div>
                  </div>

                  {/* The timeline. Five dots is enough to see where a thing is. */}
                  <div className="row" style={{ gap: 3, marginTop: 14 }}>
                    {stages.map((s, i) => (
                      <div key={s.key} style={{ flex: 1 }}>
                        <div style={{ height: 4, borderRadius: 99,
                          background: i <= done ? 'var(--leaf)' : 'var(--line)' }} />
                        <div style={{ fontSize: 'calc(8.5px * var(--font-scale))', marginTop: 5, textAlign: 'center',
                                      fontWeight: 700, lineHeight: 1.25,
                                      color: i <= done ? 'var(--leaf)' : 'var(--muted)' }}
                             lang={lang}>
                          {lang === 'hi' ? s.label_hi : s.label}
                        </div>
                      </div>
                    ))}
                  </div>

                  {/* The two things an order actually needs doing to it. An
                      order that can only be re-labelled is a status board; one
                      that can be paid for and despatched is a business. */}
                  <div className="row" style={{ gap: 8, marginTop: 12 }}>
                    <button className="btn btn-primary btn-sm" style={{ flex: 1 }}
                            onClick={() => navigate(`/orders/${o.id}/pay`)}>
                      💰 {t('पैसा', 'Get paid')}
                    </button>
                    <button className="btn btn-soft btn-sm" style={{ flex: 1 }}
                            onClick={() => navigate(`/orders/${o.id}/ship`)}>
                      📦 {t('भेजिए', 'Send it')}
                    </button>
                  </div>

                  {nextStage && o.status !== 'cancelled' && (
                    <button className="btn btn-ghost btn-sm btn-block" style={{ marginTop: 8 }}
                            onClick={() => advance(o, nextStage.key)}
                            disabled={busy === o.id}>
                      {busy === o.id ? <span className="spinner dark" />
                        : `→ ${t('अगला:', 'Mark as:')} ${lang === 'hi' ? nextStage.label_hi : nextStage.label}`}
                    </button>
                  )}

                  {o.timeline?.length > 0 && (
                    <div style={{ marginTop: 11, paddingTop: 10,
                                  borderTop: '1px solid var(--line)' }}>
                      {o.timeline.slice(-3).map((entry, i) => (
                        <div key={i} className="row-between muted"
                             style={{ fontSize: 'calc(10.5px * var(--font-scale))', padding: '2px 0' }}>
                          <span>{entry.note}</span>
                          <span className="mono">
                            {new Date(entry.at).toLocaleDateString('en-IN',
                              { day: 'numeric', month: 'short' })}
                          </span>
                        </div>
                      ))}
                    </div>
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
