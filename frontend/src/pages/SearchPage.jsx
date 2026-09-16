import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, ProductCard, SkeletonCard, VoiceOrb, rupees, useScreenVoice } from '../components/ui'
import useSpeechRecognition from '../hooks/useSpeechRecognition'
import { search, suggest } from '../api/client'

const SORTS = [
  ['relevance', 'सटीक', 'Best match'],
  ['price_asc', 'सस्ता पहले', 'Price ↑'],
  ['price_desc', 'महँगा पहले', 'Price ↓'],
  ['quality', 'गुणवत्ता', 'Quality'],
  ['newest', 'नया', 'Newest'],
]

export default function SearchPage() {
  const navigate = useNavigate()
  const [params, setParams] = useSearchParams()
  const { t, lang, toast, L } = useApp()

  const [q, setQ] = useState(params.get('q') || '')
  const [data, setData] = useState(null)
  const [loading, setLoading] = useState(false)
  const [sort, setSort] = useState('relevance')
  const [filters, setFilters] = useState({})
  const [showFilters, setShowFilters] = useState(false)
  const [suggestions, setSuggestions] = useState([])
  const inputRef = useRef(null)

  useScreenVoice('search')

  const mic = useSpeechRecognition({
    lang,
    onFinal: (text) => { setQ(text); run(text) },
  })

  const run = useCallback(async (query = q, nextSort = sort, nextFilters = filters) => {
    setLoading(true)
    try {
      const res = await search({ q: query, sort: nextSort, limit: 40, ...nextFilters })
      setData(res)
      setParams(query ? { q: query } : {}, { replace: true })
    } catch (err) {
      toast(err.message, 'err')
    } finally {
      setLoading(false)
      setSuggestions([])
    }
  }, [q, sort, filters]) // eslint-disable-line

  useEffect(() => { run(params.get('q') || '') }, []) // eslint-disable-line

  // autocomplete
  useEffect(() => {
    if (q.trim().length < 2) { setSuggestions([]); return undefined }
    const timer = setTimeout(() => {
      suggest(q.trim().split(/\s+/).pop()).then((r) => setSuggestions(r.suggestions || [])).catch(() => {})
    }, 180)
    return () => clearTimeout(timer)
  }, [q])

  const applyFilter = (key, value) => {
    const next = { ...filters }
    if (next[key] === value || value === '') delete next[key]
    else next[key] = value
    setFilters(next)
    run(q, sort, next)
  }

  const facets = data?.facets || {}
  const activeCount = Object.keys(filters).length

  return (
    <>
      <TopBar title={t('खोजिए', 'Search')} back onBack={() => navigate(-1)} />
      <Screen>
        <div className="page-tight stack" style={{ paddingTop: 14 }}>
          <div style={{ position: 'relative' }}>
            <div className="card row" style={{ gap: 9, padding: '10px 13px' }}>
              <span style={{ fontSize: 'calc(15px * var(--font-scale))' }}>🔍</span>
              <input
                ref={inputRef}
                value={q}
                lang={lang}
                onChange={(e) => setQ(e.target.value)}
                onKeyDown={(e) => e.key === 'Enter' && run()}
                placeholder={t('हिंदी या अंग्रेज़ी में लिखिए…', 'Type in Hindi or English…')}
                style={{ flex: 1, border: 0, outline: 0, background: 'none', fontSize: 'calc(14.5px * var(--font-scale))', minWidth: 0 }}
              />
              {q && (
                <button
                  onClick={() => { setQ(''); run('') }}
                  style={{ border: 0, background: 'none', color: 'var(--muted)', fontSize: 'calc(16px * var(--font-scale))' }}
                >
                  ✕
                </button>
              )}
              <button
                onClick={() => (mic.listening ? mic.stop() : mic.start({ reset: true }))}
                style={{
                  border: 0, borderRadius: 10, width: 34, height: 34,
                  background: mic.listening ? 'var(--madder)' : 'var(--paper-2)',
                  color: mic.listening ? '#fff' : 'var(--ink)', fontSize: 'calc(15px * var(--font-scale))',
                  animation: mic.listening ? 'pulseRing 1.5s infinite' : 'none',
                }}
                aria-label={t('बोलकर खोजिए', 'Search by voice')}
              >
                {mic.listening ? '⏹' : '🎤'}
              </button>
            </div>

            {suggestions.length > 0 && (
              <div
                className="card fade-up"
                style={{ position: 'absolute', top: '104%', left: 0, right: 0, zIndex: 30, padding: 6 }}
              >
                {suggestions.map((s) => (
                  <button
                    key={s}
                    onClick={() => { const next = q.trim().split(/\s+/).slice(0, -1).concat(s).join(' '); setQ(next); run(next) }}
                    style={{
                      display: 'block', width: '100%', textAlign: 'left', border: 0,
                      background: 'none', padding: '9px 10px', fontSize: 'calc(13.5px * var(--font-scale))', borderRadius: 9,
                    }}
                  >
                    🔍 {s}
                  </button>
                ))}
              </div>
            )}
          </div>

          {mic.listening && (
            <div className="center muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
              {mic.interim || t('सुन रहा हूँ…', 'Listening…')}
            </div>
          )}
          {mic.error && (
            <div className="muted center" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.5 }} lang={lang}>
              {mic.error}
            </div>
          )}

          <div className="chiprow">
            <button
              className={`chip ${showFilters || activeCount ? 'active' : ''}`}
              onClick={() => setShowFilters(!showFilters)}
            >
              ⚙︎ {t('छाँटिए', 'Filters')}{activeCount ? ` (${activeCount})` : ''}
            </button>
            {SORTS.map(([key, hi, en]) => (
              <button
                key={key}
                className={`chip ${sort === key ? 'active' : ''}`}
                onClick={() => { setSort(key); run(q, key) }}
              >
                {lang === 'hi' ? hi : en}
              </button>
            ))}
          </div>

          {showFilters && (
            <div className="card fade-up stack" style={{ gap: 13 }}>
              {[
                ['category', t('श्रेणी', 'Category')],
                ['craft_type', t('शिल्प', 'Craft')],
                ['material', t('सामग्री', 'Material')],
                ['region', t('क्षेत्र', 'Region')],
              ].map(([key, label]) => (
                (facets[key] || []).length > 0 && (
                  <div key={key}>
                    <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', fontWeight: 700, marginBottom: 6, color: 'var(--ink-soft)' }}>
                      {label}
                    </div>
                    <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                      {facets[key].slice(0, 8).map((f) => (
                        <button
                          key={f.value}
                          className={`chip ${filters[key] === f.value ? 'active' : ''}`}
                          style={{ padding: '6px 11px', fontSize: 'calc(11.5px * var(--font-scale))' }}
                          onClick={() => applyFilter(key, f.value)}
                        >
                          {L(f.value)} <span className="muted">{f.count}</span>
                        </button>
                      ))}
                    </div>
                  </div>
                )
              ))}

              {facets.price?.buckets?.length > 0 && (
                <div>
                  <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', fontWeight: 700, marginBottom: 6, color: 'var(--ink-soft)' }}>
                    {t('दाम', 'Price')}
                  </div>
                  <div className="row" style={{ gap: 6, flexWrap: 'wrap' }}>
                    {facets.price.buckets.filter((b) => b.count).map((b) => (
                      <button
                        key={b.label}
                        className={`chip ${filters.min_price === b.min ? 'active' : ''}`}
                        style={{ padding: '6px 11px', fontSize: 'calc(11.5px * var(--font-scale))' }}
                        onClick={() => {
                          const next = { ...filters }
                          if (next.min_price === b.min) { delete next.min_price; delete next.max_price }
                          else { next.min_price = b.min; if (b.max) next.max_price = b.max; else delete next.max_price }
                          setFilters(next); run(q, sort, next)
                        }}
                      >
                        {b.label.replace('Rs.', '₹')} <span className="muted">{b.count}</span>
                      </button>
                    ))}
                  </div>
                </div>
              )}

              <div className="row" style={{ gap: 8 }}>
                <button
                  className={`chip ${filters.gi_only ? 'active' : ''}`}
                  onClick={() => applyFilter('gi_only', filters.gi_only ? '' : true)}
                >
                  🏅 {t('केवल जीआई प्रमाणित', 'GI-tagged only')}
                </button>
                {activeCount > 0 && (
                  <button
                    className="chip"
                    onClick={() => { setFilters({}); run(q, sort, {}) }}
                  >
                    ✕ {t('हटाइए', 'Clear')}
                  </button>
                )}
              </div>
            </div>
          )}

          {data && !loading && (
            <div className="row-between muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))' }}>
              <span>
                {t(`${data.total} चीज़ें मिलीं`, `${data.total} results`)}
                {data.query && ` · "${data.query}"`}
              </span>
              <span className="mono">{data.took_ms}ms</span>
            </div>
          )}

          {data?.did_you_mean && (
            <button
              className="card"
              style={{ textAlign: 'left', fontSize: 'calc(13px * var(--font-scale))', padding: '11px 13px' }}
              onClick={() => { setQ(data.did_you_mean); run(data.did_you_mean) }}
            >
              {t('क्या आपका मतलब ', 'Did you mean ')}
              <strong style={{ color: 'var(--madder)' }}>{data.did_you_mean}</strong>
              {t(' था?', '?')}
            </button>
          )}

          {loading ? (
            <div className="stack"><SkeletonCard /><SkeletonCard /><SkeletonCard /></div>
          ) : data?.results?.length ? (
            <div className="stack">
              {data.results.map((p) => <ProductCard key={p.id} product={p} />)}
            </div>
          ) : data ? (
            <Empty
              icon="🔍"
              title={t('कुछ नहीं मिला', 'No matches')}
              body={t('कोई और शब्द आज़माइए, या छाँटने वाले विकल्प हटा दीजिए।',
                      'Try a different word, or clear the filters.')}
            />
          ) : null}
        </div>
        <VoiceOrb script="search" />
      </Screen>
    </>
  )
}
