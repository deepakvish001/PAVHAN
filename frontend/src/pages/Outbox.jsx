import { useCallback, useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, useScreenVoice } from '../components/ui'
import {
  MAX_ATTEMPTS, clearSent, flush, listItems, onOutboxChange, removeItem, retryItem,
} from '../lib/outbox'

/**
 * What is waiting to be sent, shown rather than hidden.
 *
 * A background sync that silently publishes an hour later is worse than no
 * sync: the artisan believed it had failed, may have re-recorded it, and may
 * have changed the price in between. So the queue is a screen. It says how
 * many pieces are waiting, what each one is, when it was recorded, and — when
 * something genuinely will not send — why.
 */
export default function Outbox() {
  const { t, lang, toast } = useApp()
  const navigate = useNavigate()
  const [items, setItems] = useState([])
  const [online, setOnline] = useState(navigator.onLine)
  const [sending, setSending] = useState(false)

  const load = useCallback(async () => {
    setItems(await listItems().catch(() => []))
  }, [])

  useEffect(() => {
    load()
    const off = onOutboxChange(load)
    const sync = () => setOnline(navigator.onLine)
    window.addEventListener('online', sync)
    window.addEventListener('offline', sync)
    return () => {
      off()
      window.removeEventListener('online', sync)
      window.removeEventListener('offline', sync)
    }
  }, [load])

  const waiting = items.filter((i) => i.status !== 'sent')
  const sent = items.filter((i) => i.status === 'sent')
  const stuck = waiting.filter((i) => i.attempts >= MAX_ATTEMPTS)

  useScreenVoice('outbox', {
    count: waiting.length,
    line: waiting.length
      ? t(`${waiting.length} सामान भेजने बाकी हैं।`, `${waiting.length} items are waiting to be sent.`)
      : t('सब कुछ भेजा जा चुका है।', 'Everything has been sent.'),
  }, [waiting.length])

  const sendAll = async () => {
    setSending(true)
    try {
      const res = await flush()
      if (res.offline) {
        toast(t('अभी भी सिग्नल नहीं है।', 'Still no signal.'), 'warn')
      } else {
        toast(res.sent
          ? t(`${res.sent} सामान भेज दिए।`, `Sent ${res.sent} item${res.sent === 1 ? '' : 's'}.`)
          : t('कुछ नहीं भेजा जा सका।', 'Nothing could be sent.'),
          res.sent ? 'ok' : 'warn')
      }
    } finally {
      setSending(false)
      load()
    }
  }

  return (
    <>
      <TopBar title={t('भेजने की कतार', 'Outbox')}
              subtitle={online
                ? t('सिग्नल है', 'Connected')
                : t('सिग्नल नहीं है', 'No signal')}
              back />
      <Screen>
        <div className="stack">
          <div className="card" style={{
            borderColor: online ? 'var(--line)' : 'var(--marigold)',
          }}>
            <div className="row-between">
              <div>
                <div style={{ fontWeight: 800, fontSize: 'calc(15px * var(--font-scale))' }} lang={lang}>
                  {online ? '📶 ' : '📵 '}
                  {waiting.length
                    ? t(`${waiting.length} भेजने बाकी`, `${waiting.length} waiting to send`)
                    : t('कुछ बाकी नहीं', 'Nothing waiting')}
                </div>
                <div className="muted" style={{ fontSize: 'calc(12.5px * var(--font-scale))', marginTop: 4, lineHeight: 1.5 }}
                     lang={lang}>
                  {online
                    ? t('सिग्नल आते ही ये अपने आप चले जाते हैं।',
                         'These go on their own as soon as there is a connection.')
                    : t('सिग्नल आते ही अपने आप चले जाएँगे। आप तब तक और सामान रिकॉर्ड कर सकते हैं।',
                         'They will go on their own when the signal returns. You can keep recording more in the meantime.')}
                </div>
              </div>
            </div>
            {waiting.length > 0 && (
              <button className="btn btn-primary btn-block" onClick={sendAll}
                      disabled={sending || !online} style={{ marginTop: 12 }}>
                {sending
                  ? <><span className="spinner" /> {t('भेजा जा रहा है…', 'Sending…')}</>
                  : online ? t('अभी भेजिए', 'Send now')
                           : t('सिग्नल का इंतज़ार', 'Waiting for a signal')}
              </button>
            )}
          </div>

          {waiting.length === 0 && sent.length === 0 && (
            <Empty icon="📥"
                   title={t('कतार खाली है', 'The outbox is empty')}
                   body={t('जब सिग्नल न हो तब भी आप सामान रिकॉर्ड कर सकते हैं — वह यहाँ रुकेगा और सिग्नल आते ही चला जाएगा।',
                            'You can record a piece even with no signal — it waits here and goes when the connection returns.')}
                   action={<button className="btn btn-primary" onClick={() => navigate('/add')}>
                     {t('नया सामान', 'Add a piece')}
                   </button>} />
          )}

          {waiting.map((item) => (
            <OutboxRow key={item.id} item={item} lang={lang} t={t}
                       onRetry={async () => { await retryItem(item.id); sendAll() }}
                       onRemove={async () => {
                         await removeItem(item.id)
                         toast(t('हटा दिया।', 'Removed.'), 'ok')
                       }} />
          ))}

          {stuck.length > 0 && (
            <div className="card" style={{ borderColor: 'var(--madder)' }}>
              <div style={{ fontWeight: 800, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
                {t('कुछ सामान बार-बार कोशिश के बाद भी नहीं गया',
                   'Some items did not send even after repeated tries')}
              </div>
              <div className="muted" style={{ fontSize: 'calc(12.5px * var(--font-scale))', marginTop: 4, lineHeight: 1.5 }}
                   lang={lang}>
                {t('ये अपने आप दोबारा कोशिश नहीं करेंगे। ऊपर दिया कारण देखिए, फिर "दोबारा कोशिश" दबाइए।',
                   'These have stopped retrying on their own. Read the reason above, then press "Try again".')}
              </div>
            </div>
          )}

          {sent.length > 0 && (
            <>
              <div className="row-between" style={{ marginTop: 4 }}>
                <div className="section-title" lang={lang}>
                  {t('भेज दिए गए', 'Sent')}
                </div>
                <button className="btn btn-soft btn-sm" onClick={clearSent}>
                  {t('सूची साफ़ करें', 'Clear list')}
                </button>
              </div>
              {sent.map((item) => (
                <button key={item.id} className="card" style={{ textAlign: 'left', width: '100%' }}
                        onClick={() => item.productId && navigate(`/product/${item.productId}`)}>
                  <div className="row-between">
                    <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))' }}>
                      ✅ {item.title || item.label || t('सामान', 'Listing')}
                    </div>
                    <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))' }}>
                      {t('देखिए', 'View')} ›
                    </div>
                  </div>
                </button>
              ))}
            </>
          )}
        </div>
      </Screen>
    </>
  )
}

function OutboxRow({ item, lang, t, onRetry, onRemove }) {
  const when = new Date(item.createdAt)
  const stuck = item.attempts >= MAX_ATTEMPTS
  return (
    <div className="card">
      <div className="row-between" style={{ gap: 10, alignItems: 'flex-start' }}>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.4 }}
               lang={lang}>
            {item.status === 'sending' ? '📤 ' : stuck ? '⚠️ ' : '⏳ '}
            {item.label || t('बिना नाम का सामान', 'Untitled piece')}
          </div>
          <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 4 }}>
            {item.photo ? t('फोटो + आवाज़', 'Photo + voice') : t('सिर्फ़ आवाज़', 'Voice only')}
            {' · '}
            {when.toLocaleString(lang === 'hi' ? 'hi-IN' : 'en-IN',
              { day: 'numeric', month: 'short', hour: 'numeric', minute: '2-digit' })}
            {item.attempts > 0 && ` · ${t(`${item.attempts} कोशिश`, `${item.attempts} attempt${item.attempts === 1 ? '' : 's'}`)}`}
          </div>
          {item.lastError && (
            <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 6,
                          color: 'var(--madder)', lineHeight: 1.45 }}>
              {item.lastError}
            </div>
          )}
        </div>
      </div>
      <div className="row" style={{ gap: 8, marginTop: 10 }}>
        {stuck && (
          <button className="btn btn-soft btn-sm" onClick={onRetry}>
            {t('दोबारा कोशिश', 'Try again')}
          </button>
        )}
        <button className="btn btn-ghost btn-sm" onClick={onRemove}>
          {t('हटाइए', 'Remove')}
        </button>
      </div>
    </div>
  )
}
