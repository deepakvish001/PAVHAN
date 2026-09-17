import { useCallback, useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, Loading, rupees, useScreenVoice } from '../components/ui'
import { checkVpa, listUsers, paymentStatement, releasePayment, saveVpa } from '../api/client'

/**
 * Where the money is.
 *
 * The app's welcome line promises the artisan money rather than a listing, so
 * this screen has to be able to answer the question that promise invites: has
 * it arrived? Three numbers answer it — received, held, still to come — and
 * the fourth is the one that makes the case for the whole platform: what a
 * trader at the door would have paid for the same work.
 */
export default function Earnings() {
  const { t, lang, user, setUser, toast } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')

  const load = useCallback(async () => {
    let id = user?.id
    if (!id) {
      const artisans = await listUsers('artisan').catch(() => [])
      id = artisans[0]?.id
      if (artisans[0]) setUser(artisans[0])
    }
    if (!id) { setLoading(false); return }
    setData(await paymentStatement(id).catch(() => null))
    setLoading(false)
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { load() }, [load])
  useScreenVoice('earnings', {}, [!!data])

  const release = async (payment) => {
    setBusy(payment.id)
    try {
      await releasePayment(payment.id)
      toast(t('पैसा आपके UPI में भेज दिया।', 'Released to your UPI.'), 'ok')
      await load()
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  if (loading) return (<><TopBar title="…" /><Screen><Loading /></Screen></>)
  if (!data) return (
    <><TopBar title={t('कमाई', 'Earnings')} back /><Screen>
      <Empty icon="💰" title={t('अभी कुछ नहीं', 'Nothing yet')}
             body={t('जब कोई ऑर्डर आएगा और उसका भुगतान होगा, वह यहाँ दिखेगा।',
                      'When an order is paid for, it appears here.')} />
    </Screen></>
  )

  const s = data.summary
  return (
    <>
      <TopBar title={t('कमाई', 'Earnings')}
              subtitle={data.artisan.upi_vpa || t('UPI ID नहीं डाली', 'No UPI ID yet')} back />
      <Screen>
        <div className="stack">
          <VpaCard artisan={data.artisan} onSaved={load} />

          <div className="card">
            <div className="grid-2" style={{ gap: 10 }}>
              <Stat label={t('आपके पास आ चुका', 'Reached you')} value={s.received} strong />
              <Stat label={t('डिलीवरी तक रोका हुआ', 'Held until delivery')} value={s.held} />
              <Stat label={t('भुगतान बाकी', 'Awaiting payment')} value={s.awaiting} />
              <Stat label={t('प्लेटफ़ॉर्म शुल्क', 'Platform fee')} value={s.platform_fees} muted />
            </div>
            {s.gross > 0 && (
              <div style={{
                marginTop: 12, padding: 11, borderRadius: 12,
                background: 'var(--paper-2)', lineHeight: 1.5,
                fontSize: 'calc(12.5px * var(--font-scale))',
              }} lang={lang}>
                {t(`बिचौलिया इसी काम के लिए लगभग ${rupees(s.middleman_would_have_paid)} देता। यहाँ आपको ${rupees(s.extra_vs_middleman)} ज़्यादा मिले।`,
                   `A middleman would have paid about ${rupees(s.middleman_would_have_paid)} for the same work. You are ${rupees(s.extra_vs_middleman)} better off.`)}
              </div>
            )}
          </div>

          {data.payments.length === 0 && (
            <Empty icon="💰" title={t('अभी कोई भुगतान नहीं', 'No payments yet')}
                   body={t('ऑर्डर पन्ने पर जाकर खरीदार को भुगतान लिंक भेजिए।',
                            'Open an order and send the buyer a payment link.')} />
          )}

          {data.payments.map((p) => (
            <div key={p.id} className="card">
              <div className="row-between" style={{ alignItems: 'flex-start', gap: 10 }}>
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.4 }}>
                    {p.product_title || t('ऑर्डर', 'Order')}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 3 }}
                       lang={lang}>
                    {lang === 'hi' ? p.label_hi : p.label}
                    {p.reference && ` · ${p.reference}`}
                  </div>
                </div>
                <div style={{ textAlign: 'right' }}>
                  <div style={{ fontWeight: 800, fontSize: 'calc(15px * var(--font-scale))' }}>
                    {rupees(p.artisan_amount)}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))' }}>
                    {t('कुल', 'of')} {rupees(p.amount)}
                  </div>
                </div>
              </div>
              {p.state === 'held' && (
                <button className="btn btn-soft btn-sm" style={{ marginTop: 10 }}
                        onClick={() => release(p)} disabled={busy === p.id}>
                  {busy === p.id ? <span className="spinner" />
                    : t('डिलीवरी हो गई — पैसा भेजिए', 'Delivered — release the money')}
                </button>
              )}
            </div>
          ))}

          <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.55, padding: '0 2px' }}
               lang={lang}>
            {lang === 'hi' ? data.disclaimer.hi : data.disclaimer.en}
          </div>
        </div>
      </Screen>
    </>
  )
}

function Stat({ label, value, strong, muted }) {
  const { lang } = useApp()
  return (
    <div style={{ padding: '10px 11px', borderRadius: 12, background: 'var(--paper-2)' }}>
      <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.35 }} lang={lang}>
        {label}
      </div>
      <div style={{
        fontWeight: strong ? 800 : 700, marginTop: 4,
        fontSize: `calc(${strong ? 17 : 15}px * var(--font-scale))`,
        color: muted ? 'var(--muted)' : 'inherit',
      }}>
        {rupees(value)}
      </div>
    </div>
  )
}

/**
 * The UPI ID, checked as it is typed.
 *
 * An artisan who mistypes their VPA does not find out at the moment of the
 * mistake; they find out when money that was supposed to be theirs has gone
 * somewhere else. So the check runs while they type, names the bank it
 * recognises back to them, and — when it does not recognise the handle — says
 * so plainly instead of either rejecting a perfectly good new bank or
 * pretending to have verified something.
 */
function VpaCard({ artisan, onSaved }) {
  const { t, lang, toast } = useApp()
  const [value, setValue] = useState(artisan.upi_vpa || '')
  const [verdict, setVerdict] = useState(null)
  const [saving, setSaving] = useState(false)
  const [open, setOpen] = useState(!artisan.upi_vpa)

  useEffect(() => {
    const raw = value.trim()
    if (!raw || raw === artisan.upi_vpa) { setVerdict(null); return }
    const timer = setTimeout(() => {
      checkVpa(raw).then(setVerdict).catch(() => setVerdict(null))
    }, 350)
    return () => clearTimeout(timer)
  }, [value, artisan.upi_vpa])

  const save = async () => {
    setSaving(true)
    try {
      await saveVpa(artisan.id, { vpa: value.trim() })
      toast(t('UPI ID सुरक्षित कर ली।', 'UPI ID saved.'), 'ok')
      setOpen(false)
      onSaved()
    } catch (err) {
      toast(err.message, 'err')
    } finally { setSaving(false) }
  }

  if (!open) {
    return (
      <button className="card" style={{ textAlign: 'left', width: '100%' }} onClick={() => setOpen(true)}>
        <div className="row-between">
          <div>
            <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))' }} lang={lang}>
              {t('पैसा यहाँ आएगा', 'Money arrives here')}
            </div>
            <div style={{ fontWeight: 800, fontSize: 'calc(14.5px * var(--font-scale))', marginTop: 3 }}>
              {artisan.upi_vpa}
            </div>
          </div>
          <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }}>
            {t('बदलिए', 'Change')} ›
          </div>
        </div>
      </button>
    )
  }

  return (
    <div className="card" style={{ borderColor: artisan.upi_vpa ? 'var(--line)' : 'var(--marigold)' }}>
      <div style={{ fontWeight: 800, fontSize: 'calc(14px * var(--font-scale))' }} lang={lang}>
        {t('आपकी UPI ID', 'Your UPI ID')}
      </div>
      <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 4, lineHeight: 1.5 }}
           lang={lang}>
        {t('खरीदार का पैसा सीधे इसी में आएगा। अपने पेमेंट ऐप में "My UPI ID" में देख सकते हैं।',
           'The buyer’s money comes straight here. You can find it in your payment app under "My UPI ID".')}
      </div>
      <div className="field" style={{ marginTop: 10 }}>
        <input className="input" value={value} inputMode="email" autoCapitalize="off"
               spellCheck={false} placeholder="name@bank"
               onChange={(e) => setValue(e.target.value)} />
      </div>
      {verdict && (
        <div style={{
          fontSize: 'calc(12px * var(--font-scale))', marginTop: 7, lineHeight: 1.45,
          color: verdict.valid ? 'var(--ink-soft)' : 'var(--madder)',
        }} lang={lang}>
          {verdict.valid ? '✓ ' : '• '}{lang === 'hi' ? verdict.reason_hi : verdict.reason}
        </div>
      )}
      <button className="btn btn-primary btn-block" style={{ marginTop: 11 }}
              onClick={save} disabled={saving || !verdict?.valid}>
        {saving ? <span className="spinner" /> : t('सुरक्षित कीजिए', 'Save')}
      </button>
    </div>
  )
}
