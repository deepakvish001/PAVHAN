import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Bar, Loading, rupees } from '../components/ui'
import { artisanStalls, createStall, listFairs, listUsers, stallPerformance } from '../api/client'

/**
 * Making a fair last longer than the fair.
 *
 * The problem statement's own diagnosis is that exhibitions give "a temporary
 * boost" and what artisans lack is year-round access. The gap is concrete: a
 * visitor who admired a shawl at Surajkund in February has no way to find that
 * weaver in March. A card at the stall closes it — scan once, and the artisan
 * is on your phone permanently.
 *
 * The counter afterwards measures the thing that matters: orders that arrived
 * AFTER the fair closed.
 */
export default function FairMode() {
  const { t, lang, user, setUser, toast } = useApp()
  const [fairs, setFairs] = useState([])
  const [stalls, setStalls] = useState([])
  const [performance, setPerformance] = useState({})
  const [selected, setSelected] = useState(null)
  const [stallNumber, setStallNumber] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    let alive = true
    async function load() {
      let id = user?.id
      if (!id) {
        const artisans = await listUsers('artisan').catch(() => [])
        id = artisans[0]?.id
        if (artisans[0]) setUser(artisans[0])
      }
      const [f, s] = await Promise.all([
        listFairs().catch(() => ({ fairs: [] })),
        id ? artisanStalls(id).catch(() => ({ stalls: [] })) : { stalls: [] },
      ])
      if (!alive) return
      setFairs(f.fairs || [])
      setStalls(s.stalls || [])
      setLoading(false)
      ;(s.stalls || []).forEach((card) => {
        stallPerformance(card.code)
          .then((p) => setPerformance((prev) => ({ ...prev, [card.code]: p })))
          .catch(() => {})
      })
    }
    load()
    return () => { alive = false }
  }, []) // eslint-disable-line

  const makeCard = async () => {
    if (!user?.id) return
    setBusy(true)
    try {
      const card = await createStall({
        artisan_id: user.id, exhibition_id: selected, stall_number: stallNumber,
      })
      setStalls((prev) => prev.some((s) => s.code === card.code) ? prev : [...prev, card])
      toast(t('स्टॉल कार्ड बन गया।', 'Stall card created.'), 'ok')
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)

  return (
    <>
      <TopBar
        title={t('मेला मोड', 'Fair mode')}
        subtitle={t('भीड़ को साल भर का ग्राहक बनाइए', 'Turn footfall into year-round customers')}
        back
      />
      <Screen>
        <div className="page stack">
          <div className="card tinted">
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 6 }} lang={lang}>
              {t('मेला दो हफ़्ते का होता है — ग्राहक हमेशा का',
                 'A fair lasts a fortnight. A customer should not.')}
            </div>
            <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.65 }} lang={lang}>
              {t('अपने स्टॉल पर यह कार्ड लगाइए। जो कोई स्कैन करेगा, उसके फ़ोन में आपकी दुकान '
                 + 'हमेशा के लिए आ जाएगी — मेला ख़त्म होने के बाद भी वह आपसे ख़रीद सकेगा।',
                 'Print this card and tape it to your stall. Anyone who scans it keeps your '
                 + 'shop on their phone — and can still buy from you after the fair ends.')}
            </div>
          </div>

          {stalls.map((card) => {
            const perf = performance[card.code]
            return (
              <div key={card.code} className="card">
                <div className="row-between" style={{ marginBottom: 11 }}>
                  <div>
                    <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))' }}>
                      {card.exhibition || t('स्थायी कार्ड', 'Standing card')}
                    </div>
                    <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 2 }}>
                      {card.stall_number && `${t('स्टॉल', 'Stall')} ${card.stall_number} · `}
                      <span className="mono">{card.code}</span>
                    </div>
                  </div>
                </div>

                <div style={{ background: '#fff', padding: 14, borderRadius: 14,
                              display: 'grid', placeItems: 'center' }}>
                  <img src={card.qr_svg_url} alt={t('स्टॉल का क्यूआर', 'Stall QR code')}
                       style={{ width: '100%', maxWidth: 210, display: 'block' }} />
                  <div className="mono" style={{ fontSize: 'calc(11px * var(--font-scale))', color: '#161B33',
                                                 marginTop: 8, letterSpacing: '0.1em' }}>
                    {card.code}
                  </div>
                </div>

                <div className="row" style={{ gap: 14, marginTop: 13 }}>
                  {[
                    [perf?.scans ?? card.scans, t('स्कैन', 'scans')],
                    [perf?.follows ?? card.follows, t('जुड़े', 'follows')],
                    [perf?.orders_after_fair ?? card.orders_after_fair,
                     t('मेले के बाद ऑर्डर', 'orders after')],
                  ].map(([n, label]) => (
                    <div key={label} style={{ flex: 1 }}>
                      <div className="mono" style={{ fontSize: 'calc(17px * var(--font-scale))', fontWeight: 800 }}>{n}</div>
                      <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase',
                                                      lineHeight: 1.3 }} lang={lang}>{label}</div>
                    </div>
                  ))}
                </div>

                {perf && (
                  <>
                    <div style={{ marginTop: 11 }}>
                      <Bar value={perf.follow_rate_percent} tone="var(--marigold)" height={5} />
                      <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', marginTop: 5 }} lang={lang}>
                        {t(`${perf.follow_rate_percent}% स्कैन करने वालों ने आपको फ़ॉलो किया`,
                           `${perf.follow_rate_percent}% of scanners followed you`)}
                      </div>
                    </div>
                    <div style={{ marginTop: 11, padding: '10px 12px', borderRadius: 11,
                                  background: perf.orders_after_fair ? 'var(--leaf-soft)'
                                                                     : 'var(--paper-2)',
                                  fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.65 }} lang={lang}>
                      {lang === 'hi' ? perf.reading_hi : perf.reading}
                    </div>
                  </>
                )}

                <a className="btn btn-soft btn-block btn-sm" style={{ marginTop: 11,
                   textDecoration: 'none' }} href={card.url} target="_blank" rel="noreferrer">
                  {t('देखिए ग्राहक को क्या दिखेगा', 'See what a visitor sees')} ↗
                </a>
              </div>
            )
          })}

          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
              {t('नया स्टॉल कार्ड बनाइए', 'Create a stall card')}
            </div>
            <div className="stack" style={{ gap: 11 }}>
              <div className="field">
                <label>{t('कौन सा मेला?', 'Which fair?')}</label>
                <select className="select" value={selected || ''}
                        onChange={(e) => setSelected(e.target.value || null)}>
                  <option value="">{t('कोई नहीं — स्थायी कार्ड', 'None — standing card')}</option>
                  {fairs.map((f) => (
                    <option key={f.id} value={f.id}>
                      {lang === 'hi' ? f.name_hi || f.name : f.name} · {f.city}
                    </option>
                  ))}
                </select>
              </div>
              <div className="field">
                <label>{t('स्टॉल नंबर (अगर पता हो)', 'Stall number (if you know it)')}</label>
                <input className="input" value={stallNumber} placeholder="A-42"
                       onChange={(e) => setStallNumber(e.target.value)} />
              </div>
              <button className="btn btn-primary btn-block" onClick={makeCard} disabled={busy}>
                {busy ? <span className="spinner" /> : t('कार्ड बनाइए', 'Create the card')}
              </button>
            </div>
          </div>

          <div>
            <div className="section-title" lang={lang}>{t('आने वाले मेले', 'Fairs')}</div>
            <div className="stack" style={{ gap: 9, marginTop: 9 }}>
              {fairs.map((f) => (
                <div key={f.id} className="card">
                  <div className="row-between">
                    <div style={{ flex: 1 }}>
                      <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }}>
                        {lang === 'hi' ? f.name_hi || f.name : f.name}
                      </div>
                      <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 2 }}>
                        {f.venue} · {f.city}
                      </div>
                      <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', marginTop: 3 }}>
                        {f.organiser}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span className={`pill ${f.state === 'running' ? 'leaf'
                        : f.state === 'upcoming' ? 'gold' : ''}`} lang={lang}>
                        {f.state === 'running' ? t('चल रहा है', 'running')
                          : f.state === 'upcoming' ? t('आने वाला', 'upcoming')
                          : t('ख़त्म', 'finished')}
                      </span>
                      <div className="mono muted" style={{ fontSize: 'calc(10px * var(--font-scale))', marginTop: 5 }}>
                        {(f.annual_footfall / 100000).toFixed(1)}L {t('लोग', 'visitors')}
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      </Screen>
    </>
  )
}
