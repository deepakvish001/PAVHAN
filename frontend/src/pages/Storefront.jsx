import { useEffect, useState } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Toasts } from '../components/Shell'
import { Empty, Loading, ProductImage, rupees } from '../components/ui'
import { stallStorefront } from '../api/client'

/**
 * Where a stall QR lands.
 *
 * Deliberately not the marketplace home page. Someone who scanned a card at
 * Dilli Haat is not browsing — they met this specific weaver ten seconds ago
 * and want to keep hold of them. So the page opens on the artisan, not the
 * catalogue, and the primary action is to keep the shop.
 */
export default function Storefront() {
  const { code } = useParams()
  const navigate = useNavigate()
  const { t, lang, toast, L, P } = useApp()
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(true)
  const [followed, setFollowed] = useState(false)

  useEffect(() => {
    stallStorefront(code).then(setData).catch(() => setData(null)).finally(() => setLoading(false))
  }, [code])

  const follow = async () => {
    try {
      const next = await stallStorefront(code, true)
      setData(next)
      setFollowed(true)
      try {
        const saved = JSON.parse(localStorage.getItem('pavhan.following') || '[]')
        if (!saved.includes(code)) {
          localStorage.setItem('pavhan.following', JSON.stringify([...saved, code]))
        }
      } catch { /* private mode; the follow still counted on the server */ }
      toast(t('अब यह दुकान आपके फ़ोन में सुरक्षित है।',
              'This shop is saved on your phone now.'), 'ok', 4500)
    } catch (err) {
      toast(err.message, 'err')
    }
  }

  if (loading) return <div className="app-body no-nav"><Loading /></div>
  if (!data) {
    return (
      <div className="app-body no-nav">
        <Empty icon="🔍" title={t('यह कार्ड नहीं मिला', 'That card was not found')}
               body={t('कोड दोबारा जाँचिए।', 'Check the code and try again.')} />
      </div>
    )
  }

  const { artisan, exhibition, products } = data

  return (
    <>
      <div className="app-body no-nav">
        <div style={{ background: 'var(--ink)', color: '#fff', padding: '26px 18px 22px' }}>
          {exhibition && (
            <div style={{ fontSize: 'calc(10.5px * var(--font-scale))', color: '#b0b8d8', textTransform: 'uppercase',
                          letterSpacing: '0.06em', fontWeight: 700, marginBottom: 12 }}
                 lang={lang}>
              {t('आप यहाँ मिले थे', 'You met here')} · {lang === 'hi'
                ? exhibition.name_hi || exhibition.name : exhibition.name}
            </div>
          )}
          <div className="row" style={{ gap: 13 }}>
            <div style={{ width: 56, height: 56, borderRadius: 18, fontSize: 'calc(28px * var(--font-scale))',
                          background: 'rgba(255,255,255,0.12)', display: 'grid',
                          placeItems: 'center' }}>
              {artisan?.avatar || '🧑‍🎨'}
            </div>
            <div style={{ flex: 1 }}>
              <h1 style={{ fontSize: 'calc(21px * var(--font-scale))', color: '#fff' }}>{artisan?.name}</h1>
              <div style={{ fontSize: 'calc(12px * var(--font-scale))', color: '#b0b8d8', marginTop: 3 }}>
                {artisan?.craft_focus} · {artisan?.region}
              </div>
              {artisan?.experience_years > 0 && (
                <div style={{ fontSize: 'calc(11px * var(--font-scale))', color: '#98a0c0', marginTop: 3 }} lang={lang}>
                  {t(`${artisan.experience_years} साल से यही काम`,
                     `${artisan.experience_years} years at this craft`)}
                </div>
              )}
            </div>
          </div>

          <button
            className={`btn btn-block ${followed ? 'btn-soft' : 'btn-gold'}`}
            style={{ marginTop: 18 }}
            onClick={follow}
            disabled={followed}
          >
            {followed
              ? `✓ ${t('सुरक्षित हो गया', 'Saved to your phone')}`
              : `⭐ ${t('इस दुकान को अपने फ़ोन में रखिए', 'Keep this shop on my phone')}`}
          </button>
          <div className="center" style={{ fontSize: 'calc(10.5px * var(--font-scale))', color: '#98a0c0', marginTop: 9,
                                           lineHeight: 1.6 }} lang={lang}>
            {t('मेला ख़त्म होने के बाद भी आप यहीं से ख़रीद सकते हैं।',
               'You can still buy from here long after the fair has closed.')}
          </div>
        </div>

        <div className="page stack">
          <div className="section-title" lang={lang}>
            {t('इनका बनाया सामान', 'What they make')}
          </div>
          {products.length === 0 ? (
            <Empty title={t('अभी कुछ नहीं डाला गया', 'Nothing listed yet')} />
          ) : (
            products.map((p) => (
              <button key={p.id} className="card row fade-up"
                      style={{ gap: 12, width: '100%', textAlign: 'left' }}
                      onClick={() => navigate(`/product/${p.id}`)}>
                <ProductImage product={{ images: [p.image] }} height={78} style={{ width: 78 }} />
                <div style={{ flex: 1, minWidth: 0 }}>
                  <div style={{ fontWeight: 700, fontSize: 'calc(14px * var(--font-scale))', lineHeight: 1.3 }}>
                    {lang === 'hi' ? p.title_hi || p.title : p.title}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', margin: '3px 0 6px' }}>
                    {L(p.craft_type)} · {L(p.region)}
                  </div>
                  <span className="pill gold mono">{rupees(p.price)}</span>
                </div>
              </button>
            ))
          )}

          <button className="btn btn-ghost btn-block" onClick={() => navigate('/shop')}>
            {t('और कारीगर देखिए', 'Browse other artisans')}
          </button>
        </div>
      </div>
      <Toasts />
    </>
  )
}
