import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Loading, rupees, useScreenVoice } from '../components/ui'
import {
  advanceShipment, bookShipment, orderShipment, shippingOptions,
} from '../api/client'

/**
 * Despatch: the half of "shipped" that used to be missing.
 *
 * The only opinionated thing on this screen is which carriers appear. Options
 * are drawn from what actually serves the destination pincode, so an artisan
 * in Bhadohi sending to Aizawl is shown India Post and told, by name, which
 * couriers refused — rather than being offered a cheap Delhivery rate that
 * would be rejected at the counter.
 */
export default function Shipping() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const { t, lang, toast } = useApp()
  const [pin, setPin] = useState('')
  const [options, setOptions] = useState(null)
  const [shipment, setShipment] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')

  const load = useCallback(async () => {
    try {
      const { shipment: existing } = await orderShipment(orderId)
      setShipment(existing)
      if (!existing) setOptions(await shippingOptions(orderId, ''))
    } catch (err) {
      // A real failure, not the ordinary "nothing booked yet" — say so rather
      // than showing an empty form that will not work.
      toast(err.message, 'err')
    } finally {
      setLoading(false)
    }
  }, [orderId, toast])

  useEffect(() => { load() }, [load])
  useScreenVoice('shipping', {}, [loading])

  const lookUp = async () => {
    if (pin.trim().length !== 6) {
      toast(t('पिनकोड छह अंकों का होता है।', 'A pincode is six digits.'), 'warn')
      return
    }
    setBusy('lookup')
    try {
      setOptions(await shippingOptions(orderId, pin.trim()))
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  const book = async (carrier) => {
    setBusy(carrier)
    try {
      const res = await bookShipment(orderId, { carrier, to_pincode: pin.trim() })
      setShipment(res.shipment)
      toast(t('खेप बुक हो गई।', 'Shipment booked.'), 'ok')
      if (res.whatsapp_to_buyer) window.open(res.whatsapp_to_buyer, '_blank', 'noopener')
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  const move = async (to) => {
    setBusy(to)
    try {
      const res = await advanceShipment(shipment.id, to)
      setShipment(res.shipment)
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  if (loading) return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)

  if (shipment) {
    const next = shipment.stages[shipment.stage_index + 1]
    return (
      <>
        <TopBar title={t('खेप', 'Shipment')} subtitle={shipment.awb} back />
        <Screen>
          <div className="stack">
            <div className="card">
              <div style={{ fontWeight: 800, fontSize: 'calc(15px * var(--font-scale))' }}>
                {shipment.service}
              </div>
              <div className="mono" style={{ fontSize: 'calc(13px * var(--font-scale))', marginTop: 4 }}>
                {shipment.awb}
              </div>
              <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 5 }}
                   lang={lang}>
                {shipment.from_pincode} → {shipment.to_pincode} · {shipment.weight_g}g ·{' '}
                {rupees(shipment.rate)} · {shipment.promised_days} {t('दिन', 'days')}
              </div>

              <div className="row" style={{ gap: 3, marginTop: 14 }}>
                {shipment.stages.map((s, i) => (
                  <div key={s.key} style={{ flex: 1 }}>
                    <div style={{ height: 4, borderRadius: 99,
                      background: i <= shipment.stage_index ? 'var(--leaf)' : 'var(--line)' }} />
                    <div style={{ fontSize: 'calc(8.5px * var(--font-scale))', marginTop: 5, textAlign: 'center',
                                  fontWeight: 700, lineHeight: 1.25,
                                  color: i <= shipment.stage_index ? 'var(--leaf)' : 'var(--muted)' }}
                         lang={lang}>
                      {lang === 'hi' ? s.label_hi : s.label}
                    </div>
                  </div>
                ))}
              </div>

              {next && (
                <button className="btn btn-soft btn-sm btn-block" style={{ marginTop: 12 }}
                        onClick={() => move(next.key)} disabled={busy === next.key}>
                  {busy === next.key ? <span className="spinner dark" />
                    : `→ ${lang === 'hi' ? next.label_hi : next.label}`}
                </button>
              )}
            </div>

            {shipment.timeline?.length > 0 && (
              <div className="card">
                {shipment.timeline.map((e, i) => (
                  <div key={i} className="row-between"
                       style={{ fontSize: 'calc(12px * var(--font-scale))', padding: '4px 0' }}>
                    <span>{e.note}</span>
                    <span className="mono muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))' }}>
                      {new Date(e.at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                    </span>
                  </div>
                ))}
              </div>
            )}

            <button className="btn btn-ghost btn-block" onClick={() => navigate('/orders')}>
              {t('ऑर्डर पर वापस', 'Back to orders')}
            </button>
          </div>
        </Screen>
      </>
    )
  }

  return (
    <>
      <TopBar title={t('भेजिए', 'Send it')} back />
      <Screen>
        <div className="stack">
          {options?.needs_origin && (
            <div className="card" style={{ borderColor: 'var(--marigold)' }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
                {lang === 'hi' ? options.reason_hi : options.reason}
              </div>
              <button className="btn btn-soft btn-sm" style={{ marginTop: 10 }}
                      onClick={() => navigate('/profile')}>
                {t('प्रोफ़ाइल खोलिए', 'Open Profile')}
              </button>
            </div>
          )}

          <div className="card">
            <div className="field">
              <label lang={lang}>{t('कहाँ भेजना है — पिनकोड', 'Delivery pincode')}</label>
              <input className="input" value={pin} inputMode="numeric" maxLength={6}
                     placeholder="796001"
                     onChange={(e) => setPin(e.target.value.replace(/\D/g, ''))} />
            </div>
            <button className="btn btn-primary btn-block" style={{ marginTop: 10 }}
                    onClick={lookUp} disabled={busy === 'lookup'}>
              {busy === 'lookup' ? <span className="spinner" />
                : t('दाम देखिए', 'See the rates')}
            </button>
          </div>

          {options?.serviceable && (
            <>
              <div className="section-sub" lang={lang} style={{ padding: '0 2px' }}>
                {options.zone_label && (lang === 'hi' ? options.zone_label_hi : options.zone_label)}
                {' · '}{options.weight_basis}
                {options.packing_note && ` · ${options.packing_note}`}
              </div>

              {options.only_government && (
                <div className="card tinted" style={{ lineHeight: 1.5 }}>
                  <div style={{ fontWeight: 800, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
                    {t('यहाँ सिर्फ़ इंडिया पोस्ट जाता है', 'Only India Post goes here')}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 4 }}
                       lang={lang}>
                    {t('निजी कूरियर इस पिनकोड पर सेवा नहीं देते। इंडिया पोस्ट देश के हर पिनकोड तक जाता है।',
                       'The private couriers do not serve this pincode. India Post reaches every pincode in the country.')}
                  </div>
                </div>
              )}

              {options.options.map((o, i) => (
                <div key={o.carrier} className="card"
                     style={{ borderColor: i === 0 ? 'var(--leaf)' : 'var(--line)' }}>
                  <div className="row-between" style={{ alignItems: 'flex-start', gap: 10 }}>
                    <div style={{ flex: 1, minWidth: 0 }}>
                      <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.35 }}
                           lang={lang}>
                        {lang === 'hi' ? o.name_hi : o.name}
                        {i === 0 && ` · ${t('सबसे सस्ता', 'cheapest')}`}
                      </div>
                      <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 4, lineHeight: 1.45 }}
                           lang={lang}>
                        {lang === 'hi' ? o.note_hi : o.note}
                      </div>
                      <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 5 }}>
                        {t('भाड़ा', 'Freight')} {rupees(o.freight)} + GST {rupees(o.gst)}
                        {' + '}{t('पैकिंग', 'packing')} {rupees(o.packing)}
                      </div>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <div style={{ fontWeight: 800, fontSize: 'calc(16px * var(--font-scale))' }}>
                        {rupees(o.total)}
                      </div>
                      <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))' }} lang={lang}>
                        {o.days} {t('दिन', 'days')}
                      </div>
                    </div>
                  </div>
                  <button className="btn btn-soft btn-sm btn-block" style={{ marginTop: 11 }}
                          onClick={() => book(o.carrier)} disabled={!!busy}>
                    {busy === o.carrier ? <span className="spinner dark" />
                      : t('इससे भेजिए', 'Book this')}
                  </button>
                </div>
              ))}

              {options.unavailable?.map((u) => (
                <div key={u.carrier} className="card" style={{ opacity: 0.6 }}>
                  <div style={{ fontWeight: 600, fontSize: 'calc(12.5px * var(--font-scale))' }} lang={lang}>
                    ✕ {u.name}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 3 }}
                       lang={lang}>
                    {lang === 'hi' ? u.reason_hi : u.reason}
                  </div>
                </div>
              ))}

              <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.55, padding: '0 2px' }}
                   lang={lang}>
                {lang === 'hi' ? options.disclaimer_hi : options.disclaimer}
              </div>
            </>
          )}

          {options && options.serviceable === false && !options.needs_origin && !options.needs_destination && (
            <div className="card" style={{ borderColor: 'var(--madder)' }}>
              <div style={{ fontSize: 'calc(13px * var(--font-scale))', lineHeight: 1.5 }} lang={lang}>
                {lang === 'hi' ? (options.reason_hi || options.reason) : options.reason}
              </div>
            </div>
          )}
        </div>
      </Screen>
    </>
  )
}
