/**
 * Transliteration checks, run by `./run.sh test`.
 *
 * Plain node, no framework: this is one pure function and it does not deserve
 * a dependency. What it does deserve is a test, because on every machine with
 * no Hindi voice installed — which is most of them — this function is the
 * only reason the artisan hears anything at all.
 *
 *     node src/lib/devanagari.test.mjs
 */
import { hasDevanagari, hasIndicVoice, toLatin } from './devanagari.js'

let failed = 0
const is = (name, got, want) => {
  const pass = got === want
  if (!pass) failed += 1
  console.log(`  ${pass ? 'PASS' : 'FAIL'}  ${name}`)
  if (!pass) console.log(`        got  "${got}"\n        want "${want}"`)
}
const ok = (name, cond, detail = '') => {
  if (!cond) failed += 1
  console.log(`  ${cond ? 'PASS' : 'FAIL'}  ${name}${detail ? ` — ${detail}` : ''}`)
}

console.log('\n[Devanagari to Roman, so Hindi can be spoken without a Hindi voice]')

// The word-final inherent vowel is not pronounced. Getting this wrong is what
// makes a transliterator sound like a robot reading Sanskrit.
is('the word-final schwa is dropped', toLatin('राम'), 'raam')
is('a danda does not resurrect it', toLatin('क्लीन।'), 'kleen.')
is('nor does a comma', toLatin('कारीगर,'), 'kaareegar,')

// Three-syllable words drop the middle one too: अपने is "apne", not "apane".
is('the middle schwa goes in a three-syllable word', toLatin('अपने'), 'apne')
is('but a compound keeps it', toLatin('चित्रकला'), 'chitrakalaa')

// Conjuncts, matras, nukta consonants.
is('conjuncts have no vowel between them', toLatin('स्वागत'), 'swaagat')
is('nukta consonants are not their bare forms', toLatin('ज़री'), 'zaree')
is('anusvara becomes n', toLatin('रंग'), 'rang')

// Numbers, currency and Latin words must survive untouched: an artisan who
// hears the wrong price is worse off than one who hears none.
is('digits and currency pass through',
   toLatin('कीमत ₹4,249 रुपये।'), 'keemat ₹4,249 rupaye.')
is('Latin words are left alone', toLatin('आपके UPI में'), 'aapke UPI mein')
is('an all-English string is untouched',
   toLatin('Your listing is live'), 'Your listing is live')

// The lines a judge will actually hear.
is('the welcome line',
   toLatin('स्वागत है आपका पावहन में।'), 'swaagat hai aapka pavhan mein.')
ok('a full sentence comes out readable',
   toLatin('यह वाराणसी में हाथ से बनी है। कीमत 4249 रुपये।')
     === 'yeh vaaraanasee mein haath se banee hai. keemat 4249 rupaye.',
   toLatin('यह वाराणसी में हाथ से बनी है। कीमत 4249 रुपये।'))

// Nothing may come out still carrying Devanagari — that is the whole point.
const samples = [
  'स्वागत है आपका पावहन में, जहाँ हम सिर्फ़ आपसे सामान नहीं लेंगे बल्कि आपको पैसे भी देंगे।',
  'अब अपने सामान की फोटो लीजिए। दिन की रोशनी में, सादे कपड़े पर रखकर।',
  'केवल ड्राई क्लीन। सूती कपड़े में लपेटकर रखें और कुछ महीनों में तह बदलें।',
  'आपको नया ऑर्डर मिला है। ₹52,000 आपके UPI में भेज दिया।',
  'यह वाराणसी की बनारसी रेशम है, जिसे पारंपरिक हस्तकला तकनीक से बनाया गया है।',
  'मिलकर आप 42 दिनों में लगभग 409 पीस दे सकते हैं।',
]
const leftover = samples.filter((s) => hasDevanagari(toLatin(s)))
ok('no Devanagari survives transliteration', leftover.length === 0,
   leftover[0] ? toLatin(leftover[0]) : `${samples.length} sentences`)
const empty = samples.filter((s) => !toLatin(s).trim())
ok('nothing transliterates to silence', empty.length === 0)

console.log('\n[choosing a voice]')
ok('a Hindi voice is recognised',
   hasIndicVoice([{ name: 'Google हिन्दी', lang: 'hi-IN' }]))
ok('a Marathi voice counts too — it reads the same script',
   hasIndicVoice([{ name: 'Marathi India', lang: 'mr-IN' }]))
ok('English-only is correctly reported as having no Indic voice',
   !hasIndicVoice([{ name: 'Microsoft Heera - English (India)', lang: 'en-IN' },
                   { name: 'David', lang: 'en-US' }]))
ok('no voices at all is handled', !hasIndicVoice([]) && !hasIndicVoice(null))

console.log(`\n  ${failed ? `${failed} failed` : 'all transliteration checks passed'}\n`)
process.exit(failed ? 1 : 0)
