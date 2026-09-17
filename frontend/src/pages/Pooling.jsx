import { useCallback, useEffect, useState } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { Empty, Loading, rupees, useScreenVoice } from '../components/ui'
import {
  artisanPools, createPool, listRequirements, listUsers, poolCluster,
  previewPool, submitPoolQuote,
} from '../api/client'

/**
 * Taking an order together.
 *
 * The orders worth having are the ones a single artisan has to refuse. This
 * screen is where six people who can each make seventy pieces answer a buyer
 * who wants four hundred.
 *
 * Everything on it is designed to be shown to the group before they agree:
 * each member's capacity, each member's share, each member's rupees, and the
 * one sentence that explains why the leftovers went where they went.
 */
export default function Pooling() {
  const [params] = useSearchParams()
  const navigate = useNavigate()
  const { t, lang, user, setUser, toast } = useApp()

  const [artisanId, setArtisanId] = useState(user?.id || '')
  const [requirements, setRequirements] = useState([])
  const [requirementId, setRequirementId] = useState(params.get('requirement') || '')
  const [cluster, setCluster] = useState(null)
  const [chosen, setChosen] = useState([])
  const [plan, setPlan] = useState(null)
  const [pools, setPools] = useState([])
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState('')

  const requirement = requirements.find((r) => r.id === requirementId)

  const boot = useCallback(async () => {
    let id = user?.id
    if (!id) {
      const artisans = await listUsers('artisan').catch(() => [])
      id = artisans[0]?.id
      if (artisans[0]) setUser(artisans[0])
    }
    if (!id) { setLoading(false); return }
    setArtisanId(id)
    const [reqs, mine] = await Promise.all([
      listRequirements(id).catch(() => ({ requirements: [] })),
      artisanPools(id).catch(() => ({ pools: [] })),
    ])
    setRequirements(reqs.requirements || [])
    setPools(mine.pools || [])
    if (!requirementId && reqs.requirements?.length) {
      // Default to the one that most needs pooling.
      const biggest = [...reqs.requirements].sort((a, b) => b.quantity - a.quantity)[0]
      setRequirementId(biggest.id)
    }
    setLoading(false)
  }, [user?.id]) // eslint-disable-line react-hooks/exhaustive-deps

  useEffect(() => { boot() }, [boot])
  useScreenVoice('pooling', {}, [loading])

  // Reload the cluster whenever the deadline changes, because capacity is
  // measured inside the buyer's window and a different window is a different
  // set of people who can help.
  useEffect(() => {
    if (!artisanId || !requirement) return
    poolCluster(artisanId, requirement.delivery_days)
      .then((c) => {
        setCluster(c)
        setChosen(c.members.map((m) => m.artisan_id))
        setPlan(null)
      })
      .catch(() => setCluster(null))
  }, [artisanId, requirementId]) // eslint-disable-line react-hooks/exhaustive-deps

  const toggle = (id) => {
    setChosen((prev) => prev.includes(id) ? prev.filter((x) => x !== id) : [...prev, id])
    setPlan(null)
  }

  const workOut = async () => {
    setBusy('plan')
    try {
      setPlan(await previewPool({
        requirement_id: requirementId, lead_artisan_id: artisanId,
        member_ids: chosen, coordination: true,
      }))
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  const commit = async () => {
    setBusy('commit')
    try {
      const res = await createPool({
        requirement_id: requirementId, lead_artisan_id: artisanId,
        member_ids: chosen, coordination: true,
      })
      toast(t('समूह बन गया। सबको न्योता भेजिए।', 'Pool created. Now invite everyone.'), 'ok')
      setPlan(null)
      await boot()
      // Open the first invite straight away — the message is already written.
      if (res.invites?.[0]) window.open(res.invites[0].whatsapp, '_blank', 'noopener')
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy('') }
  }

  if (loading) return (<><TopBar title="…" back /><Screen><Loading /></Screen></>)

  return (
    <>
      <TopBar title={t('मिलकर ऑर्डर लीजिए', 'Take an order together')}
              subtitle={cluster?.lead?.shg_name || cluster?.lead?.cluster || ''} back />
      <Screen>
        <div className="stack">
          {pools.length > 0 && pools.map((p) => (
            <PoolCard key={p.id} pool={p} t={t} lang={lang} toast={toast}
                      onChanged={boot} />
          ))}

          {requirements.length === 0 ? (
            <Empty icon="👥" title={t('अभी कोई माँग नहीं', 'No requirements yet')}
                   body={t('जब कोई खरीदार बड़ी माँग डालेगा, उसे यहाँ समूह में बाँट सकेंगे।',
                            'When a buyer posts a large requirement, you can share it across your group here.')} />
          ) : (
            <>
              <div className="card">
                <div className="field">
                  <label lang={lang}>{t('कौन-सी माँग', 'Which requirement')}</label>
                  <select className="input" value={requirementId}
                          onChange={(e) => setRequirementId(e.target.value)}>
                    {requirements.map((r) => (
                      <option key={r.id} value={r.id}>
                        {r.title} · {r.quantity} × · {r.delivery_days}d
                      </option>
                    ))}
                  </select>
                </div>
                {requirement && (
                  <div className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))', marginTop: 8, lineHeight: 1.5 }}
                       lang={lang}>
                    {requirement.quantity} {t('पीस', 'pieces')} · {requirement.delivery_days} {t('दिन', 'days')}
                    {' · '}{rupees(requirement.budget_min)}–{rupees(requirement.budget_max)} {t('प्रति पीस', 'each')}
                  </div>
                )}
              </div>

              {cluster && (
                <>
                  <div className="section-title" lang={lang}>
                    {t('आपका समूह', 'Your group')}
                  </div>
                  <div className="section-sub" lang={lang} style={{ padding: '0 2px', marginTop: -4 }}>
                    {lang === 'hi' ? cluster.note_hi : cluster.note}
                  </div>

                  <MemberRow member={cluster.lead} lead lang={lang} t={t} />
                  {cluster.members.map((m) => (
                    <MemberRow key={m.artisan_id} member={m} lang={lang} t={t}
                               checked={chosen.includes(m.artisan_id)}
                               onToggle={() => toggle(m.artisan_id)} />
                  ))}
                  {cluster.members.length === 0 && (
                    <div className="card muted" style={{ fontSize: 'calc(12.5px * var(--font-scale))', lineHeight: 1.5 }}
                         lang={lang}>
                      {t('आपके समूह या क्लस्टर में अभी कोई और कारीगर नहीं है।',
                         'Nobody else is in your self-help group or cluster yet.')}
                    </div>
                  )}

                  <button className="btn btn-primary btn-block" onClick={workOut}
                          disabled={busy === 'plan' || !chosen.length}>
                    {busy === 'plan' ? <span className="spinner" />
                      : t('हिस्सा निकालिए', 'Work out the split')}
                  </button>
                </>
              )}

              {plan && <PlanCard plan={plan} lang={lang} t={t}
                                 onCommit={commit} busy={busy === 'commit'} />}
            </>
          )}
        </div>
      </Screen>
    </>
  )
}

function MemberRow({ member, lead, checked, onToggle, lang, t }) {
  return (
    <button className="card" onClick={onToggle} disabled={lead}
            style={{
              textAlign: 'left', width: '100%', padding: '11px 12px',
              borderColor: lead || checked ? 'var(--indigo)' : 'var(--line)',
              opacity: lead || checked ? 1 : 0.62,
            }}>
      <div className="row" style={{ gap: 10, alignItems: 'center' }}>
        <div style={{ fontSize: 'calc(21px * var(--font-scale))' }}>{member.avatar || '🧑‍🎨'}</div>
        <div style={{ flex: 1, minWidth: 0 }}>
          <div style={{ fontWeight: 700, fontSize: 'calc(13.5px * var(--font-scale))' }}>
            {member.name}{lead && ` · ${t('आप', 'you')}`}
          </div>
          <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', marginTop: 2 }} lang={lang}>
            {lead ? (member.shg_name || member.cluster)
                  : (lang === 'hi' ? member.reason_hi : member.reason)}
            {!member.capacity_stated && ` · ${t('अनुमानित क्षमता', 'capacity estimated')}`}
          </div>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ fontWeight: 800, fontSize: 'calc(15px * var(--font-scale))' }}>
            {member.capacity_window}
          </div>
          <div className="muted" style={{ fontSize: 'calc(9.5px * var(--font-scale))', textTransform: 'uppercase' }}
               lang={lang}>
            {t('पीस', 'pieces')}
          </div>
        </div>
      </div>
    </button>
  )
}

function PlanCard({ plan, lang, t, onCommit, busy }) {
  return (
    <div className="card" style={{ borderColor: plan.feasible ? 'var(--leaf)' : 'var(--marigold)' }}>
      <div style={{ fontWeight: 800, fontSize: 'calc(14px * var(--font-scale))', lineHeight: 1.4 }} lang={lang}>
        {plan.feasible ? '✅ ' : '⚠️ '}{lang === 'hi' ? plan.summary_hi : plan.summary}
      </div>

      <div style={{ marginTop: 12 }}>
        {plan.members.filter((m) => m.allocated > 0).map((m) => (
          <div key={m.artisan_id} className="row-between"
               style={{ padding: '7px 0', borderBottom: '1px solid var(--line)', gap: 10 }}>
            <div style={{ flex: 1, minWidth: 0 }}>
              <div style={{ fontWeight: 700, fontSize: 'calc(12.5px * var(--font-scale))' }}>
                {m.name}{m.is_lead && ` · ${t('मुखिया', 'lead')}`}
              </div>
              <div className="muted" style={{ fontSize: 'calc(10.5px * var(--font-scale))', marginTop: 2, lineHeight: 1.4 }}
                   lang={lang}>
                {lang === 'hi' ? m.note_hi : m.note}
                {m.coordination > 0 && ` · +${rupees(m.coordination)} ${t('समन्वय', 'coordination')}`}
              </div>
            </div>
            <div style={{ textAlign: 'right' }}>
              <div style={{ fontWeight: 800, fontSize: 'calc(13.5px * var(--font-scale))' }}>
                {m.allocated}
              </div>
              <div className="mono muted" style={{ fontSize: 'calc(11px * var(--font-scale))' }}>
                {rupees(m.payout)}
              </div>
            </div>
          </div>
        ))}
      </div>

      <div className="row-between" style={{ marginTop: 11 }}>
        <span className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
          {t('कुल ऑर्डर', 'Order total')}
        </span>
        <span style={{ fontWeight: 700 }}>{rupees(plan.gross)}</span>
      </div>
      <div className="row-between" style={{ marginTop: 4 }}>
        <span className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
          {t('प्लेटफ़ॉर्म शुल्क', 'Platform fee')}
        </span>
        <span className="muted">−{rupees(plan.platform_fee)}</span>
      </div>
      {plan.coordination_pot > 0 && (
        <div className="row-between" style={{ marginTop: 4 }}>
          <span className="muted" style={{ fontSize: 'calc(12px * var(--font-scale))' }} lang={lang}>
            {t('मुखिया का समन्वय हिस्सा', 'Lead’s coordination share')} · 3%
          </span>
          <span className="muted">{rupees(plan.coordination_pot)}</span>
        </div>
      )}

      <div style={{
        marginTop: 11, padding: 10, borderRadius: 11, background: 'var(--paper-2)',
        fontSize: 'calc(11.5px * var(--font-scale))', lineHeight: 1.5,
      }} lang={lang}>
        {lang === 'hi' ? plan.fairness_note_hi : plan.fairness_note}
      </div>

      {plan.feasible && (
        <button className="btn btn-primary btn-block" style={{ marginTop: 12 }}
                onClick={onCommit} disabled={busy}>
          {busy ? <span className="spinner" />
            : t('समूह बनाइए और न्योता भेजिए', 'Create the pool and invite')}
        </button>
      )}
    </div>
  )
}

function PoolCard({ pool, t, lang, toast, onChanged }) {
  const [busy, setBusy] = useState(false)
  const quote = async () => {
    setBusy(true)
    try {
      await submitPoolQuote(pool.id)
      toast(t('खरीदार को एक ही कोटेशन भेज दिया।', 'One quote sent to the buyer.'), 'ok')
      onChanged()
    } catch (err) {
      toast(err.message, 'err')
    } finally { setBusy(false) }
  }
  return (
    <div className="card" style={{ borderColor: 'var(--indigo)' }}>
      <div className="row-between">
        <div style={{ fontWeight: 800, fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.35 }}>
          👥 {pool.requirement_title || t('समूह ऑर्डर', 'Pooled order')}
        </div>
        <span className="pill">{pool.status}</span>
      </div>
      <div className="muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginTop: 5 }} lang={lang}>
        {pool.shg_name || pool.cluster} · {pool.members.length} {t('कारीगर', 'artisans')}
        {' · '}{pool.committed_qty}/{pool.quantity} {t('पक्के', 'committed')}
      </div>
      {pool.my_membership && (
        <div style={{ marginTop: 8, fontSize: 'calc(12.5px * var(--font-scale))' }} lang={lang}>
          {t('आपका हिस्सा', 'Your share')}: <strong>{pool.my_membership.allocated_qty}</strong>
          {' · '}<strong>{rupees(pool.my_membership.payout)}</strong>
        </div>
      )}
      {pool.my_membership?.is_lead && pool.status === 'forming' && (
        <button className="btn btn-soft btn-sm btn-block" style={{ marginTop: 10 }}
                onClick={quote} disabled={busy || !pool.all_accepted}>
          {busy ? <span className="spinner dark" />
            : pool.all_accepted
              ? t('खरीदार को कोटेशन भेजिए', 'Send the buyer one quote')
              : t(`${pool.pending_qty} पीस की मंज़ूरी बाकी`, `${pool.pending_qty} pieces still unaccepted`)}
        </button>
      )}
    </div>
  )
}
