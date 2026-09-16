import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Bar, Empty, Loading, rupees } from '../components/ui'
import {
  artisanQuotes, listProducts, listRequirements, listUsers, sendQuote,
} from '../api/client'

/**
 * What buyers are asking for, ranked for this artisan.
 *
 * Buyer matching told an artisan who might want a piece they had already
 * made. This is the other direction, and it is the one that produces orders:
 * a buyer states a need, and the artisans who can serve it answer with a
 * price. Ranked, because nobody should read forty postings to find the two
 * they can actually fulfil.
 */
export default function Requirements() {
  const { t, lang, user, setUser, toast } = useApp()
  const [requirements, setRequirements] = useState([])
  const [quotes, setQuotes] = useState([])
  const [products, setProducts] = useState([])
  const [tab, setTab] = useState('open')
  const [quoting, setQuoting] = useState(null)
  const [form, setForm] = useState({ unit_price: '', quantity: '', lead_time_days: '', message: '' })
  const [busy, setBusy] = useState(false)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    let id = user?.id
    if (!id) {
      const artisans = await listUsers('artisan').catch(() => [])
      id = artisans[0]?.id
      if (artisans[0]) setUser(artisans[0])
    }
    if (!id) { setLoading(false); return }
    const [r, q, p] = await Promise.all([
      listRequirements(id).catch(() => ({ requirements: [] })),
      artisanQuotes(id).catch(() => ({ quotes: [] })),
      listProducts({ artisan_id: id, limit: 40 }).catch(() => []),
    ])
    setRequirements(r.requirements || [])
    setQuotes(q.quotes || [])
    setProducts(p)
    setLoading(false)
  }

  useEffect(() => { load() }, []) // eslint-disable-line

  const openQuote = (req) => {
    const mine = products.find((p) => p.craft_type === req.craft_type) || products[0]
    setQuoting(req)
    setForm({
      unit_price: mine ? String(Math.round(mine.price * 0.85)) : '',
      quantity: String(req.quantity),
      lead_time_days: String(Math.min(req.delivery_days, 30)),
      message: '',
      product_id: mine?.id || null,
    })
  }

  const submit = async () => {
    setBusy(true)
    try {
      const res = await sendQuote({
        requirement_id: quoting.id,
        artisan_id: user.id,
        product_id: form.product_id || null,
        unit_price: Number(form.unit_price),
        quantity: Number(form.quantity),
        lead_time_days: Number(form.lead_time_days) || 15,
        message: form.message,
      })
      toast(lang === 'hi' ? res.message_hi : res.message, 'ok', 5000)
      setQuoting(null)
      await load()
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setBusy(false)
    }
  }

  if (loading) return (<><TopBar title="…" /><Screen><Loading /></Screen></>)

  return (
    <>
      <TopBar
        title={t('खरीदारों की माँग', 'Buyer requirements')}
        subtitle={t(`${requirements.length} खुली माँगें`, `${requirements.length} open`)}
      />
      <Screen>
        <div className="page stack">
          <div className="chiprow">
            <button className={`chip ${tab === 'open' ? 'active' : ''}`}
                    onClick={() => setTab('open')}>
              {t('खुली माँगें', 'Open requirements')}
            </button>
            <button className={`chip ${tab === 'mine' ? 'active' : ''}`}
                    onClick={() => setTab('mine')}>
              {t('मेरे भेजे भाव', 'My quotes')} {quotes.length > 0 && `· ${quotes.length}`}
            </button>
          </div>

          {tab === 'open' && (requirements.length === 0 ? (
            <Empty icon="📋" title={t('अभी कोई माँग नहीं', 'No open requirements')} />
          ) : requirements.map((r) => (
            <div key={r.id} className="card fade-up">
              <div className="row-between" style={{ alignItems: 'flex-start' }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))', lineHeight: 1.35 }}>
                    {r.title}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 4 }}>
                    {r.buyer?.logo} {r.buyer?.name} · {r.buyer?.city}
                  </div>
                </div>
                {r.fit_score > 0 && (
                  <div className="center" style={{ width: 44 }}>
                    <div className="mono" style={{ fontSize: 'calc(15px * var(--font-scale))', fontWeight: 800,
                      color: r.fit_score >= 60 ? 'var(--leaf)' : 'var(--marigold)' }}>
                      {r.fit_score}
                    </div>
                    <div className="muted" style={{ fontSize: 'calc(8.5px * var(--font-scale))', textTransform: 'uppercase' }}
                         lang={lang}>{t('मेल', 'fit')}</div>
                  </div>
                )}
              </div>

              <div className="row" style={{ gap: 8, marginTop: 11, padding: '9px 11px',
                    background: 'var(--paper-2)', borderRadius: 11, flexWrap: 'wrap' }}>
                {[
                  [t('मात्रा', 'Quantity'), `${r.quantity}`],
                  [t('बजट', 'Budget'), `${rupees(r.budget_min)}–${rupees(r.budget_max)}`],
                  [t('समय', 'Delivery'), `${r.delivery_days}d`],
                ].map(([label, value]) => (
                  <div key={label} style={{ flex: 1, minWidth: 74 }}>
                    <div className="muted" style={{ fontSize: 'calc(9px * var(--font-scale))', textTransform: 'uppercase',
                                                    fontWeight: 700 }} lang={lang}>{label}</div>
                    <div className="mono" style={{ fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 700 }}>{value}</div>
                  </div>
                ))}
              </div>

              {r.fit_reasons?.length > 0 && (
                <div style={{ marginTop: 10 }}>
                  <Bar value={r.fit_score} tone="var(--leaf)" height={4} />
                  <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.5, marginTop: 5 }}
                       lang={lang}>
                    ✓ {(lang === 'hi' ? r.fit_reasons_hi : r.fit_reasons).join(' · ')}
                  </div>
                </div>
              )}

              <button
                className={`btn btn-block btn-sm ${r.already_quoted ? 'btn-soft' : 'btn-gold'}`}
                style={{ marginTop: 11 }}
                onClick={() => openQuote(r)}
                disabled={r.already_quoted}
              >
                {r.already_quoted ? `✓ ${t('भाव भेज चुके हैं', 'Quote sent')}`
                                  : `💬 ${t('अपना भाव भेजिए', 'Send your price')}`}
              </button>
            </div>
          )))}

          {tab === 'mine' && (quotes.length === 0 ? (
            <Empty icon="💬" title={t('अभी कोई भाव नहीं भेजा', 'No quotes sent yet')} />
          ) : quotes.map((q) => (
            <div key={q.id} className="card fade-up">
              <div className="row-between">
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }}>
                    {q.requirement?.title}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 3 }}>
                    {q.buyer?.logo} {q.buyer?.name}
                  </div>
                </div>
                <span className={`pill ${q.status === 'accepted' ? 'leaf'
                  : q.status === 'declined' ? 'madder' : 'gold'}`}>
                  {q.status}
                </span>
              </div>
              <div className="row" style={{ gap: 14, marginTop: 11 }}>
                {[
                  [rupees(q.unit_price), t('प्रति पीस', 'per piece')],
                  [q.quantity, t('मात्रा', 'quantity')],
                  [rupees(q.total), t('कुल', 'total')],
                ].map(([n, label]) => (
                  <div key={label} style={{ flex: 1 }}>
                    <div className="mono" style={{ fontSize: 'calc(14px * var(--font-scale))', fontWeight: 700 }}>{n}</div>
                    <div className="muted" style={{ fontSize: 'calc(9px * var(--font-scale))', textTransform: 'uppercase' }}
                         lang={lang}>{label}</div>
                  </div>
                ))}
              </div>
            </div>
          )))}
        </div>

        {quoting && (
          <div style={{ position: 'absolute', inset: 0, zIndex: 150,
                        background: 'rgba(11,10,13,0.62)', display: 'flex',
                        alignItems: 'flex-end' }}
               onClick={(e) => e.target === e.currentTarget && setQuoting(null)}>
            <div className="fade-up" style={{ background: 'var(--paper)', width: '100%',
                  borderRadius: '24px 24px 0 0', padding: '20px 16px 26px',
                  maxHeight: '86%', overflowY: 'auto' }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(16px * var(--font-scale))', marginBottom: 4 }}>
                {t('अपना भाव भेजिए', 'Send your price')}
              </div>
              <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.55, marginBottom: 14 }}>
                {quoting.title}
              </div>

              <div className="grid-2">
                {[
                  ['unit_price', t('प्रति पीस ₹', 'Per piece ₹')],
                  ['quantity', t('कितने पीस', 'How many')],
                  ['lead_time_days', t('कितने दिन में', 'Days to deliver')],
                ].map(([key, label]) => (
                  <div className="field" key={key}>
                    <label>{label}</label>
                    <input className="input mono" inputMode="numeric" value={form[key]}
                           onChange={(e) => setForm({ ...form,
                             [key]: e.target.value.replace(/[^\d]/g, '') })} />
                  </div>
                ))}
                <div className="field">
                  <label>{t('कुल', 'Total')}</label>
                  <div className="input mono" style={{ display: 'flex', alignItems: 'center',
                        fontWeight: 800, background: 'var(--paper-2)' }}>
                    {rupees(Number(form.unit_price || 0) * Number(form.quantity || 0))}
                  </div>
                </div>
              </div>

              <div className="field" style={{ marginTop: 11 }}>
                <label>{t('कुछ कहना है? (वैकल्पिक)', 'Anything to add? (optional)')}</label>
                <textarea className="textarea" rows={3} lang={lang} value={form.message}
                          placeholder={t('जैसे: दो खेप में भेज सकता हूँ',
                                         'e.g. I can send it in two batches')}
                          onChange={(e) => setForm({ ...form, message: e.target.value })} />
              </div>

              {Number(form.unit_price) > quoting.budget_max && (
                <div className="card" style={{ background: 'var(--marigold-soft)',
                      borderColor: 'var(--line)', fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.6,
                      marginTop: 11 }} lang={lang}>
                  ⚠️ {t(`आपका भाव इनके बजट (${rupees(quoting.budget_max)}) से ऊपर है। `
                        + `भेज सकते हैं, पर मंज़ूरी की संभावना कम है।`,
                        `Your price is above their ${rupees(quoting.budget_max)} ceiling. `
                        + `You can still send it, but it is less likely to be accepted.`)}
                </div>
              )}

              <div className="row" style={{ gap: 9, marginTop: 15 }}>
                <button className="btn btn-ghost" style={{ flex: 1 }}
                        onClick={() => setQuoting(null)}>
                  {t('रहने दीजिए', 'Cancel')}
                </button>
                <button className="btn btn-primary" style={{ flex: 2 }}
                        onClick={submit} disabled={busy || !form.unit_price || !form.quantity}>
                  {busy ? <span className="spinner" /> : t('भाव भेजिए', 'Send quote')}
                </button>
              </div>
            </div>
          </div>
        )}
      </Screen>
    </>
  )
}
