/**
 * Voice choice, number reading and chunking — run by `./run.sh test`.
 *
 * Between them these three decide whether the Hindi guide sounds like a
 * person or like a fault, and none of them needs a browser to check.
 */
import { MAX_CHUNK, chunkForSpeech } from './speech.js'
import { chooseVoice, describe, rankVoices } from './voices.js'
import { speakNumbersInHindi, toHindiWords } from './hindiNumbers.js'

let failed = 0
const is = (name, got, want) => {
  const pass = got === want
  if (!pass) failed += 1
  console.log(`  ${pass ? 'PASS' : 'FAIL'}  ${name}`)
  if (!pass) console.log(`        got  ${JSON.stringify(got)}\n        want ${JSON.stringify(want)}`)
}
const ok = (name, cond, detail = '') => {
  if (!cond) failed += 1
  console.log(`  ${cond ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`)
}

console.log('\n[choosing the best voice, not the first one that matches]')

// The case that matters: a device carrying both a neural voice and eSpeak.
const android = [
  { name: 'eSpeak hindi', lang: 'hi', localService: true },
  { name: 'Google हिन्दी', lang: 'hi-IN', localService: false },
  { name: 'Google UK English Female', lang: 'en-GB', localService: false },
]
is('a neural Hindi voice beats eSpeak on the same device',
   chooseVoice(android, 'hi').voice.name, 'Google हिन्दी')
is('and is reported as natural quality', describe(chooseVoice(android, 'hi').voice), 'natural')

const windows = [
  { name: 'Microsoft Kalpana - Hindi (India)', lang: 'hi-IN', localService: true, default: true },
  { name: 'Microsoft Swara Online (Natural) - Hindi (India)', lang: 'hi-IN', localService: false },
]
is('a neural voice beats the platform default',
   chooseVoice(windows, 'hi').voice.name,
   'Microsoft Swara Online (Natural) - Hindi (India)')

const noHindi = [
  { name: 'Microsoft David - English (United States)', lang: 'en-US', localService: true, default: true },
  { name: 'Microsoft Heera - English (India)', lang: 'en-IN', localService: true },
]
const fallback = chooseVoice(noHindi, 'hi')
is('with no Hindi voice, Indian English wins over American',
   fallback.voice.name, 'Microsoft Heera - English (India)')
ok('and the text is marked for romanising', fallback.romanise === true)

ok('a Hindi-capable device is not asked to romanise',
   chooseVoice(android, 'hi').romanise === false)
ok('Marathi counts as Devanagari-capable',
   chooseVoice([{ name: 'Marathi India', lang: 'mr-IN' }], 'hi').romanise === false)
ok('eSpeak still wins over silence when it is all there is',
   chooseVoice([{ name: 'espeak-ng hindi', lang: 'hi' }], 'hi').voice.name === 'espeak-ng hindi')
is('and is honest about being basic', describe({ name: 'espeak-ng hindi', lang: 'hi' }), 'basic')
ok('no voices at all is handled', chooseVoice([], 'hi').voice === null)
ok('a voice that cannot read the script is never offered for Hindi',
   rankVoices([{ name: 'David', lang: 'en-US' }], 'hi').length === 0)

console.log('\n[numbers, as a Hindi speaker says them]')
is('the irregular fifties', toHindiWords(52), 'baavan')
is('the irregular forties', toHindiWords(49), 'unchaas')
is('hundreds', toHindiWords(250), 'do sau pachaas')
is('a price', toHindiWords(4249), 'chaar hazaar do sau unchaas')
is('Indian grouping, not thousands', toHindiWords(185000), 'ek laakh pachaasee hazaar')
is('zero', toHindiWords(0), 'shoonya')

is('a price inside a sentence becomes words',
   speakNumbersInHindi('keemat 4249 rupaye'), 'keemat chaar hazaar do sau unchaas rupaye')
is('comma grouping is money, so it is read as money',
   speakNumbersInHindi('52,000 bhej diyaa'), 'baavan hazaar bhej diyaa')

// The other half of the rule, and the more important one: a pincode read as
// a quantity is wrong in a way that sends a parcel to the wrong state.
is('a pincode is left as digits',
   speakNumbersInHindi('pincode 221001 hai'), 'pincode 221001 hai')
is('a tracking number is left alone',
   speakNumbersInHindi('tracking EB238558441IN'), 'tracking EB238558441IN')
is('a leading zero means an identifier, not a count',
   speakNumbersInHindi('order 0042 hai'), 'order 0042 hai')

console.log('\n[chunking, which is a repair and should happen as rarely as possible]')

// Splitting is audible. Every seam is a place the voice restarts, so the
// first thing to assert is that ordinary speech is NOT split: a chatbot
// answer, a product line and the welcome greeting all have to come out as
// one unbroken utterance. Over-eager chunking is what made the guide sound
// like it was being read one line at a time.
const oneUtterance = {
  'a chatbot answer': 'पावहन बिक्री का सिर्फ़ 5% रखता है, और इसके अलावा कोई कटौती नहीं है। '
    + 'यह हर सामान के पन्ने पर लिखा होता है, खरीदार को भी दिखता है।',
  'a product line': 'यह वाराणसी में हाथ से बनी है। कीमत 4249 रुपये।',
  'the welcome greeting': 'स्वागत है आपका पावहन में। यहाँ हम आपसे सिर्फ़ सामान नहीं लेंगे, '
    + 'आपको उसका पूरा दाम भी दिलाएँगे। आप बस बोलिए — फोटो खींचिए और बोलकर बता दीजिए कि '
    + 'यह क्या है, किस चीज़ से बना है, और कितने दिन लगे। बाकी सब मैं कर दूँगा।',
}
for (const [what, text] of Object.entries(oneUtterance)) {
  ok(`${what} is spoken in one piece`, chunkForSpeech(text).length === 1,
     `${text.length} chars`)
}

// Only genuinely long passages are split, because past Chrome's window the
// alternative is not hearing the end at all.
const greeting = Object.values(oneUtterance).join(' ')
const pieces = chunkForSpeech(greeting)
ok('a passage past the limit is split rather than truncated',
   pieces.length >= 2, `${greeting.length} chars → ${pieces.length} pieces`)
ok('no piece is long enough for Chrome to truncate',
   pieces.every((p) => p.length <= MAX_CHUNK),
   `longest ${Math.max(...pieces.map((p) => p.length))} of ${MAX_CHUNK}`)
is('nothing is lost in the split',
   pieces.join(' ').replace(/\s+/g, ''), greeting.replace(/\s+/g, ''))
ok('it breaks at sentence ends, not mid-clause',
   pieces.slice(0, -1).every((p) => /[।.!?]$/.test(p)), pieces[0])

is('a short line is left as one piece', chunkForSpeech('नमस्ते।').length, 1)
is('empty text produces nothing to say', chunkForSpeech('').length, 0)
ok('a single sentence with no punctuation still gets cut safely', (() => {
  const wall = 'shabd '.repeat(80)
  const parts = chunkForSpeech(wall)
  return parts.every((p) => p.length <= MAX_CHUNK) && !parts.some((p) => /shab$|shabd[a-z]/.test(p))
})(), 'never mid-word')

console.log(`\n  ${failed ? `${failed} failed` : 'all speech checks passed'}\n`)
process.exit(failed ? 1 : 0)
