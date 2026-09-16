import { useEffect, useState } from 'react'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Bar, Loading, ScoreRing, rupees } from '../components/ui'
import { artisanImpact, listUsers, ministryCsvUrl, ministryReport } from '../api/client'

/**
 * What the assistance actually did.
 *
 * MoSJE lends through NSFDC, NSKFDC, NBCFDC and NDFDC to set up a handicraft
 * unit, and then has no way to learn what happened to that household's income
 * except by surveying them years later. PAVHAN holds the transactions, so it
 * can answer the question with measurements instead of recall.
 *
 * Two views: the artisan's own, which is about whether they can service what
 * they borrowed, and the ministry's, which is the aggregate a desk would open.
 */
export default function Impact() {
  const { t, lang, user, setUser, role } = useApp()
  const [view, setView] = useState(role === 'artisan' ? 'mine' : 'ministry')
  const [mine, setMine] = useState(null)
  const [ministry, setMinistry] = useState(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    let alive = true
    async function load() {
      let id = user?.id
      if (!id) {
        const artisans = await listUsers('artisan').catch(() => [])
        id = artisans[0]?.id
        if (artisans[0]) setUser(artisans[0])
      }
      const [a, m] = await Promise.all([
        id ? artisanImpact(id).catch(() => null) : null,
        ministryReport().catch(() => null),
      ])
      if (!alive) return
      setMine(a); setMinistry(m); setLoading(false)
    }
    load()
    return () => { alive = false }
  }, []) // eslint-disable-line

  if (loading) return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)

  return (
    <>
      <TopBar
        title={t('योजना का असर', 'Scheme impact')}
        subtitle={t('सामाजिक न्याय मंत्रालय', 'Ministry of Social Justice')}
        back
      />
      <Screen>
        <div className="page stack">
          <div className="chiprow">
            <button className={`chip ${view === 'mine' ? 'active' : ''}`}
                    onClick={() => setView('mine')}>
              {t('मेरा हिसाब', 'My record')}
            </button>
            <button className={`chip ${view === 'ministry' ? 'active' : ''}`}
                    onClick={() => setView('ministry')}>
              {t('मंत्रालय की रिपोर्ट', 'Ministry report')}
            </button>
          </div>

          {view === 'mine' && mine && <MyImpact report={mine} />}
          {view === 'ministry' && ministry && <MinistryView data={ministry} />}
        </div>
      </Screen>
    </>
  )
}

function MyImpact({ report }) {
  const { t, lang } = useApp()
  const up = report.uplift_percent
  const notes = (lang === 'hi' ? report.notes_hi : report.notes) || []

  return (
    <>
      {report.scheme_linked ? (
        <div className="card" style={{ background: 'var(--ink)', color: '#fff', border: 0 }}>
          <div style={{ fontSize: 'calc(11px * var(--font-scale))', color: '#b0b8d8', textTransform: 'uppercase',
                        letterSpacing: '0.06em', fontWeight: 700 }}>
            {report.corporation}
          </div>
          <div style={{ fontWeight: 700, fontSize: 'calc(15px * var(--font-scale))', marginTop: 4 }}>
            {report.scheme_name}
          </div>
          <div style={{ fontSize: 'calc(11.5px * var(--font-scale))', color: '#b0b8d8', marginTop: 3 }} className="mono">
            {report.beneficiary_id}
          </div>
          {report.corporation_detail && (
            <div style={{ fontSize: 'calc(11px * var(--font-scale))', color: '#98a0c0', marginTop: 8, lineHeight: 1.55 }}
                 lang={lang}>
              {lang === 'hi' ? report.corporation_detail.name_hi
                             : report.corporation_detail.name}
            </div>
          )}
        </div>
      ) : (
        <div className="card" style={{ background: 'var(--marigold-soft)',
                                       borderColor: 'var(--line)' }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
            {t('कोई योजना जुड़ी नहीं है', 'No scheme is linked')}
          </div>
          <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.6, marginTop: 5 }}
               lang={lang}>
            {t('अगर आपका काम किसी सरकारी योजना के ऋण से शुरू हुआ है, तो उसे जोड़िए — '
               + 'आपकी बिक्री ही इसका सबूत बनेगी कि सहायता से फ़र्क़ पड़ा।',
               'If a government loan set up your unit, link it — your sales become the '
               + 'evidence that the assistance worked.')}
          </div>
        </div>
      )}

      <div className="card">
        <div className="row" style={{ gap: 14, alignItems: 'center' }}>
          <div style={{ flex: 1 }}>
            <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', textTransform: 'uppercase',
                                            fontWeight: 700 }} lang={lang}>
              {t('पहले (आपका बताया)', 'Before — self-declared')}
            </div>
            <div className="mono" style={{ fontSize: 'calc(19px * var(--font-scale))', fontWeight: 700 }}>
              {rupees(report.baseline_monthly)}
            </div>
          </div>
          <div style={{ fontSize: 'calc(20px * var(--font-scale))', color: 'var(--muted)' }}>→</div>
          <div style={{ flex: 1, textAlign: 'right' }}>
            <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', textTransform: 'uppercase',
                                            fontWeight: 700 }} lang={lang}>
              {t('अब (मापी गई)', 'Now — measured')}
            </div>
            <div className="mono" style={{ fontSize: 'calc(22px * var(--font-scale))', fontWeight: 800,
                                           color: 'var(--leaf)' }}>
              {rupees(report.monthly_earnings)}
            </div>
          </div>
        </div>
        {up !== 0 && report.baseline_monthly > 0 && (
          <div style={{ marginTop: 12, padding: '9px 12px', borderRadius: 10,
                        background: up > 0 ? 'var(--leaf-soft)' : 'var(--marigold-soft)',
                        fontSize: 'calc(12.5px * var(--font-scale))', fontWeight: 700, textAlign: 'center' }} lang={lang}>
            {up > 0
              ? t(`महीने की आमदनी ${up.toFixed(0)}% बढ़ी`, `Monthly income up ${up.toFixed(0)}%`)
              : t(`महीने की आमदनी ${Math.abs(up).toFixed(0)}% घटी`,
                   `Monthly income down ${Math.abs(up).toFixed(0)}%`)}
          </div>
        )}
        <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 9 }}
             lang={lang}>
          {t(`${report.months_active} महीने की असली बिक्री से निकाला गया।`,
             `Computed from ${report.months_active} months of actual sales.`)}
        </div>
      </div>

      {report.loan_amount > 0 && (
        <div className="card">
          <div className="row-between" style={{ marginBottom: 10 }}>
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
              {t('ऋण चुकाने की स्थिति', 'Loan repayment')}
            </div>
            <span className={`pill ${report.emi_coverage >= 2 ? 'leaf'
              : report.emi_coverage >= 1 ? 'gold' : 'madder'}`} lang={lang}>
              {lang === 'hi' ? report.repayment_status_hi : report.repayment_status}
            </span>
          </div>
          {[
            [t('लिया गया ऋण', 'Loan taken'), rupees(report.loan_amount)],
            [t('अनुमानित मासिक किस्त', 'Indicative monthly instalment'),
             rupees(report.indicative_emi)],
            [t('आपकी मासिक कमाई', 'Your monthly earnings'), rupees(report.monthly_earnings)],
          ].map(([label, value]) => (
            <div key={label} className="row-between"
                 style={{ fontSize: 'calc(12.5px * var(--font-scale))', padding: '6px 0',
                          borderTop: '1px solid var(--line)' }}>
              <span className="muted" lang={lang}>{label}</span>
              <span className="mono" style={{ fontWeight: 700 }}>{value}</span>
            </div>
          ))}
          <div style={{ marginTop: 10 }}>
            <Bar value={Math.min(100, report.emi_coverage * 33)}
                 tone={report.emi_coverage >= 2 ? 'var(--leaf)'
                   : report.emi_coverage >= 1 ? 'var(--marigold)' : 'var(--madder)'} />
            <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 6, lineHeight: 1.55 }}
                 lang={lang}>
              {t(`आपकी कमाई किस्त से ${report.emi_coverage}× है।`,
                 `Your earnings cover the instalment ${report.emi_coverage}× over.`)}
            </div>
          </div>
        </div>
      )}

      <div className="card">
        <div className="row" style={{ gap: 13, alignItems: 'center' }}>
          <ScoreRing value={report.digital_readiness} label={t('डिजिटल', 'digital')} />
          <div style={{ flex: 1 }}>
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
              {t('डिजिटल तैयारी', 'Digital readiness')}
            </div>
            <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.55, marginTop: 3 }}
                 lang={lang}>
              {t(`${report.products} सामान, ${report.orders} ऑर्डर, ${report.buyers_reached} खरीदार तक पहुँच।`,
                 `${report.products} listings, ${report.orders} orders, ${report.buyers_reached} buyers reached.`)}
            </div>
          </div>
        </div>
      </div>

      <div className="card" style={{ background: 'var(--leaf-soft)', borderColor: 'var(--line)' }}>
        <div style={{ fontSize: 'calc(12px * var(--font-scale))', fontWeight: 700, color: 'var(--leaf)' }} lang={lang}>
          {t('बिचौलिये के मुक़ाबले', 'Compared with a middleman')}
        </div>
        <div className="mono" style={{ fontSize: 'calc(22px * var(--font-scale))', fontWeight: 800, marginTop: 4,
                                       color: 'var(--leaf)' }}>
          +{rupees(report.kept_from_middleman)}
        </div>
        <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.55, marginTop: 4 }}
             lang={lang}>
          {t('यही सामान बिचौलिये को देते तो इतना कम मिलता।',
             'That is what a trader would have kept from these same sales.')}
        </div>
      </div>

      {notes.length > 0 && (
        <div className="card tinted">
          <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))', marginBottom: 7 }} lang={lang}>
            {t('इन आँकड़ों के बारे में', 'About these numbers')}
          </div>
          {notes.map((n) => (
            <div key={n} className="muted"
                 style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.65, marginBottom: 5 }} lang={lang}>
              • {n}
            </div>
          ))}
        </div>
      )}
    </>
  )
}

function MinistryView({ data }) {
  const { t, lang } = useApp()
  return (
    <>
      <div className="card" style={{ background: 'var(--ink)', color: '#fff', border: 0 }}>
        <div style={{ fontSize: 'calc(10.5px * var(--font-scale))', color: '#b0b8d8', textTransform: 'uppercase',
                      letterSpacing: '0.06em', fontWeight: 700 }} lang={lang}>
          {lang === 'hi' ? data.ministry_hi : data.ministry}
        </div>
        <div className="row" style={{ gap: 16, marginTop: 12, flexWrap: 'wrap' }}>
          {[
            [data.artisans_scheme_linked, t('योजना से जुड़े', 'scheme-linked')],
            [rupees(data.loan_disbursed_total), t('ऋण दिया गया', 'disbursed')],
            [rupees(data.mean_monthly_earnings), t('औसत मासिक', 'mean monthly')],
          ].map(([n, label]) => (
            <div key={label} style={{ flex: 1, minWidth: 92 }}>
              <div className="mono" style={{ fontSize: 'calc(17px * var(--font-scale))', fontWeight: 800,
                                             color: 'var(--marigold)' }}>{n}</div>
              <div style={{ fontSize: 'calc(9.5px * var(--font-scale))', color: '#98a0c0', textTransform: 'uppercase' }}
                   lang={lang}>{label}</div>
            </div>
          ))}
        </div>
      </div>

      {data.mean_uplift_percent !== null && (
        <div className="card">
          <div className="row-between">
            <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }} lang={lang}>
              {t('औसत आमदनी बढ़त', 'Mean income uplift')}
            </div>
            <span className="pill leaf mono">+{data.mean_uplift_percent}%</span>
          </div>
          <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.6, marginTop: 7 }}
               lang={lang}>
            {t(`${data.uplift_sample_size} कारीगरों के आँकड़े से`,
               `From a sample of ${data.uplift_sample_size} artisans`)}
            {data.uplift_excluded_implausible > 0 && t(
              `; ${data.uplift_excluded_implausible} असंभव आँकड़े हटाए गए`,
              `; ${data.uplift_excluded_implausible} implausible row(s) excluded`)}
          </div>
        </div>
      )}

      <div className="card">
        <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 10 }} lang={lang}>
          {t('निगम के अनुसार', 'By corporation')}
        </div>
        {data.by_corporation.map((c) => (
          <div key={c.corporation} style={{ padding: '8px 0',
                                            borderTop: '1px solid var(--line)' }}>
            <div className="row-between" style={{ fontSize: 'calc(13px * var(--font-scale))' }}>
              <span style={{ fontWeight: 700 }}>{c.corporation}</span>
              <span className="mono muted">{c.artisans} {t('कारीगर', 'artisans')}</span>
            </div>
            <div className="row-between" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 3 }}>
              <span className="muted">{t('ऋण', 'disbursed')} {rupees(c.loan_disbursed)}</span>
              {c.mean_uplift_percent !== null && (
                <span className="mono" style={{ fontWeight: 700, color: 'var(--leaf)' }}>
                  +{c.mean_uplift_percent}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <div className="card">
        <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
          {t('श्रेणी के अनुसार', 'By social category')}
        </div>
        <div className="row" style={{ gap: 7, flexWrap: 'wrap' }}>
          {Object.entries(data.by_social_category).map(([code, n]) => (
            <span key={code} className="pill">{code} · {n}</span>
          ))}
        </div>
      </div>

      <div className="card">
        <div style={{ fontWeight: 700, fontSize: 'calc(13px * var(--font-scale))', marginBottom: 9 }} lang={lang}>
          {t('कारीगरवार', 'Artisan by artisan')}
        </div>
        {data.artisans.slice(0, 10).map((a) => (
          <div key={a.id} style={{ padding: '8px 0', borderTop: '1px solid var(--line)' }}>
            <div className="row-between" style={{ fontSize: 'calc(12.5px * var(--font-scale))' }}>
              <span style={{ fontWeight: 600 }}>{a.name}</span>
              <span className="mono">{rupees(a.monthly_earnings)}</span>
            </div>
            <div className="row-between muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', marginTop: 2 }}>
              <span>{a.social_category} {a.corporation ? `· ${a.corporation}` : ''}</span>
              {a.uplift_percent !== null && (
                <span style={{ color: a.uplift_percent >= 0 ? 'var(--leaf)' : 'var(--madder)',
                               fontWeight: 700 }}>
                  {a.uplift_percent >= 0 ? '+' : ''}{a.uplift_percent}%
                </span>
              )}
            </div>
          </div>
        ))}
      </div>

      <a className="btn btn-ink btn-block" href={ministryCsvUrl()} download
         style={{ textDecoration: 'none' }}>
        ⬇ {t('पूरी रिपोर्ट डाउनलोड कीजिए (CSV)', 'Download the full report (CSV)')}
      </a>

      <div className="card tinted">
        <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))', marginBottom: 6 }} lang={lang}>
          {t('यह आँकड़े कैसे बने', 'How these numbers were produced')}
        </div>
        <div style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.7, color: 'var(--ink-soft)' }} lang={lang}>
          {lang === 'hi' ? data.method_hi : data.method}
        </div>
      </div>
    </>
  )
}
