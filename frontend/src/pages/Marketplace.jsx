import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, ProductCard, SkeletonCard, VoiceOrb, useScreenVoice } from '../components/ui'
import { featuredProducts, listProducts, platformStats, trending } from '../api/client'

export default function Marketplace() {
  const navigate = useNavigate()
  const { t, lang, L } = useApp()
  const [featured, setFeatured] = useState([])
  const [all, setAll] = useState([])
  const [tags, setTags] = useState([])
  const [stats, setStats] = useState(null)
  const [category, setCategory] = useState('')
  const [loading, setLoading] = useState(true)

  useScreenVoice('marketplace')

  useEffect(() => {
    Promise.all([
      featuredProducts(8).catch(() => []),
      listProducts({ limit: 40 }).catch(() => []),
      trending().catch(() => ({ trending: [] })),
      platformStats().catch(() => null),
    ]).then(([f, a, tr, st]) => {
      setFeatured(f); setAll(a); setTags(tr.trending || []); setStats(st); setLoading(false)
    })
  }, [])

  const categories = [...new Set(all.map((p) => p.category))].filter(Boolean)
  const shown = category ? all.filter((p) => p.category === category) : all

  return (
    <>
      <TopBar
        title="PAVHAN"
        subtitle={t('सीधे कारीगर से', 'Straight from the maker')}
      />
      <Screen>
        <div className="page stack">
          <button
            onClick={() => navigate('/search')}
            className="card row"
            style={{ gap: 10, padding: '13px 15px', textAlign: 'left', color: 'var(--muted)' }}
          >
            <span style={{ fontSize: 'calc(17px * var(--font-scale))' }}>🔍</span>
            <span style={{ fontSize: 'calc(14px * var(--font-scale))' }} lang={lang}>
              {t('साड़ी, मिट्टी के बर्तन, गहने…', 'Saree, pottery, jewellery…')}
            </span>
            <span className="spacer" />
            <span style={{ fontSize: 'calc(16px * var(--font-scale))' }}>🎤</span>
          </button>

          {stats && (
            <div className="card tinted row" style={{ gap: 14 }}>
              {[
                [stats.artisans, t('कारीगर', 'artisans')],
                [stats.products, t('सामान', 'pieces')],
                [`${stats.artisan_share_percent}%`, t('कारीगर को जाता है', 'goes to the maker')],
              ].map(([n, label]) => (
                <div key={label} style={{ flex: 1 }}>
                  <div className="mono" style={{ fontSize: 'calc(17px * var(--font-scale))', fontWeight: 800, color: 'var(--madder)' }}>
                    {n}
                  </div>
                  <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase', lineHeight: 1.3 }}>
                    {label}
                  </div>
                </div>
              ))}
            </div>
          )}

          {tags.length > 0 && (
            <div className="chiprow">
              {tags.slice(0, 8).map((tag) => (
                <button
                  key={tag}
                  className="chip"
                  onClick={() => navigate(`/search?q=${encodeURIComponent(tag)}`)}
                >
                  {L(tag)}
                </button>
              ))}
            </div>
          )}

          <div className="section-title" lang={lang}>{t('चुनिंदा', 'Featured')}</div>
          {loading ? (
            <div className="stack"><SkeletonCard /><SkeletonCard /></div>
          ) : (
            <div className="scroll-x">
              {featured.map((p) => <ProductCard key={p.id} product={p} compact />)}
            </div>
          )}

          {categories.length > 0 && (
            <div className="chiprow" style={{ marginTop: 4 }}>
              <button
                className={`chip ${!category ? 'active' : ''}`}
                onClick={() => setCategory('')}
              >
                {t('सब', 'All')}
              </button>
              {categories.map((c) => (
                <button
                  key={c}
                  className={`chip ${category === c ? 'active' : ''}`}
                  onClick={() => setCategory(c)}
                >
                  {L(c)}
                </button>
              ))}
            </div>
          )}

          {loading ? (
            <div className="stack"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
          ) : shown.length ? (
            <div className="stack">
              {shown.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          ) : (
            <Empty title={t('कुछ नहीं मिला', 'Nothing here yet')} />
          )}
        </div>
        <VoiceOrb script="marketplace" />
      </Screen>
    </>
  )
}
