import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { aiStatus, health, platformStats, priceModelCard, voiceLanguages } from '../api/client'

export default function Profile() {
  const navigate = useNavigate()
  const { t, lang, setLang, role, setRole, user, voiceOn, setVoiceOn, assistant,
          sayRaw, L, pwa, theme, toggleTheme } = useApp()
  const [status, setStatus] = useState(null)
  const [stats, setStats] = useState(null)
  const [modelCard, setModelCard] = useState(null)
  const [langCount, setLangCount] = useState(0)

  useEffect(() => {
    Promise.all([
      aiStatus().catch(() => null),
      platformStats().catch(() => null),
      health().catch(() => null),
      priceModelCard().catch(() => null),
      voiceLanguages().catch(() => null),
    ]).then(([ai, st, , model, langs]) => {
      setStatus(ai); setStats(st); setModelCard(model)
      setLangCount(langs?.languages?.length || 0)
    })
  }, [])

  const ROLES = [
    ['artisan', '🧵', t('कारीगर', 'Artisan'), '/artisan'],
    ['customer', '🛍️', t('ख़रीदार', 'Shopper'), '/shop'],
    ['b2b', '🏬', t('थोक ख़रीदार', 'Bulk buyer'), '/b2b'],
    ['exporter', '🌍', t('निर्यातक', 'Exporter'), '/b2b'],
  ]

  return (
    <>
      <TopBar title={t('खाता और सेटिंग', 'Account & settings')} />
      <Screen>
        <div className="page stack">
          <div className="card row" style={{ gap: 13 }}>
            <div
              style={{
                width: 52, height: 52, borderRadius: 16, background: 'var(--paper-2)',
                display: 'grid', placeItems: 'center', fontSize: 26,
              }}
            >
              {user?.avatar || '👤'}
            </div>
            <div style={{ flex: 1 }}>
              <div style={{ fontWeight: 700, fontSize: 15.5 }}>
                {user?.name || t('मेहमान', 'Guest')}
              </div>
              <div className="muted" style={{ fontSize: 12, marginTop: 2 }}>
                {L(user?.craft_focus) || ''} {user?.region ? `· ${L(user.region)}` : ''}
              </div>
            </div>
          </div>

          <div className="card">
            <div style={{ fontWeight: 700, fontSize: 13.5, marginBottom: 10 }} lang={lang}>
              {t('मैं यहाँ किस काम से हूँ', 'What I am here for')}
            </div>
            <div className="grid-2">
              {ROLES.map(([key, icon, label, path]) => (
                <button
                  key={key}
                  className={`chip ${role === key ? 'active' : ''}`}
                  style={{ padding: '12px 10px', justifyContent: 'center', display: 'flex', gap: 7 }}
                  onClick={() => { setRole(key); navigate(path) }}
                >
                  <span>{icon}</span> {label}
                </button>
              ))}
            </div>
          </div>

          {/* Installing matters more than it sounds: an icon on the home
              screen is what turns this from "a website someone showed me"
              into something an artisan opens on their own next week. */}
          {(pwa.canInstall || pwa.installed) && (
            <div className="card" style={{ background: 'var(--marigold-soft)',
                                           borderColor: 'var(--line)' }}>
              <div className="row-between">
                <div style={{ flex: 1 }}>
                  <div style={{ fontWeight: 700, fontSize: 13.5 }} lang={lang}>
                    📲 {pwa.installed
                      ? t('ऐप इंस्टॉल है', 'Installed as an app')
                      : t('फ़ोन में ऐप की तरह लगाइए', 'Install it like an app')}
                  </div>
                  <div className="muted" style={{ fontSize: 11.5, lineHeight: 1.55, marginTop: 3 }}
                       lang={lang}>
                    {pwa.installed
                      ? t('बिना इंटरनेट भी खुलेगा और सहेजा काम दिखेगा।',
                           'It opens without internet and shows your saved work.')
                      : t('होम स्क्रीन पर आइकॉन आ जाएगा, इंटरनेट न हो तब भी खुलेगा।',
                           'You get an icon on your home screen, and it opens offline.')}
                  </div>
                </div>
                {!pwa.installed && (
                  <button className="btn btn-gold btn-sm" onClick={pwa.install}>
                    {t('लगाइए', 'Install')}
                  </button>
                )}
              </div>
            </div>
          )}

          <div className="card">
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div>
                <div style={{ fontWeight: 700, fontSize: 13.5 }} lang={lang}>
                  🗣️ {t('आवाज़ वाली मदद', 'Voice guide')}
                </div>
                <div className="muted" style={{ fontSize: 11.5, marginTop: 2, lineHeight: 1.5 }} lang={lang}>
                  {t('हर पन्ने पर बोलकर बताती है कि क्या करना है।',
                     'Explains every screen out loud as you go.')}
                </div>
              </div>
              <button
                className={`btn btn-sm ${voiceOn ? 'btn-gold' : 'btn-soft'}`}
                onClick={() => { if (voiceOn) assistant.cancel(); setVoiceOn(!voiceOn) }}
              >
                {voiceOn ? t('चालू', 'On') : t('बंद', 'Off')}
              </button>
            </div>
            <div className="row-between" style={{ marginBottom: 12 }}>
              <div style={{ fontWeight: 700, fontSize: 13.5 }} lang={lang}>
                {theme === 'dark' ? '🌙' : '☀️'} {t('रंग-रूप', 'Appearance')}
              </div>
              <div className="row" style={{ gap: 7 }}>
                <button className={`chip ${theme === 'light' ? 'active' : ''}`}
                        onClick={() => theme === 'dark' && toggleTheme()}>
                  {t('उजला', 'Light')}
                </button>
                <button className={`chip ${theme === 'dark' ? 'active' : ''}`}
                        onClick={() => theme === 'light' && toggleTheme()}>
                  {t('गहरा', 'Dark')}
                </button>
              </div>
            </div>
            <div className="row-between">
              <div style={{ fontWeight: 700, fontSize: 13.5 }} lang={lang}>
                🌐 {t('भाषा', 'Language')}
              </div>
              <div className="row" style={{ gap: 7 }}>
                <button
                  className={`chip ${lang === 'hi' ? 'active' : ''}`}
                  onClick={() => setLang('hi')}
                >
                  हिंदी
                </button>
                <button
                  className={`chip ${lang === 'en' ? 'active' : ''}`}
                  onClick={() => setLang('en')}
                >
                  English
                </button>
              </div>
            </div>
            {voiceOn && (
              <button
                className="btn btn-soft btn-sm btn-block"
                style={{ marginTop: 12 }}
                onClick={() => sayRaw(
                  t('नमस्ते! मैं पवन की आवाज़ हूँ। मैं हर कदम पर आपकी मदद करूँगा।',
                    'Hello! I am the PAVHAN voice guide. I will help you at every step.'),
                )}
              >
                🔊 {t('आवाज़ जाँचिए', 'Test the voice')}
              </button>
            )}
          </div>

          {status && (
            <div className="card">
              <div style={{ fontWeight: 700, fontSize: 13.5, marginBottom: 10 }} lang={lang}>
                ⚙️ {t('कौन सा इंजन चल रहा है', 'Which engines are live')}
              </div>
              {[
                [t('विवरण लिखना', 'Listing copy'), status.llm_model],
                [t('फोटो पढ़ना', 'Image understanding'), status.vision],
                [t('आवाज़ से लिखना', 'Speech to text'), status.speech_to_text],
                [t('ज्ञात शिल्प', 'Crafts known'), status.crafts_known],
                [t('बोलने की भाषाएँ', 'Spoken languages'), langCount || '—'],
                [t('दाम का मॉडल', 'Pricing model'),
                 modelCard?.available ? `${modelCard.metrics.median_abs_pct}% median error` : '—'],
              ].map(([label, value]) => (
                <div
                  key={label}
                  className="row-between"
                  style={{ fontSize: 12, padding: '7px 0', borderTop: '1px solid var(--line)' }}
                >
                  <span className="muted">{label}</span>
                  <span className="mono" style={{ fontWeight: 600 }}>{value}</span>
                </div>
              ))}
              <div className="muted" style={{ fontSize: 10.5, lineHeight: 1.55, marginTop: 9 }} lang={lang}>
                {status.llm === 'claude'
                  ? t('Claude API जुड़ा है — विवरण और फोटो दोनों उसी से पढ़े जा रहे हैं।',
                       'Claude API is connected — copy and image understanding both run through it.')
                  : t('बिना किसी API key के चल रहा है। ANTHROPIC_API_KEY डालते ही Claude अपने आप जुड़ जाएगा।',
                       'Running fully on-device with no API key. Set ANTHROPIC_API_KEY and Claude is used automatically.')}
              </div>
            </div>
          )}

          {stats && (
            <div className="card tinted row" style={{ gap: 14 }}>
              {[
                [stats.artisans, t('कारीगर', 'artisans')],
                [stats.products, t('सामान', 'listings')],
                [stats.regions_covered, t('क्षेत्र', 'clusters')],
              ].map(([n, label]) => (
                <div key={label} style={{ flex: 1 }}>
                  <div className="mono" style={{ fontSize: 17, fontWeight: 800 }}>{n}</div>
                  <div className="muted" style={{ fontSize: 9.5, textTransform: 'uppercase' }}>{label}</div>
                </div>
              ))}
            </div>
          )}

          <button
            className="btn btn-ghost btn-block"
            onClick={() => { localStorage.removeItem('pavhan.session.v1'); window.location.href = '/' }}
          >
            {t('शुरू से शुरू कीजिए', 'Start over')}
          </button>

          <div className="center muted" style={{ fontSize: 10.5, lineHeight: 1.7, paddingTop: 6 }}>
            PAVHAN · AI-Powered Growth for Artisan Craft<br />
            Smart India Hackathon · PS 26090
          </div>
        </div>
      </Screen>
    </>
  )
}
