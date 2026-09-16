import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useApp } from '../context/AppContext'
import { Screen, TopBar } from '../components/Shell'
import { VoiceOrb } from '../components/ui'
import useSpeechRecognition from '../hooks/useSpeechRecognition'
import { askAssistant, assistantSuggestions } from '../api/client'

/**
 * The chat surface for the business manager.
 *
 * Deliberately not a general chatbot: every reply comes from an intent that
 * was resolved against this artisan's real catalogue, so "what have I earned"
 * returns their actual number and "how do I photograph this" returns the
 * three rules that matter. When an answer maps to a screen, the reply carries
 * a button that goes there — an assistant that can only talk is a help page
 * with extra steps.
 */
export default function Assistant() {
  const navigate = useNavigate()
  const { t, lang, user, voiceOn, sayRaw, assistant, toast } = useApp()
  const [messages, setMessages] = useState([])
  const [input, setInput] = useState('')
  const [chips, setChips] = useState([])
  const [busy, setBusy] = useState(false)
  const endRef = useRef(null)
  const greeted = useRef(false)

  const mic = useSpeechRecognition({
    lang,
    onFinal: (text) => { if (text.trim()) send(text.trim()) },
  })

  useEffect(() => {
    assistantSuggestions(lang).then((d) => setChips(d.suggestions || [])).catch(() => {})
  }, [lang])

  useEffect(() => {
    if (greeted.current) return
    greeted.current = true
    const hello = t(
      'नमस्ते! मैं पवन हूँ, आपका बिज़नेस मैनेजर। कुछ भी पूछिए — अपने दाम, अपनी कमाई, '
      + 'फोटो कैसे लें, या जीआई क्या होता है।',
      "Namaste. I am PAVHAN, your business manager. Ask me anything — your prices, "
      + 'your earnings, how to photograph a piece, or what a GI tag means.',
    )
    setMessages([{ who: 'bot', text: hello }])
    if (voiceOn) setTimeout(() => sayRaw(hello), 500)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => { endRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [messages, busy])

  const send = async (raw) => {
    const question = (raw ?? input).trim()
    if (!question || busy) return
    mic.stop()
    setInput('')
    mic.reset()
    setMessages((m) => [...m, { who: 'me', text: question }])
    setBusy(true)
    try {
      const reply = await askAssistant(question, lang, user?.id)
      setMessages((m) => [...m, {
        who: 'bot', text: reply.text, action: reply.action,
        actionLabel: reply.action_label, intent: reply.intent, data: reply.data,
      }])
      if (reply.suggestions?.length) setChips(reply.suggestions)
      if (voiceOn) sayRaw(reply.text)
    } catch (err) {
      toast(err.message, 'err')
      setMessages((m) => [...m, {
        who: 'bot',
        text: t('अभी जवाब नहीं ला पाया। दोबारा पूछिए।',
                'I could not fetch that just now. Please ask again.'),
      }])
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <TopBar
        title={t('पवन सहायक', 'PAVHAN Assistant')}
        subtitle={t('आपका बिज़नेस मैनेजर', 'Your business manager')}
        back
      />
      <Screen>
        <div className="page stack" style={{ gap: 12 }}>
          {messages.map((m, i) => (
            <div
              key={i}
              className="fade-up"
              style={{ display: 'flex', justifyContent: m.who === 'me' ? 'flex-end' : 'flex-start' }}
            >
              <div
                style={{
                  maxWidth: '86%',
                  background: m.who === 'me' ? 'var(--ink)' : 'var(--card)',
                  color: m.who === 'me' ? '#fff' : 'var(--ink)',
                  border: m.who === 'me' ? 'none' : '1px solid var(--line)',
                  borderRadius: m.who === 'me' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                  padding: '12px 14px', fontSize: 'calc(13.5px * var(--font-scale))', lineHeight: 1.7,
                  boxShadow: 'var(--shadow-1)',
                }}
                lang={lang}
              >
                {m.who === 'bot' && (
                  <div style={{ fontSize: 'calc(10.5px * var(--font-scale))', fontWeight: 700, color: 'var(--madder)',
                                marginBottom: 5, letterSpacing: '0.04em' }}>
                    🪡 PAVHAN
                  </div>
                )}
                {m.text}
                {m.action && (
                  <button
                    className="btn btn-gold btn-sm btn-block"
                    style={{ marginTop: 10 }}
                    onClick={() => navigate(m.action)}
                  >
                    {m.actionLabel} →
                  </button>
                )}
              </div>
            </div>
          ))}

          {busy && (
            <div style={{ display: 'flex', justifyContent: 'flex-start' }}>
              <div className="card" style={{ padding: '12px 16px' }}>
                <span className="spinner dark" />
              </div>
            </div>
          )}
          <div ref={endRef} />

          {chips.length > 0 && !busy && (
            <div className="chiprow" style={{ marginTop: 4 }}>
              {chips.map((c) => (
                <button key={c} className="chip" onClick={() => send(c)} lang={lang}>{c}</button>
              ))}
            </div>
          )}
        </div>

        {/* composer */}
        <div
          style={{
            position: 'sticky', bottom: 0, background: 'var(--paper)',
            borderTop: '1px solid var(--line)', padding: '10px 14px',
          }}
        >
          {mic.listening && (
            <div className="center muted" style={{ fontSize: 'calc(11.5px * var(--font-scale))', marginBottom: 7 }} lang={lang}>
              {mic.interim || t('सुन रहा हूँ…', 'Listening…')}
            </div>
          )}
          <div className="row" style={{ gap: 8 }}>
            <input
              className="input"
              lang={lang}
              value={input}
              placeholder={t('कुछ भी पूछिए…', 'Ask me anything…')}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => e.key === 'Enter' && send()}
              style={{ flex: 1 }}
            />
            <button
              onClick={() => (mic.listening ? mic.stop() : mic.start({ reset: true }))}
              aria-label={t('बोलकर पूछिए', 'Ask by voice')}
              style={{
                width: 46, height: 46, borderRadius: 13, border: 0, flexShrink: 0,
                background: mic.listening ? 'var(--madder)' : 'var(--paper-2)',
                color: mic.listening ? '#fff' : 'var(--ink)', fontSize: 'calc(19px * var(--font-scale))',
                animation: mic.listening ? 'pulseRing 1.5s infinite' : 'none',
              }}
            >
              {mic.listening ? '⏹' : '🎙️'}
            </button>
            <button
              className="btn btn-primary"
              onClick={() => send()}
              disabled={!input.trim() || busy}
              style={{ width: 46, height: 46, padding: 0, flexShrink: 0 }}
              aria-label={t('भेजिए', 'Send')}
            >
              ➤
            </button>
          </div>
          {mic.error && (
            <div className="muted" style={{ fontSize: 'calc(11px * var(--font-scale))', lineHeight: 1.5, marginTop: 7 }} lang={lang}>
              {mic.error}
            </div>
          )}
        </div>
        <VoiceOrb text={messages[messages.length - 1]?.who === 'bot'
          ? messages[messages.length - 1].text : null} />
      </Screen>
    </>
  )
}
