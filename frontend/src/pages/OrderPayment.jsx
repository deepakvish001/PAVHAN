import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Loading, rupees } from '../components/ui'
import { confirmPayment, orderPayment, raisePayment, releasePayment } from '../api/client'

/**
 * Asking to be paid.
 *
 * The artisan raises a payment; the buyer taps a `upi://pay` link that opens
 * their own payment app with the amount and the artisan's VPA already filled
 * in. Nothing is typed by hand, because a hand-typed VPA is how money reaches
 * the wrong person.
 *
 * The hold between paid and delivered is stated on the screen in both
 * directions. A buyer paying a stranger in a village wants to know the money
 * is not simply gone; an artisan shipping first wants to know it already
 * exists. Saying so is the only arrangement that answers both.
 */
export default function OrderPayment() {
  const { orderId } = useParams()
  const navigate = useNavigate()
  const { t, lang, toast } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')
  const [reference, setReference] = useState('')

  const load = useCallback(async () => {
    setData(await orderPayment(orderId).catch(() => null))
    setLoading(false)
  }, [orderId])

  useEffect(() => { load() }, [load])

  const raise = async () => {
    setBusy('raise')
    try {
      await raisePayment(orderId, { method: 'upi' })
      await load()
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  const confirm = async () => {
    setBusy('confirm')
    try {
      await confirmPayment(data.payment.id, { reference: reference.trim() })
      toast(t('भुगतान दर्ज कर लिया।', 'Payment recorded.'), 'ok')
      setReference('')
      await load()
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  const release = async () => {
    setBusy('release')
    try {
      await releasePayment(data.payment.id)
      toast(t('पैसा कारीगर के UPI में भेज दिया।', 'Released to the artisan.'), 'ok')
      await load()
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  if (loading) return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)
  if (!data) return (<><TopBar title={t('भुगतान', 'Payment')} back /><Screen>
    <div className="card">{t('ऑर्डर नहीं मिला।', 'Order not found.')}</div></Screen></>)

  const p = data.payment
  return (
    <>
      <TopBar title={t('भुगतान', 'Payment')}
              subtitle={`${data.order.quantity} × · ${rupees(data.order.amount)}`} back />
      <Screen>
        <div className="stack">
          <div className="card">
            <div className="row-between">
              <span className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
                {t('खरीदार देगा', 'Buyer pays')}
              </span>
              <span style={{ fontWeight: 800, fontSize: 'calc(16px * var(--font-scale))' }}>
                {rupees(data.split.amount)}
              </span>
            </div>
            <div className="row-between" style={{ marginTop: 6 }}>
              <span className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
                {t('प्लेटफ़ॉर्म शुल्क', 'Platform fee')} · 5%
              </span>
              <span className="muted" style={{ fontSize: 'calc(13px * var(--font-scale))' }}>
                −{rupees(data.split.platform_fee)}
              </span>
            </div>
            <div className="row-between" style={{
              marginTop: 8, paddingTop: 9, borderTop: '1px solid var(--line)',
            }}>
              <span style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
                {t('कारीगर को मिलेगा', 'Artisan receives')}
              </span>
              <span style={{ fontWeight: 800, fontSize: 'calc(17px * var(--font-scale))', color: 'var(--leaf)' }}>
                {rupees(data.split.artisan_amount)}
              </span>
            </div>
            <div style={{
              marginTop: 11, padding: 10, borderRadius: 11, background: 'var(--paper-2)',
              fontSize: 'calc(12px * var(--font-scale))', lineHeight: 1.5,
            }} lang={lang}>
              {lang === 'hi' ? data.split.note_hi : data.split.note}
            </div>
          </div>

          {data.vpa_missing && (
            <div className="card" style={{ borderColor: 'var(--madder)' }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', lineHeight: 1.45 }}
                   lang={lang}>
                {t('इस कारीगर ने अभी UPI ID नहीं डाली, इसलिए पैसा भेजने की कोई जगह नहीं है।',
                   'This artisan has not added a UPI ID yet, so there is nowhere to send the money.')}
              </div>
              <button className="btn btn-soft btn-sm" style={{ marginTop: 10 }}
                      onClick={() => navigate('/earnings')}>
                {t('UPI ID डालिए', 'Add a UPI ID')}
              </button>
            </div>
          )}

          {!p && !data.vpa_missing && (
            <button className="btn btn-primary btn-block" onClick={raise} disabled={busy === 'raise'}>
              {busy === 'raise' ? <span className="spinner" />
                : t('भुगतान लिंक बनाइए', 'Create a payment link')}
            </button>
          )}

          {p && (
            <div className="card">
              <div style={{ fontWeight: 800, fontSize: 'calc(14.5px * var(--font-scale))' }} lang={lang}>
                {lang === 'hi' ? p.label_hi : p.label}
              </div>
              <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 4, lineHeight: 1.5 }}>
                {p.detail}
              </div>

              {p.upi_link && (
                <>
                  <a className="btn btn-primary btn-block" href={p.upi_link}
                     style={{ marginTop: 12, textDecoration: 'none' }}>
                    {t('UPI ऐप में भुगतान कीजिए', 'Pay in your UPI app')}
                  </a>
                  <a className="btn btn-soft btn-block" href={p.whatsapp}
                     target="_blank" rel="noopener noreferrer"
                     style={{ marginTop: 8, textDecoration: 'none' }}>
                    💬 {t('व्हाट्सऐप पर भेजिए', 'Send on WhatsApp')}
                  </a>
                  <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 8, lineHeight: 1.5 }}
                       lang={lang}>
                    {t('यह लिंक फ़ोन पर GPay, PhonePe या Paytm में खुलता है — रकम और UPI ID पहले से भरी होती है।',
                       'On a phone this opens GPay, PhonePe or Paytm with the amount and UPI ID already filled in.')}
                  </div>
                </>
              )}

              {p.state === 'awaiting_payment' && (
                <div style={{ marginTop: 14, paddingTop: 12, borderTop: '1px solid var(--line)' }}>
                  <div className="field">
                    <label lang={lang}>
                      {t('भुगतान हो गया? UTR / संदर्भ नंबर डालिए', 'Paid? Enter the UTR / reference')}
                    </label>
                    <input className="input" value={reference} inputMode="numeric"
                           placeholder="429911307755"
                           onChange={(e) => setReference(e.target.value)} />
                  </div>
                  <button className="btn btn-soft btn-block" style={{ marginTop: 10 }}
                          onClick={confirm} disabled={busy === 'confirm' || reference.trim().length < 6}>
                    {busy === 'confirm' ? <span className="spinner dark" />
                      : t('भुगतान दर्ज कीजिए', 'Record the payment')}
                  </button>
                </div>
              )}

              {p.state === 'held' && (
                <button className="btn btn-soft btn-block" style={{ marginTop: 12 }}
                        onClick={release} disabled={busy === 'release'}>
                  {busy === 'release' ? <span className="spinner dark" />
                    : t('डिलीवरी हो गई — पैसा छोड़िए', 'Delivered — release the money')}
                </button>
              )}

              {p.timeline?.length > 0 && (
                <div style={{ marginTop: 13, paddingTop: 11, borderTop: '1px solid var(--line)' }}>
                  {p.timeline.map((e, i) => (
                    <div key={i} className="row-between"
                         style={{ fontSize: 'calc(11.5px * var(--font-scale))', padding: '3px 0' }}>
                      <span>{e.note}</span>
                      <span className="mono muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))' }}>
                        {new Date(e.at).toLocaleDateString('en-IN', { day: 'numeric', month: 'short' })}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.55, padding: '0 2px' }}
               lang={lang}>
            {lang === 'hi' ? data.disclaimer.hi : data.disclaimer.en}
          </div>
        </div>
      </Screen>
    </>
  )
}
