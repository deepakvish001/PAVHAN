import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import {
  Bar, Loading, Money, ProductCard, ProductImage, ScoreRing, VoiceOrb, rupees,
} from '../components/ui'
import { getProduct, placeOrder, shareProduct, similarProducts } from '../api/client'

export default function ProductDetail() {
  const { id } = useParams()
  const navigate = useNavigate()
  const { t, lang, role, toast, sayRaw, voiceOn, L, P } = useApp()
  const [product, setProduct] = useState(null)
  const [similar, setSimilar] = useState([])
  const [busy, setBusy] = useState(false)
  const [qty, setQty] = useState(1)

  useEffect(() => {
    let alive = true
    setProduct(null)
    getProduct(id).then((p) => {
      if (!alive) return
      setProduct(p)
      if (voiceOn) {
        // The region has to go through L() before it is spoken. A Hindi
        // sentence with a raw "Madhubani" dropped into it is read out by a
        // Hindi voice, which mangles the one word in it the artisan would
        // have recognised — and it is the same mixing the screen used to do.
        // A listing without a region produced "यह  में हाथ से बनाई गई है" —
        // a sentence with a hole in it, which a voice reads as a stumble.
        // Say the shorter sentence instead of the broken one.
        const where = L(p.region)
        setTimeout(() => sayRaw(
          where
            ? t(`यह ${where} में हाथ से बनाई गई है। कीमत ${Math.round(p.price)} रुपये।`,
                `This piece was handmade in ${where}. The price is ${Math.round(p.price)} rupees.`)
            : t(`यह हाथ से बनाई गई है। कीमत ${Math.round(p.price)} रुपये।`,
                `This piece is handmade. The price is ${Math.round(p.price)} rupees.`),
        ), 700)
      }
    }).catch(() => {})
    similarProducts(id).then((s) => { if (alive) setSimilar(s) }).catch(() => {})
    return () => { alive = false }
  }, [id, L]) // eslint-disable-line

  if (!product) {
    return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)
  }

  const buy = async () => {
    setBusy(true)
    try {
      const order = await placeOrder({ product_id: product.id, quantity: qty, customer_name: 'PAVHAN Demo' })
      toast(
        t(`ऑर्डर हो गया। कारीगर को ₹${Math.round(order.artisan_payout).toLocaleString('en-IN')} जाएँगे।`,
          `Order placed. ₹${Math.round(order.artisan_payout).toLocaleString('en-IN')} goes to the artisan.`),
        'ok', 5200,
      )
      setProduct({ ...product, stock: product.stock - qty })
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setBusy(false)
    }
  }

  const pm = product.pricing_meta || {}
  const isB2B = role === 'b2b' || role === 'exporter'
  const unit = isB2B && qty >= 20 ? product.price * (qty >= 50 ? 0.78 : 0.85) : product.price

  return (
    <>
      <TopBar title={product.craft_type || t('सामान', 'Product')} back />
      <Screen>
        <ProductImage product={product} height={250} radius={0} style={{ width: '100%' }} />

        <div className="page stack" style={{ marginTop: -18, position: 'relative' }}>
          <div className="card">
            <div className="row" style={{ gap: 6, flexWrap: 'wrap', marginBottom: 9 }}>
              {product.gi_tagged && <span className="pill leaf">🏅 GI {t('प्रमाणित', 'tagged')}</span>}
              <span className="pill" lang={lang}>{L(product.category)}</span>
              {product.handmade && <span className="pill gold">✋ {t('हस्तनिर्मित', 'Handmade')}</span>}
            </div>
            <h2 lang={lang} style={{ fontSize: 'calc(20px * var(--font-scale))', lineHeight: 1.28 }}>
              {P(product, 'title')}
            </h2>
            <p className="muted" lang={lang}
               style={{ fontSize: 'calc(13px * var(--font-scale))', lineHeight: 1.6, margin: '8px 0 0' }}>
              {P(product, 'short_description')}
            </p>
            <div className="row-between" style={{ marginTop: 14 }}>
              <div>
                <div className="mono" style={{ fontSize: 'calc(25px * var(--font-scale))', fontWeight: 800, color: 'var(--madder)' }}>
                  {rupees(unit * qty)}
                </div>
                {isB2B && unit < product.price && (
                  <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))' }}>
                    {rupees(unit)} × {qty} · {t('थोक छूट लागू', 'bulk rate applied')}
                  </div>
                )}
              </div>
              <ScoreRing value={product.quality_score} label={t('गुणवत्ता', 'quality')} />
            </div>
          </div>

          {/* Transparency: what the artisan actually receives */}
          <div className="card" style={{ background: 'var(--leaf-soft)', borderColor: '#bcdbd1' }}>
            <div className="row-between">
              <div>
                <div style={{ fontSize: 'calc(12px * var(--font-scale))', fontWeight: 700, color: '#145244' }} lang={lang}>
                  {t('कारीगर को मिलेगा', 'The artisan receives')}
                </div>
                <div className="mono" style={{ fontSize: 'calc(21px * var(--font-scale))', fontWeight: 800, color: '#145244', marginTop: 3 }}>
                  {rupees(unit * qty * 0.95)}
                </div>
              </div>
              <div className="center">
                <div className="mono" style={{ fontSize: 'calc(19px * var(--font-scale))', fontWeight: 800, color: '#145244' }}>95%</div>
                <div style={{ fontSize: 'calc(9px * var(--font-scale))', color: '#3d7a68', textTransform: 'uppercase' }}>
                  {t('हर रुपये का', 'of every rupee')}
                </div>
              </div>
            </div>
          </div>

          {P(product, 'story') && (
            <div className="card tinted">
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 6 }} lang={lang}>
                📖 {t('इसकी कहानी', 'The story')}
              </div>
              <div lang={lang}
                   style={{ fontSize: 'calc(13px * var(--font-scale))', lineHeight: 1.7, color: 'var(--ink-soft)' }}>
                {P(product, 'story')}
              </div>
            </div>
          )}

          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
              {t('पूरा विवरण', 'Details')}
            </div>
            <p lang={lang}
               style={{ fontSize: 'calc(13px * var(--font-scale))', lineHeight: 1.7, margin: '0 0 12px', color: 'var(--ink-soft)' }}>
              {P(product, 'detailed_description')}
            </p>
            {[
              // The values are data tokens, not prose, so they go through L()
              // — the same table the rest of the app translates "Silk" and
              // "Varanasi" with. Care is prose and has its own Hindi field.
              [t('सामग्री', 'Material'), L(product.material)],
              [t('तकनीक', 'Technique'), L(product.technique)],
              [t('रंग', 'Colour'), L(product.colour)],
              [t('नाप', 'Size'), product.size],
              [t('वज़न', 'Weight'), product.weight],
              [t('कहाँ से', 'Origin'), L(product.region)],
              [t('तैयार होने में', 'Lead time'), `${product.lead_time_days} ${t('दिन', 'days')}`],
              [t('कम से कम मात्रा', 'MOQ'), product.moq],
              [t('रख-रखाव', 'Care'), P(product, 'care')],
            ].filter(([, v]) => v).map(([label, value]) => (
              <div
                key={label}
                className="row-between"
                style={{ fontSize: 'calc(12.5px * var(--font-scale))', padding: '7px 0', borderTop: '1px solid var(--line)' }}
              >
                <span className="muted">{label}</span>
                <span style={{ fontWeight: 600, textAlign: 'right', maxWidth: '62%' }}>{value}</span>
              </div>
            ))}
          </div>

          {product.sustainability_score > 0 && (
            <div className="card">
              <div className="row-between" style={{ marginBottom: 7 }}>
                <span style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))' }} lang={lang}>
                  🌱 {t('पर्यावरण अंक', 'Sustainability')}
                </span>
                <span className="mono pill leaf">{product.sustainability_score}/100</span>
              </div>
              <Bar value={product.sustainability_score} tone="var(--leaf)" />
            </div>
          )}

          {pm.comparables?.length > 0 && (
            <div className="card">
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
                {t('यही चीज़ और जगह', 'The same piece elsewhere')}
              </div>
              {pm.comparables.slice(0, 3).map((c) => (
                <div key={c.label} className="row-between" style={{ fontSize: 'calc(12px * var(--font-scale))', padding: '5px 0' }}>
                  <span className="muted" lang={lang}>{lang === 'hi' ? c.label_hi || c.label : c.label}</span>
                  <span className="mono" style={{ fontWeight: 700 }}>{rupees(c.price)}</span>
                </div>
              ))}
            </div>
          )}

          {isB2B && (
            <div className="card">
              <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
                {t('कितने चाहिए?', 'How many?')}
              </div>
              <div className="row" style={{ gap: 8, flexWrap: 'wrap' }}>
                {[1, 10, 20, 50, 100].map((n) => (
                  <button
                    key={n}
                    className={`chip ${qty === n ? 'active' : ''}`}
                    onClick={() => setQty(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
            </div>
          )}

          <button
            className="btn btn-primary btn-block"
            onClick={buy}
            disabled={busy || product.stock < 1}
            style={{ padding: 16 }}
          >
            {product.stock < 1
              ? t('अभी उपलब्ध नहीं', 'Out of stock')
              : busy
                ? <><span className="spinner" /> …</>
                : isB2B
                  ? `📨 ${t('पूछताछ भेजिए', 'Request a quote')}`
                  : `🛍️ ${t('अभी ख़रीदिए', 'Buy now')} · ${rupees(unit * qty)}`}
          </button>

          {/* Sharing a craft is how a craft actually travels, and in India that
              means WhatsApp. No Business API, no template approval: the
              message opens pre-written in whichever WhatsApp is already on
              the phone and the sender presses send. */}
          <ShareButton productId={product.id} />

          {role === 'artisan' && (
            <>
              <button className="btn btn-soft btn-block"
                      onClick={() => navigate(`/artisan/buyers?product=${product.id}`)}>
                🤝 {t('इसके लिए खरीदार देखिए', 'See buyers for this piece')}
              </button>
              <button className="btn btn-soft btn-block"
                      onClick={() => navigate(`/export/${product.id}`)}>
                🏛️ {t('सरकारी बाज़ार के लिए तैयार कीजिए', 'Prepare for a government marketplace')}
              </button>
            </>
          )}

          {similar.length > 0 && (
            <>
              <div className="section-title" style={{ marginTop: 6 }} lang={lang}>
                {t('इससे मिलता-जुलता', 'You may also like')}
              </div>
              <div className="scroll-x">
                {similar.map((p) => <ProductCard key={p.id} product={p} compact />)}
              </div>
            </>
          )}
        </div>
        {/* The voice used to build a Hindi sentence around the English title
            and English description, so a Hindi speaker heard a Hindi frame
            with English words dropped into the middle of it — read out by a
            Hindi voice, which mangles them. It now speaks the same text the
            screen is showing. */}
        <VoiceOrb
          text={t(
            `${P(product, 'title')}। ${P(product, 'short_description')} कीमत ${Math.round(product.price)} रुपये, जिसमें से ${Math.round(product.price * 0.95)} रुपये सीधे कारीगर को जाते हैं।`,
            `${product.title}. ${product.short_description} It costs ${Math.round(product.price)} rupees, of which ${Math.round(product.price * 0.95)} goes straight to the artisan.`,
          )}
        />
      </Screen>
    </>
  )
}


function ShareButton({ productId }) {
  const { t, lang, toast } = useApp()
  const [busy, setBusy] = useState(false)

  const go = async () => {
    setBusy(true)
    try {
      const res = await shareProduct(productId, lang)
      // The phone's own share sheet first where it exists — it reaches
      // WhatsApp plus everything else the person actually uses. The wa.me
      // link is the fallback, and on a desktop it is the only route.
      if (navigator.share) {
        try {
          await navigator.share({ text: res.text, url: res.url })
          return
        } catch (err) {
          if (err?.name === 'AbortError') return   // they changed their mind
        }
      }
      window.open(res.whatsapp, '_blank', 'noopener')
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy(false) }
  }

  return (
    <button className="btn btn-soft btn-block" onClick={go} disabled={busy}>
      {busy ? <span className="spinner dark" /> : `💬 ${t('व्हाट्सऐप पर भेजिए', 'Share on WhatsApp')}`}
    </button>
  )
}
