/**
 * Choosing the best voice on the device, not merely the first one that matches.
 *
 * `getVoices()` returns an unordered pile, and on a real machine the gap
 * between the entries is enormous. A Chrome Android device commonly offers
 * both "Google हिन्दी" — a neural voice that sounds like a person — and an
 * eSpeak Hindi voice that sounds like a 1998 answering machine. Taking the
 * first `hi-IN` match is a coin toss between them, and on the demo laptop
 * where it matters it lands on the wrong one.
 *
 * So every candidate is scored. The scores encode what is actually true about
 * these engines today:
 *
 *   - Neural / cloud voices (Google's, Microsoft's "Natural" and "Online"
 *     ranges, Apple's "Premium" and "Enhanced") are in a different league to
 *     anything local and older.
 *   - eSpeak and Espeak-NG are the fallback of last resort on Linux and some
 *     Android builds. They are intelligible and nothing more, and they should
 *     never win while a real voice exists.
 *   - For Hindi, `hi-IN` beats every other tag. For the romanised fallback,
 *     `en-IN` beats `en-GB` beats `en-US` — an Indian-English voice says
 *     "kaareegar" and "rupaye" close to right, and an American one does not.
 */

// Engines, best first. The number is a bonus, not a rank, so a great engine
// on the wrong language still loses to a poor engine on the right one.
const ENGINE_BONUS = [
  [/google/i, 60],
  [/natural|neural/i, 58],
  [/\bonline\b|\(natural\)/i, 55],
  [/premium|enhanced/i, 50],
  [/microsoft/i, 30],
  [/apple|siri/i, 30],
  [/samsung|bixby/i, 25],
]

// Named Hindi and Indian-English voices that are known to be the good ones.
const GOOD_NAMES = [
  [/स्वरा|swara/i, 40],      // Microsoft neural Hindi, female
  [/मधुर|madhur/i, 38],      // Microsoft neural Hindi, male
  [/हिन्दी|हिंदी/i, 35],       // Google's Hindi voice announces itself in Hindi
  [/neerja/i, 34],           // Microsoft neural Indian English, female
  [/prabhat/i, 32],          // Microsoft neural Indian English, male
  [/heera|kalpana/i, 22],    // older Microsoft Indian voices, still decent
  [/ravi|hemant/i, 20],
  [/lekha|rishi|veena/i, 20], // Apple Indian voices
]

// Anything here is a last resort.
const PENALTY = [
  [/espeak|e-speak/i, -80],
  [/compact/i, -25],
  [/\bpico\b/i, -40],
]

function score(voice, want) {
  const tag = `${voice.lang || ''}`.toLowerCase().replace('_', '-')
  const name = `${voice.name || ''}`
  let points = 0

  // --- language, which dominates everything else --------------------------
  if (want === 'hi') {
    if (tag.startsWith('hi-in') || tag === 'hi') points += 1000
    else if (tag.startsWith('hi')) points += 950
    // Other Devanagari languages can read the script, just less naturally.
    else if (/^(mr|ne|sa)/.test(tag)) points += 700
    else return -1                       // cannot read the script at all
  } else {
    if (tag.startsWith('en-in')) points += 1000
    else if (tag.startsWith('en-gb')) points += 820
    else if (tag.startsWith('en-au') || tag.startsWith('en-za')) points += 760
    else if (tag.startsWith('en')) points += 740
    else return -1
  }

  for (const [pattern, bonus] of ENGINE_BONUS) if (pattern.test(name)) { points += bonus; break }
  for (const [pattern, bonus] of GOOD_NAMES) if (pattern.test(name)) { points += bonus; break }
  for (const [pattern, malus] of PENALTY) if (malus && pattern.test(name)) points += malus

  // A non-local voice is a cloud/neural one on every engine that reports it.
  if (voice.localService === false) points += 25
  // Ties broken towards whatever the platform itself considers default.
  if (voice.default) points += 5

  return points
}

/** Every usable voice for a language, best first. */
export function rankVoices(voices, want) {
  return (voices || [])
    .map((voice) => ({ voice, points: score(voice, want) }))
    .filter((row) => row.points >= 0)
    .sort((a, b) => b.points - a.points)
    .map((row) => row.voice)
}

/**
 * The voice to speak with, and whether the text has to be romanised first.
 *
 * Returned together because the two decisions are one decision: a device with
 * no Devanagari-capable voice needs both an English voice *and* romanised
 * text, and letting those be chosen separately is how they drift apart.
 */
export function chooseVoice(voices, want, preferred = '') {
  // A person's ear beats any scoring table. When they have picked a voice on
  // this device, and it is still installed, it wins outright — accent is a
  // matter of taste and of which engine happens to be on the machine, and
  // neither is something this file can know better than the listener.
  if (preferred) {
    const chosen = (voices || []).find((v) => v.name === preferred)
    if (chosen) {
      const tag = `${chosen.lang || ''}`.toLowerCase().replace('_', '-')
      const indic = /^(hi|mr|ne|sa)/.test(tag)
      return {
        voice: chosen,
        romanise: want === 'hi' && !indic,
        quality: describe(chosen),
        picked: true,
      }
    }
  }

  if (want === 'hi') {
    const indic = rankVoices(voices, 'hi')
    if (indic.length) {
      return { voice: indic[0], romanise: false, quality: describe(indic[0]) }
    }
    const english = rankVoices(voices, 'en')
    return {
      voice: english[0] || null,
      romanise: true,
      quality: english[0] ? describe(english[0]) : 'none',
    }
  }
  const english = rankVoices(voices, 'en')
  return { voice: english[0] || null, romanise: false,
           quality: english[0] ? describe(english[0]) : 'none' }
}

/**
 * Every voice worth offering the listener, best first.
 *
 * Both the Devanagari-capable voices and the Indian-English ones, because on
 * a machine with no Hindi voice the English list is the only choice there is
 * — and an artisan who prefers one Indian-English voice to another should be
 * able to say so.
 */
export function offerableVoices(voices) {
  const indic = rankVoices(voices, 'hi')
  const english = rankVoices(voices, 'en').filter((v) => {
    const tag = `${v.lang || ''}`.toLowerCase()
    // Only Indian and neutral-sounding English. A US voice reading romanised
    // Hindi is the thing this whole feature exists to avoid.
    return tag.startsWith('en-in') || tag.startsWith('en-gb')
  })
  const seen = new Set()
  return [...indic, ...english].filter((v) => {
    if (seen.has(v.name)) return false
    seen.add(v.name)
    return true
  }).map((v) => ({
    name: v.name,
    lang: v.lang,
    quality: describe(v),
    readsHindi: /^(hi|mr|ne|sa)/.test(`${v.lang || ''}`.toLowerCase()),
  }))
}

/** A one-word verdict on a voice, for the diagnostic screen. */
export function describe(voice) {
  const name = voice?.name || ''
  if (/espeak|pico|compact/i.test(name)) return 'basic'
  if (/google|natural|neural|online|premium|enhanced/i.test(name)) return 'natural'
  if (voice?.localService === false) return 'natural'
  return 'standard'
}
